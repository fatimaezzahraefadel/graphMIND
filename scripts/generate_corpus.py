#!/usr/bin/env python3
"""
Génère le corpus synthétique pour GraphMind (graine fixe 42).

Produit 25 documents dans src/crawler/mock_corpus/ :
  - 5 HTML   : html/doc_01.html … html/doc_05.html
  - 5 PDF    : pdf/doc_01.pdf  … pdf/doc_05.pdf
  - 5 Word   : word/doc_01.docx … word/doc_05.docx
  - 5 JSON   : json/doc_01.json … json/doc_05.json
  - 5 email  : email/doc_01.eml … email/doc_05.eml

Génère aussi :
  - src/crawler/mock_corpus/manifest.json
  - data/extraction_gold.json  (champ "documents" peuplé)
"""

from __future__ import annotations

import hashlib
import io
import json
import random
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "src" / "crawler" / "mock_corpus"
GOLD_PATH = ROOT / "data" / "extraction_gold.json"

SEED = 42
rng = random.Random(SEED)

# ---------------------------------------------------------------------------
# Entités et relations du domaine
# ---------------------------------------------------------------------------
ENTITIES = {
    "alice": {
        "canonical": "Alice Benali",
        "variants": ["A. Benali", "Alice B.", "Dr Alice Benali"],
        "type": "Person",
    },
    "tazi": {
        "canonical": "Mohamed Tazi",
        "variants": ["M. Tazi", "Prof. Tazi"],
        "type": "Person",
    },
    "sara": {
        "canonical": "Sara El Mansouri",
        "variants": ["S. El Mansouri", "Sara EM"],
        "type": "Person",
    },
    "jean": {
        "canonical": "Jean-Pierre Dubois",
        "variants": ["JP Dubois", "J.-P. Dubois"],
        "type": "Person",
    },
    "uar": {
        "canonical": "Université Atlas de Rabat",
        "variants": ["Univ. Atlas Rabat", "UAR"],
        "type": "Organization",
    },
    "innotech": {
        "canonical": "InnoTech Solutions",
        "variants": ["InnoTech", "ITS"],
        "type": "Organization",
    },
    "imed": {
        "canonical": "Centre de Recherche IMED",
        "variants": ["IMED", "CR-IMED"],
        "type": "Organization",
    },
    "fundx": {
        "canonical": "FundX Capital",
        "variants": ["FundX"],
        "type": "Organization",
    },
    "graphia": {
        "canonical": "Projet GraphIA",
        "variants": ["GraphIA", "Proj. GraphIA"],
        "type": "Project",
    },
    "databridge": {
        "canonical": "DataBridge",
        "variants": ["Data Bridge"],
        "type": "Project",
    },
    "neo4j": {
        "canonical": "Neo4j",
        "variants": ["Neo4J"],
        "type": "Technology",
    },
    "spark": {
        "canonical": "Apache Spark",
        "variants": ["Spark"],
        "type": "Technology",
    },
    "python": {
        "canonical": "Python",
        "variants": ["Python 3"],
        "type": "Technology",
    },
    "conf": {
        "canonical": "Conférence IA Maroc 2024",
        "variants": ["ConfIA2024"],
        "type": "Event",
    },
}

# Chaînes multi-sauts : chaque relation doit apparaître dans au moins 1 document
RELATIONS = [
    ("Alice Benali", "WORKS_FOR", "Université Atlas de Rabat"),
    ("Alice Benali", "LEADS", "Projet GraphIA"),
    ("Projet GraphIA", "USES", "Neo4j"),
    ("Projet GraphIA", "USES", "Apache Spark"),
    ("FundX Capital", "FUNDS", "Projet GraphIA"),
    ("InnoTech Solutions", "COLLABORATES_WITH", "Centre de Recherche IMED"),
    ("Mohamed Tazi", "PARTICIPATES_IN", "Conférence IA Maroc 2024"),
    ("Jean-Pierre Dubois", "WORKS_FOR", "InnoTech Solutions"),
    ("InnoTech Solutions", "LOCATED_IN", "Paris"),
    ("DataBridge", "USES", "Python"),
    ("Sara El Mansouri", "LEADS", "DataBridge"),
    ("Centre de Recherche IMED", "ORGANIZES", "Conférence IA Maroc 2024"),
]

