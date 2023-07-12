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

from packages.algovera.protocols.rabbitmq import rabbitmq_pb2
from packages.algovera.protocols.rabbitmq.message import RabbitMQMessage


class RabbitMQSerializer(Serializer):
    """Serialization for the 'rabbitmq' protocol."""

    @staticmethod
    def encode(msg: Message) -> bytes:
        """
        Encode a 'RabbitMQ' message into bytes.

        :param msg: the message object.
        :return: the bytes.
        """
        msg = cast(RabbitMQMessage, msg)
        message_pb = ProtobufMessage()
        dialogue_message_pb = DialogueMessage()
        rabbitmq_msg = rabbitmq_pb2.RabbitMQMessage()

        dialogue_message_pb.message_id = msg.message_id
        dialogue_reference = msg.dialogue_reference
        dialogue_message_pb.dialogue_starter_reference = dialogue_reference[0]
        dialogue_message_pb.dialogue_responder_reference = dialogue_reference[1]
        dialogue_message_pb.target = msg.target

        performative_id = msg.performative
        if performative_id == RabbitMQMessage.Performative.CONSUME_REQUEST:
            performative = rabbitmq_pb2.RabbitMQMessage.Consume_Request_Performative()
            consume_queue_name = msg.consume_queue_name
            performative.consume_queue_name = consume_queue_name
            rabbitmq_details = msg.rabbitmq_details
            performative.rabbitmq_details.update(rabbitmq_details)
            rabbitmq_msg.consume_request.CopyFrom(performative)
        elif performative_id == RabbitMQMessage.Performative.CONSUME_RESPONSE:
            performative = rabbitmq_pb2.RabbitMQMessage.Consume_Response_Performative()
            consume_reponse = msg.consume_reponse
            performative.consume_reponse.update(consume_reponse)
            rabbitmq_msg.consume_response.CopyFrom(performative)
        elif performative_id == RabbitMQMessage.Performative.PUBLISH_REQUEST:
            performative = rabbitmq_pb2.RabbitMQMessage.Publish_Request_Performative()
            publish_queue_name = msg.publish_queue_name
            performative.publish_queue_name = publish_queue_name
            publish_message = msg.publish_message
            performative.publish_message.update(publish_message)
            rabbitmq_msg.publish_request.CopyFrom(performative)
        elif performative_id == RabbitMQMessage.Performative.PUBLISH_RESPONSE:
            performative = rabbitmq_pb2.RabbitMQMessage.Publish_Response_Performative()
            publish_response = msg.publish_response
            performative.publish_response.update(publish_response)
            rabbitmq_msg.publish_response.CopyFrom(performative)
        else:
            raise ValueError("Performative not valid: {}".format(performative_id))

        dialogue_message_pb.content = rabbitmq_msg.SerializeToString()

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
        rabbitmq_pb = rabbitmq_pb2.RabbitMQMessage()
        message_pb.ParseFromString(obj)
        message_id = message_pb.dialogue_message.message_id
        dialogue_reference = (
            message_pb.dialogue_message.dialogue_starter_reference,
            message_pb.dialogue_message.dialogue_responder_reference,
        )
        target = message_pb.dialogue_message.target

        message_pb.ParseFromString(message_pb.dialogue_message.content)
        performative = message_pb.WhichOneof("performative")
        performative_id = RabbitMQMessage.Performative(str(performative))
        performative_content = dict()  # type: Dict[str, Any]
        if performative_id == RabbitMQMessage.Performative.CONSUME_REQUEST:
            consume_queue_name = rabbitmq_pb.consume_request.consume_queue_name
            performative_content["consume_queue_name"] = consume_queue_name
            rabbitmq_details = rabbitmq_pb.consume_request.rabbitmq_details
            performative_content["rabbitmq_details"] = rabbitmq_details
        elif performative_id == RabbitMQMessage.Performative.CONSUME_RESPONSE:
            consume_reponse = rabbitmq_pb.consume_response.consume_reponse
            performative_content["consume_reponse"] = consume_reponse
        elif performative_id == RabbitMQMessage.Performative.PUBLISH_REQUEST:
            publish_queue_name = rabbitmq_pb.publish_request.publish_queue_name
            performative_content["publish_queue_name"] = publish_queue_name
            publish_message = rabbitmq_pb.publish_request.publish_message
            performative_content["publish_message"] = publish_message
            rabbitmq_details = rabbitmq_pb.publish_request.rabbitmq_details
            performative_content["rabbitmq_details"] = rabbitmq_details
        elif performative_id == RabbitMQMessage.Performative.PUBLISH_RESPONSE:
            publish_response = rabbitmq_pb.publish_response.publish_response
            performative_content["publish_response"] = publish_response
        else:
            raise ValueError("Performative not valid: {}.".format(performative_id))
        return RabbitMQMessage(
            message_id=message_id,
            dialogue_reference=dialogue_reference,
            target=target,
            performative=performative,
            **performative_content
        )