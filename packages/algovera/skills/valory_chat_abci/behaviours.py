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

"""This package contains round behaviours of ValoryChatAbciApp."""

import json
import subprocess
import tempfile
import time
from abc import ABC
from pathlib import Path
from typing import Dict, Generator, List, Optional, Set, Type, Union, cast

from packages.algovera.connections.chat_completion.connection import (
    PUBLIC_ID as CHAT_COMPLETION_PUBLIC_ID,
)
from packages.algovera.protocols.chat_completion.dialogues import (
    ChatCompletionDialogue,
    ChatCompletionDialogues,
)
from packages.algovera.protocols.chat_completion.message import ChatCompletionMessage
from packages.algovera.skills.valory_chat_abci.models import Params, Requests
from packages.algovera.skills.valory_chat_abci.rounds import (
    ChatPayload,
    ChatRound,
    EmbeddingPayload,
    EmbeddingRound,
    SynchronizeEmbeddingsPayload,
    SynchronizeEmbeddingsRound,
    SynchronizeRequestsPayload,
    SynchronizeRequestsRound,
    SynchronizedData,
    ValoryChatAbciApp,
)
from packages.algovera.skills.valory_chat_abci.schemas import Chat, Embedding
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)
from packages.valory.skills.abstract_round_abci.io_.store import SupportedFiletype


