"""
Tests de propriétés Hypothesis pour src/shared/ids.py.

**Validates: Requirements 10.2, 28.1**

Propriétés testées :
- Déterminisme de entity_id : un même type + label produit toujours le même id.
- Format : entity_id retourne exactement 16 caractères hexadécimaux.

Conformément à l'exigence 28.4, aucune fixture à portée fonction n'est
utilisée dans @given ; les dépendances sont instanciées dans le test.
"""

import os
import re

from hypothesis import given, settings
from hypothesis import strategies as st

from src.shared.ids import entity_id

# Types de nœuds valides (instanciés directement, sans fixture)
_NODE_TYPES = [
    "Person",
    "Organization",
    "Location",
    "Project",
    "Technology",
    "Event",
    "Document",
]

# ---------------------------------------------------------------------------
# Stratégies
# ---------------------------------------------------------------------------

node_type_strategy = st.sampled_from(_NODE_TYPES)

# Libellés : chaînes Unicode non vides, longueur raisonnable
label_strategy = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),  # exclut les surrogates
    min_size=1,
    max_size=200,
)


# ---------------------------------------------------------------------------
# Propriétés
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(entity_type=node_type_strategy, label=label_strategy)
def test_same_type_same_normalized_label_same_id(entity_type: str, label: str):
    """**Validates: Requirements 10.2**

    Pour tout type de nœud valide et tout libellé, deux appels à entity_id
    avec les mêmes arguments retournent le même identifiant (déterminisme).
    """
    id1 = entity_id(entity_type, label)
    id2 = entity_id(entity_type, label)
    assert id1 == id2, (
        f"entity_id n'est pas déterministe pour type={entity_type!r}, label={label!r}: "
        f"{id1!r} != {id2!r}"
    )


@settings(max_examples=100)
@given(entity_type=node_type_strategy, label=label_strategy)
def test_entity_id_is_16_hex_chars(entity_type: str, label: str):
    """**Validates: Requirements 10.2**

    entity_id retourne toujours une chaîne de exactement 16 caractères
    hexadécimaux (minuscules).
    """
    result = entity_id(entity_type, label)
    assert len(result) == 16, (
        f"Longueur attendue 16, obtenu {len(result)} pour "
        f"type={entity_type!r}, label={label!r}"
    )
    assert re.fullmatch(r"[0-9a-f]{16}", result) is not None, (
        f"Format hexadécimal invalide : {result!r}"
    )
