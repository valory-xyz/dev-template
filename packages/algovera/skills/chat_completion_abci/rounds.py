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

"""This package contains the rounds of ChatCompletionAbciApp."""

import json
import logging
from abc import ABC
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Type, cast

from packages.algovera.skills.chat_completion_abci.payloads import (
    ProcessRequestPayload,
    RegistrationPayload,
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
    DegenerateRound,
    EventToTimeout,
)


class Event(Enum):
    """ChatCompletionAbciApp Events"""

    DONE = "done"
    ROUND_TIMEOUT = "round_timeout"
    ERROR = "error"


class SynchronizedData(BaseSynchronizedData):
    """
    Class to represent the synchronized data.

    This data is replicated by the tendermint application.
    """

    @property
    def responses(self) -> List:
        """Return the responses."""
        return cast(List, self.db.get("responses", []))

    @property
    def requests(self) -> List:
        """Return the requests."""
        return cast(List, self.db.get("requests", []))


class ChatCompletionABCIAbstractRound(AbstractRound, ABC):
    synchronized_data_class: Type[BaseSynchronizedData] = SynchronizedData

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, self._synchronized_data)


class ProcessRequestRound(
    CollectDifferentUntilAllRound, ChatCompletionABCIAbstractRound
):
    """ProcessRequestRound"""

    payload_class = ProcessRequestPayload
    synchronized_data_class = SynchronizedData

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        if len(self.collection) == len(self.synchronized_data.all_participants):
            # Get existing requests and responses
            existing_requests = self.synchronized_data.requests
            existing_responses = self.synchronized_data.responses

            # Get new responses and failed requests
            if self.collection.values():
                new_responses = set()
                failed_requests = set()
                for payload in self.collection.values():
                    res = json.loads(payload.json["response"])
                    if payload.json["failed_request"]:
                        fail = json.loads(payload.json["failed_request"])
                        failed_requests.add(fail)
                    if res:
                        new_responses.add(tuple(res[0].items()))

                new_responses = [dict(response) for response in new_responses]

                # Update failed requests in existing_requests
                failed_requests_ids = [request["id"] for request in failed_requests]
                for request in existing_requests:
                    if request["id"] in failed_requests_ids:
                        request["failed"] = True
                        request["processor"] = ""
                        request["processed"] = False

                # Remove processed requests from existing_requests and add to existing_responses
                processed_request_ids = [response["id"] for response in new_responses]
                existing_requests = [
                    request
                    for request in existing_requests
                    if request["id"] not in processed_request_ids
                ]
                existing_responses.extend(new_responses)

                # Update synchronized data with requests and responses
                synchronized_data = self.synchronized_data.update(
                    requests=existing_requests,
                    responses=existing_responses,
                    synchronized_data_class=SynchronizedData,
                )

                return synchronized_data, Event.DONE

        return None


class RegistrationRound(CollectSameUntilAllRound, ChatCompletionABCIAbstractRound):
    """RegistrationRound"""

    payload_class = RegistrationPayload

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Event]]:
        """Process the end of the block."""

        if self.collection_threshold_reached:
            synchronized_data = self.synchronized_data.update(
                participants=tuple(sorted(self.collection)),
                synchronized_data_class=SynchronizedData,
            )
            return synchronized_data, Event.DONE
        return None


class SynchronizeRequestsRound(
    CollectDifferentUntilAllRound, ChatCompletionABCIAbstractRound
):
    """SynchronizeRequestsRound"""

    payload_class = SynchronizeRequestsPayload
    synchronized_data_class = SynchronizedData

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        if self.collection_threshold_reached:
            # Get existing requests and responses
            existing_requests = cast(SynchronizedData, self.synchronized_data).requests
            existing_responses = cast(
                SynchronizedData, self.synchronized_data
            ).responses

            # Get new requests
            new_requests = set()
            if self.collection.values():
                for payload in self.collection.values():
                    p = json.loads(payload.json["new_requests"])
                    if p:
                        for each in p:
                            new_requests.add(tuple(each.items()))

            new_requests = [dict(each) for each in new_requests]

            # Convert set to list to be able to serialize it
            new_requests = list(new_requests)
            if new_requests:
                # Get IDs already in requests and responses
                existing_ids = set()
                if existing_requests:
                    for request in existing_requests:
                        existing_ids.add(request["id"])
                if existing_responses:
                    for response in existing_responses:
                        existing_ids.add(response["id"])

                # Remove IDs already in requests and responses from new requests
                new_requests = [
                    request
                    for request in new_requests
                    if request["id"] not in list(existing_ids)
                ]

            # Add new requests to existing requests
            existing_requests.extend(new_requests)

            # Remove existing requests with more than 2 num_tries
            existing_requests = [
                request for request in existing_requests if request["num_tries"] < 3
            ]

            # Sort existing requests by request_time
            existing_requests.sort(key=lambda x: x["request_time"])

            if existing_requests:
                # Assign a processor to requests
                num_participants = len(self.synchronized_data.all_participants)
                particiapnts = list(self.synchronized_data.all_participants)
                for i, request in enumerate(existing_requests):
                    if request["processor"] == "":
                        request["processor"] = particiapnts[i % num_participants]

            # Update synchronized data
            synchronized_data = self.synchronized_data.update(
                requests=existing_requests,
                synchronized_data_class=SynchronizedData,
            )
            return synchronized_data, Event.DONE

        return None


class ChatCompletionAbciApp(AbciApp[Event]):
    """ChatCompletionAbciApp"""

    initial_round_cls: AppState = RegistrationRound
    initial_states: Set[AppState] = {RegistrationRound}
    transition_function: AbciAppTransitionFunction = {
        RegistrationRound: {Event.DONE: SynchronizeRequestsRound},
        SynchronizeRequestsRound: {
            Event.DONE: ProcessRequestRound,
            Event.ERROR: SynchronizeRequestsRound,
        },
        ProcessRequestRound: {
            Event.DONE: SynchronizeRequestsRound,
            Event.ERROR: SynchronizeRequestsRound,
            Event.ROUND_TIMEOUT: SynchronizeRequestsRound,
        },
    }
    final_states: Set[AppState] = set()
    event_to_timeout: EventToTimeout = {}
    cross_period_persisted_keys: Set[str] = []
    db_pre_conditions: Dict[AppState, Set[str]] = {
        RegistrationRound: [],
    }
    db_post_conditions: Dict[AppState, Set[str]] = {}
