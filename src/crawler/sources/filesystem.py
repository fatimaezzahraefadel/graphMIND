"""Source de collecte locale : lit les fichiers d'un répertoire."""

from __future__ import annotations

from pathlib import Path

from src.crawler.sources.base import BaseSource
from src.shared.logging import get_logger

logger = get_logger("filesystem_source")

# Extensions supportées et leur document_type
_SUPPORTED_EXTENSIONS = {".html", ".htm", ".pdf", ".docx", ".json", ".eml"}


class FilesystemSource(BaseSource):
    """Lit les fichiers locaux d'un répertoire selon les extensions supportées."""

    def fetch(self, config: dict) -> list[tuple[bytes, str]]:
        """Lit les fichiers du répertoire configuré.

        Args:
            config: Doit contenir ``path`` (str) ; optionnel ``recursive`` (bool, défaut False).

        Returns:
            Liste de (contenu_bytes, chemin_absolu).
        """
        directory = Path(config.get("path", "."))
        recursive = config.get("recursive", False)

        if not directory.is_dir():
            logger.warning("filesystem_dir_not_found", path=str(directory))
            return []

        results: list[tuple[bytes, str]] = []
        glob_fn = directory.rglob if recursive else directory.glob

        for file_path in sorted(glob_fn("*")):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
                continue
            try:
                content = file_path.read_bytes()
                results.append((content, str(file_path)))
            except Exception as exc:
                logger.warning(
                    "filesystem_read_error",
                    path=str(file_path),
                    error=str(exc),
                )

        return results
