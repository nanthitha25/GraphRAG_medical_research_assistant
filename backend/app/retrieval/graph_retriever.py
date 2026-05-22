from app.graph.neo4j_store import Neo4jStore
from app.graph.entity_extractor import EntityExtractor

class GraphRetriever:
    def __init__(self, neo4j_store: Neo4jStore, extractor: EntityExtractor):
        self.neo4j_store = neo4j_store
        self.extractor = extractor

    def retrieve(self, query: str):
        """
        Extracts entities from the query and performs a multi-hop traversal in the graph.
        Returns a list of relationship strings.
        """
        # Extract entities from the user's query
        extraction = self.extractor.extract(query)
        entities = extraction.get("entities", [])
        
        graph_context = []
        if not entities:
            return graph_context
            
        # Traverse relationships in Neo4j (Multi-hop reasoning)
        try:
            with self.neo4j_store.driver.session() as session:
                for entity_dict in entities:
                    entity_name = entity_dict.get("name")
                    if not entity_name:
                        continue
                        
                    # Advanced Cypher query: Find the entity and traverse up to 2 relationship hops
                    cypher = """
                    MATCH p=(n)-[*1..2]-(m)
                    WHERE toLower(n.name) CONTAINS toLower($entity)
                    UNWIND relationships(p) AS rel
                    RETURN startNode(rel).name AS source, type(rel) AS relationship, endNode(rel).name AS target
                    LIMIT 10
                    """
                    results = session.run(cypher, entity=entity_name)
                    for record in results:
                        context = f"{record['source']} -> {record['relationship']} -> {record['target']}"
                        graph_context.append(context)
        except Exception as e:
            # Catching connection errors seamlessly
            pass
            
        # Return unique graph connections
        return list(set(graph_context))

    def get_mock_graph_results(self, query: str):
        """
        Mock graph reasoning for testing without an active Neo4j container.
        This simulates the multi-hop output.
        """
        if "diabetes" in query.lower() and "kidney" in query.lower():
            return [
                "Diabetes -> CAUSES -> Kidney Disease",
                "ACE Inhibitors -> TREATS -> Kidney Disease"
            ]
        return []
