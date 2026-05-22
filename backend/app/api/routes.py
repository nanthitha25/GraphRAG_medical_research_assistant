import os
import shutil
import logging
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException

try:
    from app.utils.config import get_config
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    config = get_config()
except ImportError:
    logger = logging.getLogger(__name__)
    config = None

from app.api.schemas import (
    QueryRequest, QueryResponse, UploadResponse, 
    FeedbackRequest, FeedbackResponse, GraphResponse, 
    HealthResponse, AnalyticsResponse
)

from app.vectordb.chroma_store import ChromaStore
from app.graph.neo4j_store import Neo4jStore
from app.graph.entity_extractor import EntityExtractor
from app.pipelines.rag_pipeline import RagPipeline
from app.pipelines.ingestion_pipeline import IngestionPipeline
from app.feedback.feedback_store import FeedbackStore
from app.feedback.analytics import Analytics

router = APIRouter()

# Initialize dependencies with graceful fallbacks
try:
    chroma_path = config.chroma_path if config else os.environ.get("CHROMA_PATH", "data/chroma")
    chroma_store = ChromaStore(path=chroma_path)
except Exception as e:
    logger.error(f"Failed to initialize ChromaStore: {e}")
    chroma_store = None

try:
    neo4j_store = Neo4jStore()
except Exception as e:
    logger.error(f"Failed to initialize Neo4jStore: {e}")
    neo4j_store = None

try:
    entity_extractor = EntityExtractor()
except Exception as e:
    logger.error(f"Failed to initialize EntityExtractor: {e}")
    entity_extractor = None

try:
    feedback_store = FeedbackStore()
except Exception as e:
    logger.error(f"Failed to initialize FeedbackStore: {e}")
    feedback_store = None

try:
    rag_pipeline = RagPipeline(
        store=chroma_store, 
        neo4j_store=neo4j_store, 
        extractor=entity_extractor
    )
except Exception as e:
    logger.error(f"Failed to initialize RagPipeline: {e}")
    rag_pipeline = None

try:
    ingestion_pipeline = IngestionPipeline(
        chroma_store=chroma_store,
        neo4j_store=neo4j_store,
        extractor=entity_extractor
    ) if chroma_store else None
except Exception as e:
    logger.error(f"Failed to initialize IngestionPipeline: {e}")
    ingestion_pipeline = None

try:
    analytics = Analytics(feedback_store=feedback_store) if feedback_store else None
except Exception as e:
    logger.error(f"Failed to initialize Analytics: {e}")
    analytics = None

@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    if not rag_pipeline:
        raise HTTPException(status_code=500, detail="RagPipeline is not initialized")
    
    try:
        result = rag_pipeline.execute(request.query)
        return QueryResponse(
            answer=result.get("answer", ""),
            confidence=result.get("confidence", 0.0),
            hallucination_score=result.get("hallucination_score", 0.0),
            supported=result.get("supported", True),
            sources=result.get("sources", []),
            graph_paths=result.get("graph_paths", []),
            retrieval_stats=result.get("retrieval_stats", {})
        )
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    if not ingestion_pipeline:
        raise HTTPException(status_code=500, detail="IngestionPipeline is not initialized")
    
    upload_dir = "data/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        result = ingestion_pipeline.ingest_pdf(file_path)
        
        return UploadResponse(
            filename=result.filename,
            chunks_indexed=result.chunks_indexed,
            entities_found=result.entities_found,
            relationships_found=result.relationships_found,
            graph_nodes_created=result.graph_nodes_created,
            duration_seconds=result.duration_seconds,
            success=result.success,
            error=result.error
        )
    except Exception as e:
        logger.error(f"Error during upload/ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {file_path}: {e}")

@router.get("/graph", response_model=GraphResponse)
async def get_graph():
    if not neo4j_store or not neo4j_store.verify_connection():
        return GraphResponse(nodes=[], relationships=[], total_nodes=0, total_relationships=0)
    
    try:
        nodes = neo4j_store.get_all_nodes()
        relationships = neo4j_store.get_all_relationships()
        return GraphResponse(
            nodes=nodes,
            relationships=relationships,
            total_nodes=len(nodes),
            total_relationships=len(relationships)
        )
    except Exception as e:
        logger.error(f"Error fetching graph data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    if not feedback_store:
        raise HTTPException(status_code=500, detail="FeedbackStore is not initialized")
    
    try:
        success = feedback_store.update_rating(request.interaction_id, request.rating.value)
        return FeedbackResponse(
            success=success,
            message="Feedback updated successfully" if success else "Interaction not found"
        )
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health", response_model=HealthResponse)
async def health_check():
    chroma_chunks = chroma_store.count() if chroma_store else 0
    neo4j_connected = neo4j_store.verify_connection() if neo4j_store else False
    total_interactions = analytics.get_total_interactions() if analytics else 0
    
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        chroma_chunks=chroma_chunks,
        neo4j_connected=neo4j_connected,
        total_interactions=total_interactions
    )

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics():
    if not analytics:
        raise HTTPException(status_code=500, detail="Analytics module is not initialized")
    
    try:
        summary = analytics.get_summary()
        return AnalyticsResponse(**summary)
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/interactions")
async def get_interactions(limit: int = 20):
    if not feedback_store:
        raise HTTPException(status_code=500, detail="FeedbackStore is not initialized")
    
    try:
        return feedback_store.get_recent_interactions(limit)
    except Exception as e:
        logger.error(f"Error fetching interactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
