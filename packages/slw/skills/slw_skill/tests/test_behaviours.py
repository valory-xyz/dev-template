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

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Hashable, Optional, Type, cast
from unittest.mock import Mock, patch

import pytest

from packages.slw.skills.slw_skill.behaviours import (
    GetDataBehaviour,
    PrintResultBehaviour,
    ProcessDataBehaviour,
    RegistrationBehaviour,
    SlwWorldBaseBehaviour,
    SlwWorldRoundBehaviour,
)
from packages.slw.skills.slw_skill.payloads import GetDataPayload
from packages.slw.skills.slw_skill.rounds import Event, SynchronizedData
from packages.valory.skills.abstract_round_abci.base import AbciAppDB
from packages.valory.skills.abstract_round_abci.behaviours import (
    BaseBehaviour,
    make_degenerate_behaviour,
)
from packages.valory.skills.abstract_round_abci.test_tools.base import (
    FSMBehaviourBaseCase,
)


@dataclass
class BehaviourTestCase:
    """BehaviourTestCase"""

    name: str
    initial_data: Dict[str, Hashable]
    event: Event


class BaseSlwWorldTest(FSMBehaviourBaseCase):
    """Base test case."""

    path_to_skill = Path(__file__).parent.parent

    behaviour: SlwWorldRoundBehaviour
    behaviour_class: Type[SlwWorldBaseBehaviour]
    next_behaviour_class: Type[SlwWorldBaseBehaviour]
    synchronized_data: SynchronizedData
    done_event = Event.DONE

    @property
    def current_behaviour_id(self) -> str:
        """Current RoundBehaviour's behaviour id"""

        return self.behaviour.current_behaviour.behaviour_id

    def fast_forward(self, data: Optional[Dict[str, Any]] = None) -> None:
        """Fast-forward on initialization"""

        data = data if data is not None else {}
        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.behaviour_id,
            SynchronizedData(AbciAppDB(setup_data=AbciAppDB.data_to_lists(data))),
        )
        assert self.current_behaviour_id == self.behaviour_class.behaviour_id

    def complete(self, event: Event) -> None:
        """Complete test"""

        self.behaviour.act_wrapper()
        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(done_event=event)
        assert self.current_behaviour_id == self.next_behaviour_class.behaviour_id


class TestGetDataBehaviour(BaseSlwWorldTest):
    """Tests GetDataBehaviour"""

    behaviour_class: Type[BaseBehaviour] = GetDataBehaviour
    next_behaviour_class: Type[BaseBehaviour] = ProcessDataBehaviour

    def test_run(self) -> None:
        """Test get data."""
        self.fast_forward({})
        self.behaviour.act_wrapper()
        self.mock_http_request(
            request_kwargs=dict(
                method="GET",
                headers="",
                version="",
                body=b"",
                url="https://www.random.org/integers/?num=1&min=1&max=3&col=1&base=10&format=plain&rnd=new",
            ),
            response_kwargs=dict(
                version="",
                status_code=200,
                status_text="",
                headers="",
                body=b"17",
            ),
        )
        self.complete(Event.DONE)
        ### HOW TO CATCH self.send_a2a_transaction(payload) ???


class TestProcessDataBehaviour(BaseSlwWorldTest):
    """Tests ProcessDataBehaviour"""

    # TODO: set next_behaviour_class
    behaviour_class: Type[BaseBehaviour] = ProcessDataBehaviour
    next_behaviour_class: Type[BaseBehaviour] = PrintResultBehaviour

    def test_run(self) -> None:
        """Run tests."""

        self.fast_forward({"init_data": 12})
        self.behaviour.act_wrapper()
        self.complete(Event.DONE)

    def test_run2(self) -> None:
        """Run tests."""

        self.fast_forward({"init_data": 12})
        self.behaviour.act_wrapper()
        self.complete(Event.DONE)


class TestGetDataBehaviourNoMajority(BaseSlwWorldTest):
    """Tests GetDataBehaviour No majority"""

    behaviour_class: Type[BaseBehaviour] = GetDataBehaviour
    next_behaviour_class: Type[BaseBehaviour] = GetDataBehaviour

    def test_run(self) -> None:
        """Run tests."""

        self.fast_forward({})
        self.behaviour.act_wrapper()
        self.mock_http_request(
            request_kwargs=dict(
                method="GET",
                headers="",
                version="",
                body=b"",
                url="https://www.random.org/integers/?num=1&min=1&max=3&col=1&base=10&format=plain&rnd=new",
            ),
            response_kwargs=dict(
                version="",
                status_code=200,
                status_text="",
                headers="",
                body=b"17",
            ),
        )
        self.complete(Event.NO_MAJORITY)


### sure can use BehaviourTestCase, but wantede to try manually
