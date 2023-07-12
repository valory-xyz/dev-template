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

"""Serialization module for chat_completion protocol."""

# pylint: disable=too-many-statements,too-many-locals,no-member,too-few-public-methods,redefined-builtin
from typing import Any, Dict, cast

from aea.mail.base_pb2 import DialogueMessage
from aea.mail.base_pb2 import Message as ProtobufMessage
from aea.protocols.base import Message, Serializer

from packages.algovera.protocols.chat_completion import chat_completion_pb2
from packages.algovera.protocols.chat_completion.message import ChatCompletionMessage


class ChatCompletionSerializer(Serializer):
    """Serialization for the 'chat_completion' protocol."""

    @staticmethod
    def encode(msg: Message) -> bytes:
        """
        Encode a 'ChatCompletion' message into bytes.

        :param msg: the message object.
        :return: the bytes.
        """
        msg = cast(ChatCompletionMessage, msg)
        message_pb = ProtobufMessage()
        dialogue_message_pb = DialogueMessage()
        chat_completion_msg = chat_completion_pb2.ChatCompletionMessage()

        dialogue_message_pb.message_id = msg.message_id
        dialogue_reference = msg.dialogue_reference
        dialogue_message_pb.dialogue_starter_reference = dialogue_reference[0]
        dialogue_message_pb.dialogue_responder_reference = dialogue_reference[1]
        dialogue_message_pb.target = msg.target

        performative_id = msg.performative
        if performative_id == ChatCompletionMessage.Performative.REQUEST:
            performative = chat_completion_pb2.ChatCompletionMessage.Request_Performative()  # type: ignore
            system_template = msg.system_template
            performative.prompt_template = system_template
            user_template = msg.user_template
            performative.user_template = user_template
            chat_completion_msg.request.CopyFrom(performative)
        elif performative_id == ChatCompletionMessage.Performative.RESPONSE:
            performative = chat_completion_pb2.ChatCompletionMessage.Response_Performative()  # type: ignore
            response = msg.response
            performative.response = response
            chat_completion_msg.response.CopyFrom(performative)
        else:
            raise ValueError("Performative not valid: {}".format(performative_id))

        dialogue_message_pb.content = chat_completion_msg.SerializeToString()

        message_pb.dialogue_message.CopyFrom(dialogue_message_pb)
        message_bytes = message_pb.SerializeToString()
        return message_bytes

    @staticmethod
    def decode(obj: bytes) -> Message:
        """
        Decode bytes into a 'ChatCompletion' message.

        :param obj: the bytes object.
        :return: the 'ChatCompletion' message.
        """
        message_pb = ProtobufMessage()
        chat_completion_pb = chat_completion_pb2.ChatCompletionMessage()
        message_pb.ParseFromString(obj)
        message_id = message_pb.dialogue_message.message_id
        dialogue_reference = (
            message_pb.dialogue_message.dialogue_starter_reference,
            message_pb.dialogue_message.dialogue_responder_reference,
        )
        target = message_pb.dialogue_message.target

        message_pb.ParseFromString(message_pb.dialogue_message.content)
        performative = message_pb.WhichOneof("performative")
        performative_id = ChatCompletionMessage.Performative(str(performative))
        performative_content = dict()  # type: Dict[str, Any]
        if performative_id == ChatCompletionMessage.Performative.REQUEST:
            system_template = chat_completion_pb.request.system_template
            performative_content["system_template"] = system_template
            user_template = chat_completion_pb.request.user_template
            performative_content["user_template"] = user_template
        elif performative_id == ChatCompletionMessage.Performative.RESPONSE:
            value = chat_completion_pb.response.value
            performative_content["value"] = value
        else:
            raise ValueError("Performative not valid: {}.".format(performative_id))

        return ChatCompletionMessage(
            message_id=message_id,
            dialogue_reference=dialogue_reference,
            target=target,
            performative=performative,
            **performative_content
        )