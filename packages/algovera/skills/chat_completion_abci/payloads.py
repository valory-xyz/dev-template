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
from os import error, system
from typing import Optional
from dataclasses import dataclass

from packages.valory.skills.abstract_round_abci.base import BaseTxPayload


@dataclass(frozen=True)
class CollectRandomnessPayload(BaseTxPayload):
    """Represent a transaction payload for the CollectRandomnessRound."""
    round_id: int
    randomness: str


@dataclass(frozen=True)
class ProcessRequestPayload(BaseTxPayload):
    """Represent a transaction payload for the ProcessRequestRound."""
    request_id: Optional[int] = None
    system_message: Optional[str] = None
    user_message: Optional[str] = None
    response: Optional[str] = None
    total_tokens: Optional[int] = None
    total_cost: Optional[float] = None
    error: Optional[bool] = None
    request_processed_at: Optional[str] = None


@dataclass(frozen=True)
class PublishResponsePayload(BaseTxPayload):
    """Represent a transaction payload for the PublishResponseRound."""
    error: Optional[bool] = None
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
    id: Optional[str] = None
    user_message: Optional[str] = None
    system_message: Optional[str] = None
    request_received_at: Optional[str] = None

