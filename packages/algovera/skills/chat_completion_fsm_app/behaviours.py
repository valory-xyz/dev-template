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

import random
import time
from abc import ABC
from typing import Generator, Set, Type, cast

from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)

from packages.algovera.skills.chat_completion_fsm_app.models import Params
from packages.algovera.skills.chat_completion_fsm_app.rounds import (
    SynchronizedData,
    LLMChatCompletionAbciApp,
    CollectRandomnessRound,
    ProcessRequestRound,
    PublishResponseRound,
    RegistrationRound,
    SelectKeeperRound,
    WaitForRequestRound,
)
from packages.algovera.skills.chat_completion_fsm_app.rounds import (
    CollectRandomnessPayload,
    ProcessRequestPayload,
    PublishResponsePayload,
    RegistrationPayload,
    SelectKeeperPayload,
    WaitForRequestPayload,
)

from langchain.callbacks import get_openai_callback


class LLMChatCompletionBaseBehaviour(BaseBehaviour, ABC):
    """Base behaviour for the chat_completion_fsm_app skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)


class RegistrationBehaviour(LLMChatCompletionBaseBehaviour):
    """RegistrationBehaviour"""

    matching_round: Type[AbstractRound] = RegistrationRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""
        payload = RegistrationPayload(sender=self.context.agent_address)
        self.context.logger.info(f"Sending registration payload: {payload}.")
        yield from self.send_a2a_transaction(payload)
        yield from self.wait_until_round_end()
        self.set_done()


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
            self.context.logger.info(f"Retrieved DRAND values: {observation}.")
            payload = CollectRandomnessPayload(
                self.context.agent_address,
                observation["round"],
                observation["randomness"],
            )
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()
            self.set_done()
        else:
            self.context.logger.error(
                f"Could not get randomness from {self.context.randomness_api.api_id}"
            )
            yield from self.sleep(self.params.sleep_time)
            self.context.randomness_api.increment_retries()


class SelectKeeperBehaviour(LLMChatCompletionBaseBehaviour):
    """SelectKeeperBehaviour"""

    matching_round: Type[AbstractRound] = SelectKeeperRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""
        participants = sorted(self.synchronized_data.participants)
        random.seed(self.synchronized_data.most_voted_randomness, 2)  # nosec
        index = random.randint(0, len(participants) - 1)  # nosec

        keeper_address = participants[index]

        self.context.logger.info(f"Selected a new keeper: {keeper_address}.")
        payload = SelectKeeperPayload(self.context.agent_address, keeper_address)

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
            self.context.logger.info("Waiting for a request.")
            self.context.interact_rabbitmq.start()
            self.context.interact_rabbitmq.wait_for_request()
            request = self.context.interact_rabbitmq.request

            self.context.logger.info(f"Received a request: {request}.")
            request_received_at = str(time.time())
            payload = WaitForRequestPayload(self.context.agent_address, request_received_at=request_received_at)
            self.context.interact_rabbitmq.stop()
        else:
            payload = WaitForRequestPayload(self.context.agent_address)

        yield from self.send_a2a_transaction(payload)
        yield from self.wait_until_round_end()
        self.set_done()


class ProcessRequestBehaviour(LLMChatCompletionBaseBehaviour):
    """ProcessRequestBehaviour"""

    matching_round: Type[AbstractRound] = ProcessRequestRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""
        if (
            self.context.agent_address
            == self.synchronized_data.most_voted_keeper_address
        ):
            request = self.context.interact_rabbitmq.request
            self.context.logger.info(f"Processing request: {request}.")
 
            with get_openai_callback() as cb:
                response = self.context.chat_completion(request["request"])

            self.context.interact_rabbitmq.response = response
            self.context.logger.info(f"Processed request: {response}.")
            payload = ProcessRequestPayload(
                self.context.agent_address, 
                request_id=request["id"],
                request=request["request"],
                response=response,
                total_tokens=cb.total_tokens,
                total_cost=cb.total_cost,           
                request_processed_at=str(time.time()),
            )
        else:
            payload = ProcessRequestPayload(self.context.agent_address)


        yield from self.send_a2a_transaction(payload)
        yield from self.wait_until_round_end()
        self.set_done()

class PublishResponseBehaviour(LLMChatCompletionBaseBehaviour):
    """PublishResponseBehaviour"""

    matching_round: Type[AbstractRound] = PublishResponseRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""
        if (
            self.context.agent_address
            == self.synchronized_data.most_voted_keeper_address
        ):
            publish_data = self.context.interact_rabbitmq.request
            publish_data["response"] = self.context.interact_rabbitmq.response

            # Start SQL
            self.context.interact_rabbitmq.start()
            self.context.interact_rabbitmq.enqueue_response(**publish_data)

            self.context.logger.info(f"Publishing response: {publish_data}.")
            payload = PublishResponsePayload(
                self.context.agent_address, 
                request_published_at=str(time.time()),
            )
        else:
            payload = PublishResponsePayload(
                self.context.agent_address,
                request_published_at=str(time.time()),
            )

        yield from self.send_a2a_transaction(payload)
        yield from self.wait_until_round_end()
        self.set_done()


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