# ---------------------------------------------------------------------------
# Contenu textuel pré-défini par document (assure toutes les relations)
# ---------------------------------------------------------------------------

HTML_CONTENTS = [
    # doc_01 : Alice → UAR + Alice → GraphIA + GraphIA → Neo4j
    """\
<!DOCTYPE html>
<html lang="fr">
<head><title>Profil Alice Benali</title></head>
<body>
<h1>Dr Alice Benali</h1>
<p>A. Benali est professeure à l'Université Atlas de Rabat (UAR), où elle dirige
le Projet GraphIA. Son équipe exploite Neo4j pour modéliser les connaissances.
</p>
<p>licence: synthetic</p>
</body>
</html>""",
    # doc_02 : GraphIA → Spark + FundX → GraphIA
    """\
<!DOCTYPE html>
<html lang="fr">
<head><title>Financement GraphIA</title></head>
<body>
<h1>Projet GraphIA et ses technologies</h1>
<p>Le Proj. GraphIA utilise Apache Spark pour le traitement distribué.
FundX Capital a décidé de financer Projet GraphIA lors du dernier tour de table.
</p>
<p>licence: synthetic</p>
</body>
</html>""",
    # doc_03 : InnoTech → IMED + Jean-Pierre → InnoTech
    """\
<!DOCTYPE html>
<html lang="fr">
<head><title>Partenariats InnoTech</title></head>
<body>
<h1>InnoTech Solutions et le CR-IMED</h1>
<p>InnoTech Solutions collabore avec le Centre de Recherche IMED sur plusieurs projets.
J.-P. Dubois, directeur R&amp;D chez InnoTech Solutions, coordonne ces travaux.
InnoTech est localisé à Paris.</p>
<p>licence: synthetic</p>
</body>
</html>""",
    # doc_04 : Mohamed Tazi → ConfIA + IMED → Organise ConfIA
    """\
<!DOCTYPE html>
<html lang="fr">
<head><title>Conférence IA Maroc 2024</title></head>
<body>
<h1>ConfIA2024 — Programme</h1>
<p>Le Centre de Recherche IMED organise la Conférence IA Maroc 2024.
Prof. Tazi participe activement à la Conférence IA Maroc 2024.
</p>
<p>licence: synthetic</p>
</body>
</html>""",
    # doc_05 : Sara → DataBridge + DataBridge → Python
    """\
<!DOCTYPE html>
<html lang="fr">
<head><title>Projet DataBridge</title></head>
<body>
<h1>Data Bridge — Présentation</h1>
<p>Sara EM pilote le projet DataBridge. DataBridge repose entièrement sur Python 3
pour son pipeline d'ingestion de données.</p>
<p>licence: synthetic</p>
</body>
</html>""",
]

PDF_TEXTS = [
    "Rapport annuel — Université Atlas de Rabat\n\n"
    "Alice B. dirige le Projet GraphIA depuis 2022.\n"
    "Le graphe de connaissances utilise Neo4J comme base de données graphe.\n"
    "licence: synthetic",

    "Note de recherche — Apache Spark et GraphIA\n\n"
    "Proj. GraphIA exploite Spark pour la déduplication à grande échelle.\n"
    "FundX a accordé un financement de série A au projet.\n"
    "licence: synthetic",

    "Compte-rendu partenariat ITS / IMED\n\n"
    "InnoTech collabore avec CR-IMED sur l'IA appliquée.\n"
    "JP Dubois représente InnoTech Solutions dans ce partenariat.\n"
    "InnoTech Solutions est basé à Paris.\n"
    "licence: synthetic",

    "Actes ConfIA2024\n\n"
    "La Conférence IA Maroc 2024 est organisée par le Centre de Recherche IMED.\n"
    "M. Tazi présente ses travaux sur les graphes de connaissances.\n"
    "licence: synthetic",

    "Fiche projet DataBridge\n\n"
    "S. El Mansouri est responsable du projet DataBridge.\n"
    "Le projet utilise Python 3 pour l'ensemble du traitement.\n"
    "licence: synthetic",
]

