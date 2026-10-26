"""
Normalisation de libellés et génération d'identifiants déterministes.

Les identifiants sont des empreintes SHA-256 tronquées à 16 caractères
hexadécimaux, ce qui garantit la reproductibilité inter-exécutions et
l'idempotence du pipeline.

Usage::

    from src.shared.ids import normalize_label, entity_id, relation_id

    eid = entity_id("Person", "Alice Martin")   # '4a7f…' (16 hex chars)
    rid = relation_id("WORKS_FOR", eid1, eid2)
"""

import hashlib
import re
import unicodedata


def normalize_label(label: str) -> str:
    """Normalise un libellé pour la comparaison et la génération d'identifiants.

    Étapes :
    1. Décomposition Unicode NFKD (sépare les lettres de leurs diacritiques).
    2. Suppression des caractères combinants (accents, cédilles…).
    3. Passage en minuscules et remplacement des caractères non alphanumériques
       (hors espaces) par un espace.
    4. Réduction des espaces multiples et suppression des espaces en bordure.

    Args:
        label: Libellé brut.

    Returns:
        Libellé normalisé (minuscules, sans accents, sans ponctuation).
    """
    s = unicodedata.normalize("NFKD", label)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def entity_id(entity_type: str, label: str) -> str:
    """Génère un identifiant déterministe pour une entité.

    L'identifiant est calculé comme ``sha256("{entity_type}:{label_normalisé}")[:16]``.

    Args:
        entity_type: Type de l'entité (ex. ``"Person"``).
        label: Libellé de l'entité (ex. ``"Alice Martin"``).

    Returns:
        Chaîne hexadécimale de 16 caractères.
    """
    return hashlib.sha256(f"{entity_type}:{normalize_label(label)}".encode()).hexdigest()[:16]


def relation_id(rel_type: str, src_id: str, tgt_id: str) -> str:
    """Génère un identifiant déterministe pour une relation.

    L'identifiant est calculé comme
    ``sha256("{rel_type}:{src_id}:{tgt_id}")[:16]``.

    Args:
        rel_type: Type de la relation (ex. ``"WORKS_FOR"``).
        src_id: Identifiant du nœud source.
        tgt_id: Identifiant du nœud cible.

    Returns:
        Chaîne hexadécimale de 16 caractères.
    """
    return hashlib.sha256(f"{rel_type}:{src_id}:{tgt_id}".encode()).hexdigest()[:16]
