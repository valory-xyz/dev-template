# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2023 Valory AG
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

"""This module contains the shared state for the abci skill of LLMChatCompletionAbciApp."""
import os
import json
import pika
from typing import Any
from aea.skills.base import SkillContext
from packages.valory.skills.abstract_round_abci.models import BaseParams, ApiSpecs
from packages.valory.skills.abstract_round_abci.models import (
    BenchmarkTool as BaseBenchmarkTool,
)
from packages.valory.skills.abstract_round_abci.models import Requests as BaseRequests
from packages.valory.skills.abstract_round_abci.models import (
    SharedState as BaseSharedState,
    Model as BaseModel
)
from packages.algovera.skills.chat_completion_fsm_app.rounds import LLMChatCompletionAbciApp, Event

from langchain.chat_models import ChatOpenAI

class SharedState(BaseSharedState):
    """Keep the current shared state of the skill."""

    abci_app_cls = LLMChatCompletionAbciApp

    def setup(self) -> None:
        """Set up."""
        super().setup()
        LLMChatCompletionAbciApp.event_to_timeout[
            Event.ROUND_TIMEOUT
        ] = self.context.params.round_timeout_seconds


class Params(BaseParams):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.openai_api_key: str = self._ensure("openai_api_key", kwargs, str)
        super().__init__(*args, **kwargs)
        os.environ["OPENAI_API_KEY"] = self.openai_api_key


class LLMChatCompletion(BaseModel):
    def __init__(self, *args:Any, **kwargs:Any):
        self.model_name = kwargs.get('model_name', 'gpt-3.5-turbo')
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 256)
        self.llm = ChatOpenAI(
            model=self.model_name, 
            temperature=self.temperature, 
            max_tokens=self.max_tokens
        )
        self._name = 'LLMChatCompletion'
        self._context = SkillContext()
        super().__init__(*args, **kwargs)

    def __call__(self, input):
        return self.llm.predict(input)


class InteractRabbitMQ(BaseModel):
    def __init__(self, *args:Any, **kwargs:Any):
        self.rabbitmq_host = kwargs.get('rabbitmq_host', 'localhost')
        self.rabbitmq_port = kwargs.get('rabbitmq_port', 5672)
        self.rabbitmq_username = kwargs.get('rabbitmq_username', 'guest')
        self.rabbitmq_password = kwargs.get('rabbitmq_password', 'guest')
        self.request_queue_name = kwargs.get('request_queue_name', 'request_queue')
        self.response_queue_name = kwargs.get('response_queue_name', 'response_queue')
        self.request = None
        self.response = None
        self._name = 'InteractRabbitMQ'
        self._context = SkillContext()
        super().__init__(*args, **kwargs)

    def start(self):
        credentials = pika.PlainCredentials(self.rabbitmq_username, self.rabbitmq_password)
        parameters = pika.ConnectionParameters(self.rabbitmq_host, self.rabbitmq_port, credentials=credentials)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.request_queue_name)
        self.channel.queue_declare(queue=self.response_queue_name)

    def stop(self):
        if self.connection and self.connection.is_open:
            self.channel.stop_consuming()  # Stop consuming messages
            self.connection.close()  # Close the connection

    def enqueue_request(self, item):
        self.channel.basic_publish(
            exchange='',
            routing_key=self.request_queue_name,
            body=json.dumps(item)  
        )

    def enqueue_response(self, id, request, response):
        response_item = {
            'id': id,
            'request': request,
            'response': response
        }
        self.channel.basic_publish(
            exchange='',
            routing_key=self.response_queue_name,
            body=json.dumps(response_item)  # Serialize response_item as JSON
        )

    def dequeue_request(self):
        method_frame, _, body = self.channel.basic_get(queue=self.request_queue_name)
        if method_frame:
            self.channel.basic_ack(delivery_tag=method_frame.delivery_tag)
            return {**json.loads(body.decode())}  # Deserialize body as JSON
        else:
            return None

    def wait_for_request(self):
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue=self.request_queue_name,
            on_message_callback=self._request_callback,
            auto_ack=True  
        )
        self.channel.start_consuming()

    def _request_callback(self, ch, method, properties, body):
        self.request = json.loads(body.decode())
        ch.stop_consuming()

    def get_response_queue(self, id=None):
        response_queue = []
        for method_frame, _, body in self.channel.consume(self.response_queue_name, inactivity_timeout=0.5):
            if body is not None:
                response_item = json.loads(body.decode())  # Deserialize body as JSON
                if id is None or response_item['id'] == id:
                    response_queue.append(response_item)
                self.channel.basic_ack(delivery_tag=method_frame.delivery_tag)

        return response_queue

    def clear_response_queue(self):
        self.channel.queue_purge(queue=self.response_queue_name)


Requests = BaseRequests
BenchmarkTool = BaseBenchmarkTool
RandomnessApi = ApiSpecs