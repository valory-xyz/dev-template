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

"""Test dialogues module for llm protocol."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,redefined-builtin
from aea.test_tools.test_protocol import BaseProtocolDialoguesTestCase

from packages.algovera.protocols.chat_completion.dialogues import ChatCompletionDialogue, ChatCompletionDialogues
from packages.algovera.protocols.chat_completion.message import ChatCompletionMessage


class TestDialoguesChatCompletion(BaseProtocolDialoguesTestCase):
    """Test for the 'llm' protocol dialogues."""

    MESSAGE_CLASS = ChatCompletionMessage

    DIALOGUE_CLASS = ChatCompletionDialogue

    DIALOGUES_CLASS = ChatCompletionDialogues

    ROLE_FOR_THE_FIRST_MESSAGE = ChatCompletionDialogue.Role.CONNECTION  # CHECK

    def make_message_content(self) -> dict:
        """Make a dict with message contruction content for dialogues.create."""
        return dict(
            performative=ChatCompletionMessage.Performative.REQUEST,
            system_template="system_template",
            user_template="user_template",
        )