WORD_PARAGRAPHS = [
    [
        "Université Atlas de Rabat — Rapport de recherche",
        "Dr Alice Benali, rattachée à l'Université Atlas de Rabat (UAR), "
        "coordonne le Projet GraphIA.",
        "Le projet utilise Neo4j pour la persistance du graphe.",
        "licence: synthetic",
    ],
    [
        "Présentation FundX Capital",
        "FundX Capital investit dans des projets d'IA. "
        "GraphIA, porté par Univ. Atlas Rabat, bénéficie de ce soutien.",
        "Apache Spark est au cœur du pipeline de traitement de GraphIA.",
        "licence: synthetic",
    ],
    [
        "InnoTech Solutions — Fiche partenaire",
        "ITS collabore avec IMED sur des projets de NLP.",
        "J.-P. Dubois, responsable technique chez InnoTech Solutions, "
        "assure le suivi du partenariat.",
        "InnoTech Solutions est localisé à Paris.",
        "licence: synthetic",
    ],
    [
        "Conférence IA Maroc 2024 — Programme détaillé",
        "CR-IMED organise la Conférence IA Maroc 2024 à Casablanca.",
        "Prof. Tazi interviendra lors de la session plénière sur les graphes.",
        "licence: synthetic",
    ],
    [
        "DataBridge — Documentation technique",
        "Sara El Mansouri dirige le projet Data Bridge.",
        "DataBridge s'appuie sur Python pour son moteur d'extraction.",
        "Voir aussi : Python 3, Spark.",
        "licence: synthetic",
    ],
]

JSON_DOCS = [
    {
        "title": "Profil chercheur",
        "name": "Alice Benali",
        "affiliation": "Université Atlas de Rabat",
        "project": "Projet GraphIA",
        "technology": "Neo4j",
        "license": "synthetic",
    },
    {
        "title": "Fiche projet",
        "project": "GraphIA",
        "sponsor": "FundX Capital",
        "stack": {"batch": "Apache Spark", "graph": "Neo4J"},
        "license": "synthetic",
    },
    {
        "title": "Partenariat",
        "organizations": ["InnoTech Solutions", "Centre de Recherche IMED"],
        "contact": "JP Dubois",
        "location": "Paris",
        "license": "synthetic",
    },
    {
        "title": "Événement",
        "event": "Conférence IA Maroc 2024",
        "organizer": "CR-IMED",
        "speaker": "M. Tazi",
        "alias": "ConfIA2024",
        "license": "synthetic",
    },
    {
        "title": "Projet DataBridge",
        "lead": "Sara El Mansouri",
        "project": "DataBridge",
        "technology": "Python 3",
        "alias_project": "Data Bridge",
        "license": "synthetic",
    },
]

