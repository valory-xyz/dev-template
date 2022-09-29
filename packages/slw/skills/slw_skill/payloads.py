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

"""This module contains the transaction payloads of the SlwWorldAbciApp."""

from abc import ABC
from enum import Enum
from typing import Any, Dict, Hashable, Optional

from packages.valory.skills.abstract_round_abci.base import BaseTxPayload


class TransactionType(Enum):
    """Enumeration of transaction types."""

    # TODO: define transaction types: e.g. TX_HASH: "tx_hash"
    GET_DATA = "get_data"
    PRINT_RESULT = "print_result"
    PROCESS_DATA = "process_data"
    REGISTRATION = "registration"
    RESET_AND_PAUSE = "reset_and_pause"
    SELECT_KEEPER = "select_keeper"

    def __str__(self) -> str:
        """Get the string value of the transaction type."""
        return self.value


class BaseSlwWorldPayload(BaseTxPayload, ABC):
    """Base payload for SlwWorldAbciApp."""

    def __hash__(self) -> int:
        """Hash the payload."""
        return hash(tuple(sorted(self.data.items())))


class GetDataPayload(BaseSlwWorldPayload):
    """Represent a transaction payload for the GetDataRound."""

    # TODO: specify the transaction type
    transaction_type = TransactionType.GET_DATA

    def __init__(self, sender: str, init_data: str, **kwargs: Any) -> None:
        super().__init__(sender, **kwargs)
        self._init_data = init_data

    @property
    def init_data(self) -> str:
        """Get the message"""
        return self._init_data

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(init_data=self.init_data)


class PrintResultPayload(BaseSlwWorldPayload):
    """Represent a transaction payload for the PrintResultRound."""

    # TODO: specify the transaction type
    transaction_type = TransactionType.PRINT_RESULT

    def __init__(self, sender: str, printed_data: str, **kwargs: Any) -> None:
        super().__init__(sender, **kwargs)
        self._printed_data = printed_data

    @property
    def printed_data(self) -> str:
        """Get the message"""
        return self._printed_data

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(printed_data=self.printed_data)


class ProcessDataPayload(BaseSlwWorldPayload):
    """Represent a transaction payload for the ProcessDataRound."""

    # TODO: specify the transaction type
    transaction_type = TransactionType.PROCESS_DATA

    def __init__(self, sender: str, processed_data: str, **kwargs: Any) -> None:
        super().__init__(sender, **kwargs)
        self._processed_data = processed_data

    @property
    def processed_data(self) -> str:
        """Get the message"""
        return self._processed_data

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(processed_data=self._processed_data)


class RegistrationPayload(BaseSlwWorldPayload):
    """Represent a transaction payload for the RegistrationRound."""

    # TODO: specify the transaction type
    transaction_type = TransactionType.REGISTRATION


class ResetAndPausePayload(BaseSlwWorldPayload):
    """Represent a transaction payload for the ResetAndPauseRound."""

    # TODO: specify the transaction type
    transaction_type = TransactionType.RESET_AND_PAUSE

    def __init__(self, sender: str, period_count: int, **kwargs: Any) -> None:
        """Initialize an 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param period_count: the period count id
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._period_count = period_count

    @property
    def period_count(self) -> int:
        """Get the period_count."""
        return self._period_count

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(period_count=self.period_count)


class SelectKeeperPayload(BaseSlwWorldPayload):
    """Represent a transaction payload for the SelectKeeperRound."""

    # TODO: specify the transaction type
    transaction_type = TransactionType.SELECT_KEEPER

    def __init__(self, sender: str, keeper: str, **kwargs: Any) -> None:
        """Initialize an 'select_keeper' transaction payload.

        :param sender: the sender (Ethereum) address
        :param keeper: the keeper selection
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._keeper = keeper

    @property
    def keeper(self) -> str:
        """Get the keeper."""
        return self._keeper

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(keeper=self.keeper)
