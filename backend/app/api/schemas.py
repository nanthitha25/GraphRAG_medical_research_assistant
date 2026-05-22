from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, description="The medical research query")
    expand_graph: bool = Field(default=False, description="Force expanded graph traversal")

class QueryResponse(BaseModel):
    answer: str
    confidence: float
    hallucination_score: float
    supported: bool
    sources: List[dict]
    graph_paths: List[str]
    retrieval_stats: dict

class UploadResponse(BaseModel):
    filename: str
    chunks_indexed: int
    entities_found: int
    relationships_found: int
    graph_nodes_created: int
    duration_seconds: float
    success: bool
    error: Optional[str] = None

class RatingEnum(str, Enum):
    helpful = "helpful"
    inaccurate = "inaccurate"
    hallucinated = "hallucinated"

class FeedbackRequest(BaseModel):
    interaction_id: int
    rating: RatingEnum

class FeedbackResponse(BaseModel):
    success: bool
    message: str

class GraphNode(BaseModel):
    name: str
    labels: List[str] = []

class GraphRelationship(BaseModel):
    source: str
    relation: str
    target: str

class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    relationships: List[GraphRelationship]
    total_nodes: int
    total_relationships: int

class HealthResponse(BaseModel):
    status: str
    version: str
    chroma_chunks: int
    neo4j_connected: bool
    total_interactions: int

class AnalyticsResponse(BaseModel):
    total_interactions: int
    hallucination_rate: float
    avg_confidence: float
    user_satisfaction_rate: float
    low_performing_queries: List[dict]
