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

"""This package contains the rounds of SlwWorldAbciApp."""

from abc import ABC
from enum import Enum
from types import MappingProxyType
from typing import Any, List, Optional, Set, Tuple, cast

from packages.slw.skills.slw_skill.payloads import (
    GetDataPayload,
    PrintResultPayload,
    ProcessDataPayload,
    RegistrationPayload,
    ResetAndPausePayload,
    SelectKeeperPayload,
)
from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AbstractRound,
    AppState,
    BaseSynchronizedData,
    CollectDifferentUntilAllRound,
    CollectSameUntilAllRound,
    CollectSameUntilThresholdRound,
    DegenerateRound,
    EventToTimeout,
    OnlyKeeperSendsRound,
    TransactionType,
)


class Event(Enum):
    """SlwWorldAbciApp Events"""

    ROUND_TIMEOUT = "round_timeout"
    NO_MAJORITY = "no_majority"
    RESET_TIMEOUT = "reset_timeout"
    DONE = "done"


class SynchronizedData(BaseSynchronizedData):
    """
    Class to represent the synchronized data.

    This data is replicated by the tendermint application.
    """

    @property
    def init_data(self) -> Any:
        return self.db.get_strict("init_data")

    @property
    def processed_data(self) -> Any:
        return self.db.get_strict("processed_data")

    @property
    def printed_data(self) -> Any:
        return self.db.get_strict("printed_data")


class BaseRound(AbstractRound[Event, TransactionType], ABC):
    """Abstract round for the Hello World ABCI skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, self._synchronized_data)

    def _return_no_majority_event(self) -> Tuple[SynchronizedData, Event]:
        """
        Trigger the NO_MAJORITY event.

        :return: a new synchronized data synchronized data and a NO_MAJORITY event
        """
        return self.synchronized_data, Event.NO_MAJORITY


class GetDataRound(CollectSameUntilThresholdRound, BaseRound):
    """GetDataRound"""

    # TODO: replace AbstractRound with one of CollectDifferentUntilAllRound, CollectSameUntilAllRound, CollectSameUntilThresholdRound, CollectDifferentUntilThresholdRound, OnlyKeeperSendsRound, VotingRound
    # TODO: set the following class attributes
    round_id: str = "get_data"
    allowed_tx_type = GetDataPayload.transaction_type
    payload_attribute: str = "init_data"

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process payload."""
        if self.threshold_reached:
            synchronized_data = self.synchronized_data.update(
                init_data=self.most_voted_payload,
            )
            return synchronized_data, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.synchronized_data.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class ProcessDataRound(CollectSameUntilThresholdRound, BaseRound):
    """ProcessDataRound"""

    # TODO: replace AbstractRound with one of CollectDifferentUntilAllRound, CollectSameUntilAllRound, CollectSameUntilThresholdRound, CollectDifferentUntilThresholdRound, OnlyKeeperSendsRound, VotingRound
    # TODO: set the following class attributes
    round_id: str = "process_data"
    allowed_tx_type = ProcessDataPayload.transaction_type
    payload_attribute: str = "processed_data"

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        if self.threshold_reached:
            synchronized_data = self.synchronized_data.update(
                processed_data=self.most_voted_payload,
            )
            return synchronized_data, Event.DONE
        return None


class PrintResultRound(OnlyKeeperSendsRound, BaseRound):
    """
    PrintResultRound.
    
    Only keeper sends a message
    """

    round_id: str = "print_result"
    allowed_tx_type = PrintResultPayload.transaction_type
    payload_attribute: str = "printed_data"
    payload_key: str = "printed_data"
    done_event = Event.DONE
    fail_event = Event.ROUND_TIMEOUT  # not sure it's the best event here
    
    


class RegistrationRound(CollectDifferentUntilAllRound, BaseRound):
    """A round in which the agents get registered"""

    round_id = "registration"
    allowed_tx_type = RegistrationPayload.transaction_type
    payload_attribute = "sender"

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Event]]:
        """Process the end of the block."""

        if self.collection_threshold_reached:
            synchronized_data = self.synchronized_data.update(
                participants=self.collection,
                all_participants=self.collection,
                synchronized_data_class=SynchronizedData,
            )
            return synchronized_data, Event.DONE
        return None


class ResetAndPauseRound(CollectSameUntilThresholdRound, BaseRound):
    """ResetAndPauseRound"""

    # TODO: replace AbstractRound with one of CollectDifferentUntilAllRound, CollectSameUntilAllRound, CollectSameUntilThresholdRound, CollectDifferentUntilThresholdRound, OnlyKeeperSendsRound, VotingRound
    # TODO: set the following class attributes
    round_id: str = "reset_and_pause"
    # payload_attribute: str = ResetAndPausePayload.transaction_type
    payload_attribute = "period_count"
    allowed_tx_type = ResetAndPausePayload.transaction_type

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            synchronized_data = self.synchronized_data.create(
                SynchronizedData,
                participants=[self.synchronized_data.participants],
                all_participants=[self.synchronized_data.all_participants],
            )
            return synchronized_data, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.synchronized_data.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class SelectKeeperRound(CollectSameUntilThresholdRound, BaseRound):
    """SelectKeeperRound"""

    allowed_tx_type = SelectKeeperPayload.transaction_type
    payload_attribute = "keeper"
    round_id: str = "select_keeper"

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            synchronized_data = self.synchronized_data.update(
                participant_to_selection=MappingProxyType(self.collection),
                most_voted_keeper_address=self.most_voted_payload,
            )
            return synchronized_data, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.synchronized_data.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class SlwWorldAbciApp(AbciApp[Event]):
    """SlwWorldAbciApp"""

    initial_round_cls: AppState = RegistrationRound
    initial_states: Set[AppState] = {RegistrationRound}
    transition_function: AbciAppTransitionFunction = {
        GetDataRound: {
            Event.DONE: ProcessDataRound,
            Event.ROUND_TIMEOUT: RegistrationRound,
            Event.NO_MAJORITY: GetDataRound,
        },
        ProcessDataRound: {
            Event.DONE: PrintResultRound,
            Event.ROUND_TIMEOUT: RegistrationRound,
        },
        PrintResultRound: {
            Event.DONE: ResetAndPauseRound,
            Event.ROUND_TIMEOUT: RegistrationRound,
        },
        RegistrationRound: {Event.DONE: SelectKeeperRound},
        ResetAndPauseRound: {
            Event.DONE: RegistrationRound,
            Event.NO_MAJORITY: RegistrationRound,
            Event.RESET_TIMEOUT: RegistrationRound,
        },
        SelectKeeperRound: {
            Event.DONE: GetDataRound,
            Event.NO_MAJORITY: RegistrationRound,
            Event.ROUND_TIMEOUT: RegistrationRound,
        },
    }
    final_states: Set[AppState] = set()
    event_to_timeout: EventToTimeout = {}
    cross_period_persisted_keys: List[str] = []
