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

"""This module contains the shared state for the abci skill of PrimeNumberAbciApp."""
import os
from typing import Any
from packages.valory.skills.abstract_round_abci.models import BaseParams, ApiSpecs
from packages.valory.skills.abstract_round_abci.models import (
    BenchmarkTool as BaseBenchmarkTool,
)
from packages.valory.skills.abstract_round_abci.models import Requests as BaseRequests
from packages.valory.skills.abstract_round_abci.models import (
    SharedState as BaseSharedState,
)
from packages.arshy.skills.prime_number_app.rounds import PrimeNumberAbciApp, Event

MARGIN = 5

Params = BaseParams
Requests = BaseRequests
BenchmarkTool = BaseBenchmarkTool

class SharedState(BaseSharedState):
    """Keep the current shared state of the skill."""

    abci_app_cls = PrimeNumberAbciApp

    def setup(self) -> None:
        """Set up."""
        super().setup()
        PrimeNumberAbciApp.event_to_timeout[
            Event.ROUND_TIMEOUT
        ] = self.context.params.round_timeout_seconds
        PrimeNumberAbciApp.event_to_timeout[Event.RESET_TIMEOUT] = (
            self.context.params.reset_pause_duration + MARGIN
        )



class PrimeNumberParams(BaseParams):
    """Hello World skill parameters."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the parameters."""
        self.openai_api_key: str = self._ensure("openai_api_key", kwargs, str)
        super().__init__(*args, **kwargs)

        os.environ["OPENAI_API_KEY"] = self.openai_api_key

RandomnessApi = ApiSpecs

