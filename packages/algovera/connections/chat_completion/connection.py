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

import re
from typing import Any, Dict, cast

import openai
from aea.configurations.base import PublicId
from aea.connections.base import BaseSyncConnection
from aea.mail.base import Envelope
from aea.protocols.base import Address, Message
from aea.protocols.dialogue.base import Dialogue

from packages.algovera.protocols.chat_completion.message import ChatCompletionMessage
from packages.algovera.protocols.chat_completion.dialogues import (
    ChatCompletionDialogue,
    ChatCompletionDialogues as BaseChatCompletionDialogues,
)   
from langchain.chat_models import ChatOpenAI
from langchain.callbacks import get_openai_callback
from langchain.schema import HumanMessage, SystemMessage

PUBLIC_ID = PublicId.from_str("algovera/chat_completion:0.1.0")


class ChatCompletionDialogues(BaseChatCompletionDialogues):
    """A class to keep track of IPFS dialogues."""

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
            return ChatCompletionDialogue.Role.CONNECTION

        BaseChatCompletionDialogues.__init__(
            self,
            self_address=str(kwargs.pop("connection_id")),
            role_from_first_message=role_from_first_message,
            **kwargs,
        )


class ChatCompletionConnection(BaseSyncConnection):
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
        self.openai_settings = {
            setting: self.configuration.config.get(setting)
            for setting in ("openai_api_key", "model", "max_tokens", "temperature")
        }
        openai.api_key = self.openai_settings["openai_api_key"]
        self.dialogues = ChatCompletionDialogues(connection_id=PUBLIC_ID)

        self.chat = ChatOpenAI(
            model=self.openai_settings["model"], 
            temperature=self.openai_settings["temperature"], 
            max_tokens=self.openai_settings["max_tokens"]
        )

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
        chat_completion_message = cast(ChatCompletionMessage, envelope.message)

        dialogue = self.dialogues.update(chat_completion_message)

        if chat_completion_message.performative != ChatCompletionMessage.Performative.REQUEST:
            self.logger.error(
                f"Performative `{chat_completion_message.performative.value}` is not supported."
            )
            return

        self.logger.info("Processing LLM request...")
        response = self._get_response(
            id=chat_completion_message.request["id"],
            system_message=chat_completion_message.request["system_message"],
            user_message=chat_completion_message.request["user_message"],
        )
        
        response_message = cast(
            ChatCompletionMessage,
            dialogue.reply(
                performative=ChatCompletionMessage.Performative.RESPONSE,
                target_message=chat_completion_message,
                response=response,
            ),
        )

        response_envelope = Envelope(
            to=envelope.sender,
            sender=envelope.to,
            message=response_message,
            context=envelope.context,
        )

        self.put_envelope(response_envelope)

    def _get_response(self, id:str, system_message: str, user_message: str):
        """
        Get response from OpenAI.

        :param system_template: system template
        :param user_template: user template
        :return: response
        """
        messages = [
            SystemMessage(
                content=system_message
            ),
            HumanMessage(
                content=user_message
            ),
        ]
        try:
            with get_openai_callback() as cb:
                response = self.chat(messages).content

            reponse = {
                "id": id,
                "system_message": system_message,
                "user_message": user_message,
                "response": response,
                "total_tokens": str(cb.total_tokens),
                "total_cost": str(cb.total_cost),
                "error": "False",
                "error_message": ""
            }

            return reponse

        except Exception as e:
            reponse = {
                "id": id,
                "error": True,
                "error_class": str(e.__class__.__name__),
                "error_message": str(e),
            }

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