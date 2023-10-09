# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2023 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""This package contains the rounds of ValoryChatAbciApp."""
import json
from abc import ABC
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Set, Tuple, Type, cast

from packages.algovera.skills.valory_chat_abci.payloads import (
    ChatPayload,
    EmbeddingPayload,
    SynchronizeEmbeddingsPayload,
    SynchronizeRequestsPayload,
)
from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AbstractRound,
    AppState,
    BaseSynchronizedData,
    CollectDifferentUntilAllRound,
    CollectSameUntilAllRound,
    CollectionRound,
    DegenerateRound,
    EventToTimeout,
)


class Event(Enum):
    """ValoryChatAbciApp Events"""

    NO_REQUEST = "no_request"
    ROUND_TIMEOUT = "round_timeout"
    CHAT = "chat"
    ERROR = "error"
    EMBEDDING = "embedding"
    DONE = "done"


class SynchronizedData(BaseSynchronizedData):
    """
    Class to represent the synchronized data.

    This data is replicated by the tendermint application.
    """

    @property
    def embedding(self) -> List:
        """Return the embeddings."""
        return cast(List, self.db.get("embedding", []))

    @property
    def chats(self) -> List:
        """Return the chat."""
        return cast(List, self.db.get("chats", []))

    @property
    def chat_histories(self) -> Dict:
        """Return the memories."""
        return cast(Dict, self.db.get("chat_histories", {}))


class ValoryChatABCIAbstractRound(AbstractRound, ABC):
    synchronized_data_class: Type[BaseSynchronizedData] = SynchronizedData

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, self._synchronized_data)


def remove_duplicates(lst):
    unique_items = {}
    result = []

    for item in lst:
        item_id = item.get("id")

        if item_id is not None and item_id not in unique_items:
            # If the 'id' is not in the set, it's a new unique item
            # Add it to the result list and also to the set to track duplicates
            result.append(item)
            unique_items[item_id] = True

    return result


class ChatRound(CollectionRound, ValoryChatABCIAbstractRound):
    """ChatRound"""

    payload_class = ChatPayload
    synchronized_data_class = SynchronizedData

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""

        if len(self.collection) == len(self.synchronized_data.all_participants):
            if self.collection.values:
                all_chats = cast(SynchronizedData, self.synchronized_data).chats
                all_chat_histories = cast(
                    SynchronizedData, self.synchronized_data
                ).chat_histories
                print(f"All chat_histories: {all_chat_histories}")

                processed_chat = []
                for payload in self.collection.values():
                    if payload.json["processed_chat"] != "":
                        chat = json.loads(payload.json["processed_chat"])
                        processed_chat.append(chat)

                # remove duplicates
                processed_chat = remove_duplicates(processed_chat)
                print("processed_chat", processed_chat)

                # Processed chat to chats by replacing the old chat with the new one
                for each in processed_chat:
                    for i, chat in enumerate(all_chats):
                        if chat["id"] == each["id"]:
                            all_chats[i] = each

                # If chat, add/replace to chat_histories
                for each in processed_chat:
                    if each["request_type"] == "chat":
                        all_chat_histories[each["memory_id"]] = each["chat_history"]

                all_chats = remove_duplicates(all_chats)
                print("all_chats", all_chats)

                synchronized_data = self.synchronized_data.update(
                    chats=all_chats,
                    chat_histories=all_chat_histories,
                    synchronized_data_class=SynchronizedData,
                )
                print("synchronized_data chat", synchronized_data.chats)
                return synchronized_data, Event.DONE


class EmbeddingRound(CollectionRound, ValoryChatABCIAbstractRound):
    """EmbeddingRound"""

    payload_class = EmbeddingPayload
    synchronized_data_class = SynchronizedData

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""

        if len(self.collection) == len(self.synchronized_data.all_participants):
            if self.collection.values:
                embedding = cast(SynchronizedData, self.synchronized_data).embedding
                print(f"All embedding: {embedding}")

                processed_embeddings = []
                for payload in self.collection.values():
                    if payload.json["processed_embedding"] != "":
                        chat = json.loads(payload.json["processed_embedding"])
                        processed_embeddings.append(chat)
                print("processed_embeddings", processed_embeddings)

                # Convert set to list to be able to serialize it
                processed_embeddings = [dict(each) for each in processed_embeddings]
                processed_embeddings = list(processed_embeddings)
                print("processed_embeddings", processed_embeddings)

                # Processed chat to chats by replacing the old chat with the new one
                for each in processed_embeddings:
                    for i, embed in enumerate(embedding):
                        embedding[i] = each

                synchronized_data = self.synchronized_data.update(
                    embedding=embedding,
                    synchronized_data_class=SynchronizedData,
                )
                print("synchronized_data embedding", synchronized_data)
                return synchronized_data, Event.DONE


