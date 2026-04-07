from pydantic import BaseModel, Field
from typing import List, Optional


class Triple(BaseModel):
    head: str
    head_type: str = "Entity"
    relation: str
    tail: str
    tail_type: str = "Entity"
    source: str = ""


class DocumentUploadResponse(BaseModel):
    filename: str
    content_length: int
    message: str


class ExtractionRequest(BaseModel):
    file_path: str
    chunk_size: int = Field(default=2000, ge=500, le=5000)
    overlap: int = Field(default=200, ge=0, le=500)


class ExtractionResponse(BaseModel):
    total_chunks: int
    total_triples: int
    triples: List[Triple]


class GraphDataResponse(BaseModel):
    nodes: List[dict]
    links: List[dict]


class QARequest(BaseModel):
    question: str
    use_kg_only: bool = False


class QAResponse(BaseModel):
    answer: str
    source: str
    related_triples: List[Triple] = []
