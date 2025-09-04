from pydantic import BaseModel
from typing import Literal, Optional

class ChatIn(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class IngestIn(BaseModel):
    dir_path: Optional[str] = None

class ResetIn(BaseModel):
    session_id: Optional[str] = "default"
    
class IntentOut(BaseModel):
    intent: Literal["patient_care", "general_info", "internal_ops"]
    confidence: float

class RouteOutput:
    def __init__(self, route: str, confidence: float):
        self.route = route
        self.confidence = confidence

class SetKeyReq(BaseModel):
    api_key: str