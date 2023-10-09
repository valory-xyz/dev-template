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

"""This module contains the shared state for the abci skill of ValoryChatChainedAbciApp."""

from packages.algovera.skills.valory_chat_abci.models import (
    Params as ValoryChatAbciParams,
)
from packages.algovera.skills.valory_chat_abci.models import (
    SharedState as BaseSharedState,
)
from packages.algovera.skills.valory_chat_abci.rounds import Event as ValoryChatEvent
from packages.algovera.skills.valory_chat_chained_abci.composition import (
    ValoryChatChainedAbciApp,
)
from packages.valory.skills.abstract_round_abci.models import ApiSpecs
from packages.valory.skills.abstract_round_abci.models import (
    BenchmarkTool as BaseBenchmarkTool,
)
from packages.valory.skills.abstract_round_abci.models import Requests as BaseRequests
from packages.valory.skills.reset_pause_abci.rounds import Event as ResetPauseEvent
from packages.valory.skills.termination_abci.models import TerminationParams


ValoryChatParams = ValoryChatAbciParams

Requests = BaseRequests
BenchmarkTool = BaseBenchmarkTool

MARGIN = 5
MULTIPLIER = 2


class RandomnessApi(ApiSpecs):
    """A model that wraps ApiSpecs for randomness api specifications."""


class SharedState(BaseSharedState):
    """Keep the current shared state of the skill."""

    abci_app_cls = ValoryChatChainedAbciApp

    def setup(self) -> None:
        """Set up."""
        super().setup()

        ValoryChatChainedAbciApp.event_to_timeout[ValoryChatEvent.ROUND_TIMEOUT] = (
            self.context.params.round_timeout_seconds * MULTIPLIER
        )
        ValoryChatChainedAbciApp.event_to_timeout[
            ResetPauseEvent.ROUND_TIMEOUT
        ] = self.context.params.round_timeout_seconds

        ValoryChatChainedAbciApp.event_to_timeout[
            ResetPauseEvent.RESET_AND_PAUSE_TIMEOUT
        ] = (self.context.params.reset_pause_duration + MARGIN)


class Params(
    ValoryChatParams,
    TerminationParams,
):
    """A model to represent params for multiple abci apps."""
