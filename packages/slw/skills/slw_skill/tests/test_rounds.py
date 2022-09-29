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

"""This package contains the tests for rounds of SlwWorld."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Hashable, List

import pytest

from packages.slw.skills.slw_skill.payloads import GetDataPayload
from packages.slw.skills.slw_skill.rounds import Event, GetDataRound, SynchronizedData
from packages.valory.skills.abstract_round_abci.base import BaseTxPayload
from packages.valory.skills.abstract_round_abci.test_tools.rounds import (
    BaseCollectSameUntilThresholdRoundTest,
    BaseRoundTestClass,
)


@dataclass
class RoundTestCase:
    """RoundTestCase"""

    name: str
    initial_data: Dict[str, Hashable]
    payloads: BaseTxPayload
    final_data: Dict[str, Hashable]
    event: Event
    synchronized_data_attr_checks: List[Callable] = field(default_factory=list)


MAX_PARTICIPANTS: int = 4


class BaseSlwWorldRoundTest(BaseRoundTestClass):
    """Base test class for SlwWorld rounds."""

    synchronized_data: SynchronizedData
    _synchronized_data_class = SynchronizedData
    _event_class = Event

    def run_test(self, test_case: RoundTestCase, **kwargs) -> None:
        """Run the test"""

        self.synchronized_data.update(**test_case.initial_data)

        test_round = self.round_class(
            synchronized_data=self.synchronized_data,
            consensus_params=self.consensus_params,
        )

        self._complete_run(
            self._test_round(
                test_round=test_round,
                round_payloads=test_case.payloads,
                synchronized_data_update_fn=lambda sync_data, _: sync_data.update(
                    **test_case.final_data
                ),
                synchronized_data_attr_checks=test_case.synchronized_data_attr_checks,
                exit_event=test_case.event,
                **kwargs,  # varies per BaseRoundTestClass child
            )
        )


class TestGetDataRound(BaseCollectSameUntilThresholdRoundTest, BaseSlwWorldRoundTest):
    """Tests for GetDataRound."""

    round_class = GetDataRound

    # TODO: provide test cases
    @pytest.mark.parametrize(
        "test_case, kwargs",
        [
            (
                RoundTestCase(
                    name="1",
                    initial_data={},
                    payloads={
                        0: GetDataPayload(sender="agent_1", init_data=12),
                        1: GetDataPayload(sender="agent_2", init_data=12),
                        2: GetDataPayload(sender="agent_3", init_data=12),
                        3: GetDataPayload(sender="agent_0", init_data=11),
                    },
                    final_data={"init_data": 12},
                    event=Event.DONE,
                    synchronized_data_attr_checks=[lambda x: x.init_data],
                ),
                {
                    "most_voted_payload": 12,
                },
            )
        ],
    )
    def test_run(self, test_case: RoundTestCase, kwargs: Any) -> None:
        """Run tests."""

        self.run_test(test_case, **kwargs)

