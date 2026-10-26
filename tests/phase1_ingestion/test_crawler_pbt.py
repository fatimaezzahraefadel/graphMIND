"""
Tests de propriétés Hypothesis pour le crawler Phase 1.

**Validates: Requirements 3.3, 28.1**

Propriétés testées :
1. Stabilité du hash : compute_hash(c) == compute_hash(c) pour tout c non-vide.
2. collected_at est un datetime valide sérialisable en ISO 8601.

Conformément à l'exigence 28.4, aucune fixture à portée fonction n'est
utilisée dans @given ; les dépendances sont instanciées dans le test.
"""

from __future__ import annotations

from datetime import datetime, timezone

from hypothesis import given, settings
from hypothesis import strategies as st

from src.crawler.collector import (
    CrawlerConfig,
    DocumentMetadata,
    ParsedDocument,
    compute_hash,
)


# ---------------------------------------------------------------------------
# Stratégies
# ---------------------------------------------------------------------------

binary_non_empty = st.binary(min_size=1, max_size=4096)

# Types de documents valides
document_type_strategy = st.sampled_from(["html", "pdf", "word", "email", "json", "db"])

# Chaînes de source non-vides
source_strategy = st.text(min_size=1, max_size=200).filter(lambda s: s.strip() != "")


# ---------------------------------------------------------------------------
# Propriété 1 : hash stable
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(content=binary_non_empty)
def test_hash_stable(content: bytes) -> None:
    """**Validates: Requirements 3.3**

    Pour tout contenu binaire non vide c, compute_hash(c) == compute_hash(c).
    Le hash est déterministe et reproductible.
    """
    h1 = compute_hash(content)
    h2 = compute_hash(content)
    assert h1 == h2, (
        f"compute_hash n'est pas stable pour content de longueur {len(content)}: "
        f"{h1!r} != {h2!r}"
    )


@settings(max_examples=100)
@given(content=binary_non_empty)
def test_hash_is_64_hex_chars(content: bytes) -> None:
    """**Validates: Requirements 3.3**

    compute_hash retourne toujours une chaîne de 64 caractères hexadécimaux
    (SHA-256 complet).
    """
    h = compute_hash(content)
    assert len(h) == 64, (
        f"Longueur de hash attendue 64, obtenu {len(h)}"
    )
    assert all(c in "0123456789abcdef" for c in h), (
        f"Hash non-hexadécimal : {h!r}"
    )


# ---------------------------------------------------------------------------
# Propriété 2 : collected_at est un datetime valide sérialisable ISO 8601
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    source=source_strategy,
    document_type=document_type_strategy,
    content=binary_non_empty,
)
def test_collected_at_is_valid_iso8601(
    source: str, document_type: str, content: bytes
) -> None:
    """**Validates: Requirements 3.2**

    Pour tout ParsedDocument produit, metadata.collected_at est un objet
    datetime timezone-aware sérialisable en ISO 8601 (round-trip).
    """
    content_hash = compute_hash(content)
    now = datetime.now(timezone.utc)

    metadata = DocumentMetadata(
        source=source,
        collected_at=now,
        document_type=document_type,
        content_hash=content_hash,
        license="synthetic",
    )

    # Sérialisation → désérialisation ISO 8601
    iso_str = metadata.collected_at.isoformat()
    parsed_dt = datetime.fromisoformat(iso_str)

    # L'objet désérialisé doit être timezone-aware
    assert parsed_dt.tzinfo is not None, (
        f"collected_at désérialisé sans timezone : {iso_str!r}"
    )
    # La valeur doit être identique (à la microseconde près)
    assert abs((parsed_dt - metadata.collected_at).total_seconds()) < 1e-3, (
        f"Round-trip ISO 8601 échoué : {iso_str!r}"
    )


@settings(max_examples=100)
@given(content=binary_non_empty)
def test_parsed_document_round_trip(content: bytes) -> None:
    """**Validates: Requirements 3.2, 9.2**

    Pour tout ParsedDocument construit, la sérialisation JSON puis la
    désérialisation reproduit un objet identique champ par champ.
    """
    content_hash = compute_hash(content)
    now = datetime.now(timezone.utc)

    metadata = DocumentMetadata(
        source="http://example.com/test",
        collected_at=now,
        document_type="html",
        content_hash=content_hash,
        license="synthetic",
    )
    doc = ParsedDocument(
        metadata=metadata,
        text_content="sample text",
        raw_path=f"/data/raw/html/{content_hash}",
    )

    # Round-trip JSON
    json_str = doc.model_dump_json()
    doc2 = ParsedDocument.model_validate_json(json_str)

    assert doc2.metadata.source == doc.metadata.source
    assert doc2.metadata.document_type == doc.metadata.document_type
    assert doc2.metadata.content_hash == doc.metadata.content_hash
    assert doc2.metadata.license == doc.metadata.license
    assert doc2.text_content == doc.text_content
    assert doc2.raw_path == doc.raw_path
    # collected_at round-trip (UTC preserved)
    assert abs((doc2.metadata.collected_at - doc.metadata.collected_at).total_seconds()) < 1e-3
