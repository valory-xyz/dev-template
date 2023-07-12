#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021-2023 Valory AG
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


# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2023 valory
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

"""This module contains chat_completion's message definition."""

import logging
from typing import Any, Dict, Set, Tuple, cast

from aea.configurations.base import PublicId
from aea.exceptions import enforce
from aea.protocols.base import Message


_default_logger = logging.getLogger("aea.packages.algovera.protocols.rabbitmq.message")

DEFAULT_BODY_SIZE = 4

class RabbitMQMessage(Message):
    """A protocol for Chat Completion requests and responses."""

    protocol_id = PublicId.from_str("algovera/rabbitmq:1.0.0")
    protocol_specification_id = PublicId.from_str("algovera/rabbitmq:1.0.0")

    class Performative(Message.Performative):
        """Performatives for the chat completion protocol."""

        CONSUME_REQUEST = "consume_request"
        CONSUME_RESPONSE = "consume_response"
        PUBLISH_REQUEST = "publish_request"
        PUBLISH_RESPONSE = "publish_response"

        def __str__(self) -> str:
            """Get the string representation."""
            return str(self.value)

    _performatives = {"consume_request", "consume_response", "publish_request", "publish_response"}
    __slots__: Tuple[str, ...] = tuple()

    class _SlotsCls:
        __slots__ = (
            "dialogue_reference",
            "message_id",
            "performative",
            "target",
            "consume_queue_name",
            "publish_queue_name",
            "rabbitmq_details",
            "publish_message",
            "consume_response",
            "publish_response",
        )

    def __init__(
        self,
        performative: Performative,
        dialogue_reference: Tuple[str, str] = ("", ""),
        message_id: int = 1,
        target: int = 0,
        **kwargs: Any,
    ):
        """
        Initialise an instance of ChatCompletionMessage.

        :param message_id: the message id.
        :param dialogue_reference: the dialogue reference.
        :param target: the message target.
        :param performative: the message performative.
        :param **kwargs: extra options.
        """
        super().__init__(
            dialogue_reference=dialogue_reference,
            message_id=message_id,
            target=target,
            performative=RabbitMQMessage.Performative(performative),
            **kwargs,
        )

    @property
    def valid_performatives(self) -> Set[str]:
        """Get valid performatives."""
        return self._performatives

    @property
    def dialogue_reference(self) -> Tuple[str, str]:
        """Get the dialogue_reference of the message."""
        enforce(self.is_set("dialogue_reference"), "dialogue_reference is not set.")
        return cast(Tuple[str, str], self.get("dialogue_reference"))

    @property
    def message_id(self) -> int:
        """Get the message_id of the message."""
        enforce(self.is_set("message_id"), "message_id is not set.")
        return cast(int, self.get("message_id"))

    @property
    def performative(self) -> Performative:  # type: ignore # noqa: F821
        """Get the performative of the message."""
        enforce(self.is_set("performative"), "performative is not set.")
        return cast(RabbitMQMessage.Performative, self.get("performative"))

    @property
    def target(self) -> int:
        """Get the target of the message."""
        enforce(self.is_set("target"), "target is not set.")
        return cast(int, self.get("target"))

    @property
    def consume_queue_name(self) -> str:
        """Get the consume_queue_name of the message."""
        enforce(self.is_set("consume_queue_name"), "consume_queue_name is not set.")
        return cast(str, self.get("consume_queue_name"))

    @property
    def publish_queue_name(self) -> str:
        """Get the publish_queue_name of the message."""
        enforce(self.is_set("publish_queue_name"), "publish_queue_name is not set.")
        return cast(str, self.get("publish_queue_name"))

    @property
    def rabbitmq_details(self) -> Dict[str, str]:
        """Get the rabbitmq_details of the message."""
        enforce(self.is_set("rabbitmq_details"), "rabbitmq_details is not set.")
        # verify there is host, port, username, password in the dict
        assert set(self.get("rabbitmq_details").keys()) == {"host", "port", "username", "password"}
        return cast(Dict[str, str], self.get("rabbitmq_details"))

    @property
    def consume_response(self) -> dict:
        """Get the consume_response of the message."""
        enforce(self.is_set("consume_response"), "consume_response is not set.")
        return cast(dict, self.get("consume_response"))

    @property
    def publish_response(self) -> dict:
        """Get the publish_response of the message."""
        enforce(self.is_set("publish_response"), "publish_response is not set.")
        return cast(dict, self.get("publish_response"))

    @property
    def publish_message(self) -> dict:
        """Get the publish_message of the message."""
        enforce(self.is_set("publish_message"), "publish_message is not set.")
        return cast(dict, self.get("publish_message"))

    def _is_consistent(self) -> bool:
        """Check that the message follows the chat completion protocol."""
        try:
            if not isinstance(self.dialogue_reference, tuple):
                return False
            elif not isinstance(self.message_id, int):
                return False
            elif self.performative not in RabbitMQMessage.Performative.valid_performatives:
                return False
            elif not isinstance(self.target, int):
                return False
            elif not isinstance(self.consume_queue_name, str):
                return False
            elif not isinstance(self.publish_queue_name, str):
                return False
            elif not isinstance(self.rabbitmq_details, dict):
                return False
            elif not isinstance(self.consume_response, dict):
                return False
            elif not isinstance(self.publish_response, dict):
                return False
            elif not isinstance(self.publish_message, dict):
                return False
            return True
        except (AssertionError, AttributeError, KeyError, TypeError, ValueError) as e:
            _default_logger.exception(str(e))
            return False