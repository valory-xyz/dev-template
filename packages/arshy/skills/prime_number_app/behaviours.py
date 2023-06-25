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

"""This package contains round behaviours of HelloWorldLLMCallAbciApp."""
import math
import random
from abc import ABC
from typing import Generator, Set, Type, cast

from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)

from packages.arshy.skills.prime_number_app.models import Params
from packages.arshy.skills.prime_number_app.rounds import (
    SynchronizedData,
    PrimeNumberAbciApp,
    CollectRandomnessRound,
    LLMCallandPrintMessageRound,
    RegistrationRound,
    ResetAndPauseRound,
    SelectKeeperRound,
)
from packages.arshy.skills.prime_number_app.rounds import (
    CollectRandomnessPayload,
    LLMCallandPrintMessagePayload,
    RegistrationPayload,
    ResetAndPausePayload,
    SelectKeeperPayload,
)
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)


def is_prime(number):
    if number < 2:
        return False
    for i in range(2, int(math.sqrt(number)) + 1):
        if number % i == 0:
            return False
    return True

def generate_random_prime(start=1, end=1_000_1000):
    while True:
        random_number = random.randint(start, end)
        if is_prime(random_number):
            return random_number

system_template = """
You are an AI agent. 
Given a prime number, you have to write something interesting about the prime number.
You do not have repeat it is a prime number. Or say why it is a prime number.
"""

human_template = """{prime_number}"""

PROMPT = ChatPromptTemplate.from_messages(
    [
    SystemMessagePromptTemplate.from_template(system_template), 
    HumanMessagePromptTemplate.from_template(human_template)
    ]
)
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
chain = LLMChain(llm=llm, prompt=PROMPT)

def generate_message(prime_number):
    return chain.predict(prime_number=prime_number)


class PrimeNumberBaseBehaviour(BaseBehaviour, ABC):
    """Base behaviour for the hello_world_llm_call skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)


class RegistrationBehaviour(PrimeNumberBaseBehaviour):
    """RegistrationBehaviour"""

    matching_round: Type[AbstractRound] = RegistrationRound

    # TODO: implement logic required to set payload content for synchronization
    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""


        payload = RegistrationPayload(sender=self.context.agent_address)
        yield from self.send_a2a_transaction(payload)
        yield from self.wait_until_round_end()
        self.set_done()


class CollectRandomnessBehaviour(PrimeNumberBaseBehaviour):
    """CollectRandomnessBehaviour"""

    matching_round: Type[AbstractRound] = CollectRandomnessRound

    def async_act(self) -> Generator:
        """
        Check whether tendermint is running or not.

        Steps:
        - Do a http request to the tendermint health check endpoint
        - Retry until healthcheck passes or timeout is hit.
        - If healthcheck passes set done event.
        """
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

    def clean_up(self) -> None:
        """
        Clean up the resources due to a 'stop' event.

        It can be optionally implemented by the concrete classes.
        """
        self.context.randomness_api.reset_retries()


class SelectKeeperBehaviour(PrimeNumberBaseBehaviour):
    """SelectKeeperBehaviour"""

    matching_round: Type[AbstractRound] = SelectKeeperRound

    def async_act(self) -> Generator:
        """
        Do the action.

        Steps:
        - Select a keeper randomly.
        - Send the transaction with the keeper and wait for it to be mined.
        - Wait until ABCI application transitions to the next round.
        - Go to the next behaviour (set done event).
        """

        participants = sorted(self.synchronized_data.participants)
        random.seed(self.synchronized_data.most_voted_randomness, 2)  # nosec
        index = random.randint(0, len(participants) - 1)  # nosec

        keeper_address = participants[index]

        self.context.logger.info(f"Selected a new keeper: {keeper_address}.")
        payload = SelectKeeperPayload(self.context.agent_address, keeper_address)

        yield from self.send_a2a_transaction(payload)
        yield from self.wait_until_round_end()

        self.set_done()


class LLMCallandPrintMessageBehaviour(PrimeNumberBaseBehaviour):
    """LLMCallandPrintMessageBehaviour"""

    matching_round: Type[AbstractRound] = LLMCallandPrintMessageRound

    def async_act(self) -> Generator:
        """
        Do the action.

        Steps:
        - Determine if this agent is the current keeper agent.
        - Print the appropriate to the local console.
        - Send the transaction with the printed message and wait for it to be mined.
        - Wait until ABCI application transitions to the next round.
        - Go to the next behaviour (set done event).
        """

        if (
            self.context.agent_address
            == self.synchronized_data.most_voted_keeper_address
        ):
            prime_number = generate_random_prime(1, 1_000_000)
            message = generate_message(prime_number)

        else:
            message = ":|"

        printed_message = f"Agent {self.context.agent_name} (address {self.context.agent_address}) in period {self.synchronized_data.period_count} says: {message}"
        self.context.logger.info(f"printed_message={printed_message}")

        payload = LLMCallandPrintMessagePayload(self.context.agent_address, printed_message)

        yield from self.send_a2a_transaction(payload)
        yield from self.wait_until_round_end()
        self.set_done()


class ResetAndPauseBehaviour(PrimeNumberBaseBehaviour):
    """ResetAndPauseBehaviour"""

    matching_round: Type[AbstractRound] = ResetAndPauseRound
    pause = True
    def async_act(self) -> Generator:
        """
        Do the action.

        Steps:
        - Trivially log the behaviour.
        - Sleep for configured interval.
        - Build a registration transaction.
        - Send the transaction and wait for it to be mined.
        - Wait until ABCI application transitions to the next round.
        - Go to the next behaviour (set done event).
        """
        if self.pause:
            self.context.logger.info("Period end.")
            yield from self.sleep(self.params.reset_pause_duration)
        else:
            self.context.logger.info(
                f"Period {self.synchronized_data.period_count} was not finished. Resetting!"
            )

        payload = ResetAndPausePayload(
            self.context.agent_address, self.synchronized_data.period_count
        )

        yield from self.send_a2a_transaction(payload)
        yield from self.wait_until_round_end()
        self.set_done()


class PrimeNumberRoundBehaviour(AbstractRoundBehaviour):
    """HelloWorldLLMCallRoundBehaviour"""

    initial_behaviour_cls = RegistrationBehaviour
    abci_app_cls = PrimeNumberAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [
        CollectRandomnessBehaviour,
        LLMCallandPrintMessageBehaviour,
        RegistrationBehaviour,
        ResetAndPauseBehaviour,
        SelectKeeperBehaviour
    ]