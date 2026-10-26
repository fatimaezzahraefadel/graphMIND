"""Parseur de résultats SQL : convertit list[dict] en texte tabulaire CSV."""

from __future__ import annotations

import csv
import io
import json

from src.shared.exceptions import CorruptedFileError
from src.shared.logging import get_logger
from src.crawler.parsers.base import BaseParser

logger = get_logger("db_parser")


class DbParser(BaseParser):
    """Convertit des lignes de résultat SQL en texte tabulaire (CSV)."""

    def can_parse(self, document_type: str) -> bool:
        return document_type == "db"

    def parse(self, content: bytes, source: str) -> str:
        """Convertit des lignes SQL (sérialisées en JSON bytes) en CSV texte.

        Le format d'entrée attendu est un tableau JSON de dicts :
        ``[{"col1": "val1", "col2": "val2"}, ...]``

        Args:
            content: Lignes SQL sérialisées en JSON bytes.
            source: Identifiant de la source (pour les logs).

        Returns:
            Texte CSV (entête + lignes).

        Raises:
            CorruptedFileError: Si le contenu n'est pas un JSON valide de list[dict].
        """
        try:
            rows: list[dict] = json.loads(content.decode("utf-8"))
            if not isinstance(rows, list):
                raise ValueError("La racine JSON doit être une liste")
        except Exception as exc:
            logger.warning("db_parse_error", source=source, error=str(exc))
            raise CorruptedFileError(
                f"Données DB corrompues ou invalides : {source}",
                component="db_parser",
                context={"source": source, "error": str(exc)},
            ) from exc

        if not rows:
            return ""

        output = io.StringIO()
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue().strip()
