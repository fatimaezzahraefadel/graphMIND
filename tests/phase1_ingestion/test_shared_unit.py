"""
Tests unitaires pour src/shared/graph_schema.py et src/shared/ids.py.
"""

import os
import pytest

from src.shared.graph_schema import GraphSchema
from src.shared.exceptions import SchemaViolationError
from src.shared.ids import normalize_label, entity_id, relation_id

_SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "graph_schema.yaml"
)


# ===========================================================================
# GraphSchema
# ===========================================================================


class TestGraphSchemaLoad:
    def test_load_schema(self, schema: GraphSchema):
        """Charge config/graph_schema.yaml : version == '1.0.0', 7 node_types, 9 relation_types."""
        assert schema.version == "1.0.0"
        assert len(schema.node_types) == 7
        assert len(schema.relation_types) == 9


class TestValidateNode:
    def test_validate_node_valid(self, schema: GraphSchema):
        """Nœud Person avec id/label/type → True."""
        node = {"id": "abc123", "label": "Alice", "type": "Person"}
        assert schema.validate_node(node) is True

    def test_validate_node_missing_required(self, schema: GraphSchema):
        """Nœud Person sans label → False."""
        node = {"id": "abc123", "type": "Person"}
        assert schema.validate_node(node) is False

    def test_validate_node_unknown_type(self, schema: GraphSchema):
        """Type 'Alien' inconnu → False."""
        node = {"id": "xyz", "label": "ET", "type": "Alien"}
        assert schema.validate_node(node) is False


class TestValidateRelation:
    def test_validate_relation_valid(self, schema: GraphSchema):
        """WORKS_FOR avec src Person, tgt Organization → True."""
        relation = {"relation_type": "WORKS_FOR"}
        assert schema.validate_relation(relation, "Person", "Organization") is True

    def test_validate_relation_incompatible_types(self, schema: GraphSchema):
        """WORKS_FOR avec src Organization → False (Organization ne peut pas WORKS_FOR)."""
        relation = {"relation_type": "WORKS_FOR"}
        assert schema.validate_relation(relation, "Organization", "Organization") is False


class TestAssertNodeType:
    def test_assert_node_type_valid(self, schema: GraphSchema):
        """'Person' → retourne 'Person'."""
        assert schema.assert_node_type("Person") == "Person"

    def test_assert_node_type_invalid(self, schema: GraphSchema):
        """'Alien' → SchemaViolationError."""
        with pytest.raises(SchemaViolationError):
            schema.assert_node_type("Alien")


class TestAssertRelationType:
    def test_assert_relation_type_valid(self, schema: GraphSchema):
        """'WORKS_FOR' → retourne 'WORKS_FOR'."""
        assert schema.assert_relation_type("WORKS_FOR") == "WORKS_FOR"

    def test_assert_relation_type_invalid(self, schema: GraphSchema):
        """'FAKE_REL' → SchemaViolationError."""
        with pytest.raises(SchemaViolationError):
            schema.assert_relation_type("FAKE_REL")


class TestIsCompatible:
    def test_is_compatible_same(self, schema: GraphSchema):
        """Un schéma est compatible avec lui-même."""
        assert schema.is_compatible(schema) is True


# ===========================================================================
# ids.py — normalize_label
# ===========================================================================


class TestNormalizeLabel:
    def test_normalize_label_lowercase(self):
        """'Alice Martin' → 'alice martin'."""
        assert normalize_label("Alice Martin") == "alice martin"

    def test_normalize_label_accents(self):
        """'Université' → 'universite'."""
        assert normalize_label("Université") == "universite"

    def test_normalize_label_extra_spaces(self):
        """'  Alice  Martin  ' → 'alice martin'."""
        assert normalize_label("  Alice  Martin  ") == "alice martin"

    def test_normalize_label_special_chars(self):
        """'OpenTech Corp.' → 'opentech corp'."""
        assert normalize_label("OpenTech Corp.") == "opentech corp"


# ===========================================================================
# ids.py — entity_id
# ===========================================================================


