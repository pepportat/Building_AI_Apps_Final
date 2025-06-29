from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class MeetingCreate(BaseModel):
    title: str

class ActionItem(BaseModel):
    task: str
    owner: Optional[str]
    deadline: Optional[str]

class Decision(BaseModel):
    decision: str
    context: Optional[str]

class MeetingResponse(BaseModel):
    id: int
    title: str
    audio_filename: Optional[str]
    transcription: Optional[str]
    summary: Optional[str]
    action_items: Optional[List[ActionItem]]
    decisions: Optional[List[Decision]]
    visual_summary_url: Optional[str]
    created_at: datetime
    language: str

class TranslationRequest(BaseModel):
    meeting_id: int
    target_language: str

class TranslationResponse(BaseModel):
    id: int
    meeting_id: int
    target_language: str
    translated_text: str
    created_at: datetime

class SearchQuery(BaseModel):
    query: str
    top_k: Optional[int] = 5

class SearchResult(BaseModel):
    meeting_id: int
    title: str
    excerpt: str
    similarity_score: float
    created_at: datetime