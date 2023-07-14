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

"""OpenAI connection and channel."""

import pika
import json
from typing import Any, cast

from aea.configurations.base import PublicId
from aea.connections.base import BaseSyncConnection
from aea.mail.base import Envelope
from aea.protocols.base import Address, Message
from aea.protocols.dialogue.base import Dialogue

from packages.algovera.protocols.rabbitmq.message import RabbitmqMessage
from packages.algovera.protocols.rabbitmq.dialogues import (
    RabbitmqDialogue,
    RabbitmqDialogues as BaseRabbitmqDialogues,
)   



PUBLIC_ID = PublicId.from_str("algovera/rabbitmq:0.1.0")


class RabbitmqDialogues(BaseRabbitmqDialogues):

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize dialogues.

        :param kwargs: keyword arguments
        """

        def role_from_first_message(  # pylint: disable=unused-argument
            message: Message, receiver_address: Address
        ) -> Dialogue.Role:
            """Infer the role of the agent from an incoming/outgoing first message

            :param message: an incoming/outgoing first message
            :param receiver_address: the address of the receiving agent
            :return: The role of the agent
            """
            return RabbitmqDialogue.Role.CONNECTION

        BaseRabbitmqDialogues.__init__(
            self,
            self_address=str(kwargs.pop("connection_id")),
            role_from_first_message=role_from_first_message,
            **kwargs,
        )


class RabbitMQConnection(BaseSyncConnection):
    """Proxy to the functionality of the openai SDK."""

    MAX_WORKER_THREADS = 1
    connection_id = PUBLIC_ID

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
        """
        Initialize the connection.

        The configuration must be specified if and only if the following
        parameters are None: connection_id, excluded_protocols or restricted_to_protocols.

        Possible arguments:
        - configuration: the connection configuration.
        - data_dir: directory where to put local files.
        - identity: the identity object held by the agent.
        - crypto_store: the crypto store for encrypted communication.
        - restricted_to_protocols: the set of protocols ids of the only supported protocols for this connection.
        - excluded_protocols: the set of protocols ids that we want to exclude for this connection.

        :param args: arguments passed to component base
        :param kwargs: keyword arguments passed to component base
        """
        super().__init__(*args, **kwargs)
        self.rabbitmq_settings = {
            setting: self.configuration.config.get(setting)
            for setting in ("host", "port", "username", "password", "consume_queue_name", "publish_queue_name")
        }
        self.dialogues = RabbitmqDialogues(connection_id=PUBLIC_ID)


    def main(self) -> None:
        """
        Run synchronous code in background.

        SyncConnection `main()` usage:
        The idea of the `main` method in the sync connection
        is to provide for a way to actively generate messages by the connection via the `put_envelope` method.

        A simple example is the generation of a message every second:
        ```
        while self.is_connected:
            envelope = make_envelope_for_current_time()
            self.put_enevelope(envelope)
            time.sleep(1)
        ```
        In this case, the connection will generate a message every second
        regardless of envelopes sent to the connection by the agent.
        For instance, this way one can implement periodically polling some internet resources
        and generate envelopes for the agent if some updates are available.
        Another example is the case where there is some framework that runs blocking
        code and provides a callback on some internal event.
        This blocking code can be executed in the main function and new envelops
        can be created in the event callback.
        """

    def on_send(self, envelope: Envelope) -> None:
        """
        Send an envelope.

        :param envelope: the envelope to send.
        """
        rabbitmq_message = cast(RabbitmqMessage, envelope.message)
        dialogue = self.dialogues.update(rabbitmq_message)

        self.logger.info(f"Processing envelope: {envelope}")
        self.logger.info(f"RabbitMQ message: {rabbitmq_message}")

        if rabbitmq_message.performative not in (
            RabbitmqMessage.Performative.PUBLISH_REQUEST,
            RabbitmqMessage.Performative.CONSUME_REQUEST,
        ):
            self.logger.error("Performative not recognized.")
            return

        if rabbitmq_message.performative == RabbitmqMessage.Performative.CONSUME_REQUEST:
            consume_response = self._get_consume_response(rabbitmq_message)

            consume_response_reply = cast(
                RabbitmqMessage,
                dialogue.reply(
                    performative=RabbitmqMessage.Performative.CONSUME_RESPONSE,
                    target_message=rabbitmq_message,
                    consume_response=consume_response,
                ),
            )
            
            response_envelope = Envelope(
                to=envelope.sender,
                sender=envelope.to,
                context=envelope.context,
                message=consume_response_reply,
            )

        if rabbitmq_message.performative == RabbitmqMessage.Performative.PUBLISH_REQUEST:

            publish_response = self._get_publish_response(rabbitmq_message)
            publish_response_reply = cast(
                RabbitmqMessage,
                dialogue.reply(
                    performative=RabbitmqMessage.Performative.PUBLISH_RESPONSE,
                    target_message=rabbitmq_message,
                    publish_response=publish_response,
                ),
            )
            response_envelope = Envelope(
                to=envelope.sender,
                sender=envelope.to,
                context=envelope.context,
                message=publish_response_reply,
            )
        
        self.put_envelope(response_envelope)

    def _get_rabbitmq_details(self, rabbitmq_msg, consume=True):
        rabbitmq_host = (rabbitmq_msg.rabbitmq_details["host"] 
                if rabbitmq_msg.rabbitmq_details["host"] 
                else self.rabbitmq_settings["host"])
        rabbitmq_port = (rabbitmq_msg.rabbitmq_details["port"]
            if rabbitmq_msg.rabbitmq_details["port"]
            else self.rabbitmq_settings["port"])
        rabbitmq_username = (rabbitmq_msg.rabbitmq_details["username"]
            if rabbitmq_msg.rabbitmq_details["username"]
            else self.rabbitmq_settings["username"])
        rabbitmq_password = (rabbitmq_msg.rabbitmq_details["password"]
            if rabbitmq_msg.rabbitmq_details["password"]
            else self.rabbitmq_settings["password"])
        if consume:
            rabbitmq_queue_name = rabbitmq_msg.consume_queue_name
        else:
            rabbitmq_queue_name = rabbitmq_msg.publish_queue_name

        return rabbitmq_host, rabbitmq_port, rabbitmq_username, rabbitmq_password, rabbitmq_queue_name

    def _get_consume_response(self, rabbitmq_msg):
        try:
            rabbitmq_host, rabbitmq_port, rabbitmq_username, rabbitmq_password, rabbitmq_queue_name = self._get_rabbitmq_details(rabbitmq_msg)

            # Connect to RabbitMQ
            credentials = pika.PlainCredentials(rabbitmq_username, rabbitmq_password)
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=rabbitmq_host, port=rabbitmq_port, credentials=credentials)
            )
            channel = connection.channel()
            channel.queue_declare(queue=rabbitmq_queue_name, durable=True)

            # Get message from queue
            method_frame, header_frame, body = channel.basic_get(queue=rabbitmq_queue_name)

            # Message not found
            if method_frame is None:
                self.logger.info("Nothing in queue")
                connection.close()
                return {"received_request": "False", "error": "False", "error_message": ""}

            # Message found
            else:
                self.logger.info(f"Message found: {body}")
                channel.basic_ack(delivery_tag=method_frame.delivery_tag)
                connection.close()
                data = json.loads(body)
                data["received_request"] = "True"
                data["error"] = "False"
                data["error_message"] = ""
                
                # if not id in data raise exception
                if not "id" in data:
                    raise Exception("No id in message")

                if not "user_message" in data:
                    raise Exception("No user_message in message")

                if not "system_message" in data:
                    data["system_message"] = ""

                return data

        except Exception as e:
            self.logger.info(f"Exception: {e}")
            return {"received_request": "False", "error": "True", "error_message": str(e)}

    def _get_publish_response(self, rabbitmq_msg: RabbitmqMessage):
        try:
            rabbitmq_host, rabbitmq_port, rabbitmq_username, rabbitmq_password, rabbitmq_queue_name = self._get_rabbitmq_details(rabbitmq_msg, consume=False)
            
            # Connect to RabbitMQ
            credentials = pika.PlainCredentials(
                rabbitmq_username, 
                rabbitmq_password
            )
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=rabbitmq_host, 
                    port=rabbitmq_port, 
                    credentials=credentials
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue=rabbitmq_queue_name, durable=True)

            # Publish message to queue
            channel.basic_publish(exchange="", routing_key=rabbitmq_queue_name, body=json.dumps(rabbitmq_msg.publish_message))
            self.logger.info(f"Message published: {rabbitmq_msg.publish_message}")

            # Close connection
            connection.close()
            return {"published": "True"}

        except Exception as e:
            self.logger.info(f"Failed to publish message: {e}")
            return {"published": "False"}

    def on_connect(self) -> None:
        """
        Tear down the connection.

        Connection status set automatically.
        """

    def on_disconnect(self) -> None:
        """
        Tear down the connection.

        Connection status set automatically.
        """