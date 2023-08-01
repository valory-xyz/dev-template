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

"""This package contains round behaviours of ChatCompletionAbciApp."""

import json
import time
from abc import ABC
from typing import Dict, Generator, List, Optional, Set, Type, Union, cast

from packages.algovera.connections.chat_completion.connection import (
    PUBLIC_ID as CHAT_COMPLETION_PUBLIC_ID,
)
from packages.algovera.protocols.chat_completion.dialogues import (
    ChatCompletionDialogue,
    ChatCompletionDialogues,
)
from packages.algovera.protocols.chat_completion.message import ChatCompletionMessage
from packages.algovera.skills.chat_completion_abci.models import Params, Requests
from packages.algovera.skills.chat_completion_abci.rounds import (
    ChatCompletionAbciApp,
    ChatPayload,
    ChatRound,
    EmbeddingPayload,
    EmbeddingRound,
    RegistrationPayload,
    RegistrationRound,
    SynchronizeEmbeddingsPayload,
    SynchronizeEmbeddingsRound,
    SynchronizeRequestsPayload,
    SynchronizeRequestsRound,
    SynchronizedData,
)
from packages.algovera.skills.chat_completion_abci.schemas import (
    Chat,
    ChatCompletion,
    Embedding,
)
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)
from packages.valory.skills.abstract_round_abci.io_.store import SupportedFiletype


