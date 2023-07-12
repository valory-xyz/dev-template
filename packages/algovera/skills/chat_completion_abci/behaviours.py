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

"""This package contains round behaviours of LLMChatCompletionAbciApp."""
from os import system
import re
import time
import random
from abc import ABC
from typing import Generator, Type, cast, Optional, Set

from aea.protocols.base import Address
from daios.packages.algovera.protocols import chat_completion
from daios.packages.algovera.protocols.chat_completion.dialogues import ChatCompletionDialogue

from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)

from packages.algovera.skills.chat_completion_abci.models import Params, Requests
from packages.algovera.skills.chat_completion_abci.rounds import (
    SynchronizedData,
    LLMChatCompletionAbciApp,
    CollectRandomnessRound,
    ProcessRequestRound,
    PublishResponseRound,
    RegistrationRound,
    SelectKeeperRound,
    WaitForRequestRound,
)
from packages.algovera.skills.chat_completion_abci.rounds import (
    CollectRandomnessPayload,
    ProcessRequestPayload,
    PublishResponsePayload,
    RegistrationPayload,
    SelectKeeperPayload,
    WaitForRequestPayload,
)

from packages.algovera.protocols.rabbitmq.dialogues import RabbitMQDialogue, RabbitMQDialogues
from packages.algovera.protocols.rabbitmq.message import RabbitMQMessage
from packages.algovera.protocols.chat_completion.message import ChatCompletionMessage
from packages.algovera.protocols.chat_completion.dialogues import ChatCompletionDialogue, ChatCompletionDialogues
from packages.algovera.connections.chat_completion.connection import PUBLIC_ID as CHAT_COMPLETION_PUBLIC_ID
from packages.algovera.connections.rabbitmq.connection import PUBLIC_ID as RABBITMQ_PUBLIC_ID


