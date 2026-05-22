import json
from app.graph.entity_extractor import EntityExtractor
from app.graph.neo4j_store import Neo4jStore

def test_pipeline():
    extractor = EntityExtractor()
    neo4j_store = Neo4jStore()
    
    test_texts = [
        "Diabetes can lead to kidney disease.",
        "Insulin helps manage diabetes."
    ]
    
    print("\n--- TESTING ENTITY EXTRACTION ---")
    
    for text in test_texts:
        print(f"\nINPUT: {text}")
        extraction = extractor.extract(text)
        print("OUTPUT JSON:")
        print(json.dumps(extraction, indent=2))
        
        # Test Neo4j insertion
        is_running = neo4j_store.verify_connection()
        if is_running:
            neo4j_store.insert_graph_data(extraction)
            print("[✓] Inserted into Neo4j Graph Database.")
        else:
            print("[!] Neo4j is offline. Skipped DB insertion.")

if __name__ == "__main__":
    test_pipeline()
