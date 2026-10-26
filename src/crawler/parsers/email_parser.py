"""Parseur d'emails .eml utilisant le module standard email."""

from __future__ import annotations

import email as email_module
import email.policy
from email.header import decode_header, make_header

from src.shared.exceptions import CorruptedFileError
from src.shared.logging import get_logger
from src.crawler.parsers.base import BaseParser

logger = get_logger("email_parser")


def _decode_header_value(value: str | None) -> str:
    """Décode une valeur d'entête email (encodage RFC 2047)."""
    if value is None:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value or ""


class EmailParser(BaseParser):
    """Extrait les champs et le corps d'un fichier .eml."""

    def can_parse(self, document_type: str) -> bool:
        return document_type == "email"

    def parse(self, content: bytes, source: str) -> str:
        """Parse un fichier .eml et retourne un texte structuré.

        Format de sortie::

            From: {from}
            To: {to}
            Subject: {subject}
            Date: {date}

            {body}

        Le corps préfère text/plain ; fallback sur text/html (balises retirées).

        Args:
            content: Contenu binaire du fichier .eml.
            source: Chemin ou identifiant (pour les logs).

        Returns:
            Texte structuré de l'email.

        Raises:
            CorruptedFileError: Si le fichier ne peut pas être parsé.
        """
        try:
            msg = email_module.message_from_bytes(content, policy=email_module.policy.compat32)
        except Exception as exc:
            logger.warning("email_parse_error", source=source, error=str(exc))
            raise CorruptedFileError(
                f"Fichier email corrompu ou illisible : {source}",
                component="email_parser",
                context={"source": source, "error": str(exc)},
            ) from exc

        from_addr = _decode_header_value(msg.get("From", ""))
        to_addr = _decode_header_value(msg.get("To", ""))
        subject = _decode_header_value(msg.get("Subject", ""))
        date = msg.get("Date", "")

        body = self._extract_body(msg)

        return (
            f"From: {from_addr}\n"
            f"To: {to_addr}\n"
            f"Subject: {subject}\n"
            f"Date: {date}\n"
            f"\n"
            f"{body}"
        )

    def _extract_body(self, msg: email_module.message.Message) -> str:
        """Extrait le corps du message. Préfère text/plain, fallback text/html."""
        plain: str | None = None
        html: str | None = None

        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                disp = str(part.get("Content-Disposition", ""))
                if "attachment" in disp:
                    continue
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                charset = part.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
                if ct == "text/plain" and plain is None:
                    plain = decoded
                elif ct == "text/html" and html is None:
                    html = decoded
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
                ct = msg.get_content_type()
                if ct == "text/plain":
                    plain = decoded
                else:
                    html = decoded

        if plain is not None:
            return plain.strip()

        if html is not None:
            # Retirer les balises HTML basiquement
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
                return soup.get_text(separator="\n").strip()
            except ImportError:
                # Fallback sans bs4 : retirer les tags manuellement
                import re
                return re.sub(r"<[^>]+>", " ", html).strip()

        return ""
