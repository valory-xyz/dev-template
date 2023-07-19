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

"""Test messages module for chat_completion protocol."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,redefined-builtin
from typing import List

from aea.test_tools.test_protocol import BaseProtocolMessagesTestCase

from packages.algovera.protocols.chat_completion.message import ChatCompletionMessage


class TestMessageChatCompletion(BaseProtocolMessagesTestCase):
    """Test for the 'chat_completion' protocol message."""

    MESSAGE_CLASS = ChatCompletionMessage

    def build_messages(self) -> List[ChatCompletionMessage]:  # type: ignore[override]
        """Build the messages to be used for testing."""
        return [
            ChatCompletionMessage(
                performative=ChatCompletionMessage.Performative.REQUEST,
                request={"some str": "some str"},
            ),
            ChatCompletionMessage(
                performative=ChatCompletionMessage.Performative.RESPONSE,
                response={"some str": "some str"},
            ),
        ]

    def build_inconsistent(self) -> List[ChatCompletionMessage]:  # type: ignore[override]
        """Build inconsistent messages to be used for testing."""
        return [
            ChatCompletionMessage(
                performative=ChatCompletionMessage.Performative.REQUEST,
                # skip content: request
            ),
            ChatCompletionMessage(
                performative=ChatCompletionMessage.Performative.RESPONSE,
                # skip content: response
            ),
        ]
