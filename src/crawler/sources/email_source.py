"""Source de collecte email : lit les fichiers .eml d'un répertoire local."""

from __future__ import annotations

from pathlib import Path

from src.crawler.sources.base import BaseSource
from src.shared.logging import get_logger

logger = get_logger("email_source")


class EmailSource(BaseSource):
    """Lit les fichiers .eml d'un répertoire local."""

    def fetch(self, config: dict) -> list[tuple[bytes, str]]:
        """Lit tous les fichiers .eml du répertoire configuré.

        Args:
            config: Doit contenir ``path`` (str).

        Returns:
            Liste de (contenu_bytes, chemin_absolu).
        """
        directory = Path(config.get("path", "."))

        if not directory.is_dir():
            logger.warning("email_source_dir_not_found", path=str(directory))
            return []

        results: list[tuple[bytes, str]] = []
        for file_path in sorted(directory.glob("*.eml")):
            try:
                content = file_path.read_bytes()
                results.append((content, str(file_path)))
            except Exception as exc:
                logger.warning(
                    "email_source_read_error",
                    path=str(file_path),
                    error=str(exc),
                )

        return results
