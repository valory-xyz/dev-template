import re
import pika
import json
from typing import Any

class InteractRabbitMQ:
    def __init__(self, *args:Any, **kwargs:Any):
        self.rabbitmq_host = kwargs.get('rabbitmq_host', 'localhost')
        self.rabbitmq_port = kwargs.get('rabbitmq_port', 5672)
        self.rabbitmq_username = kwargs.get('rabbitmq_username', 'guest')
        self.rabbitmq_password = kwargs.get('rabbitmq_password', 'guest')
        self.request_queue_name = kwargs.get('request_queue_name', 'request_queue')
        self.response_queue_name = kwargs.get('response_queue_name', 'response_queue')

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

    def enqueue_response(self, request_id, request, response):
        response_item = {
            'id': request_id,
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
            auto_ack=True  # Enable auto-acknowledgment
        )
        self.channel.start_consuming()

    def _request_callback(self, ch, method, properties, body):
        self.request = json.loads(body.decode())
        ch.stop_consuming()

    def get_response_queue(self, id=None):
        for method_frame, _, body in self.channel.consume(self.response_queue_name, inactivity_timeout=0.5):
            if body is not None:
                response_item = json.loads(body.decode())  # Deserialize body as JSON
                if response_item['id'] == id:
                    self.channel.basic_ack(delivery_tag=method_frame.delivery_tag)
                    return response_item

    def clear_response_queue(self):
        self.channel.queue_purge(queue=self.response_queue_name)
