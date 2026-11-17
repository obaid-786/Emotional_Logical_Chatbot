from pydantic import BaseModel, Field
from typing import Literal, Optional

class MessageAnalysis(BaseModel):
    emotion: Literal["angry","frustrated","confused","sad","anxious","happy","neutral"]
    intent:  Literal["question","complaint","request_help","chat","sensitive"]
    confidence: float = Field(ge=0.0, le=1.0)

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str

class FeedbackRequest(BaseModel):
    interaction_id: int
    rating: Literal["up","down"]
    comment: Optional[str] = None

class ResetRequest(BaseModel):
    session_id: str