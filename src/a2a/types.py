"""
A2A (Agent-to-Agent) protocol types per the Google A2A spec.
https://google.github.io/A2A/
"""
from __future__ import annotations
from pydantic import BaseModel, field_validator
from typing import Any, Optional, Union, Literal
from enum import Enum
import uuid
from datetime import datetime, timezone


class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class AgentCapabilities(BaseModel):
    streaming: bool = False
    pushNotifications: bool = False
    stateTransitionHistory: bool = False


class AgentSkill(BaseModel):
    id: str
    name: str
    description: str
    inputModes: list[str] = ["text", "data"]
    outputModes: list[str] = ["text", "data"]
    tags: list[str] = []


class AgentCard(BaseModel):
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    capabilities: AgentCapabilities = AgentCapabilities()
    skills: list[AgentSkill] = []
    defaultInputModes: list[str] = ["text", "data"]
    defaultOutputModes: list[str] = ["text", "data"]


class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str


class DataPart(BaseModel):
    type: Literal["data"] = "data"
    data: dict[str, Any]


Part = Union[TextPart, DataPart]


class Message(BaseModel):
    role: str  # "user" | "agent"
    parts: list[Part]

    @field_validator("parts", mode="before")
    @classmethod
    def coerce_parts(cls, v: list) -> list:
        result = []
        for item in v:
            if isinstance(item, (TextPart, DataPart)):
                result.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "data":
                    result.append(DataPart(**item))
                else:
                    result.append(TextPart(**item))
        return result


class TaskStatus(BaseModel):
    state: TaskState
    message: Optional[Message] = None
    timestamp: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class Task(BaseModel):
    id: str = ""
    sessionId: str = ""
    status: TaskStatus
    history: list[Message] = []
    metadata: dict[str, Any] = {}

    def model_post_init(self, __context: Any) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.sessionId:
            self.sessionId = self.id


class SendTaskRequest(BaseModel):
    id: str = ""
    sessionId: str = ""
    message: Message
    metadata: dict[str, Any] = {}

    def model_post_init(self, __context: Any) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())


class SendTaskResponse(BaseModel):
    id: str
    result: Optional[Task] = None
    error: Optional[dict[str, Any]] = None
