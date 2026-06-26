from typing import Literal
from pydantic import BaseModel


class ToolCall(BaseModel):
    function: str
    describe: str
    parameter: dict


class ConversationResponse(BaseModel):
    message: str
    feeling: Literal["happy", "curious", "neutral", "sad", "excited", "confused"]
