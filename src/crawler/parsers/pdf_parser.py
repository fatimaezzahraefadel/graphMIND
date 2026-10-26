"""Parseur PDF utilisant pdfminer.six pour l'extraction page par page."""

from __future__ import annotations

import io

from src.shared.exceptions import CorruptedFileError
from src.shared.logging import get_logger
from src.crawler.parsers.base import BaseParser

logger = get_logger("pdf_parser")


class PdfParser(BaseParser):
    """Extrait le texte d'un PDF page par page, préservant l'ordre de lecture."""

    def can_parse(self, document_type: str) -> bool:
        return document_type == "pdf"

    def parse(self, content: bytes, source: str) -> str:
        """Extrait le texte du PDF avec pdfminer.six.

        Tente d'abord pdfminer. Si le fichier n'est pas un vrai PDF mais
        contient du texte brut (corpus de test), lit directement en UTF-8.

        Args:
            content: Contenu binaire du fichier PDF.
            source: URL ou chemin (pour les logs).

        Returns:
            Texte extrait.

        Raises:
            CorruptedFileError: Si le contenu ne peut pas être extrait.
        """
        # Tenter pdfminer en premier
        try:
            return self._parse_with_pdfminer(content, source)
        except CorruptedFileError:
            raise
        except Exception as exc:
            logger.warning("pdf_pdfminer_failed", source=source, error=str(exc))

        # Fallback : lire comme texte brut (utile pour les PDF "minimaux" du corpus)
        try:
            return self._parse_as_text(content, source)
        except Exception as exc2:
            logger.warning("pdf_text_fallback_failed", source=source, error=str(exc2))
            raise CorruptedFileError(
                f"Fichier PDF corrompu ou illisible : {source}",
                component="pdf_parser",
                context={"source": source, "error": str(exc2)},
            ) from exc2

    def _parse_with_pdfminer(self, content: bytes, source: str) -> str:
        """Extrait le texte via pdfminer.six."""
        try:
            from pdfminer.high_level import extract_text_to_fp
            from pdfminer.layout import LAParams
        except ImportError as exc:  # pragma: no cover
            raise CorruptedFileError(
                "pdfminer.six non installé",
                component="pdf_parser",
            ) from exc

        output = io.StringIO()
        input_fp = io.BytesIO(content)
        try:
            extract_text_to_fp(input_fp, output, laparams=LAParams())
        except Exception as exc:
            raise CorruptedFileError(
                f"pdfminer ne peut pas lire le PDF : {source}",
                component="pdf_parser",
                context={"source": source, "error": str(exc)},
            ) from exc

        text = output.getvalue()
        if not text.strip():
            # PDF vide ou non textuel → essayer le fallback
            raise ValueError("pdfminer a retourné un texte vide")
        return text

    def _parse_as_text(self, content: bytes, source: str) -> str:
        """Fallback : interprète le contenu binaire comme texte UTF-8 ou latin-1."""
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1", errors="replace")
