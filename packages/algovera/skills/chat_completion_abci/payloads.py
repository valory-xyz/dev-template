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

"""This module contains the transaction payloads of the LLMChatCompletionAbciApp."""
from dataclasses import dataclass
from os import error
from typing import Any, Dict, Optional

from packages.valory.skills.abstract_round_abci.base import BaseTxPayload


@dataclass(frozen=True)
class CollectRandomnessPayload(BaseTxPayload):
    """Represent a transaction payload for the CollectRandomnessRound."""

    round_id: int
    randomness: str


@dataclass(frozen=True)
class ProcessRequestPayload(BaseTxPayload):
    """Represent a transaction payload for the ProcessRequestRound."""

    response_data: Optional[Dict[str, Any]] = None
    request_processed_at: Optional[str] = None


@dataclass(frozen=True)
class PublishResponsePayload(BaseTxPayload):
    """Represent a transaction payload for the PublishResponseRound."""

    published: bool
    error: Optional[bool] = None
    error_message: Optional[str] = None
    request_published_at: Optional[str] = None


@dataclass(frozen=True)
class RegistrationPayload(BaseTxPayload):
    """Represent a transaction payload for the RegistrationRound."""

    sender: str


@dataclass(frozen=True)
class SelectKeeperPayload(BaseTxPayload):
    """Represent a transaction payload for the SelectKeeperRound."""

    keeper: str


@dataclass(frozen=True)
class WaitForRequestPayload(BaseTxPayload):
    """Represent a transaction payload for the WaitForRequestRound."""

    request_data: Optional[Dict[str, Any]] = None
    request_received_at: Optional[str] = None