EMAIL_CONTENTS = [
    {
        "from": "alice.benali@uar.ma",
        "to": "direction@uar.ma",
        "subject": "Avancement Projet GraphIA",
        "date": "Mon, 15 Jan 2024 10:00:00 +0100",
        "body": (
            "Bonjour,\n\n"
            "Je vous informe que le Projet GraphIA progresse bien. "
            "Nous utilisons Neo4j et Apache Spark pour la phase de traitement.\n"
            "Dr Alice Benali\n"
            "Université Atlas de Rabat\n\n"
            "licence: synthetic"
        ),
    },
    {
        "from": "direction@fundx.com",
        "to": "alice.benali@uar.ma",
        "subject": "Financement GraphIA confirmé",
        "date": "Tue, 16 Jan 2024 09:00:00 +0100",
        "body": (
            "Chère A. Benali,\n\n"
            "FundX Capital est heureux de confirmer le financement de Proj. GraphIA.\n"
            "Spark sera utilisé pour les analyses distribuées.\n\n"
            "Cordialement,\n"
            "FundX\n\n"
            "licence: synthetic"
        ),
    },
    {
        "from": "jpdubois@innotech.fr",
        "to": "imed@cr-imed.ma",
        "subject": "Collaboration InnoTech / IMED",
        "date": "Wed, 17 Jan 2024 14:30:00 +0100",
        "body": (
            "Bonjour,\n\n"
            "J.-P. Dubois de InnoTech Solutions vous contacte "
            "pour finaliser notre collaboration avec le Centre de Recherche IMED.\n"
            "Notre siège est à Paris.\n\n"
            "licence: synthetic"
        ),
    },
    {
        "from": "conf@cr-imed.ma",
        "to": "tazi@imed.ma",
        "subject": "Invitation ConfIA2024",
        "date": "Thu, 18 Jan 2024 11:00:00 +0100",
        "body": (
            "Cher Prof. Tazi,\n\n"
            "Le Centre de Recherche IMED vous invite à participer "
            "à la Conférence IA Maroc 2024.\n"
            "Votre intervention sur les graphes est très attendue.\n\n"
            "licence: synthetic"
        ),
    },
    {
        "from": "sara.elmansouri@databridge.io",
        "to": "team@databridge.io",
        "subject": "Mise à jour DataBridge",
        "date": "Fri, 19 Jan 2024 16:00:00 +0100",
        "body": (
            "Équipe,\n\n"
            "S. El Mansouri ici. Le projet Data Bridge avance.\n"
            "Toute la stack Python 3 est opérationnelle.\n\n"
            "licence: synthetic"
        ),
    },
]


# ---------------------------------------------------------------------------
# Générateur PDF minimal (sans dépendance externe)
# ---------------------------------------------------------------------------

def make_minimal_pdf(text: str) -> bytes:
    """Génère un PDF minimal valide que pdfminer peut parser."""
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


# ---------------------------------------------------------------------------
# Génération des fichiers
# ---------------------------------------------------------------------------

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def generate_html(corpus_dir: Path) -> list[dict]:
    out_dir = corpus_dir / "html"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries = []
    for i, html_content in enumerate(HTML_CONTENTS, start=1):
        data = html_content.encode("utf-8")
        filename = f"doc_{i:02d}.html"
        (out_dir / filename).write_bytes(data)
        manifest_entries.append({
            "filename": f"html/{filename}",
            "document_type": "html",
            "sha256": sha256(data),
        })
    return manifest_entries


def generate_pdf(corpus_dir: Path) -> list[dict]:
    out_dir = corpus_dir / "pdf"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries = []
    for i, text in enumerate(PDF_TEXTS, start=1):
        data = make_minimal_pdf(text)
        filename = f"doc_{i:02d}.pdf"
        (out_dir / filename).write_bytes(data)
        manifest_entries.append({
            "filename": f"pdf/{filename}",
            "document_type": "pdf",
            "sha256": sha256(data),
        })
    return manifest_entries


def generate_word(corpus_dir: Path) -> list[dict]:
    try:
        import docx
    except ImportError:
        print("ERREUR: python-docx non installé. Lancez: pip install python-docx==1.1.2")
        sys.exit(1)

    out_dir = corpus_dir / "word"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries = []
    for i, paragraphs in enumerate(WORD_PARAGRAPHS, start=1):
        document = docx.Document()
        for para in paragraphs:
            document.add_paragraph(para)
        buf = io.BytesIO()
        document.save(buf)
        data = buf.getvalue()
        filename = f"doc_{i:02d}.docx"
        (out_dir / filename).write_bytes(data)
        manifest_entries.append({
            "filename": f"word/{filename}",
            "document_type": "word",
            "sha256": sha256(data),
        })
    return manifest_entries


