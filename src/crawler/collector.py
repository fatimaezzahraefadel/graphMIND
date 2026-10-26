"""
Collecte de documents et orchestration du Crawler.

Usage::

    from src.crawler.collector import Crawler, CrawlerConfig
    config = CrawlerConfig(mock_mode=True)
    docs = Crawler(config).collect()
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from src.shared.exceptions import CorruptedFileError, UnsupportedDocumentTypeError
from src.shared.logging import get_logger


# ---------------------------------------------------------------------------
# 2.1 — Modèles
# ---------------------------------------------------------------------------


def compute_hash(content: bytes) -> str:
    """Calcule le hash SHA-256 d'un contenu binaire de façon reproductible."""
    return hashlib.sha256(content).hexdigest()


class DocumentMetadata(BaseModel):
    source: str                        # URL ou chemin d'origine
    collected_at: datetime             # ISO 8601, UTC
    document_type: str                 # html | pdf | word | email | json | db
    content_hash: str                  # SHA-256 du contenu brut
    license: str = "synthetic"         # toujours "synthetic" pour le corpus de test


class ParsedDocument(BaseModel):
    metadata: DocumentMetadata
    text_content: str
    raw_path: str                      # /data/raw/{document_type}/{content_hash}


class CrawlerConfig(BaseModel):
    mock_mode: bool = False
    hdfs_base_path: str = "/data/raw"
    allowed_sources: list[str] = []
    rate_limit_per_sec: float = 1.0
    sources: list[dict] = []


# ---------------------------------------------------------------------------
# 2.6 — Classe Crawler principale
# ---------------------------------------------------------------------------

# Chemin vers le corpus mock embarqué dans le package
_MOCK_CORPUS_DIR = Path(__file__).parent / "mock_corpus"

# Extensions reconnues et leur document_type associé
_EXT_TO_TYPE: dict[str, str] = {
    ".html": "html",
    ".htm": "html",
    ".pdf": "pdf",
    ".docx": "word",
    ".json": "json",
    ".eml": "email",
}


class Crawler:
    """Orchestrateur de collecte : sources → parsing → HDFS (ou mémoire)."""

    def __init__(self, config: CrawlerConfig, hdfs_writer=None):
        self.config = config
        self.hdfs_writer = hdfs_writer
        self.logger = get_logger("crawler")

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def collect(self) -> list[ParsedDocument]:
        """Collecte les documents selon la configuration.

        En mode mock : lit depuis ``src/crawler/mock_corpus/``.
        En mode réel : itère sur ``config.sources``.
        """
        if self.config.mock_mode:
            return self._collect_mock()
        return self._collect_real()

    def parse_document(
        self, content: bytes, document_type: str, source: str
    ) -> ParsedDocument:
        """Parse un contenu brut et retourne un ParsedDocument."""
        from src.crawler.parsers.factory import get_parser

        parser = get_parser(document_type)
        text = parser.parse(content, source)
        content_hash = compute_hash(content)
        metadata = DocumentMetadata(
            source=source,
            collected_at=datetime.now(timezone.utc),
            document_type=document_type,
            content_hash=content_hash,
            license="synthetic",
        )
        raw_path = f"{self.config.hdfs_base_path}/{document_type}/{content_hash}"
        return ParsedDocument(
            metadata=metadata,
            text_content=text,
            raw_path=raw_path,
        )

    def write_to_hdfs(self, doc: ParsedDocument, content: bytes) -> None:
        """Écrit le document brut et ses métadonnées dans HDFS si le writer est disponible."""
        if self.hdfs_writer is None:
            return
        try:
            self.hdfs_writer.write(doc.raw_path, content)
            meta_path = doc.raw_path + ".meta.json"
            self.hdfs_writer.write_metadata(meta_path, doc.metadata.model_dump(mode="json"))
        except Exception as exc:  # pragma: no cover
            self.logger.error(
                "hdfs_write_failed",
                path=doc.raw_path,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Collecte mock
    # ------------------------------------------------------------------

    def _collect_mock(self) -> list[ParsedDocument]:
        docs: list[ParsedDocument] = []
        if not _MOCK_CORPUS_DIR.is_dir():
            self.logger.warning("mock_corpus_missing", path=str(_MOCK_CORPUS_DIR))
            return docs

        for file_path in sorted(_MOCK_CORPUS_DIR.rglob("*")):
            if not file_path.is_file():
                continue
            if file_path.name in {"manifest.json", ".gitkeep"}:
                continue
            ext = file_path.suffix.lower()
            # Skip standalone .json files inside json/ subdir handled separately
            # but include them with the json document_type mapping
            document_type = _EXT_TO_TYPE.get(ext)
            if document_type is None:
                continue
            try:
                content = file_path.read_bytes()
                doc = self.parse_document(content, document_type, str(file_path))
                self.write_to_hdfs(doc, content)
                docs.append(doc)
            except (CorruptedFileError, UnsupportedDocumentTypeError) as exc:
                self.logger.warning(
                    "document_skipped",
                    path=str(file_path),
                    error=str(exc),
                )
            except Exception as exc:  # pragma: no cover
                self.logger.error(
                    "document_error",
                    path=str(file_path),
                    error=str(exc),
                )
        return docs

    # ------------------------------------------------------------------
    # Collecte réelle
    # ------------------------------------------------------------------

    def _collect_real(self) -> list[ParsedDocument]:
        from src.crawler.sources.filesystem import FilesystemSource
        from src.crawler.sources.web import WebSource
        from src.crawler.sources.api_json import ApiJsonSource
        from src.crawler.sources.email_source import EmailSource
        from src.crawler.sources.database import DatabaseSource

        _SOURCE_MAP = {
            "filesystem": FilesystemSource,
            "web": WebSource,
            "api_json": ApiJsonSource,
            "email": EmailSource,
            "database": DatabaseSource,
        }

        docs: list[ParsedDocument] = []
        for source_cfg in self.config.sources:
            source_type = source_cfg.get("type", "")
            source_cls = _SOURCE_MAP.get(source_type)
            if source_cls is None:
                self.logger.warning("unknown_source_type", source_type=source_type)
                continue

            # Vérification allowed_sources
            source_url = source_cfg.get("url", source_cfg.get("path", ""))
            if self.config.allowed_sources and source_url not in self.config.allowed_sources:
                self.logger.info("source_not_allowed", source=source_url)
                continue

            try:
                source_instance = source_cls()
                items = source_instance.fetch({**source_cfg, "rate_limit_per_sec": self.config.rate_limit_per_sec})
            except Exception as exc:
                self.logger.warning(
                    "source_fetch_failed",
                    source=source_url,
                    error=str(exc),
                )
                continue

            for content, src_path in items:
                document_type = source_cfg.get("document_type", _infer_type(src_path))
                try:
                    doc = self.parse_document(content, document_type, src_path)
                    self.write_to_hdfs(doc, content)
                    docs.append(doc)
                except (CorruptedFileError, UnsupportedDocumentTypeError) as exc:
                    self.logger.warning(
                        "document_skipped",
                        source=src_path,
                        error=str(exc),
                    )

        return docs


def _infer_type(path: str) -> str:
    """Déduit le document_type depuis l'extension du chemin."""
    ext = Path(path).suffix.lower()
    return _EXT_TO_TYPE.get(ext, "html")
