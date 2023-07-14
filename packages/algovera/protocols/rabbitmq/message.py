# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2023 algovera
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

"""This module contains rabbitmq's message definition."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,too-many-branches,not-an-iterable,unidiomatic-typecheck,unsubscriptable-object
import logging
from typing import Any, Dict, Set, Tuple, cast

from aea.configurations.base import PublicId
from aea.exceptions import AEAEnforceError, enforce
from aea.protocols.base import Message


_default_logger = logging.getLogger("aea.packages.algovera.protocols.rabbitmq.message")

DEFAULT_BODY_SIZE = 4


class RabbitmqMessage(Message):
    """A protocol to interact with RabbitMQ."""

    protocol_id = PublicId.from_str("algovera/rabbitmq:0.1.0")
    protocol_specification_id = PublicId.from_str("algovera/rabbitmq:0.1.0")

    class Performative(Message.Performative):
        """Performatives for the rabbitmq protocol."""

        CONSUME_REQUEST = "consume_request"
        CONSUME_RESPONSE = "consume_response"
        PUBLISH_REQUEST = "publish_request"
        PUBLISH_RESPONSE = "publish_response"

        def __str__(self) -> str:
            """Get the string representation."""
            return str(self.value)

    _performatives = {
        "consume_request",
        "consume_response",
        "publish_request",
        "publish_response",
    }
    __slots__: Tuple[str, ...] = tuple()

    class _SlotsCls:
        __slots__ = (
            "consume_queue_name",
            "consume_response",
            "dialogue_reference",
            "message_id",
            "performative",
            "publish_message",
            "publish_queue_name",
            "publish_response",
            "rabbitmq_details",
            "target",
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
        Initialise an instance of RabbitmqMessage.

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
            performative=RabbitmqMessage.Performative(performative),
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
        return cast(RabbitmqMessage.Performative, self.get("performative"))

    @property
    def target(self) -> int:
        """Get the target of the message."""
        enforce(self.is_set("target"), "target is not set.")
        return cast(int, self.get("target"))

    @property
    def consume_queue_name(self) -> str:
        """Get the 'consume_queue_name' content from the message."""
        enforce(
            self.is_set("consume_queue_name"),
            "'consume_queue_name' content is not set.",
        )
        return cast(str, self.get("consume_queue_name"))

    @property
    def consume_response(self) -> Dict[str, str]:
        """Get the 'consume_response' content from the message."""
        enforce(
            self.is_set("consume_response"), "'consume_response' content is not set."
        )
        return cast(Dict[str, str], self.get("consume_response"))

    @property
    def publish_message(self) -> Dict[str, str]:
        """Get the 'publish_message' content from the message."""
        enforce(self.is_set("publish_message"), "'publish_message' content is not set.")
        return cast(Dict[str, str], self.get("publish_message"))

    @property
    def publish_queue_name(self) -> str:
        """Get the 'publish_queue_name' content from the message."""
        enforce(
            self.is_set("publish_queue_name"),
            "'publish_queue_name' content is not set.",
        )
        return cast(str, self.get("publish_queue_name"))

    @property
    def publish_response(self) -> Dict[str, str]:
        """Get the 'publish_response' content from the message."""
        enforce(
            self.is_set("publish_response"), "'publish_response' content is not set."
        )
        return cast(Dict[str, str], self.get("publish_response"))

    @property
    def rabbitmq_details(self) -> Dict[str, str]:
        """Get the 'rabbitmq_details' content from the message."""
        enforce(
            self.is_set("rabbitmq_details"), "'rabbitmq_details' content is not set."
        )
        return cast(Dict[str, str], self.get("rabbitmq_details"))

    def _is_consistent(self) -> bool:
        """Check that the message follows the rabbitmq protocol."""
        try:
            enforce(
                isinstance(self.dialogue_reference, tuple),
                "Invalid type for 'dialogue_reference'. Expected 'tuple'. Found '{}'.".format(
                    type(self.dialogue_reference)
                ),
            )
            enforce(
                isinstance(self.dialogue_reference[0], str),
                "Invalid type for 'dialogue_reference[0]'. Expected 'str'. Found '{}'.".format(
                    type(self.dialogue_reference[0])
                ),
            )
            enforce(
                isinstance(self.dialogue_reference[1], str),
                "Invalid type for 'dialogue_reference[1]'. Expected 'str'. Found '{}'.".format(
                    type(self.dialogue_reference[1])
                ),
            )
            enforce(
                type(self.message_id) is int,
                "Invalid type for 'message_id'. Expected 'int'. Found '{}'.".format(
                    type(self.message_id)
                ),
            )
            enforce(
                type(self.target) is int,
                "Invalid type for 'target'. Expected 'int'. Found '{}'.".format(
                    type(self.target)
                ),
            )

            # Light Protocol Rule 2
            # Check correct performative
            enforce(
                isinstance(self.performative, RabbitmqMessage.Performative),
                "Invalid 'performative'. Expected either of '{}'. Found '{}'.".format(
                    self.valid_performatives, self.performative
                ),
            )

            # Check correct contents
            actual_nb_of_contents = len(self._body) - DEFAULT_BODY_SIZE
            expected_nb_of_contents = 0
            if self.performative == RabbitmqMessage.Performative.CONSUME_REQUEST:
                expected_nb_of_contents = 2
                enforce(
                    isinstance(self.rabbitmq_details, dict),
                    "Invalid type for content 'rabbitmq_details'. Expected 'dict'. Found '{}'.".format(
                        type(self.rabbitmq_details)
                    ),
                )
                for (
                    key_of_rabbitmq_details,
                    value_of_rabbitmq_details,
                ) in self.rabbitmq_details.items():
                    enforce(
                        isinstance(key_of_rabbitmq_details, str),
                        "Invalid type for dictionary keys in content 'rabbitmq_details'. Expected 'str'. Found '{}'.".format(
                            type(key_of_rabbitmq_details)
                        ),
                    )
                    enforce(
                        isinstance(value_of_rabbitmq_details, str),
                        "Invalid type for dictionary values in content 'rabbitmq_details'. Expected 'str'. Found '{}'.".format(
                            type(value_of_rabbitmq_details)
                        ),
                    )
                enforce(
                    isinstance(self.consume_queue_name, str),
                    "Invalid type for content 'consume_queue_name'. Expected 'str'. Found '{}'.".format(
                        type(self.consume_queue_name)
                    ),
                )
            elif self.performative == RabbitmqMessage.Performative.CONSUME_RESPONSE:
                expected_nb_of_contents = 1
                enforce(
                    isinstance(self.consume_response, dict),
                    "Invalid type for content 'consume_response'. Expected 'dict'. Found '{}'.".format(
                        type(self.consume_response)
                    ),
                )
                for (
                    key_of_consume_response,
                    value_of_consume_response,
                ) in self.consume_response.items():
                    enforce(
                        isinstance(key_of_consume_response, str),
                        "Invalid type for dictionary keys in content 'consume_response'. Expected 'str'. Found '{}'.".format(
                            type(key_of_consume_response)
                        ),
                    )
                    enforce(
                        isinstance(value_of_consume_response, str),
                        "Invalid type for dictionary values in content 'consume_response'. Expected 'str'. Found '{}'.".format(
                            type(value_of_consume_response)
                        ),
                    )
            elif self.performative == RabbitmqMessage.Performative.PUBLISH_REQUEST:
                expected_nb_of_contents = 3
                enforce(
                    isinstance(self.rabbitmq_details, dict),
                    "Invalid type for content 'rabbitmq_details'. Expected 'dict'. Found '{}'.".format(
                        type(self.rabbitmq_details)
                    ),
                )
                for (
                    key_of_rabbitmq_details,
                    value_of_rabbitmq_details,
                ) in self.rabbitmq_details.items():
                    enforce(
                        isinstance(key_of_rabbitmq_details, str),
                        "Invalid type for dictionary keys in content 'rabbitmq_details'. Expected 'str'. Found '{}'.".format(
                            type(key_of_rabbitmq_details)
                        ),
                    )
                    enforce(
                        isinstance(value_of_rabbitmq_details, str),
                        "Invalid type for dictionary values in content 'rabbitmq_details'. Expected 'str'. Found '{}'.".format(
                            type(value_of_rabbitmq_details)
                        ),
                    )
                enforce(
                    isinstance(self.publish_queue_name, str),
                    "Invalid type for content 'publish_queue_name'. Expected 'str'. Found '{}'.".format(
                        type(self.publish_queue_name)
                    ),
                )
                enforce(
                    isinstance(self.publish_message, dict),
                    "Invalid type for content 'publish_message'. Expected 'dict'. Found '{}'.".format(
                        type(self.publish_message)
                    ),
                )
                for (
                    key_of_publish_message,
                    value_of_publish_message,
                ) in self.publish_message.items():
                    enforce(
                        isinstance(key_of_publish_message, str),
                        "Invalid type for dictionary keys in content 'publish_message'. Expected 'str'. Found '{}'.".format(
                            type(key_of_publish_message)
                        ),
                    )
                    enforce(
                        isinstance(value_of_publish_message, str),
                        "Invalid type for dictionary values in content 'publish_message'. Expected 'str'. Found '{}'.".format(
                            type(value_of_publish_message)
                        ),
                    )
            elif self.performative == RabbitmqMessage.Performative.PUBLISH_RESPONSE:
                expected_nb_of_contents = 1
                enforce(
                    isinstance(self.publish_response, dict),
                    "Invalid type for content 'publish_response'. Expected 'dict'. Found '{}'.".format(
                        type(self.publish_response)
                    ),
                )
                for (
                    key_of_publish_response,
                    value_of_publish_response,
                ) in self.publish_response.items():
                    enforce(
                        isinstance(key_of_publish_response, str),
                        "Invalid type for dictionary keys in content 'publish_response'. Expected 'str'. Found '{}'.".format(
                            type(key_of_publish_response)
                        ),
                    )
                    enforce(
                        isinstance(value_of_publish_response, str),
                        "Invalid type for dictionary values in content 'publish_response'. Expected 'str'. Found '{}'.".format(
                            type(value_of_publish_response)
                        ),
                    )

            # Check correct content count
            enforce(
                expected_nb_of_contents == actual_nb_of_contents,
                "Incorrect number of contents. Expected {}. Found {}".format(
                    expected_nb_of_contents, actual_nb_of_contents
                ),
            )

            # Light Protocol Rule 3
            if self.message_id == 1:
                enforce(
                    self.target == 0,
                    "Invalid 'target'. Expected 0 (because 'message_id' is 1). Found {}.".format(
                        self.target
                    ),
                )
        except (AEAEnforceError, ValueError, KeyError) as e:
            _default_logger.error(str(e))
            return False

        return True
