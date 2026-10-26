"""Parseur HTML utilisant BeautifulSoup4 avec le parser html.parser stdlib."""

from __future__ import annotations

from src.shared.exceptions import CorruptedFileError
from src.shared.logging import get_logger
from src.crawler.parsers.base import BaseParser

logger = get_logger("html_parser")

# Balises à supprimer avant extraction du texte
_TAGS_TO_REMOVE = {"script", "style", "nav", "header", "footer"}


class HtmlParser(BaseParser):
    """Extrait le texte d'un document HTML en nettoyant les balises inutiles."""

    def can_parse(self, document_type: str) -> bool:
        return document_type == "html"

    def parse(self, content: bytes, source: str) -> str:
        """Extrait le texte du document HTML.

        Args:
            content: Contenu binaire HTML.
            source: URL ou chemin (pour les logs).

        Returns:
            Texte extrait, balises script/style/nav/header/footer retirées.

        Raises:
            CorruptedFileError: Si le contenu ne peut pas être décodé ou parsé.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError as exc:  # pragma: no cover
            raise CorruptedFileError(
                "beautifulsoup4 non installé",
                component="html_parser",
            ) from exc

        try:
            # Tenter le décodage UTF-8, fallback latin-1
            try:
                text_content = content.decode("utf-8")
            except UnicodeDecodeError:
                text_content = content.decode("latin-1", errors="replace")

            soup = BeautifulSoup(text_content, "html.parser")

            # Supprimer les balises non désirées
            for tag_name in _TAGS_TO_REMOVE:
                for tag in soup.find_all(tag_name):
                    tag.decompose()

            # Extraire depuis <body> si présent, sinon tout le document
            body = soup.body
            target = body if body is not None else soup

            lines = [line.strip() for line in target.get_text(separator="\n").splitlines()]
            text = "\n".join(line for line in lines if line)
            return text

        except Exception as exc:
            logger.warning("html_parse_error", source=source, error=str(exc))
            raise CorruptedFileError(
                f"Fichier HTML corrompu ou illisible : {source}",
                component="html_parser",
                context={"source": source, "error": str(exc)},
            ) from exc
