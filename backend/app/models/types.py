from pydantic import BaseModel, Field
from typing import Literal, Optional

class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User message for the chatbot")
    session_id: Optional[str] = Field("default", pattern=r"^[a-zA-Z0-9_-]{1,64}$", description="Unique session ID for chat history")

class IngestIn(BaseModel):
    dir_path: Optional[str] = Field(None, pattern=r"^(/?[a-zA-Z0-9_.-]+/?)*$", description="Directory path for data ingestion")

class ResetIn(BaseModel):
    session_id: Optional[str] = Field("default", pattern=r"^[a-zA-Z0-9_-]{1,64}$", description="Session ID to reset chat history")
    
class IntentOut(BaseModel):
    intent: Literal["patient_care", "general_info", "internal_ops"]
    confidence: float

class RouteOutput:
    def __init__(self, route: str, confidence: float):
        self.route = route
        self.confidence = confidence

class SetKeyReq(BaseModel):
    api_key: str = Field(..., pattern=r"^sk-[^\s]{20,}$", description="OpenAI API Key")