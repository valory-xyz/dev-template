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

"""Test messages module for chat_completion protocol."""

from typing import List
from aea.test_tools.test_protocol import BaseProtocolMessagesTestCase
from packages.algovera.protocols.chat_completion.message import ChatCompletionMessage

class TestMessageLlm(BaseProtocolMessagesTestCase):
    """Test for the 'llm' protocol message."""

    MESSAGE_CLASS = ChatCompletionMessage

    def build_messages(self) -> List[ChatCompletionMessage]:  # type: ignore[override]
        """Build the messages to be used for testing."""
        return [
            ChatCompletionMessage(
                performative=ChatCompletionMessage.Performative.REQUEST,
                system_template="some str",
                user_template="some str",
            ),
            ChatCompletionMessage(
                performative=ChatCompletionMessage.Performative.RESPONSE,
                value="some str",
            ),
        ]

    def build_inconsistent(self) -> List[LlmMessage]:  # type: ignore[override]
        """Build inconsistent messages to be used for testing."""
        return [
            ChatCompletionMessage(
                performative=ChatCompletionMessage.Performative.REQUEST,
                # skip content: prompt_template
                prompt_values={"some str": "some str"},
            ),
            ChatCompletionMessage(
                performative=ChatCompletionMessage.Performative.RESPONSE,
                # skip content: value
            ),
        ]