class ValoryChatBaseBehaviour(BaseBehaviour, ABC):
    """Base behaviour for the valory_chat skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)


class ChatBehaviour(ValoryChatBaseBehaviour):
    """ChatBehaviour"""

    matching_round: Type[AbstractRound] = ChatRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            # Get the embedding_requests from the synchronized data
            requests: List = self.synchronized_data.chats
            self.context.logger.info(f"All Requests {requests}")

            # Get the request from the synchronized data matching the agent address if doesnt exist, None
            request = next(
                (
                    request
                    for request in requests
                    if request["processed"] == False
                    if request["processor"] == self.context.agent_address
                ),
                None,
            )

            # If there is a request process the request
            if request:
                if request["request_type"] == "chat":
                    request = Chat.parse_obj(request)

                    # Get c2e

                    c2e_ipfs_hash = self.synchronized_data.embedding[0]["c2e_ipfs_hash"]

                    # Get c2e
                    c2e = yield from self.get_from_ipfs(
                        c2e_ipfs_hash, SupportedFiletype.JSON
                    )
                    c2e = c2e["valory_chat_c2e.json"]

                self.context.logger.info(f"Processing request {request}")
                processed_request = yield from self.process_request(request, c2e)

                # Process the request
                processed_response = self.process_response(
                    processed_request.response, request
                )
                self.context.logger.info(f"Processed Response {processed_response}")

                # Prepare payload
                payload = ChatPayload(
                    sender=self.context.agent_address,
                    processed_chat=json.dumps(dict(processed_response)),
                )

            else:
                self.context.logger.info(f"No request to process")

                # Prepare payload
                payload = ChatPayload(
                    sender=self.context.agent_address,
                    processed_chat="",
                )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def process_request(
        self,
        chat: Chat,
        c2e: Optional[Dict] = None,
        timeout: Optional[float] = None,
    ) -> Generator:
        chat_completion_dialogues = cast(
            ChatCompletionDialogues, self.context.chat_completion_dialogues
        )
        """Get Request Package and make a request to the chat_completion skill"""

        # Prepare request package based on request type
        if type(chat) == Chat:
            self.context.logger.info(f"Processing chat request {chat}")
            request_package = self.prepare_chat(chat=chat, c2e=c2e)

        # chat completion request
        (
            request_chat_completion_message,
            chat_completion_dialogue,
        ) = chat_completion_dialogues.create(
            counterparty=str(CHAT_COMPLETION_PUBLIC_ID),
            performative=ChatCompletionMessage.Performative.REQUEST,
            request={
                "request": json.dumps(request_package),
            },
        )
        request_chat_completion_message = cast(
            ChatCompletionMessage, request_chat_completion_message
        )
        chat_completion_dialogue = cast(
            ChatCompletionDialogue, chat_completion_dialogue
        )
        self.context.outbox.put_message(message=request_chat_completion_message)

        # wait for chat completion response
        request_nonce = self._get_request_nonce_from_dialogue(chat_completion_dialogue)
        cast(Requests, self.context.requests).request_id_to_callback[
            request_nonce
        ] = self.get_callback_request()
        response = yield from self.wait_for_message(timeout=timeout)
        return response

    def process_response(self, response: Dict, request: Chat):
        """Process the response from the chat_completion skill"""

        if type(request) == Chat:
            if response["error"] == "False":
                self.context.logger.info(f"Processing chat response {response}")
                chat_history = response["chat_history"]
                answer = response["response"]
                query = response["modified_query"]

                if query != request.question:
                    request.modified_question = query

                request.chat_history = chat_history
                request.response = answer
                request.processed = True
                request.processor = self.context.agent_address
                request.response_time = str(time.time())

            else:
                request.processed = True
                request.processor = self.context.agent_address
                request.response_time = str(time.time())
                request.error = response["error"]
                request.error_message = response["error_message"]
                request.error_name = response["error_name"]

            return request

    def prepare_chat(self, chat: Chat, c2e: Dict) -> Dict:
        """Prepare the request package for the chat skill"""

        # Get chat_history
        memory_id = chat.memory_id

        # Check if memory is empty
        try:
            chat_history = self.synchronized_data.chat_histories[memory_id]
            self.context.logger.info(f"Retrieved chat history {chat_history}")
        except KeyError:
            chat_history = []

        # Retrieve relevant context
        request_package = {
            "question": chat.question,
            "chat_history": chat_history,
            "chunks_to_embeddings": c2e,
            "request_type": "chat",
        }
        return request_package


class EmbeddingBehaviour(ValoryChatBaseBehaviour):
    """EmbeddingBehaviour"""

    matching_round: Type[AbstractRound] = EmbeddingRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            # Get the embedding_requests from the synchronized data
            requests: List = self.synchronized_data.embedding
            self.context.logger.info(f"Requests {requests}")

            # Get the next request to process for the current agent if processed is False
            request = next(
                (
                    request
                    for request in requests
                    if request["processed"] == False
                    and request["processor"] == self.context.agent_address
                ),
                None,
            )

            if request:
                # If there is a request process the request
                request = Embedding.parse_obj(request)
                self.context.logger.info(f"Processing request {request}")

                # Process the request
                processed_request = yield from self.process_request(request)
                processed_response, c2e = self.process_response(
                    processed_request.response, request
                )
                # self.context.logger.info(f"Response {processed_response}")
                # self.context.logger.info(f"c2e {c2e}")

                # Add c2e to IPFS
                if c2e:
                    filename = "valory_chat_c2e.json"
                    ipfs_hash = yield from self.send_to_ipfs(
                        filename,
                        {filename: json.loads(c2e)},
                        filetype=SupportedFiletype.JSON,
                    )

                    # Add the IPFS hash to the processed request
                    processed_response.c2e_ipfs_hash = ipfs_hash
                    self.context.logger.info(f"IPFS hash {ipfs_hash}")
                    self.context.logger.info(f"Processed response {processed_response}")

                # Create payload
                payload = EmbeddingPayload(
                    sender=self.context.agent_address,
                    processed_embedding=json.dumps(dict(processed_response)),
                )

            else:
                self.context.logger.info(f"No request to process")
                payload = EmbeddingPayload(
                    sender=self.context.agent_address,
                    processed_embedding="",
                )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def process_request(
        self, embedding_request: Embedding, timeout: Optional[float] = None
    ) -> Generator:
        """Process the request."""

        chat_completion_dialogues = cast(
            ChatCompletionDialogues, self.context.chat_completion_dialogues
        )

        # Prepare for embedding request
        documents = self.get_github_docs()
        chunks = self.split_text_overlap(documents)
        self.context.logger.info(f"First Chunk {chunks[0]}")

        request_package = {"chunks": chunks, "request_type": "embedding"}

        # chat completion request
        (
            request_chat_completion_message,
            chat_completion_dialogue,
        ) = chat_completion_dialogues.create(
            counterparty=str(CHAT_COMPLETION_PUBLIC_ID),
            performative=ChatCompletionMessage.Performative.REQUEST,
            request={
                "request": json.dumps(request_package),
            },
        )
        request_chat_completion_message = cast(
            ChatCompletionMessage, request_chat_completion_message
        )

        chat_completion_dialogue = cast(
            ChatCompletionDialogue, chat_completion_dialogue
        )
        self.context.outbox.put_message(message=request_chat_completion_message)

        # wait for chat completion response
        request_nonce = self._get_request_nonce_from_dialogue(chat_completion_dialogue)

        cast(Requests, self.context.requests).request_id_to_callback[
            request_nonce
        ] = self.get_callback_request()

        response = yield from self.wait_for_message(timeout=timeout)

        return response

    def get_github_docs(self, wildcards: Optional[List[str]] = None) -> List[str]:
        """Get the github docs from the github repo."""
        repo_url = "https://github.com/valory-xyz/docs.git"
        repo_url = repo_url.replace(".git", "")
        url_parts = repo_url.split("/")
        if len(url_parts) < 5 or not url_parts[2].endswith("github.com"):
            raise ValueError("Invalid GitHub URL format")

        repo_owner = url_parts[3]
        repo_name = url_parts[4]

        if len(url_parts) > 6 and url_parts[5] == "tree":
            branch = "/".join(url_parts[6:])
        else:
            branch = None

        repo_url = f"https://github.com/{repo_owner}/{repo_name}"
        if not repo_url.endswith(".git"):
            repo_url += ".git"

        with tempfile.TemporaryDirectory() as d:
            if branch is not None:
                git_command = f"git clone --depth 1 -b {branch} {repo_url} ."
            else:
                git_command = f"git clone --depth 1 {repo_url} ."

            subprocess.check_call(
                git_command,
                cwd=d,
                shell=True,
            )

            # Initialize and pull submodules
            subprocess.check_call(
                "git submodule update --init --recursive", cwd=d, shell=True
            )

            git_sha = (
                subprocess.check_output("git rev-parse HEAD", shell=True, cwd=d)
                .decode("utf-8")
                .strip()
            )

            repo_path = Path(d)
            markdown_files = list(repo_path.glob("**/*.md")) + list(
                repo_path.glob("**/*.mdx")
            )

            documents = []
            for markdown_file in markdown_files:
                with open(markdown_file, "r") as f:
                    relative_path = markdown_file.relative_to(repo_path)
                    github_url = f"https://github.com/{repo_owner}/{repo_name}/blob/{git_sha}/{relative_path}"
                    read = f.read()
                    documents.append((read, github_url))

        return documents

    def process_response(self, response: dict, embedding_request: Embedding):
        """Process the response from the chat skill"""

        if response["error"] == "False":
            chunks_to_embeddings = response["chunks_to_embeddings"]
            embedding_request.processed = True
            embedding_request.processor = self.context.agent_address
            embedding_request.error = False
            embedding_request.response_time = str(time.time())
            embedding_request.documents = []

        else:
            embedding_request.processed = True
            embedding_request.processor = self.context.agent_address
            embedding_request.response_time = str(time.time())
            embedding_request.error = response["error"]
            embedding_request.error_message = response["error_message"]
            embedding_request.error_name = response["error_name"]
            embedding_request.documents = []
            chunks_to_embeddings = None

        return embedding_request, chunks_to_embeddings

    def split_text_overlap(
        self, documents: List, max_chunk_size=1200, chunk_overlap=10
    ):
        chunks = []
        for doc, url in documents:
            words = doc.split(" ")
            current_chunk = ""

            for word in words:
                if len(current_chunk) + len(word) <= max_chunk_size:
                    current_chunk += " " + word
                else:
                    # Before adding the chunk to the list, add the url at the end of the chunk
                    current_chunk += " Source: " + url
                    chunks.append(current_chunk)
                    current_chunk = (
                        " ".join(current_chunk.split(" ")[-chunk_overlap:]) + " " + word
                    )
            # Add the last chunk
            current_chunk += " Source: " + url
            chunks.append(current_chunk)

        self.context.logger.info(
            f"Split {len(documents)} documents into {len(chunks)} chunks"
        )
        return chunks


class SynchronizeEmbeddingsBehaviour(ValoryChatBaseBehaviour):
    """SynchronizeEmbeddingsBehaviour"""

    matching_round: Type[AbstractRound] = SynchronizeEmbeddingsRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            # Check if there are new embedding requests
            if self.context.state.new_embedding_requests:
                new_embedding_requests = json.dumps(
                    self.context.state.new_embedding_requests
                )
                self.context.state.new_embedding_requests = []
            else:
                new_embedding_requests = None

            # Create payload
            pl = {}
            if new_embedding_requests:
                pl["new_embedding_requests"] = new_embedding_requests

            sender = self.context.agent_address
            payload = SynchronizeEmbeddingsPayload(sender=sender, **pl)
            self.context.logger.info(
                f"New embedding requests = {new_embedding_requests}"
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class SynchronizeRequestsBehaviour(ValoryChatBaseBehaviour):
    """SynchronizeRequestsBehaviour"""

    matching_round: Type[AbstractRound] = SynchronizeRequestsRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            # Check if there are new embedding requests
            if self.context.state.new_chat_requests:
                new_chat_requests = json.dumps(self.context.state.new_chat_requests)
                self.context.state.new_chat_requests = []
            else:
                new_chat_requests = None

            # Create payload
            pl = {}
            if new_chat_requests:
                pl["new_chat_requests"] = new_chat_requests

            sender = self.context.agent_address
            payload = SynchronizeRequestsPayload(sender=sender, **pl)
            self.context.logger.info(f"New chat requests = {new_chat_requests}")

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class ValoryChatRoundBehaviour(AbstractRoundBehaviour):
    """ValoryChatRoundBehaviour"""

    initial_behaviour_cls = SynchronizeEmbeddingsBehaviour
    abci_app_cls = ValoryChatAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [
        ChatBehaviour,
        EmbeddingBehaviour,
        SynchronizeEmbeddingsBehaviour,
        SynchronizeRequestsBehaviour,
    ]
