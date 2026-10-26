"""Factory de parseurs : retourne le parseur approprié selon le document_type."""

from __future__ import annotations

from src.shared.exceptions import UnsupportedDocumentTypeError
from src.crawler.parsers.base import BaseParser
from src.crawler.parsers.html_parser import HtmlParser
from src.crawler.parsers.pdf_parser import PdfParser
from src.crawler.parsers.word_parser import WordParser
from src.crawler.parsers.email_parser import EmailParser
from src.crawler.parsers.json_parser import JsonParser
from src.crawler.parsers.db_parser import DbParser

# Registre singleton des parseurs (instanciés une seule fois)
_PARSERS: list[BaseParser] = [
    HtmlParser(),
    PdfParser(),
    WordParser(),
    EmailParser(),
    JsonParser(),
    DbParser(),
]


def get_parser(document_type: str) -> BaseParser:
    """Retourne le parseur approprié pour le type de document donné.

    Args:
        document_type: Type de document (``"html"``, ``"pdf"``, ``"word"``,
                       ``"email"``, ``"json"``, ``"db"``).

    Returns:
        Instance du parseur correspondant.

    Raises:
        UnsupportedDocumentTypeError: Si aucun parseur ne supporte ce type.
    """
    for parser in _PARSERS:
        if parser.can_parse(document_type):
            return parser

    raise UnsupportedDocumentTypeError(
        f"Type de document non supporté : {document_type!r}",
        component="factory",
        context={"document_type": document_type},
    )
