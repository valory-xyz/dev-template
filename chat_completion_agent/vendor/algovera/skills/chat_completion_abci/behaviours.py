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
from abc import ABC
import time
from typing import Generator, Set, Type, cast, Optional

from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)

from packages.algovera.skills.chat_completion_abci.models import Params, Requests
from packages.algovera.skills.chat_completion_abci.rounds import (
    SynchronizedData,
    ChatCompletionAbciApp,
    ProcessRequestRound,
    RegistrationRound,
    SynchronizeRequestsRound,
)
from packages.algovera.skills.chat_completion_abci.rounds import (
    ProcessRequestPayload,
    RegistrationPayload,
    SynchronizeRequestsPayload,
)
from packages.algovera.connections.chat_completion.connection import (
    PUBLIC_ID as CHAT_COMPLETION_PUBLIC_ID,
)
from packages.algovera.protocols.chat_completion.dialogues import (
    ChatCompletionDialogue,
    ChatCompletionDialogues,
)
from packages.algovera.protocols.chat_completion.message import ChatCompletionMessage

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


class ProcessRequestBehaviour(ChatCompletionBaseBehaviour):
    """ProcessRequestBehaviour"""

    matching_round: Type[AbstractRound] = ProcessRequestRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            
            # Get the request from the synchronized data
            requests: list = self.synchronized_data.requests
            self.context.logger.info(f"Requests {requests}")

            # Get the request from the synchronized data matching the agent address if doesnt exist, None
            request = next((request for request in requests if request["processor"] == self.context.agent_address), None)

            # If there is a request process the request
            if request:
                self.context.logger.info(f"Processing request {request}")

                # Process the request
                response = yield from self._process_request(request)
                response = response.response
                self.context.logger.info(f"Response {response}")
                
                if response["error"] == "False":
                    # Add additional information to the response
                    response["processed"] = True
                    response["processor"] = self.context.agent_address
                    response["request_time"] = request["request_time"]
                    response["response_time"] = str(time.time())

                    response.pop("error", None)
                    response.pop("error_message", None)
                    response.pop("error_class", None)
                    
                    self.context.logger.info(f"Adding response {response} to synchronized data")

                    # Prepare the payload
                    payload = ProcessRequestPayload(sender=self.context.agent_address, response=json.dumps([response]))

                else:
                    # Update the request with num_tries
                    request["num_tries"] += 1

                    # Prepare the payload
                    payload = ProcessRequestPayload(
                        sender=self.context.agent_address, 
                        failed_request=json.dumps(request), 
                        response=json.dumps([])
                    )
            
            else:
                self.context.logger.info(f"No request to process")
                payload = ProcessRequestPayload(sender=self.context.agent_address, response=json.dumps([]))

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _process_request(self, request, timeout: Optional[float] = None):
        """Process the request and return the address of the keeper."""
        self.context.logger.info(
            f"Sending LLM request...\nRequest ID: {request['id']}\nSystemMessage: {request['system_message']}\nUserMessage: {request['user_message']}"
        )
        chat_completion_dialogues = cast(
            ChatCompletionDialogues, self.context.chat_completion_dialogues
        )

        # chat completion request
        (
            request_chat_completion_message,
            chat_completion_dialogue,
        ) = chat_completion_dialogues.create(
            counterparty=str(CHAT_COMPLETION_PUBLIC_ID),
            performative=ChatCompletionMessage.Performative.REQUEST,
            request={
                "id": request["id"],
                "system_message": request["system_message"],
                "user_message": request["user_message"],
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


class SynchronizeRequestsBehaviour(ChatCompletionBaseBehaviour):
    """SynchronizeRequestsBehaviour"""

    matching_round: Type[AbstractRound] = SynchronizeRequestsRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            new_requests = json.dumps(
                self.context.state.new_requests
            )  
            self.context.state.new_requests = []

            sender = self.context.agent_address
            payload = SynchronizeRequestsPayload(
                sender=sender, 
                new_requests=new_requests
            )
            self.context.logger.info(f"New requests = {new_requests}")

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class ChatCompletionRoundBehaviour(AbstractRoundBehaviour):
    """ChatCompletionRoundBehaviour"""

    initial_behaviour_cls = RegistrationBehaviour
    abci_app_cls = ChatCompletionAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [
        ProcessRequestBehaviour,
        RegistrationBehaviour,
        SynchronizeRequestsBehaviour
    ]
