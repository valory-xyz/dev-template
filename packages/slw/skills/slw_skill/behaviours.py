# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2022 Valory AG
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

"""This package contains round behaviours of SlwWorldAbciApp."""

from abc import abstractmethod
from typing import Generator, Set, Type, cast

from packages.slw.skills.slw_skill.models import Params, SharedState
from packages.slw.skills.slw_skill.payloads import (
    GetDataPayload,
    PrintResultPayload,
    ProcessDataPayload,
    RegistrationPayload,
    ResetAndPausePayload,
    SelectKeeperPayload,
)
from packages.slw.skills.slw_skill.rounds import (
    GetDataRound,
    PrintResultRound,
    ProcessDataRound,
    RegistrationRound,
    ResetAndPauseRound,
    SelectKeeperRound,
    SlwWorldAbciApp,
    SynchronizedData,
)
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)


class SlwWorldBaseBehaviour(BaseBehaviour):
    """Base behaviour for the common apps' skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(
            SynchronizedData, cast(SharedState, self.context.state).synchronized_data
        )


class GetDataBehaviour(SlwWorldBaseBehaviour):
    """GetDataBehaviour"""

    # TODO: set the following class attributes
    state_id: str
    behaviour_id: str = "get_data"
    matching_round: Type[AbstractRound] = GetDataRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""
        http_message, http_dialogue = self._build_http_request_message(
            method="GET",
            url="https://www.random.org/integers/?num=1&min=1&max=3&col=1&base=10&format=plain&rnd=new",
        )
        response = yield from self._do_request(http_message, http_dialogue)
        data = response.body
        payload = GetDataPayload(self.context.agent_address, init_data=data)
        yield from self.send_a2a_transaction(payload)
        yield from self.wait_until_round_end()
        self.set_done()


class ProcessDataBehaviour(SlwWorldBaseBehaviour):
    """ProcessDataBehaviour"""

    # TODO: set the following class attributes
    state_id: str
    behaviour_id: str = "process_data"
    matching_round: Type[AbstractRound] = ProcessDataRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""
        data = self.synchronized_data.init_data
        data = int(data) * 2
        payload = ProcessDataPayload(
            self.context.agent_address, processed_data=f"{data}".encode("utf-8")
        )
        yield from self.send_a2a_transaction(payload)
        yield from self.wait_until_round_end()
        self.set_done()


class PrintResultBehaviour(SlwWorldBaseBehaviour):
    """
    PrintResultBehaviour

    Only keeper prints and send message.
    """

    state_id: str
    behaviour_id: str = "print_result"
    matching_round: Type[AbstractRound] = PrintResultRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""
        printed_data = f"printed: {self.synchronized_data.processed_data}"
        if (
            self.context.agent_address
            == self.synchronized_data.most_voted_keeper_address
        ):
            self.context.logger.info(f"PRINT: {printed_data}")
            payload = PrintResultPayload(
                self.context.agent_address, printed_data=printed_data
            )
            yield from self.send_a2a_transaction(payload)
        yield from self.wait_until_round_end()
        self.set_done()


class RegistrationBehaviour(SlwWorldBaseBehaviour):
    """RegistrationBehaviour"""

    # TODO: set the following class attributes
    state_id: str
    behaviour_id: str = "registration"
    matching_round: Type[AbstractRound] = RegistrationRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""
        payload = RegistrationPayload(self.context.agent_address)
        yield from self.send_a2a_transaction(payload)
        yield from self.wait_until_round_end()
        self.set_done()


class ResetAndPauseBehaviour(SlwWorldBaseBehaviour):
    """ResetAndPauseBehaviour"""

    # TODO: set the following class attributes
    state_id: str
    behaviour_id: str = "reset_and_pause"
    matching_round: Type[AbstractRound] = ResetAndPauseRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""
        self.context.logger.info("Period end.")
        yield from self.sleep(self.params.observation_interval)

        payload = ResetAndPausePayload(
            self.context.agent_address, self.synchronized_data.period_count
        )

        yield from self.send_a2a_transaction(payload)
        yield from self.wait_until_round_end()
        self.set_done()


class SelectKeeperBehaviour(SlwWorldBaseBehaviour):
    """SelectKeeperBehaviour"""

    # TODO: set the following class attributes
    state_id: str
    behaviour_id: str = "select_keeper"
    matching_round: Type[AbstractRound] = SelectKeeperRound

    def async_act(self) -> Generator:
        keeper_address = sorted(self.synchronized_data.participants)[
            self.synchronized_data.period_count % self.synchronized_data.nb_participants
        ]

        self.context.logger.info(f"Selected a new keeper: {keeper_address}.")
        payload = SelectKeeperPayload(self.context.agent_address, keeper_address)

        yield from self.send_a2a_transaction(payload)
        yield from self.wait_until_round_end()

        self.set_done()


class SlwWorldRoundBehaviour(AbstractRoundBehaviour):
    """SlwWorldRoundBehaviour"""

    initial_behaviour_cls = RegistrationBehaviour
    abci_app_cls = SlwWorldAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [
        GetDataBehaviour,
        PrintResultBehaviour,
        ProcessDataBehaviour,
        RegistrationBehaviour,
        ResetAndPauseBehaviour,
        SelectKeeperBehaviour,
    ]
