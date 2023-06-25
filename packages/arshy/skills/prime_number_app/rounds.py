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

"""This package contains the rounds of HelloWorldLLMCallAbciApp."""

from abc import ABC
from enum import Enum
from re import A
from typing import Dict, List, Optional, Set, Tuple, cast, Type

from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AbstractRound,
    AppState,
    BaseSynchronizedData,
    DegenerateRound,
    EventToTimeout,
    CollectSameUntilAllRound,
    CollectSameUntilThresholdRound,
    CollectDifferentUntilAllRound,
    get_name,
)

from packages.arshy.skills.prime_number_app.payloads import (
    CollectRandomnessPayload,
    LLMCallandPrintMessagePayload,
    RegistrationPayload,
    ResetAndPausePayload,
    SelectKeeperPayload,
)


class Event(Enum):
    """HelloWorldLLMCallAbciApp Events"""

    ROUND_TIMEOUT = "round_timeout"
    DONE = "done"
    RESET_TIMEOUT = "reset_timeout"
    NO_MAJORITY = "no_majority"


class SynchronizedData(BaseSynchronizedData):
    """
    Class to represent the synchronized data.

    This data is replicated by the tendermint application.
    """
    @property
    def printed_messages(self) -> List[str]:
        """Get the printed messages list."""

        return cast(
            List[str],
            self.db.get_strict("printed_messages"),
        )


class PrimeNumberABCIAbstractRound(AbstractRound, ABC):
    synchronized_data_class: Type[BaseSynchronizedData] = SynchronizedData

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, self._synchronized_data)


class RegistrationRound(CollectSameUntilAllRound, PrimeNumberABCIAbstractRound):
    """RegistrationRound"""
    payload_class = RegistrationPayload

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        if self.collection_threshold_reached:
            synchronized_data = self.synchronized_data.update(
                participants=tuple(sorted(self.collection)),
                synchronized_data_class=SynchronizedData,
            )
            return synchronized_data, Event.DONE
        return None


class CollectRandomnessRound(CollectSameUntilThresholdRound, PrimeNumberABCIAbstractRound):
    """CollectRandomnessRound"""

    payload_class = CollectRandomnessPayload
    synchronized_data_class = SynchronizedData
    no_majority_event = Event.NO_MAJORITY
    done_event = Event.DONE
    collection_key = get_name(SynchronizedData.participant_to_randomness)
    selection_key = get_name(SynchronizedData.most_voted_randomness)


class SelectKeeperRound(CollectSameUntilThresholdRound, PrimeNumberABCIAbstractRound):
    """SelectKeeperRound"""

    payload_class = SelectKeeperPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = get_name(SynchronizedData.participant_to_selection)
    selection_key = get_name(SynchronizedData.most_voted_keeper_address)


class LLMCallandPrintMessageRound(CollectDifferentUntilAllRound, PrimeNumberABCIAbstractRound):
    """LLMCallandPrintMessageRound"""

    payload_class = LLMCallandPrintMessagePayload

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Event]]:
        """Process the end of the block."""
        if self.collection_threshold_reached:
            synchronized_data = self.synchronized_data.update(
                participants=tuple(sorted(self.collection)),
                printed_messages=sorted(
                    [
                        cast(LLMCallandPrintMessagePayload, payload).message
                        for payload in self.collection.values()
                    ]
                ),
                synchronized_data_class=SynchronizedData,
            )
            return synchronized_data, Event.DONE
        return None


class ResetAndPauseRound(CollectSameUntilThresholdRound, PrimeNumberABCIAbstractRound):
    """ResetAndPauseRound"""

    payload_class = ResetAndPausePayload

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        if self.threshold_reached:
            # TODO `cross_period_persisted_keys` should be used here instead
            synchronized_data = self.synchronized_data.create(
                participants=[tuple(sorted(self.synchronized_data.participants))],
                all_participants=[
                    tuple(sorted(self.synchronized_data.all_participants))
                ],
            )
            return synchronized_data, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.synchronized_data.nb_participants
        ):
            return self.synchronized_data, Event.NO_MAJORITY
        return None


class PrimeNumberAbciApp(AbciApp[Event]):

    initial_round_cls: AppState = RegistrationRound
    initial_states: Set[AppState] = {RegistrationRound}
    transition_function: AbciAppTransitionFunction = {
        CollectRandomnessRound: {
            Event.DONE: SelectKeeperRound,
            Event.NO_MAJORITY: CollectRandomnessRound,
            Event.ROUND_TIMEOUT: CollectRandomnessRound
        },
        LLMCallandPrintMessageRound: {
            Event.DONE: ResetAndPauseRound,
            Event.ROUND_TIMEOUT: RegistrationRound
        },
        RegistrationRound: {
            Event.DONE: CollectRandomnessRound
        },
        ResetAndPauseRound: {
            Event.DONE: CollectRandomnessRound,
            Event.NO_MAJORITY: RegistrationRound,
            Event.RESET_TIMEOUT: RegistrationRound
        },
        SelectKeeperRound: {
            Event.DONE: LLMCallandPrintMessageRound,
            Event.NO_MAJORITY: RegistrationRound,
            Event.ROUND_TIMEOUT: RegistrationRound
        }
    }
    final_states: Set[AppState] = set()
    event_to_timeout: EventToTimeout = {}
    cross_period_persisted_keys: Set[str] = []
    db_pre_conditions: Dict[AppState, Set[str]] = {
        RegistrationRound: [],
    }
    db_post_conditions: Dict[AppState, Set[str]] = {

    }
