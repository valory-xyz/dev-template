import time
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class RequestType(str, Enum):
    EMBEDDING = "embedding"
    CHAT = "chat"


def get_time():
    return str(time.time())


class Embedding(BaseModel):
    documents: List = Field(..., description="Documents to be used for embedding")
    request_time: str = Field(default_factory=get_time, description="Request time")
    c2e_ipfs_hash: Optional[str] = Field(default=None, description="C2E ipfs hash")
    response_time: Optional[str] = Field(default=None, description="Response time")
    request_type: RequestType = RequestType.EMBEDDING
    processed: bool = Field(default=False, description="Processed flag")
    processor: Optional[str] = Field(default=None, description="Processor name")
    error: bool = Field(default=False, description="Error flag")
    error_message: Optional[str] = Field(default=None, description="Error message")
    error_name: Optional[str] = Field(default=None, description="Error name")


class Chat(BaseModel):
    id: str = Field(..., description="Request job id")
    memory_id: str = Field(..., description="Memory id")
    question: str = Field(..., description="Question")
    modified_question: Optional[str] = Field(
        default=None, description="Modified question"
    )
    response: Optional[str] = Field(default=None, description="Response")
    chat_history: list = Field(default=[], description="Chat history")
    request_time: str = Field(default_factory=get_time, description="Request time")
    response_time: Optional[str] = Field(default=None, description="Response time")
    request_type: RequestType = RequestType.CHAT
    processed: bool = Field(default=False, description="Processed flag")
    processor: Optional[str] = Field(default=None, description="Processor name")
    error: bool = Field(default=False, description="Error flag")
    error_message: Optional[str] = Field(default=None, description="Error message")
    error_name: Optional[str] = Field(default=None, description="Error name")