class LLMChatCompletionBaseBehaviour(BaseBehaviour, ABC):
    """Base behaviour for the chat_completion_abci skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)


class CollectRandomnessBehaviour(LLMChatCompletionBaseBehaviour):
    """CollectRandomnessBehaviour"""

    matching_round: Type[AbstractRound] = CollectRandomnessRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""
        if self.context.randomness_api.is_retries_exceeded():
            # now we need to wait and see if the other agents progress the round
            yield from self.wait_until_round_end()
            self.set_done()
            return

        api_specs = self.context.randomness_api.get_spec()
        http_message, http_dialogue = self._build_http_request_message(
            method=api_specs["method"],
            url=api_specs["url"],
        )
        response = yield from self._do_request(http_message, http_dialogue)
        observation = self.context.randomness_api.process_response(response)
        
        if observation:
            with self.context.benchmark_tool.measure(self.behaviour_id).local():
                self.context.logger.info(f"Retrieved DRAND values: {observation}.")
                payload = CollectRandomnessPayload(
                    self.context.agent_address,
                    observation["round"],
                    observation["randomness"],
                )

            with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
                yield from self.send_a2a_transaction(payload)
                yield from self.wait_until_round_end()

            self.set_done()
        
        else:
            self.context.logger.error(
                f"Could not get randomness from {self.context.randomness_api.api_id}"
            )
            yield from self.sleep(self.params.sleep_time)
            self.context.randomness_api.increment_retries()


class ProcessRequestBehaviour(LLMChatCompletionBaseBehaviour):
    """ProcessRequestBehaviour"""

    matching_round: Type[AbstractRound] = ProcessRequestRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""
        if self.context.state.request_data:
            request = self.context.state.request_data

            self.context.logger.info(f"Processing request: {request}")
            process_response = self._process_request(request)

            if not process_response["error"]:
                self.context.state.response_data = process_response
                self.context.state.request_data = {}
                with self.context.benchmark_tool.measure(self.behaviour_id).local():
                    sender = self.context.agent_address
                    payload = ProcessRequestPayload(
                        sender=sender, 
                        request_id=process_response["id"],
                        system_message=process_response["system_message"],
                        user_message=process_response["user_message"],
                        response=process_response["response"],
                        total_tokens=process_response["total_tokens"],
                        total_cost=process_response["total_cost"],
                        request_processed_at=str(time.time()),
                        
                    )

                with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
                    yield from self.send_a2a_transaction(payload)
                    yield from self.wait_until_round_end()

                self.set_done()

    def _process_request(self, request):
        """Process the request and return the address of the keeper."""
        
        self.context.logger.info(
                f"Sending LLM request...\nRequest ID: {request['id']}\nSystemMessage: {request['system_message']}\nUserMessage: {request['user_message']}"
            )
        chat_completion_dialogues = cast(ChatCompletionDialogues, self.context.chat_completion_dialogues)

        # chat completion request
        request_chat_completion_message, chat_completion_dialogue = chat_completion_dialogues.create(
            counterparty=str(CHAT_COMPLETION_PUBLIC_ID),
            performative=ChatCompletionMessage.Performative.REQUEST,
            system_message=request["system_message"],
            user_message=request["user_message"],
        )
        request_chat_completion_message = cast(ChatCompletionMessage, request_chat_completion_message)
        chat_completion_dialogue = cast(ChatCompletionDialogue, chat_completion_dialogue)
        response = yield from self._do_request(request_chat_completion_message, chat_completion_dialogue)
        return response

    def _do_request(self, 
        request_message: ChatCompletionMessage, 
        chat_completion_dialogue: ChatCompletionDialogue, 
        timeout: Optional[float] = None
    ):
        self.context.outbox.put_message(message=request_message)
        request_nonce = self._get_request_nonce_from_dialogue(chat_completion_dialogue)
        cast(Requests, self.context.requests).request_id_to_callback[
            request_nonce
        ] = self.get_callback_request()
        # notify caller by propagating potential timeout exception.
        response = yield from self.wait_for_message(timeout=timeout)
        return response

class PublishResponseBehaviour(LLMChatCompletionBaseBehaviour):
    """PublishResponseBehaviour"""

    matching_round: Type[AbstractRound] = PublishResponseRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""
        if self.context.state.response_data:
            response_data = self.context.state.response_data

            publish_response = yield from self._publish_response(response_data)

            if publish_response["published"]:
                self.context.state.response_data = {}

                with self.context.benchmark_tool.measure(self.behaviour_id).local():
                    sender = self.context.agent_address
                    payload = PublishResponsePayload(
                        sender=sender, 
                        request_published_at=str(time.time()),
                    )

                with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
                    yield from self.send_a2a_transaction(payload)
                    yield from self.wait_until_round_end()

                self.set_done()

    def _publish_response(self, response_data, timeout: Optional[float] = None):
        """Publish the response."""
        rabbitmq_dialogues = cast(RabbitMQDialogues, self.context.rabbitmq_dialogues)
        
        rabbitmq_details = {
            "host":self.context.params.rabbitmq_host,
            "port":self.context.params.rabbitmq_port,
            "username":self.context.params.rabbitmq_username,
            "password":self.context.params.rabbitmq_password,
        }
        
        rabbitmq_messgae, rabbitmq_dialogue = rabbitmq_dialogues.create(
            counterparty=str(RABBITMQ_PUBLIC_ID),
            performative=RabbitMQMessage.Performative.PUBLISH_REQUEST,
            publish_queue_name=self.context.params.publish_queue_name,
            rabbitmq_details=rabbitmq_details,
        )

        request_message = cast(RabbitMQMessage, rabbitmq_messgae)
        rabbitmq_dialogue = cast(RabbitMQDialogue, rabbitmq_dialogue)

        self.context.outbox.put_message(message=request_message)

        request_nonce = self._get_request_nonce_from_dialogue(rabbitmq_dialogue)
        
        self.context.logger.info(f"Request nonce: {request_nonce}")
        
        cast(Requests, self.context.requests).request_id_to_callback[
            request_nonce
        ] = self.get_callback_request()

        response = yield from self.wait_for_message(timeout=timeout)
        return response

class RegistrationBehaviour(LLMChatCompletionBaseBehaviour):
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


class SelectKeeperBehaviour(LLMChatCompletionBaseBehaviour):
    """SelectKeeperBehaviour"""

    matching_round: Type[AbstractRound] = SelectKeeperRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""
        participants = sorted(self.synchronized_data.participants)
        random.seed(self.synchronized_data.most_voted_randomness, 2)  # nosec
        index = random.randint(0, len(participants) - 1)  # nosec

        keeper_address = participants[index]
        self.context.logger.info(f"Selected keeper: {keeper_address}")

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            payload = SelectKeeperPayload(sender=sender, keeper=keeper_address)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class WaitForRequestBehaviour(LLMChatCompletionBaseBehaviour):
    """WaitForRequestBehaviour"""

    matching_round: Type[AbstractRound] = WaitForRequestRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""
        if (
            self.context.agent_address
            == self.synchronized_data.most_voted_keeper_address
        ):
            with self.context.benchmark_tool.measure(self.behaviour_id).local():
                response = yield from self._consume_rabbitmq()
                self.context.logger.info(f"Received request: {response}")
                
                if response['received_request'] == True:
                    sender = self.context.agent_address
                    payload = WaitForRequestPayload(
                        sender=sender, 
                        id=response['id'], 
                        user_message=response['user_message'],
                        system_message=response['system_message'],
                        request_received_at=str(time.time()),
                    )

                    # add request data to context
                    self.context.state.request_data = response

                    with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
                        yield from self.send_a2a_transaction(payload)
                        yield from self.wait_until_round_end()

                    self.set_done()
            
    def _consume_rabbitmq(self, timeout: Optional[float]=None) -> Generator:
        """Consume a message from RabbitMQ."""
        self.context.logger.info("Waiting for request...")
        rabbitmq_dialogues = cast(RabbitMQDialogues, self.context.rabbitmq_dialogues)
        
        rabbitmq_details = {
            "host":self.context.params.rabbitmq_host,
            "port":self.context.params.rabbitmq_port,
            "username":self.context.params.rabbitmq_username,
            "password":self.context.params.rabbitmq_password,
        }
        
        rabbitmq_messgae, rabbitmq_dialogue = rabbitmq_dialogues.create(
            counterparty=str(RABBITMQ_PUBLIC_ID),
            performative=RabbitMQMessage.Performative.CONSUME_REQUEST,
            consume_queue_name=self.context.params.consume_queue_name,
            rabbitmq_details=rabbitmq_details,
        )

        request_message = cast(RabbitMQMessage, rabbitmq_messgae)
        rabbitmq_dialogue = cast(RabbitMQDialogue, rabbitmq_dialogue)

        self.context.outbox.put_message(message=request_message)

        request_nonce = self._get_request_nonce_from_dialogue(rabbitmq_dialogue)
        
        self.context.logger.info(f"Request nonce: {request_nonce}")
        
        cast(Requests, self.context.requests).request_id_to_callback[
            request_nonce
        ] = self.get_callback_request()

        response = yield from self.wait_for_message(timeout=timeout)
        return response


class LLMChatCompletionRoundBehaviour(AbstractRoundBehaviour):
    """LLMChatCompletionRoundBehaviour"""

    initial_behaviour_cls = RegistrationBehaviour
    abci_app_cls = LLMChatCompletionAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [
        CollectRandomnessBehaviour,
        ProcessRequestBehaviour,
        PublishResponseBehaviour,
        RegistrationBehaviour,
        SelectKeeperBehaviour,
        WaitForRequestBehaviour
    ]
