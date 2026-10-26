"""Parseur JSON : extrait récursivement les valeurs de type str."""

from __future__ import annotations

import json

from src.shared.exceptions import CorruptedFileError
from src.shared.logging import get_logger
from src.crawler.parsers.base import BaseParser

logger = get_logger("json_parser")


def _extract_strings(obj: object, prefix: str = "") -> list[str]:
    """Parcourt récursivement un objet JSON et retourne les paires clé.chemin: valeur.

    Seules les valeurs de type ``str`` sont extraites ; les nombres et
    booléens sont ignorés.

    Args:
        obj: Nœud courant de la hiérarchie JSON.
        prefix: Préfixe des clés parentes (ex. ``"a.b"``).

    Returns:
        Liste de chaînes ``"clé1.clé2: valeur"``.
    """
    lines: list[str] = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            lines.extend(_extract_strings(value, full_key))

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            full_key = f"{prefix}.{i}" if prefix else str(i)
            lines.extend(_extract_strings(item, full_key))

    elif isinstance(obj, str):
        lines.append(f"{prefix}: {obj}" if prefix else obj)

    # int, float, bool, None → ignorés

    return lines


class JsonParser(BaseParser):
    """Extrait les valeurs textuelles d'un document JSON."""

    def can_parse(self, document_type: str) -> bool:
        return document_type == "json"

    def parse(self, content: bytes, source: str) -> str:
        """Extrait récursivement les valeurs str d'un JSON.

        Format : ``clé1.clé2: valeur`` (une paire par ligne).

        Args:
            content: Contenu binaire JSON.
            source: Chemin ou URL (pour les logs).

        Returns:
            Texte extrait.

        Raises:
            CorruptedFileError: Si le JSON est invalide.
        """
        try:
            text = content.decode("utf-8")
            data = json.loads(text)
        except Exception as exc:
            logger.warning("json_parse_error", source=source, error=str(exc))
            raise CorruptedFileError(
                f"Fichier JSON corrompu ou invalide : {source}",
                component="json_parser",
                context={"source": source, "error": str(exc)},
            ) from exc

        lines = _extract_strings(data)
        return "\n".join(lines)
