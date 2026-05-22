"""
app/graph/neo4j_store.py

Neo4j wrapper for the GraphRAG Medical Research Assistant.

Connection parameters are resolved (in order) from:
  1. Constructor arguments
  2. Environment variables NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD
  3. Hard-coded defaults (bolt://localhost:7687 / neo4j / password)

All public methods degrade gracefully when Neo4j is unavailable —
they log a warning and return empty collections instead of raising.
"""

import logging
import os
from typing import Any

try:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)

try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable, AuthError
    _NEO4J_AVAILABLE = True
except ImportError:
    _NEO4J_AVAILABLE = False
    logger.warning(
        "neo4j package not installed — Neo4jStore will operate in stub mode."
    )


class Neo4jStore:
    """
    Thin wrapper around the Neo4j Python driver providing typed node/
    relationship CRUD and graph-exploration helpers.

    Parameters
    ----------
    uri:
        Bolt URI of the Neo4j instance.
        Falls back to ``NEO4J_URI`` env-var or ``bolt://localhost:7687``.
    user:
        Database username.
        Falls back to ``NEO4J_USER`` env-var or ``neo4j``.
    password:
        Database password.
        Falls back to ``NEO4J_PASSWORD`` env-var or ``password``.
    """

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self.uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.environ.get("NEO4J_USER", "neo4j")
        _password = password or os.environ.get("NEO4J_PASSWORD", "password")

        self._driver = None

        if not _NEO4J_AVAILABLE:
            logger.error(
                "neo4j package not available — all graph operations will be no-ops."
            )
            return

        try:
            self._driver = GraphDatabase.driver(
                self.uri, auth=(self.user, _password)
            )
            logger.info(
                "[Neo4jStore] Driver created — URI: %s, user: %s", self.uri, self.user
            )
        except Exception as exc:
            logger.warning(
                "[Neo4jStore] Driver creation failed (URI=%s): %s", self.uri, exc
            )

    # ── Compatibility property ─────────────────────────────────────────────────

    @property
    def driver(self):
        """Expose raw driver for backward compatibility with RagPipeline."""
        return self._driver

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying driver connection pool."""
        if self._driver:
            try:
                self._driver.close()
                logger.info("[Neo4jStore] Driver closed.")
            except Exception as exc:
                logger.error("[Neo4jStore] close() failed: %s", exc, exc_info=True)

    # ── Connectivity ──────────────────────────────────────────────────────────

    def verify_connection(self) -> bool:
        """
        Return *True* if Neo4j is reachable, *False* otherwise.

        Never raises — always safe to call before other operations.
        """
        if self._driver is None:
            logger.debug("[Neo4jStore] verify_connection: driver not initialised.")
            return False
        try:
            self._driver.verify_connectivity()
            logger.info("[Neo4jStore] Connectivity verified.")
            return True
        except Exception as exc:
            logger.warning("[Neo4jStore] Connectivity check failed: %s", exc)
            return False

    # ── Write operations ──────────────────────────────────────────────────────

    def insert_graph_data(self, extraction_data: dict) -> None:
        """
        Merge entities (typed nodes) and relationships from the EntityExtractor
        output into Neo4j.

        Parameters
        ----------
        extraction_data:
            Dict with optional keys:
            - ``"entities"``      : list of ``{name, type}`` dicts
            - ``"relationships"`` : list of ``{source, relation, target}`` dicts
        """
        entities = extraction_data.get("entities", [])
        relationships = extraction_data.get("relationships", [])

        if not entities and not relationships:
            logger.debug("[Neo4jStore] insert_graph_data: empty payload — skipping.")
            return

        if not self.verify_connection():
            logger.warning(
                "[Neo4jStore] insert_graph_data skipped — Neo4j unavailable."
            )
            return

        try:
            with self._driver.session() as session:
                # 1. Create/Merge typed entity nodes
                for entity in entities:
                    name = entity.get("name")
                    entity_type = entity.get("type", "Entity").replace(" ", "")
                    if name:
                        cypher = f"MERGE (n:{entity_type} {{name: $name}})"
                        session.run(cypher, name=name)

                # 2. Create/Merge relationships
                for rel in relationships:
                    source = rel.get("source")
                    relation = (
                        rel.get("relation", "RELATED_TO").upper().replace(" ", "_")
                    )
                    target = rel.get("target")
                    if source and target:
                        cypher = f"""
                        MATCH (a {{name: $source}})
                        MATCH (b {{name: $target}})
                        MERGE (a)-[r:{relation}]->(b)
                        """
                        session.run(cypher, source=source, target=target)

            logger.info(
                "[Neo4jStore] Inserted %d entity(ies) and %d relationship(s).",
                len(entities),
                len(relationships),
            )
        except Exception as exc:
            logger.error(
                "[Neo4jStore] insert_graph_data failed: %s", exc, exc_info=True
            )

    # ── Read operations ───────────────────────────────────────────────────────

    def get_all_nodes(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Return every node in the graph as a list of dicts, up to *limit*.

        Each dict contains:
        - ``name``   : the node's ``name`` property (empty string if absent)
        - ``labels`` : list[str] of Neo4j labels on the node

        Returns an empty list when Neo4j is unavailable or on error.

        Parameters
        ----------
        limit:
            Maximum number of nodes to return (default 100).
        """
        if not self.verify_connection():
            logger.warning("[Neo4jStore] get_all_nodes skipped — Neo4j unavailable.")
            return []

        try:
            with self._driver.session() as session:
                result = session.run(
                    "MATCH (n) RETURN labels(n) AS labels, n.name AS name LIMIT $limit",
                    limit=limit,
                )
                nodes = [
                    {
                        "name": record["name"] or "",
                        "labels": list(record["labels"]) if record["labels"] else [],
                    }
                    for record in result
                ]
            logger.info("[Neo4jStore] get_all_nodes: retrieved %d node(s).", len(nodes))
            return nodes
        except Exception as exc:
            logger.error(
                "[Neo4jStore] get_all_nodes failed: %s", exc, exc_info=True
            )
            return []

    def get_all_relationships(self, limit: int = 200) -> list[dict[str, Any]]:
        """
        Return every relationship in the graph as a list of dicts, up to *limit*.

        Each dict contains:
        - ``source``   : ``name`` of the start node
        - ``relation`` : relationship type string
        - ``target``   : ``name`` of the end node

        Returns an empty list when Neo4j is unavailable or on error.

        Parameters
        ----------
        limit:
            Maximum number of relationships to return (default 200).
        """
        if not self.verify_connection():
            logger.warning(
                "[Neo4jStore] get_all_relationships skipped — Neo4j unavailable."
            )
            return []

        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (a)-[r]->(b)
                    RETURN a.name AS source, type(r) AS relation, b.name AS target
                    LIMIT $limit
                    """,
                    limit=limit,
                )
                rels = [
                    {
                        "source": record["source"] or "",
                        "relation": record["relation"] or "",
                        "target": record["target"] or "",
                    }
                    for record in result
                ]
            logger.info(
                "[Neo4jStore] get_all_relationships: retrieved %d relationship(s).",
                len(rels),
            )
            return rels
        except Exception as exc:
            logger.error(
                "[Neo4jStore] get_all_relationships failed: %s", exc, exc_info=True
            )
            return []

    def get_subgraph(
        self, entity_name: str, depth: int = 2
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Return the subgraph centred on *entity_name* up to *depth* hops.

        Suitable for adaptive retrieval — provides the LLM with local graph
        context around a named entity without returning the full graph.

        Parameters
        ----------
        entity_name:
            The ``name`` property of the anchor node.
        depth:
            Traversal depth (clamped to [1, 5] to avoid runaway queries).

        Returns
        -------
        dict with two keys:
        - ``nodes``         : list of ``{name, labels}`` dicts
        - ``relationships`` : list of ``{source, relation, target}`` dicts

        Both lists are empty when Neo4j is unavailable or on error.
        """
        empty: dict[str, list] = {"nodes": [], "relationships": []}

        if not self.verify_connection():
            logger.warning(
                "[Neo4jStore] get_subgraph skipped — Neo4j unavailable."
            )
            return empty

        # Clamp depth to a safe range
        depth = max(1, min(depth, 5))

        try:
            with self._driver.session() as session:
                # All nodes reachable within `depth` hops (bidirectional)
                node_result = session.run(
                    f"""
                    MATCH path = (anchor {{name: $name}})-[*1..{depth}]-(neighbour)
                    UNWIND nodes(path) AS n
                    RETURN DISTINCT n.name AS name, labels(n) AS labels
                    """,
                    name=entity_name,
                )
                nodes = [
                    {
                        "name": r["name"] or "",
                        "labels": list(r["labels"]) if r["labels"] else [],
                    }
                    for r in node_result
                ]

                # All relationships on those paths
                rel_result = session.run(
                    f"""
                    MATCH path = (anchor {{name: $name}})-[*1..{depth}]-(neighbour)
                    UNWIND relationships(path) AS rel
                    RETURN DISTINCT
                        startNode(rel).name AS source,
                        type(rel)           AS relation,
                        endNode(rel).name   AS target
                    """,
                    name=entity_name,
                )
                rels = [
                    {
                        "source": r["source"] or "",
                        "relation": r["relation"] or "",
                        "target": r["target"] or "",
                    }
                    for r in rel_result
                ]

            logger.info(
                "[Neo4jStore] get_subgraph('%s', depth=%d): %d node(s), %d rel(s).",
                entity_name,
                depth,
                len(nodes),
                len(rels),
            )
            return {"nodes": nodes, "relationships": rels}

        except Exception as exc:
            logger.error(
                "[Neo4jStore] get_subgraph('%s', depth=%d) failed: %s",
                entity_name,
                depth,
                exc,
                exc_info=True,
            )
            return empty
