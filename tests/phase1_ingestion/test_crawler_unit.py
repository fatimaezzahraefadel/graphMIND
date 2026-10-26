"""
Tests unitaires pour le crawler Phase 1 :
parseurs, factory, HDFSWriter, Crawler mock mode.

**Validates: Requirements 1, 2, 3, 4**
"""

from __future__ import annotations

import io
import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import responses as responses_lib

from src.crawler.collector import Crawler, CrawlerConfig, ParsedDocument, compute_hash
from src.crawler.hdfs_writer import HDFSWriter
from src.crawler.parsers.db_parser import DbParser
from src.crawler.parsers.email_parser import EmailParser
from src.crawler.parsers.factory import get_parser
from src.crawler.parsers.html_parser import HtmlParser
from src.crawler.parsers.json_parser import JsonParser
from src.crawler.parsers.pdf_parser import PdfParser
from src.crawler.parsers.word_parser import WordParser
from src.shared.exceptions import CorruptedFileError, UnsupportedDocumentTypeError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_minimal_pdf(text: str) -> bytes:
    """Génère un PDF minimal valide (réutilisé depuis generate_corpus)."""
    safe = text.encode("latin-1", errors="replace")
    stream = b"BT /F1 12 Tf 50 750 Td (" + safe + b") Tj ET"
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        ),
        (
            b"4 0 obj\n<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
            + stream + b"\nendstream\nendobj\n"
        ),
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    body = b"%PDF-1.4\n"
    offsets: list[int] = []
    for obj in objects:
        offsets.append(len(body))
        body += obj
    xref_offset = len(body)
    xref = b"xref\n0 " + str(len(objects) + 1).encode() + b"\n"
    xref += b"0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()
    trailer = (
        b"trailer\n<< /Size " + str(len(objects) + 1).encode()
        + b" /Root 1 0 R >>\nstartxref\n"
        + str(xref_offset).encode() + b"\n%%EOF\n"
    )
    return body + xref + trailer


def _make_minimal_docx(text: str) -> bytes:
    """Crée un .docx minimal en mémoire."""
    import docx

    doc = docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 2.1 — compute_hash
# ---------------------------------------------------------------------------


