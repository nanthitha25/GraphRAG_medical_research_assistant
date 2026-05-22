from app.vectordb.chroma_store import ChromaStore
from app.graph.entity_extractor import EntityExtractor
from app.graph.neo4j_store import Neo4jStore
from app.pipelines.rag_pipeline import RagPipeline

def test_elite_architecture():
    print("\n=== INITIALIZING ELITE GRAPHRAG SYSTEM ===")
    
    store = ChromaStore(path="data/chroma", collection_name="medical_test")
    extractor = EntityExtractor()
    neo4j_store = Neo4jStore()
    
    pipeline = RagPipeline(store=store, neo4j_store=neo4j_store, extractor=extractor)
    
    query = "How does diabetes affect kidneys and what treatments help?"
    
    print(f"\n[USER QUERY]: {query}")
    print("[SYSTEM]: Executing Self-Correcting Orchestrator...")
    
    result = pipeline.execute(query)
    
    print("\n=== PIPELINE EXECUTION COMPLETE ===")
    print(f"CONFIDENCE SCORE : {result['confidence']:.2f}")
    
    print("\n--- FINAL ANSWER ---")
    print(result['answer'])
    
    print("\n--- SOURCES USED ---")
    print(f"Semantic Chunks: {len(result['sources'])}")
    print(f"Graph Paths: {len(result['graph_paths'])}")
    
if __name__ == "__main__":
    test_elite_architecture()