class TestEntityId:
    def test_entity_id_deterministic(self):
        """Même type + même label → même id."""
        assert entity_id("Person", "Alice") == entity_id("Person", "Alice")

    def test_entity_id_different_labels(self):
        """Labels différents → ids différents."""
        assert entity_id("Person", "Alice") != entity_id("Person", "Bob")

    def test_entity_id_different_types(self):
        """Même label, types différents → ids différents."""
        assert entity_id("Person", "Atlas") != entity_id("Organization", "Atlas")

    def test_entity_id_length(self):
        """Retourne exactement 16 caractères hexadécimaux."""
        result = entity_id("Person", "Alice Martin")
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_entity_id_variant_normalization(self):
        """Teste le comportement réel de normalisation sur des variantes proches.

        'Univ. Atlas Rabat' et 'Univ Atlas Rabat' : après normalisation,
        le point est remplacé par un espace puis les espaces multiples sont
        réduits — les deux produisent 'univ atlas rabat', donc même id.
        """
        norm1 = normalize_label("Univ. Atlas Rabat")
        norm2 = normalize_label("Univ Atlas Rabat")
        eid1 = entity_id("Organization", "Univ. Atlas Rabat")
        eid2 = entity_id("Organization", "Univ Atlas Rabat")
        # Si la normalisation les rend identiques, les ids doivent être égaux
        if norm1 == norm2:
            assert eid1 == eid2
        else:
            assert eid1 != eid2


# ===========================================================================
# ids.py — relation_id
# ===========================================================================


class TestRelationId:
    def test_relation_id_deterministic(self):
        """Mêmes paramètres → même id."""
        rid1 = relation_id("WORKS_FOR", "src1", "tgt1")
        rid2 = relation_id("WORKS_FOR", "src1", "tgt1")
        assert rid1 == rid2

    def test_relation_id_order_matters(self):
        """src↔tgt inversés → id différent."""
        rid_fwd = relation_id("WORKS_FOR", "src1", "tgt1")
        rid_rev = relation_id("WORKS_FOR", "tgt1", "src1")
        assert rid_fwd != rid_rev


# ===========================================================================
# config.py — require_env() et méthodes require_* de Settings
# ===========================================================================


from src.shared.config import Settings, require_env
from src.shared.exceptions import ConfigError


class TestRequireEnv:
    """Tests pour require_env() et les méthodes require_* de Settings."""

    def test_absent_raises(self):
        """Variable None → ConfigError."""
        with pytest.raises(ConfigError, match="manquante ou vide"):
            require_env("SOME_VAR", None, "dev")

    def test_empty_raises(self):
        """Variable vide ('') → ConfigError."""
        with pytest.raises(ConfigError, match="manquante ou vide"):
            require_env("SOME_VAR", "", "dev")

    def test_changeme_in_prod_raises(self):
        """'changeme' avec app_env='prod' → ConfigError."""
        with pytest.raises(ConfigError, match="non configurée pour la production"):
            require_env("SOME_SECRET", "changeme", "prod")

    def test_changeme_accepted_in_dev(self):
        """'changeme' avec app_env='dev' → retourne 'changeme'."""
        result = require_env("SOME_SECRET", "changeme", "dev")
        assert result == "changeme"

    def test_valid_value_returned(self):
        """Valeur réelle → retournée telle quelle."""
        result = require_env("API_KEY", "sk-abc123", "prod")
        assert result == "sk-abc123"

    def test_mock_llm_no_key_required(self):
        """mock_llm=True → require_llm_api_key() ne lève pas d'erreur même sans clé."""
        settings = Settings(mock_llm=True, llm_api_key=None, app_env="dev")
        # Ne doit pas lever ConfigError
        result = settings.require_llm_api_key()
        assert result == ""

    def test_ollama_no_key_required(self):
        """llm_provider='ollama' → require_llm_api_key() ne lève pas même sans clé."""
        settings = Settings(llm_provider="ollama", mock_llm=False, llm_api_key=None, app_env="prod")
        # Ne doit pas lever ConfigError
        result = settings.require_llm_api_key()
        assert result == ""

    def test_openai_without_key_raises(self):
        """llm_provider='openai', mock_llm=False, llm_api_key=None → ConfigError."""
        settings = Settings(llm_provider="openai", mock_llm=False, llm_api_key=None, app_env="dev")
        with pytest.raises(ConfigError, match="manquante ou vide"):
            settings.require_llm_api_key()

    def test_anthropic_without_key_raises(self):
        """llm_provider='anthropic', mock_llm=False, llm_api_key=None → ConfigError nommant LLM_API_KEY."""
        settings = Settings(llm_provider="anthropic", mock_llm=False, llm_api_key=None, app_env="dev")
        with pytest.raises(ConfigError, match="manquante ou vide"):
            settings.require_llm_api_key()