class TestComputeHash:
    def test_deterministic(self):
        """Deux appels avec le même contenu → même hash."""
        content = b"hello world"
        assert compute_hash(content) == compute_hash(content)

    def test_sha256_format(self):
        """Hash de 64 caractères hexadécimaux."""
        h = compute_hash(b"test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_different_contents_different_hash(self):
        """Contenus différents → hashes différents."""
        assert compute_hash(b"abc") != compute_hash(b"def")

    def test_known_value(self):
        """Vérifie la valeur pour b'' (hash SHA-256 connu)."""
        import hashlib
        expected = hashlib.sha256(b"").hexdigest()
        assert compute_hash(b"") == expected


# ---------------------------------------------------------------------------
# 2.2 — HtmlParser
# ---------------------------------------------------------------------------


class TestHtmlParser:
    def test_parse_valid_html(self):
        """HTML valide → texte du body, sans balises."""
        html = b"<html><body><p>Bonjour Alice Benali</p></body></html>"
        parser = HtmlParser()
        result = parser.parse(html, "test.html")
        assert "Alice Benali" in result
        assert "<p>" not in result

    def test_removes_script_style(self):
        """Les balises script/style sont supprimées."""
        html = (
            "<html><body>"
            '<script>alert("x")</script>'
            "<style>body{color:red}</style>"
            "<p>Texte visible</p>"
            "</body></html>"
        ).encode("utf-8")
        parser = HtmlParser()
        result = parser.parse(html, "test.html")
        assert "alert" not in result
        assert "color:red" not in result
        assert "Texte visible" in result

    def test_removes_nav_header_footer(self):
        """Les balises nav/header/footer sont supprimées."""
        html = (
            "<html><body>"
            "<nav>Menu</nav>"
            "<header>Header section</header>"
            "<main>Contenu principal</main>"
            "<footer>Pied de page</footer>"
            "</body></html>"
        ).encode("utf-8")
        parser = HtmlParser()
        result = parser.parse(html, "test.html")
        assert "Menu" not in result
        assert "Header section" not in result
        assert "Pied de page" not in result
        assert "Contenu principal" in result

    def test_corrupted_raises(self):
        """Contenu totalement invalide → CorruptedFileError."""
        # bytes non-décodables en UTF-8 et pas de HTML valide
        parser = HtmlParser()
        # Forcer une erreur en patchant BeautifulSoup
        import unittest.mock as mock
        with mock.patch("bs4.BeautifulSoup", side_effect=RuntimeError("crash")):
            with pytest.raises(CorruptedFileError):
                parser.parse(b"\xff\xfe\x00\x01", "bad.html")

    def test_can_parse_html(self):
        assert HtmlParser().can_parse("html") is True

    def test_cannot_parse_pdf(self):
        assert HtmlParser().can_parse("pdf") is False


# ---------------------------------------------------------------------------
# PdfParser
# ---------------------------------------------------------------------------


class TestPdfParser:
    def test_parse_minimal_pdf(self):
        """PDF minimal généré par make_minimal_pdf → texte extrait."""
        content = _make_minimal_pdf("Alice Benali works at UAR")
        parser = PdfParser()
        result = parser.parse(content, "test.pdf")
        assert result.strip() != ""

    def test_corrupted_raises(self):
        """Fichier totalement corrompu → CorruptedFileError."""
        parser = PdfParser()
        # Contenu non-PDF et non-texte (bytes nulls)
        with pytest.raises(CorruptedFileError):
            parser.parse(b"\x00\x01\x02\x03", "bad.pdf")

    def test_can_parse_pdf(self):
        assert PdfParser().can_parse("pdf") is True

    def test_cannot_parse_html(self):
        assert PdfParser().can_parse("html") is False


# ---------------------------------------------------------------------------
# WordParser
# ---------------------------------------------------------------------------


class TestWordParser:
    def test_parse_valid_docx(self):
        """Docx valide → texte des paragraphes."""
        content = _make_minimal_docx("InnoTech Solutions collabore avec CR-IMED")
        parser = WordParser()
        result = parser.parse(content, "test.docx")
        assert "InnoTech Solutions" in result

    def test_corrupted_raises(self):
        """Bytes aléatoires → CorruptedFileError."""
        parser = WordParser()
        with pytest.raises(CorruptedFileError):
            parser.parse(b"not a docx file at all!!", "bad.docx")

    def test_can_parse_word(self):
        assert WordParser().can_parse("word") is True

    def test_cannot_parse_json(self):
        assert WordParser().can_parse("json") is False


# ---------------------------------------------------------------------------
# EmailParser
# ---------------------------------------------------------------------------


class TestEmailParser:
    def test_parse_valid_eml(self):
        """Email .eml valide → format From/To/Subject/Date/body."""
        eml = textwrap.dedent("""\
            From: alice@uar.ma
            To: bob@example.com
            Subject: Test email
            Date: Mon, 01 Jan 2024 10:00:00 +0000
            MIME-Version: 1.0
            Content-Type: text/plain; charset=utf-8

            Alice Benali travaille sur Projet GraphIA.
        """).encode("utf-8")
        parser = EmailParser()
        result = parser.parse(eml, "test.eml")
        assert "From: alice@uar.ma" in result
        assert "To: bob@example.com" in result
        assert "Subject: Test email" in result
        assert "Alice Benali" in result

    def test_extract_body_prefers_plain(self):
        """Multipart avec text/plain → préfère text/plain."""
        eml = textwrap.dedent("""\
            From: a@b.com
            To: c@d.com
            Subject: Multi
            MIME-Version: 1.0
            Content-Type: multipart/alternative; boundary="bound"

            --bound
            Content-Type: text/plain; charset=utf-8

            Corps en texte brut
            --bound
            Content-Type: text/html; charset=utf-8

            <html><body>Corps HTML</body></html>
            --bound--
        """).encode("utf-8")
        parser = EmailParser()
        result = parser.parse(eml, "test.eml")
        assert "Corps en texte brut" in result

    def test_can_parse_email(self):
        assert EmailParser().can_parse("email") is True

    def test_cannot_parse_html(self):
        assert EmailParser().can_parse("html") is False


# ---------------------------------------------------------------------------
# JsonParser
# ---------------------------------------------------------------------------


class TestJsonParser:
    def test_parse_flat_json(self):
        """JSON plat → clé: valeur."""
        data = json.dumps({"name": "Alice Benali", "project": "GraphIA"}).encode()
        parser = JsonParser()
        result = parser.parse(data, "test.json")
        assert "name: Alice Benali" in result
        assert "project: GraphIA" in result

    def test_parse_nested_json(self):
        """JSON imbriqué → clé.sous-clé: valeur."""
        data = json.dumps({"org": {"name": "InnoTech Solutions"}}).encode()
        parser = JsonParser()
        result = parser.parse(data, "test.json")
        assert "org.name: InnoTech Solutions" in result

    def test_parse_list_json(self):
        """JSON liste → index.champ: valeur."""
        data = json.dumps([{"label": "Neo4j"}]).encode()
        parser = JsonParser()
        result = parser.parse(data, "test.json")
        assert "label: Neo4j" in result

    def test_corrupted_raises(self):
        """JSON invalide → CorruptedFileError."""
        parser = JsonParser()
        with pytest.raises(CorruptedFileError):
            parser.parse(b"{bad json }", "bad.json")

    def test_ignores_numbers(self):
        """Les nombres et booléens sont ignorés."""
        data = json.dumps({"count": 42, "active": True, "name": "test"}).encode()
        parser = JsonParser()
        result = parser.parse(data, "test.json")
        assert "42" not in result
        assert "True" not in result
        assert "name: test" in result

    def test_can_parse_json(self):
        assert JsonParser().can_parse("json") is True


# ---------------------------------------------------------------------------
# DbParser
# ---------------------------------------------------------------------------


class TestDbParser:
    def test_parse_rows(self):
        """list[dict] sérialisée en JSON → texte CSV avec entête."""
        rows = [{"id": "1", "name": "Alice Benali"}, {"id": "2", "name": "Mohamed Tazi"}]
        content = json.dumps(rows).encode()
        parser = DbParser()
        result = parser.parse(content, "db:test")
        assert "id" in result
        assert "name" in result
        assert "Alice Benali" in result
        assert "Mohamed Tazi" in result

    def test_empty_rows(self):
        """Liste vide → chaîne vide."""
        parser = DbParser()
        result = parser.parse(b"[]", "db:test")
        assert result == ""

    def test_corrupted_raises(self):
        """JSON non-liste → CorruptedFileError."""
        parser = DbParser()
        with pytest.raises(CorruptedFileError):
            parser.parse(b'{"key": "val"}', "db:test")

    def test_can_parse_db(self):
        assert DbParser().can_parse("db") is True


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestFactory:
    def test_get_html_parser(self):
        """factory retourne HtmlParser pour 'html'."""
        assert isinstance(get_parser("html"), HtmlParser)

    def test_get_pdf_parser(self):
        assert isinstance(get_parser("pdf"), PdfParser)

    def test_get_word_parser(self):
        assert isinstance(get_parser("word"), WordParser)

    def test_get_email_parser(self):
        assert isinstance(get_parser("email"), EmailParser)

    def test_get_json_parser(self):
        assert isinstance(get_parser("json"), JsonParser)

    def test_get_db_parser(self):
        assert isinstance(get_parser("db"), DbParser)

    def test_unsupported_raises(self):
        """Type inconnu → UnsupportedDocumentTypeError."""
        with pytest.raises(UnsupportedDocumentTypeError):
            get_parser("xlsx")

    def test_unsupported_empty_raises(self):
        with pytest.raises(UnsupportedDocumentTypeError):
            get_parser("")


# ---------------------------------------------------------------------------
# HDFSWriter
# ---------------------------------------------------------------------------

NAMENODE = "http://namenode:9870"


class TestHDFSWriterExists:
    @responses_lib.activate
    def test_exists_true_on_200(self):
        """GETFILESTATUS 200 → exists() == True."""
        responses_lib.add(
            responses_lib.GET,
            f"{NAMENODE}/webhdfs/v1/data/raw/html/abc?user.name=root&op=GETFILESTATUS",
            json={"FileStatus": {}},
            status=200,
        )
        writer = HDFSWriter(NAMENODE)
        assert writer.exists("/data/raw/html/abc") is True

    @responses_lib.activate
    def test_exists_false_on_404(self):
        """GETFILESTATUS 404 → exists() == False."""
        responses_lib.add(
            responses_lib.GET,
            f"{NAMENODE}/webhdfs/v1/data/raw/html/abc?user.name=root&op=GETFILESTATUS",
            json={"RemoteException": {"exception": "FileNotFoundException"}},
            status=404,
        )
        writer = HDFSWriter(NAMENODE)
        assert writer.exists("/data/raw/html/abc") is False

    @responses_lib.activate
    def test_exists_raises_on_500(self):
        """GETFILESTATUS 500 → CrawlerError."""
        from src.shared.exceptions import CrawlerError

        responses_lib.add(
            responses_lib.GET,
            f"{NAMENODE}/webhdfs/v1/data/raw/html/abc?user.name=root&op=GETFILESTATUS",
            status=500,
        )
        writer = HDFSWriter(NAMENODE)
        with pytest.raises(CrawlerError):
            writer.exists("/data/raw/html/abc")


class TestHDFSWriterWrite:
    @responses_lib.activate
    def test_write_success(self):
        """write() déclenche 2 PUT : NameNode (307) puis DataNode (201)."""
        datanode_url = "http://datanode:9864/webhdfs/v1/data/raw/html/abc"

        # Étape 1 : CREATE → 307
        responses_lib.add(
            responses_lib.PUT,
            f"{NAMENODE}/webhdfs/v1/data/raw/html/abc",
            status=307,
            headers={"Location": datanode_url},
        )
        # exists() avant CREATE
        responses_lib.add(
            responses_lib.GET,
            f"{NAMENODE}/webhdfs/v1/data/raw/html/abc?user.name=root&op=GETFILESTATUS",
            status=404,
        )
        # Étape 2 : DataNode → 201
        responses_lib.add(responses_lib.PUT, datanode_url, status=201)

        writer = HDFSWriter(NAMENODE)
        writer.write("/data/raw/html/abc", b"hello")

    @responses_lib.activate
    def test_write_idempotent_when_exists(self):
        """write() avec overwrite=False et fichier existant → skippé, pas de PUT CREATE."""
        # exists() → 200 (fichier existe)
        responses_lib.add(
            responses_lib.GET,
            f"{NAMENODE}/webhdfs/v1/data/raw/html/abc?user.name=root&op=GETFILESTATUS",
            json={"FileStatus": {}},
            status=200,
        )
        writer = HDFSWriter(NAMENODE)
        writer.write("/data/raw/html/abc", b"hello", overwrite=False)
        # Seul GET a été appelé, pas de PUT
        assert len(responses_lib.calls) == 1
        assert responses_lib.calls[0].request.method == "GET"

    @responses_lib.activate
    def test_write_raises_on_step1_error(self):
        """CREATE step1 != 307 → CrawlerError."""
        from src.shared.exceptions import CrawlerError

        # exists() → 404
        responses_lib.add(
            responses_lib.GET,
            f"{NAMENODE}/webhdfs/v1/data/raw/html/abc?user.name=root&op=GETFILESTATUS",
            status=404,
        )
        # CREATE → 500
        responses_lib.add(
            responses_lib.PUT,
            f"{NAMENODE}/webhdfs/v1/data/raw/html/abc",
            status=500,
        )
        writer = HDFSWriter(NAMENODE)
        with pytest.raises(CrawlerError, match="step1"):
            writer.write("/data/raw/html/abc", b"hello")

    @responses_lib.activate
    def test_write_raises_on_step2_error(self):
        """CREATE step2 != 200/201 → CrawlerError."""
        from src.shared.exceptions import CrawlerError

        datanode_url = "http://datanode:9864/webhdfs/v1/data/raw/html/abc"

        # exists() → 404
        responses_lib.add(
            responses_lib.GET,
            f"{NAMENODE}/webhdfs/v1/data/raw/html/abc?user.name=root&op=GETFILESTATUS",
            status=404,
        )
        # CREATE step1 → 307
        responses_lib.add(
            responses_lib.PUT,
            f"{NAMENODE}/webhdfs/v1/data/raw/html/abc",
            status=307,
            headers={"Location": datanode_url},
        )
        # DataNode → 500
        responses_lib.add(responses_lib.PUT, datanode_url, status=500)

        writer = HDFSWriter(NAMENODE)
        with pytest.raises(CrawlerError, match="step2"):
            writer.write("/data/raw/html/abc", b"hello")


# ---------------------------------------------------------------------------
# Crawler — mode mock
# ---------------------------------------------------------------------------

_CORPUS_DIR = Path(__file__).parent.parent.parent / "src" / "crawler" / "mock_corpus"


class TestCrawlerMockMode:
    def test_mock_mode_returns_documents(self):
        """Mode mock → retourne une liste non-vide de ParsedDocument."""
        if not _CORPUS_DIR.is_dir():
            pytest.skip("Corpus non généré — lancez scripts/generate_corpus.py")
        config = CrawlerConfig(mock_mode=True)
        crawler = Crawler(config)
        docs = crawler.collect()
        assert isinstance(docs, list)
        assert len(docs) > 0
        for doc in docs:
            assert isinstance(doc, ParsedDocument)

    def test_mock_mode_returns_25_documents(self):
        """Mode mock → exactement 25 documents (5 × 5 formats)."""
        if not _CORPUS_DIR.is_dir():
            pytest.skip("Corpus non généré — lancez scripts/generate_corpus.py")
        config = CrawlerConfig(mock_mode=True)
        crawler = Crawler(config)
        docs = crawler.collect()
        assert len(docs) == 25

    def test_mock_mode_no_network(self):
        """Mode mock → aucune requête réseau (responses bloque tout)."""
        if not _CORPUS_DIR.is_dir():
            pytest.skip("Corpus non généré")

        @responses_lib.activate
        def _run():
            # Pas de mock enregistré → toute requête réseau lèverait ConnectionError
            config = CrawlerConfig(mock_mode=True)
            crawler = Crawler(config)
            docs = crawler.collect()
            assert len(docs) > 0

        _run()

    def test_mock_mode_document_types(self):
        """Mock mode → couvre html, pdf, word, email, json."""
        if not _CORPUS_DIR.is_dir():
            pytest.skip("Corpus non généré")
        config = CrawlerConfig(mock_mode=True)
        crawler = Crawler(config)
        docs = crawler.collect()
        doc_types = {doc.metadata.document_type for doc in docs}
        assert doc_types == {"html", "pdf", "word", "email", "json"}

    def test_mock_mode_metadata_license(self):
        """Tous les documents ont license='synthetic'."""
        if not _CORPUS_DIR.is_dir():
            pytest.skip("Corpus non généré")
        config = CrawlerConfig(mock_mode=True)
        crawler = Crawler(config)
        docs = crawler.collect()
        for doc in docs:
            assert doc.metadata.license == "synthetic"

    def test_mock_mode_raw_path_format(self):
        """raw_path respecte le format /data/raw/{type}/{hash}."""
        if not _CORPUS_DIR.is_dir():
            pytest.skip("Corpus non généré")
        config = CrawlerConfig(mock_mode=True)
        crawler = Crawler(config)
        docs = crawler.collect()
        for doc in docs:
            assert doc.raw_path.startswith("/data/raw/")
            parts = doc.raw_path.split("/")
            assert len(parts) >= 4

    def test_mock_mode_with_hdfs_writer(self):
        """HDFSWriter est appelé pour chaque document en mode mock."""
        if not _CORPUS_DIR.is_dir():
            pytest.skip("Corpus non généré")
        mock_writer = MagicMock()
        mock_writer.exists.return_value = False
        config = CrawlerConfig(mock_mode=True)
        crawler = Crawler(config, hdfs_writer=mock_writer)
        docs = crawler.collect()
        assert len(docs) > 0
        # write() doit avoir été appelé au moins une fois
        assert mock_writer.write.call_count >= len(docs)

    def test_mock_mode_content_hash_reproducible(self):
        """Deux collectes mock → mêmes content_hash."""
        if not _CORPUS_DIR.is_dir():
            pytest.skip("Corpus non généré")
        config = CrawlerConfig(mock_mode=True)
        docs1 = Crawler(config).collect()
        docs2 = Crawler(config).collect()
        hashes1 = sorted(d.metadata.content_hash for d in docs1)
        hashes2 = sorted(d.metadata.content_hash for d in docs2)
        assert hashes1 == hashes2
