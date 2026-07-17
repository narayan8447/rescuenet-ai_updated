from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Citation(BaseModel):
    source_name: str
    chunk_id: str
    relevance_score: float
    text_snippet: str

class RAGQuery(BaseModel):
    query: str
    disaster_type: Optional[str] = None
    location: Optional[str] = None
    agency: Optional[str] = None
    top_k: int = 5

class RAGResponse(BaseModel):
    answer: str
    citations: List[Citation]
    confidence_score: float
    processing_time_ms: float

class DocumentChunk(BaseModel):
    id: str
    text: str
    metadata: Dict[str, Any]
    score: Optional[float] = None
