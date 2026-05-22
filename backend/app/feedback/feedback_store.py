"""
app/feedback/feedback_store.py

SQLite-backed store that persists every RAG interaction together with
hallucination flags, confidence scores, and optional user ratings for
self-improvement analytics.

Schema migration strategy
-------------------------
``_migrate_schema()`` inspects ``PRAGMA table_info`` after ``_init_db()``
runs.  If ``user_rating`` is not already TEXT it renames the old table,
recreates the schema with the correct type, copies all rows (casting
``user_rating`` to TEXT), and drops the old table — all inside a single
transaction so any failure rolls back cleanly.
"""

import logging
import os
import sqlite3
from typing import Any, Optional

try:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


class FeedbackStore:
    """
    Stores queries, contexts, answers, and evaluations for self-improvement
    analytics.

    All interactions are persisted in a local SQLite database so that the
    analytics engine and adaptive retriever can surface performance trends
    without requiring an external service.

    Valid values for ``user_rating``:
        - ``"helpful"``
        - ``"inaccurate"``
        - ``"hallucinated"``
    """

    VALID_RATINGS = frozenset({"helpful", "inaccurate", "hallucinated"})

    def __init__(self, db_path: str = "data/feedback.db") -> None:
        self.db_path = db_path
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._init_db()
        self._migrate_schema()
        logger.info("[FeedbackStore] Initialised at %s", self.db_path)

    # ------------------------------------------------------------------
    # Schema helpers
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Create the interactions table if it does not already exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS interactions (
                        id               INTEGER PRIMARY KEY AUTOINCREMENT,
                        query            TEXT,
                        context          TEXT,
                        answer           TEXT,
                        is_hallucinated  BOOLEAN,
                        confidence_score REAL,
                        user_rating      TEXT,
                        timestamp        DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.commit()
            logger.debug("[FeedbackStore] _init_db: table verified/created.")
        except Exception as exc:
            logger.error("[FeedbackStore] _init_db failed: %s", exc, exc_info=True)

    def _migrate_schema(self) -> None:
        """
        Migrate ``user_rating`` from INTEGER (legacy) to TEXT if needed.

        Uses a rename-recreate-copy-drop pattern inside a transaction so
        the migration is atomic and existing data is preserved.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                info = conn.execute("PRAGMA table_info(interactions)").fetchall()
                col_types = {row[1]: row[2].upper() for row in info}

            rating_type = col_types.get("user_rating", "TEXT")
            if rating_type == "TEXT":
                logger.debug(
                    "[FeedbackStore] _migrate_schema: user_rating already TEXT — skipping."
                )
                return

            logger.info(
                "[FeedbackStore] _migrate_schema: migrating user_rating from %s to TEXT.",
                rating_type,
            )

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("BEGIN")
                try:
                    conn.execute(
                        "ALTER TABLE interactions RENAME TO _interactions_old"
                    )
                    conn.execute(
                        """
                        CREATE TABLE interactions (
                            id               INTEGER PRIMARY KEY AUTOINCREMENT,
                            query            TEXT,
                            context          TEXT,
                            answer           TEXT,
                            is_hallucinated  BOOLEAN,
                            confidence_score REAL,
                            user_rating      TEXT,
                            timestamp        DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                    conn.execute(
                        """
                        INSERT INTO interactions
                            (id, query, context, answer, is_hallucinated,
                             confidence_score, user_rating, timestamp)
                        SELECT
                            id, query, context, answer, is_hallucinated,
                            confidence_score, CAST(user_rating AS TEXT), timestamp
                        FROM _interactions_old
                        """
                    )
                    conn.execute("DROP TABLE _interactions_old")
                    conn.execute("COMMIT")
                    logger.info(
                        "[FeedbackStore] _migrate_schema: migration completed successfully."
                    )
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
        except Exception as exc:
            logger.error(
                "[FeedbackStore] _migrate_schema failed: %s", exc, exc_info=True
            )

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def log_interaction(
        self,
        query: str,
        context: str,
        answer: str,
        is_hallucinated: bool,
        confidence_score: float,
    ) -> Optional[int]:
        """
        Persist a single RAG interaction.

        Parameters
        ----------
        query:
            The user's raw query string.
        context:
            The retrieved context passages (joined as a single string).
        answer:
            The LLM-generated answer.
        is_hallucinated:
            Whether the evaluator flagged a hallucination.
        confidence_score:
            Float confidence score in [0.0, 1.0].

        Returns
        -------
        int | None
            The new row's integer ID, or None on failure.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO interactions
                        (query, context, answer, is_hallucinated, confidence_score)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (query, context, answer, is_hallucinated, confidence_score),
                )
                conn.commit()
                row_id: int = cursor.lastrowid  # type: ignore[assignment]
            logger.info(
                "[FeedbackStore] log_interaction: saved interaction id=%d.", row_id
            )
            return row_id
        except Exception as exc:
            logger.error(
                "[FeedbackStore] log_interaction failed: %s", exc, exc_info=True
            )
            return None

    def update_rating(self, interaction_id: int, rating: str) -> bool:
        """
        Attach a user rating to an existing interaction.

        Parameters
        ----------
        interaction_id:
            Primary key of the target interaction row.
        rating:
            One of ``"helpful"``, ``"inaccurate"``, or ``"hallucinated"``.

        Returns
        -------
        bool
            *True* if the row was found and updated, *False* otherwise
            (including invalid rating values).
        """
        if rating not in self.VALID_RATINGS:
            logger.warning(
                "[FeedbackStore] update_rating: invalid rating '%s'. "
                "Must be one of %s.",
                rating,
                sorted(self.VALID_RATINGS),
            )
            return False

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "UPDATE interactions SET user_rating = ? WHERE id = ?",
                    (rating, interaction_id),
                )
                conn.commit()
                updated = cursor.rowcount > 0

            if updated:
                logger.info(
                    "[FeedbackStore] update_rating: interaction id=%d rated '%s'.",
                    interaction_id,
                    rating,
                )
            else:
                logger.warning(
                    "[FeedbackStore] update_rating: no row found for id=%d.",
                    interaction_id,
                )
            return updated
        except Exception as exc:
            logger.error(
                "[FeedbackStore] update_rating(id=%d, rating='%s') failed: %s",
                interaction_id,
                rating,
                exc,
                exc_info=True,
            )
            return False

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    @staticmethod
    def _rows_to_dicts(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
        """Convert all fetched rows to dicts keyed by column name."""
        cols = [description[0] for description in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def get_recent_interactions(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Return the *limit* most recent interactions, newest first.

        Parameters
        ----------
        limit:
            Maximum number of rows to return (default 50).

        Returns
        -------
        list[dict]
            Each dict contains all columns of the ``interactions`` table.
            Empty list on error.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM interactions
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = self._rows_to_dicts(cursor)
            logger.debug(
                "[FeedbackStore] get_recent_interactions(limit=%d): %d row(s).",
                limit,
                len(rows),
            )
            return rows
        except Exception as exc:
            logger.error(
                "[FeedbackStore] get_recent_interactions failed: %s", exc, exc_info=True
            )
            return []

    def get_low_confidence_queries(
        self, threshold: float = 0.5
    ) -> list[dict[str, Any]]:
        """
        Return interactions whose ``confidence_score`` is strictly below
        *threshold*, ordered by confidence ascending.

        Parameters
        ----------
        threshold:
            Upper bound (exclusive) for the confidence score (default 0.5).

        Returns
        -------
        list[dict]
            Each dict contains all columns of the ``interactions`` table.
            Empty list on error.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM interactions
                    WHERE confidence_score < ?
                    ORDER BY confidence_score ASC
                    """,
                    (threshold,),
                )
                rows = self._rows_to_dicts(cursor)
            logger.debug(
                "[FeedbackStore] get_low_confidence_queries(threshold=%.2f): %d row(s).",
                threshold,
                len(rows),
            )
            return rows
        except Exception as exc:
            logger.error(
                "[FeedbackStore] get_low_confidence_queries failed: %s",
                exc,
                exc_info=True,
            )
            return []

    def get_hallucinated_queries(self) -> list[dict[str, Any]]:
        """
        Return all interactions flagged as hallucinated
        (``is_hallucinated = 1``), ordered newest first.

        Returns
        -------
        list[dict]
            Each dict contains all columns of the ``interactions`` table.
            Empty list on error.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM interactions
                    WHERE is_hallucinated = 1
                    ORDER BY timestamp DESC
                    """
                )
                rows = self._rows_to_dicts(cursor)
            logger.debug(
                "[FeedbackStore] get_hallucinated_queries: %d row(s).", len(rows)
            )
            return rows
        except Exception as exc:
            logger.error(
                "[FeedbackStore] get_hallucinated_queries failed: %s",
                exc,
                exc_info=True,
            )
            return []

    def get_interaction_by_id(
        self, interaction_id: int
    ) -> Optional[dict[str, Any]]:
        """
        Retrieve a single interaction by its primary key.

        Parameters
        ----------
        interaction_id:
            Integer primary key of the target row.

        Returns
        -------
        dict | None
            Dict of all columns, or *None* if not found / on error.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM interactions WHERE id = ?",
                    (interaction_id,),
                )
                row = cursor.fetchone()

            if row is None:
                logger.warning(
                    "[FeedbackStore] get_interaction_by_id: no row for id=%d.",
                    interaction_id,
                )
                return None

            cols = [d[0] for d in cursor.description]
            result = dict(zip(cols, row))
            logger.debug(
                "[FeedbackStore] get_interaction_by_id: found id=%d.", interaction_id
            )
            return result
        except Exception as exc:
            logger.error(
                "[FeedbackStore] get_interaction_by_id(id=%d) failed: %s",
                interaction_id,
                exc,
                exc_info=True,
            )
            return None