class SynchronizeEmbeddingsRound(CollectionRound, ValoryChatABCIAbstractRound):
    """SynchronizeEmbeddingsRound"""

    payload_class = SynchronizeEmbeddingsPayload
    synchronized_data_class = SynchronizedData

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        if len(self.collection) == len(self.synchronized_data.all_participants):
            # Get all embedding requests
            all_embedding_requests = cast(
                SynchronizedData, self.synchronized_data
            ).embedding

            # Get unprocessed embedding requests
            unprocessed_embedding_requests = [
                each for each in all_embedding_requests if not each["processed"]
            ]
            print("unprocessed_embedding_requests", unprocessed_embedding_requests)

            # Get new embedding requests
            new_embedding_requests = []
            if self.collection.values():
                for payload in self.collection.values():
                    try:
                        emb = json.loads(payload.json["new_embedding_requests"])
                        if emb:
                            for each in emb:
                                new_embedding_requests.append(each)
                    except:
                        pass

            print("new_embedding_requests", new_embedding_requests)
            # Add new requests to unprocessed requests
            if new_embedding_requests:
                unprocessed_embedding_requests.extend(new_embedding_requests)

            print("unprocessed_embedding_requests", unprocessed_embedding_requests)
            # if there are unprocessed requests, set processor
            if unprocessed_embedding_requests:
                # Sort existing requests by request_time
                unprocessed_embedding_requests.sort(key=lambda x: x["request_time"])

                num_participants = len(self.synchronized_data.all_participants)
                participants = list(self.synchronized_data.all_participants)
                for participant in range(num_participants):
                    try:
                        # Get the next request
                        next_request = unprocessed_embedding_requests[participant]
                        # Set the processor
                        next_request["processor"] = participants[participant]
                    except IndexError:
                        break

                # Merge unprocessed requests with all requests
                all_embedding_requests.extend(unprocessed_embedding_requests)

                # Convert set to list to be able to serialize it
                all_embedding_requests = [dict(each) for each in all_embedding_requests]

                # Update synchronized data
                synchronized_data = self.synchronized_data.update(
                    embedding=all_embedding_requests,
                    synchronized_data_class=SynchronizedData,
                )
                return synchronized_data, Event.EMBEDDING

            else:
                # Update synchronized data
                synchronized_data = self.synchronized_data.update(
                    embedding=all_embedding_requests,
                    synchronized_data_class=SynchronizedData,
                )
                return synchronized_data, Event.NO_REQUEST


class SynchronizeRequestsRound(CollectionRound, ValoryChatABCIAbstractRound):
    """SynchronizeRequestsRound"""

    payload_class = SynchronizeRequestsPayload
    synchronized_data_class = SynchronizedData

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        if len(self.collection) == len(self.synchronized_data.all_participants):
            # Get al chats
            all_chat_requests = cast(SynchronizedData, self.synchronized_data).chats

            # Get unprocessed chat requests
            unprocessed_chat_requests = [
                each for each in all_chat_requests if each["processed"] == False
            ]

            # Get new chat requests
            new_chat_requests = []
            if self.collection.values():
                for payload in self.collection.values():
                    try:
                        emb = json.loads(payload.json["new_chat_requests"])
                        if emb:
                            for each in emb:
                                new_chat_requests.append(each)
                    except:
                        pass

            # Make sure there are no duplicates
            new_chat_requests = remove_duplicates(new_chat_requests)

            # Add new requests to unprocessed requests
            if new_chat_requests:
                unprocessed_chat_requests.extend(new_chat_requests)

            # if there are unprocessed requests, set processor
            if unprocessed_chat_requests:
                # Sort existing requests by request_time
                unprocessed_chat_requests.sort(key=lambda x: x["request_time"])

                num_participants = len(self.synchronized_data.all_participants)
                participants = list(self.synchronized_data.all_participants)

                for participant in range(num_participants):
                    try:
                        # Get the next request
                        next_request = unprocessed_chat_requests[participant]
                        # Set the processor
                        next_request["processor"] = participants[participant]
                    except IndexError:
                        break

                # Merge unprocessed requests with all requests
                all_chat_requests.extend(unprocessed_chat_requests)

                # Convert set to list to be able to serialize it
                all_chat_requests = [dict(each) for each in all_chat_requests]

                # Update synchronized data
                synchronized_data = self.synchronized_data.update(
                    chats=all_chat_requests,
                    synchronized_data_class=SynchronizedData,
                )
                return synchronized_data, Event.CHAT

            else:
                # Update synchronized data
                synchronized_data = self.synchronized_data.update(
                    chat_requests=all_chat_requests,
                    synchronized_data_class=SynchronizedData,
                )
                return synchronized_data, Event.NO_REQUEST


class FinishedValoryChatRound(DegenerateRound, ABC):
    """FinishedValoryChatRound"""


class ValoryChatAbciApp(AbciApp[Event]):
    """ValoryChatAbciApp"""

    initial_round_cls: AppState = SynchronizeEmbeddingsRound
    initial_states: Set[AppState] = {SynchronizeEmbeddingsRound}
    transition_function: AbciAppTransitionFunction = {
        SynchronizeEmbeddingsRound: {
            Event.EMBEDDING: EmbeddingRound,
            Event.NO_REQUEST: SynchronizeRequestsRound,
            Event.ROUND_TIMEOUT: SynchronizeRequestsRound,
        },
        EmbeddingRound: {
            Event.DONE: SynchronizeRequestsRound,
            Event.ERROR: SynchronizeRequestsRound,
        },
        SynchronizeRequestsRound: {
            Event.CHAT: ChatRound,
            Event.NO_REQUEST: SynchronizeEmbeddingsRound,
            Event.ROUND_TIMEOUT: SynchronizeEmbeddingsRound,
        },
        ChatRound: {
            Event.DONE: FinishedValoryChatRound,
            Event.ERROR: SynchronizeEmbeddingsRound,
        },
        FinishedValoryChatRound: {},
    }
    final_states: Set[AppState] = {FinishedValoryChatRound}
    event_to_timeout: EventToTimeout = {}
    cross_period_persisted_keys: FrozenSet[str] = frozenset()
    db_pre_conditions: Dict[AppState, Set[str]] = {
        SynchronizeEmbeddingsRound: set(),
        EmbeddingRound: set(),
        SynchronizeRequestsRound: set(),
        ChatRound: set(),
    }
    db_post_conditions: Dict[AppState, Set[str]] = {
        SynchronizeEmbeddingsRound: set(),
        EmbeddingRound: set(),
        SynchronizeRequestsRound: set(),
        ChatRound: set(),
        FinishedValoryChatRound: set(),
    }
