from app.embeddings.embedder import create_embeddings
from app.vectordb.chroma_store import ChromaStore
from app.graph.neo4j_store import Neo4jStore
from app.graph.entity_extractor import EntityExtractor

class SemanticRetriever:
    def __init__(self, store: ChromaStore):
        self.store = store

    def retrieve(self, query: str, top_k: int = 5):
        """
        Embeds the user query and searches the vector database
        for the most semantically related chunks using cosine similarity.
        """
        query_embedding = create_embeddings([query])[0]
        results = self.store.query(query_embedding, n_results=top_k)
        
        retrieved_chunks = []
        if results and "documents" in results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                retrieved_chunks.append(doc)
                
        return retrieved_chunks


class HybridRetriever(SemanticRetriever):
    """
    Upgraded retriever that combines Semantic Vector Search with 
    Multi-Hop Graph Reasoning from Neo4j.
    """
    def __init__(self, store: ChromaStore, neo4j_store: Neo4jStore, extractor: EntityExtractor):
        super().__init__(store)
        self.neo4j_store = neo4j_store
        self.extractor = extractor

    def graph_retrieve(self, query: str):
        """
        Extracts entities from the query and performs a multi-hop traversal in the graph.
        """
        # 1. Extract entities from the user's query
        extraction = self.extractor.extract(query)
        entities = extraction.get("entities", [])
        
        graph_context = []
        if not entities:
            return graph_context
            
        # 2. Traverse relationships in Neo4j (Multi-hop reasoning)
        try:
            with self.neo4j_store.driver.session() as session:
                for entity in entities:
                    # Cypher query: Find the entity and traverse up to 2 relationship hops
                    cypher = """
                    MATCH p=(n:MedicalEntity)-[*1..2]-(m:MedicalEntity)
                    WHERE toLower(n.name) CONTAINS toLower($entity)
                    UNWIND relationships(p) AS rel
                    RETURN startNode(rel).name AS source, type(rel) AS relationship, endNode(rel).name AS target
                    LIMIT 5
                    """
                    results = session.run(cypher, entity=entity)
                    for record in results:
                        context = f"{record['source']} -[{record['relationship']}]-> {record['target']}"
                        graph_context.append(context)
        except Exception as e:
            print(f"Error querying Neo4j (is it running?): {e}")
                    
        return list(set(graph_context))
        
    def retrieve_hybrid(self, query: str, top_k: int = 5):
        """
        Returns both vector similarity results and graph traversal results.
        """
        # Get semantic chunks
        vector_results = super().retrieve(query, top_k)
        
        # Get graph connections
        graph_results = self.graph_retrieve(query)
            
        return {
            "vector_context": vector_results,
            "graph_context": graph_results
        }
