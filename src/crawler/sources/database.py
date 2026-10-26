"""Source de collecte base de données : SQLite in-memory ou fichier, retourne les lignes en JSON bytes."""

from __future__ import annotations

import json
import sqlite3

from src.crawler.sources.base import BaseSource
from src.shared.logging import get_logger

logger = get_logger("database_source")


class DatabaseSource(BaseSource):
    """Exécute une requête SQL sur SQLite et retourne les lignes en JSON bytes."""

    def fetch(self, config: dict) -> list[tuple[bytes, str]]:
        """Exécute la requête SQL configurée et retourne le résultat sérialisé.

        Args:
            config: Doit contenir ``query`` (str).
                    Optionnel : ``db_path`` (str, défaut ``:memory:``).

        Returns:
            Liste d'un seul élément : (json_bytes, "db:{db_path}:{query[:40]}").
        """
        db_path: str = config.get("db_path", ":memory:")
        query: str = config.get("query", "")

        if not query:
            logger.warning("database_source_no_query")
            return []

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query)
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()

            content = json.dumps(rows, ensure_ascii=False, default=str).encode("utf-8")
            source_id = f"db:{db_path}:{query[:40]}"
            return [(content, source_id)]
        except Exception as exc:
            logger.warning("database_fetch_error", db_path=db_path, error=str(exc))
            return []