class ChatCompletionBaseBehaviour(BaseBehaviour, ABC):
    """Base behaviour for the chat_completion_abci skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)


class ChatBehaviour(ChatCompletionBaseBehaviour):
    """ChatBehaviour"""

    matching_round: Type[AbstractRound] = ChatRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            # Get the embedding_requests from the synchronized data
            requests: List = self.synchronized_data.chats
            self.context.logger.info(f"All Requests {requests}")

            # Get the request from the synchronized data matching the agent address if doesnt exist, None
            request = next(
                (
                    request
                    for request in requests
                    if request["processed"] == False
                    if request["processor"] == self.context.agent_address
                ),
                None,
            )

            # If there is a request process the request
            if request:
                if request["request_type"] == "chat":
                    request = Chat.parse_obj(request)

                    # Get c2e
                    context_id = request.context_id
                    context = [
                        context
                        for context in self.synchronized_data.embeddings
                        if context["id"] == context_id
                    ][0]
                    c2e_ipfs_hash = context["c2e_ipfs_hash"]

                    # Get c2e
                    c2e = yield from self.get_from_ipfs(
                        c2e_ipfs_hash, SupportedFiletype.JSON
                    )
                    c2e = c2e[f"{request.context_id}_c2e.json"]

                elif request["request_type"] == "chat_completion":
                    request = ChatCompletion.parse_obj(request)
                    c2e = None

                self.context.logger.info(f"Processing request {request}")
                processed_request = yield from self.process_request(request, c2e)

                # Process the request
                processed_response = self.process_response(
                    processed_request.response, request
                )
                self.context.logger.info(f"Processed Response {processed_response}")

                # Prepare payload
                payload = ChatPayload(
                    sender=self.context.agent_address,
                    processed_chat=json.dumps(dict(processed_response)),
                )

            else:
                self.context.logger.info(f"No request to process")

                # Prepare payload
                payload = ChatPayload(
                    sender=self.context.agent_address,
                    processed_chat="",
                )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def process_request(
        self,
        chat: Union[Chat, ChatCompletion],
        c2e: Optional[Dict] = None,
        timeout: Optional[float] = None,
    ) -> Generator:
        chat_completion_dialogues = cast(
            ChatCompletionDialogues, self.context.chat_completion_dialogues
        )
        """Get Request Package and make a request to the chat_completion skill"""

        # Prepare request package based on request type
        if type(chat) == Chat:
            self.context.logger.info(f"Processing chat request {chat}")
            request_package = self.prepare_chat(chat=chat, c2e=c2e)

        if type(chat) == ChatCompletion:
            self.context.logger.info(f"Processing chat_completion request {chat}")
            request_package = self.prepare_cc(chat=chat)

        # chat completion request
        (
            request_chat_completion_message,
            chat_completion_dialogue,
        ) = chat_completion_dialogues.create(
            counterparty=str(CHAT_COMPLETION_PUBLIC_ID),
            performative=ChatCompletionMessage.Performative.REQUEST,
            request={
                "request": json.dumps(request_package),
            },
        )
        request_chat_completion_message = cast(
            ChatCompletionMessage, request_chat_completion_message
        )
        chat_completion_dialogue = cast(
            ChatCompletionDialogue, chat_completion_dialogue
        )
        self.context.outbox.put_message(message=request_chat_completion_message)

        # wait for chat completion response
        request_nonce = self._get_request_nonce_from_dialogue(chat_completion_dialogue)
        cast(Requests, self.context.requests).request_id_to_callback[
            request_nonce
        ] = self.get_callback_request()
        response = yield from self.wait_for_message(timeout=timeout)
        return response

    def process_response(self, response: Dict, request: Union[Chat, ChatCompletion]):
        """Process the response from the chat_completion skill"""

        if type(request) == Chat:
            if response["error"] == "False":
                self.context.logger.info(f"Processing chat response {response}")
                chat_history = response["chat_history"]
                answer = response["response"]
                query = response["modified_query"]

                if query != request.question:
                    request.modified_question = query

                request.chat_history = chat_history
                request.response = answer
                request.processed = True
                request.processor = self.context.agent_address
                request.response_time = str(time.time())

            else:
                request.processed = True
                request.processor = self.context.agent_address
                request.response_time = str(time.time())
                request.error = response["error"]
                request.error_message = response["error_message"]
                request.error_name = response["error_name"]

            return request

        if type(request) == ChatCompletion:
            if response["error"] == "False":
                request.response = response["response"]
                request.response_time = str(time.time())
                request.processed = True
                request.processor = self.context.agent_address
            else:
                request.processed = True
                request.processor = self.context.agent_address
                request.response_time = str(time.time())
                request.error = response["error"]
                request.error_message = response["error_message"]
                request.error_name = response["error_name"]

            return request

    def prepare_chat(self, chat: Chat, c2e: Dict) -> Dict:
        """Prepare the request package for the chat skill"""

        # Get chat_history
        memory_id = chat.memory_id

        # Check if memory is empty
        try:
            chat_history = self.synchronized_data.chat_histories[memory_id]
            self.context.logger.info(f"Retrieved chat history {chat_history}")
        except KeyError:
            chat_history = []

        # Retrieve relevant context
        request_package = {
            "question": chat.question,
            "chat_history": chat_history,
            "chunks_to_embeddings": c2e,
            "request_type": "chat",
        }
        return request_package

    def prepare_cc(self, chat: ChatCompletion):
        """Prepare the request package for the chat_completion skill"""

        request_package = {
            "system_message": chat.system_message,
            "user_message": chat.user_message,
            "request_type": "chat_completion",
        }

        return request_package


class EmbeddingBehaviour(ChatCompletionBaseBehaviour):
    """EmbeddingBehaviour"""

    matching_round: Type[AbstractRound] = EmbeddingRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            # Get the embedding_requests from the synchronized data
            requests: list = self.synchronized_data.embeddings
            self.context.logger.info(f"Requests {requests}")

            # Get the next request to process for the current agent if processed is False
            request = next(
                (
                    request
                    for request in requests
                    if request["processed"] == False
                    and request["processor"] == self.context.agent_address
                ),
                None,
            )

            if request:
                # If there is a request process the request
                request = Embedding.parse_obj(request)
                self.context.logger.info(f"Processing request {request}")

                # Process the request
                processed_request = yield from self.process_request(request)
                processed_response, c2e = self.process_response(
                    processed_request.response, request
                )
                self.context.logger.info(f"Response {processed_response}")

                # Add c2e to IPFS
                if c2e:
                    filename = f"{processed_response.id}_c2e.json"
                    ipfs_hash = yield from self.send_to_ipfs(
                        filename,
                        {filename: json.loads(c2e)},
                        filetype=SupportedFiletype.JSON,
                    )

                    # Add the IPFS hash to the processed request
                    processed_response.c2e_ipfs_hash = ipfs_hash

                # Create payload
                payload = EmbeddingPayload(
                    sender=self.context.agent_address,
                    processed_embedding=json.dumps(dict(processed_response)),
                )

            else:
                self.context.logger.info(f"No request to process")
                payload = EmbeddingPayload(
                    sender=self.context.agent_address,
                    processed_embedding="",
                )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def process_request(
        self, embedding_request: Embedding, timeout: Optional[float] = None
    ) -> Generator:
        """Process the request."""

        chat_completion_dialogues = cast(
            ChatCompletionDialogues, self.context.chat_completion_dialogues
        )

        # Prepare for embedding request
        file_content = embedding_request.file["content"]
        chunks = self.split_text_overlap(file_content)

        request_package = {"chunks": chunks, "request_type": "embedding"}

        # chat completion request
        (
            request_chat_completion_message,
            chat_completion_dialogue,
        ) = chat_completion_dialogues.create(
            counterparty=str(CHAT_COMPLETION_PUBLIC_ID),
            performative=ChatCompletionMessage.Performative.REQUEST,
            request={
                "request": json.dumps(request_package),
            },
        )
        request_chat_completion_message = cast(
            ChatCompletionMessage, request_chat_completion_message
        )

        chat_completion_dialogue = cast(
            ChatCompletionDialogue, chat_completion_dialogue
        )
        self.context.outbox.put_message(message=request_chat_completion_message)

        # wait for chat completion response
        request_nonce = self._get_request_nonce_from_dialogue(chat_completion_dialogue)

        cast(Requests, self.context.requests).request_id_to_callback[
            request_nonce
        ] = self.get_callback_request()

        response = yield from self.wait_for_message(timeout=timeout)

        return response

    def process_response(self, response: dict, embedding_request: Embedding):
        """Process the response from the chat skill"""

        if response["error"] == "False":
            chunks_to_embeddings = response["chunks_to_embeddings"]
            embedding_request.processed = True
            embedding_request.processor = self.context.agent_address
            embedding_request.error = False
            embedding_request.response_time = str(time.time())
            embedding_request.file = {}

        else:
            embedding_request.processed = True
            embedding_request.processor = self.context.agent_address
            embedding_request.response_time = str(time.time())
            embedding_request.error = response["error"]
            embedding_request.error_message = response["error_message"]
            embedding_request.error_name = response["error_name"]
            embedding_request.file = {}
            chunks_to_embeddings = None

        return embedding_request, chunks_to_embeddings

    def split_text_overlap(self, text, max_chunk_size=1200, chunk_overlap=100):
        words = text.split(" ")
        chunks = []
        current_chunk = ""

        for word in words:
            if len(current_chunk) + len(word) <= max_chunk_size:
                current_chunk += " " + word
            else:
                chunks.append(current_chunk)
                current_chunk = (
                    " ".join(current_chunk.split(" ")[-chunk_overlap:]) + " " + word
                )
        chunks.append(current_chunk)
        return chunks


class RegistrationBehaviour(ChatCompletionBaseBehaviour):
    """RegistrationBehaviour"""

    matching_round: Type[AbstractRound] = RegistrationRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            payload = RegistrationPayload(sender=sender)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class SynchronizeEmbeddingsBehaviour(ChatCompletionBaseBehaviour):
    """SynchronizeEmbeddingsBehaviour"""

    matching_round: Type[AbstractRound] = SynchronizeEmbeddingsRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            # Check if there are new embedding requests
            if self.context.state.new_embedding_requests:
                new_embedding_requests = json.dumps(
                    self.context.state.new_embedding_requests
                )
                self.context.state.new_embedding_requests = []
            else:
                new_embedding_requests = None

            # Create payload
            pl = {}
            if new_embedding_requests:
                pl["new_embedding_requests"] = new_embedding_requests

            sender = self.context.agent_address
            payload = SynchronizeEmbeddingsPayload(sender=sender, **pl)
            self.context.logger.info(
                f"New embedding requests = {new_embedding_requests}"
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class SynchronizeRequestsBehaviour(ChatCompletionBaseBehaviour):
    """SynchronizeRequestsBehaviour"""

    matching_round: Type[AbstractRound] = SynchronizeRequestsRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            # Check if there are new embedding requests
            if self.context.state.new_chat_requests:
                new_chat_requests = json.dumps(self.context.state.new_chat_requests)
                self.context.state.new_chat_requests = []
            else:
                new_chat_requests = None

            # Create payload
            pl = {}
            if new_chat_requests:
                pl["new_chat_requests"] = new_chat_requests

            sender = self.context.agent_address
            payload = SynchronizeRequestsPayload(sender=sender, **pl)
            self.context.logger.info(f"New chat requests = {new_chat_requests}")

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class ChatCompletionRoundBehaviour(AbstractRoundBehaviour):
    """ChatCompletionRoundBehaviour"""

    initial_behaviour_cls = RegistrationBehaviour
    abci_app_cls = ChatCompletionAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [
        ChatBehaviour,
        EmbeddingBehaviour,
        RegistrationBehaviour,
        SynchronizeEmbeddingsBehaviour,
        SynchronizeRequestsBehaviour,
    ]