def generate_json(corpus_dir: Path) -> list[dict]:
    out_dir = corpus_dir / "json"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries = []
    for i, doc in enumerate(JSON_DOCS, start=1):
        data = json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8")
        filename = f"doc_{i:02d}.json"
        (out_dir / filename).write_bytes(data)
        manifest_entries.append({
            "filename": f"json/{filename}",
            "document_type": "json",
            "sha256": sha256(data),
        })
    return manifest_entries


def generate_email(corpus_dir: Path) -> list[dict]:
    out_dir = corpus_dir / "email"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries = []
    for i, eml in enumerate(EMAIL_CONTENTS, start=1):
        lines = [
            f"From: {eml['from']}",
            f"To: {eml['to']}",
            f"Subject: {eml['subject']}",
            f"Date: {eml['date']}",
            "MIME-Version: 1.0",
            "Content-Type: text/plain; charset=utf-8",
            "",
            eml["body"],
        ]
        data = "\n".join(lines).encode("utf-8")
        filename = f"doc_{i:02d}.eml"
        (out_dir / filename).write_bytes(data)
        manifest_entries.append({
            "filename": f"email/{filename}",
            "document_type": "email",
            "sha256": sha256(data),
        })
    return manifest_entries


def update_extraction_gold(gold_path: Path, manifest_files: list[dict]) -> None:
    """Met à jour data/extraction_gold.json avec le champ 'documents'."""
    gold_path.parent.mkdir(parents=True, exist_ok=True)

    gold_data = {
        "version": "1.0.0",
        "entities": [
            {
                "canonical_label": "Université Atlas de Rabat",
                "type": "Organization",
                "variants": [
                    {"label": "Univ. Atlas Rabat", "fusion": "normalization"},
                    {"label": "Université Atlas", "fusion": "fuzzy"},
                    {"label": "UAR", "fusion": "none"},
                ],
            },
            {
                "canonical_label": "Alice Benali",
                "type": "Person",
                "variants": [
                    {"label": "A. Benali", "fusion": "fuzzy"},
                    {"label": "Alice B.", "fusion": "fuzzy"},
                    {"label": "Dr Alice Benali", "fusion": "normalization"},
                ],
            },
            {
                "canonical_label": "InnoTech Solutions",
                "type": "Organization",
                "variants": [
                    {"label": "InnoTech", "fusion": "fuzzy"},
                    {"label": "ITS", "fusion": "none"},
                    {"label": "Inno Tech Solutions", "fusion": "normalization"},
                ],
            },
            {
                "canonical_label": "Projet GraphIA",
                "type": "Project",
                "variants": [
                    {"label": "GraphIA", "fusion": "fuzzy"},
                    {"label": "Proj. GraphIA", "fusion": "normalization"},
                    {"label": "Project GraphIA", "fusion": "normalization"},
                ],
            },
            {
                "canonical_label": "Neo4j",
                "type": "Technology",
                "variants": [
                    {"label": "Neo4J", "fusion": "normalization"},
                ],
            },
            {
                "canonical_label": "Apache Spark",
                "type": "Technology",
                "variants": [
                    {"label": "Spark", "fusion": "fuzzy"},
                ],
            },
            {
                "canonical_label": "Mohamed Tazi",
                "type": "Person",
                "variants": [
                    {"label": "M. Tazi", "fusion": "fuzzy"},
                    {"label": "Prof. Tazi", "fusion": "fuzzy"},
                ],
            },
            {
                "canonical_label": "Centre de Recherche IMED",
                "type": "Organization",
                "variants": [
                    {"label": "IMED", "fusion": "none"},
                    {"label": "CR-IMED", "fusion": "fuzzy"},
                ],
            },
            {
                "canonical_label": "Conférence IA Maroc 2024",
                "type": "Event",
                "variants": [
                    {"label": "ConfIA2024", "fusion": "none"},
                    {"label": "Conf. IA Maroc", "fusion": "fuzzy"},
                ],
            },
            {
                "canonical_label": "DataBridge",
                "type": "Project",
                "variants": [
                    {"label": "Data Bridge", "fusion": "normalization"},
                ],
            },
            {
                "canonical_label": "Jean-Pierre Dubois",
                "type": "Person",
                "variants": [
                    {"label": "JP Dubois", "fusion": "fuzzy"},
                    {"label": "J.-P. Dubois", "fusion": "normalization"},
                ],
            },
            {
                "canonical_label": "Sara El Mansouri",
                "type": "Person",
                "variants": [
                    {"label": "S. El Mansouri", "fusion": "fuzzy"},
                    {"label": "Sara EM", "fusion": "none"},
                ],
            },
            {
                "canonical_label": "FundX Capital",
                "type": "Organization",
                "variants": [
                    {"label": "FundX", "fusion": "fuzzy"},
                    {"label": "Fund X Capital", "fusion": "normalization"},
                ],
            },
            {
                "canonical_label": "Python",
                "type": "Technology",
                "variants": [
                    {"label": "Python 3", "fusion": "normalization"},
                    {"label": "Python3", "fusion": "normalization"},
                ],
            },
        ],
        "relations": [
            {
                "relation_type": "WORKS_FOR",
                "source": "Alice Benali",
                "target": "Université Atlas de Rabat",
            },
            {
                "relation_type": "LEADS",
                "source": "Alice Benali",
                "target": "Projet GraphIA",
            },
            {
                "relation_type": "USES",
                "source": "Projet GraphIA",
                "target": "Neo4j",
            },
            {
                "relation_type": "USES",
                "source": "Projet GraphIA",
                "target": "Apache Spark",
            },
            {
                "relation_type": "FUNDS",
                "source": "FundX Capital",
                "target": "Projet GraphIA",
            },
            {
                "relation_type": "COLLABORATES_WITH",
                "source": "InnoTech Solutions",
                "target": "Centre de Recherche IMED",
            },
            {
                "relation_type": "PARTICIPATES_IN",
                "source": "Mohamed Tazi",
                "target": "Conférence IA Maroc 2024",
            },
            {
                "relation_type": "WORKS_FOR",
                "source": "Jean-Pierre Dubois",
                "target": "InnoTech Solutions",
            },
            {
                "relation_type": "LOCATED_IN",
                "source": "InnoTech Solutions",
                "target": "Paris",
            },
            {
                "relation_type": "USES",
                "source": "DataBridge",
                "target": "Python",
            },
            {
                "relation_type": "LEADS",
                "source": "Sara El Mansouri",
                "target": "DataBridge",
            },
            {
                "relation_type": "ORGANIZES",
                "source": "Centre de Recherche IMED",
                "target": "Conférence IA Maroc 2024",
            },
        ],
        "documents": manifest_files,
    }

    gold_path.write_text(
        json.dumps(gold_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  Écrit : {gold_path}")


def main() -> None:
    print(f"Génération du corpus synthétique (SEED={SEED}) …")
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    all_files: list[dict] = []

    print("  Génération HTML …")
    all_files.extend(generate_html(CORPUS_DIR))

    print("  Génération PDF …")
    all_files.extend(generate_pdf(CORPUS_DIR))

    print("  Génération Word …")
    all_files.extend(generate_word(CORPUS_DIR))

    print("  Génération JSON …")
    all_files.extend(generate_json(CORPUS_DIR))

    print("  Génération email …")
    all_files.extend(generate_email(CORPUS_DIR))

    # Manifest
    manifest = {
        "generated_with_seed": SEED,
        "files": all_files,
    }
    manifest_path = CORPUS_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  Écrit : {manifest_path} ({len(all_files)} fichiers)")

    # extraction_gold.json
    print("  Mise à jour extraction_gold.json …")
    update_extraction_gold(GOLD_PATH, all_files)

    print(f"\nCorpus généré dans : {CORPUS_DIR}")
    print("Terminé.")


if __name__ == "__main__":
    main()
