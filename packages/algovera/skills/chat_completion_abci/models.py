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

"""This module contains the shared state for the abci skill of LLMChatCompletionAbciApp."""
from typing import Any

from aea.skills.base import SkillContext

from packages.algovera.skills.chat_completion_abci.rounds import (
    LLMChatCompletionAbciApp,
)
from packages.valory.skills.abstract_round_abci.models import ApiSpecs, BaseParams
from packages.valory.skills.abstract_round_abci.models import (
    BenchmarkTool as BaseBenchmarkTool,
)
from packages.valory.skills.abstract_round_abci.models import Requests as BaseRequests
from packages.valory.skills.abstract_round_abci.models import (
    SharedState as BaseSharedState,
)


class SharedState(BaseSharedState):
    """Keep the current shared state of the skill."""

    abci_app_cls = LLMChatCompletionAbciApp

    def __init__(self, *args: Any, skill_context: SkillContext, **kwargs: Any) -> None:
        """Init"""
        super().__init__(*args, skill_context=skill_context, **kwargs)


Requests = BaseRequests
BenchmarkTool = BaseBenchmarkTool


class RandomnessApi(ApiSpecs):
    """A model that wraps ApiSpecs for randomness api specifications."""


class Params(BaseParams):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init"""
        self.rabbitmq_host = self._ensure("rabbitmq_host", kwargs, str)
        self.rabbitmq_port = self._ensure("rabbitmq_port", kwargs, int)
        self.rabbitmq_username = self._ensure("rabbitmq_username", kwargs, str)
        self.rabbitmq_password = self._ensure("rabbitmq_password", kwargs, str)
        self.consume_queue_name = self._ensure("consume_queue_name", kwargs, str)
        self.publish_queue_name = self._ensure("publish_queue_name", kwargs, str)
        super().__init__(*args, **kwargs)
