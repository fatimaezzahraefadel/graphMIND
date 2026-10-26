"""
Fixtures partagées entre tous les tests.
"""

import os
import pytest

from src.shared.graph_schema import GraphSchema

# Chemin absolu vers le schéma, indépendant du répertoire de travail
_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "graph_schema.yaml")


@pytest.fixture(scope="session")
def schema() -> GraphSchema:
    """Charge config/graph_schema.yaml une seule fois pour toute la session."""
    return GraphSchema.load(_SCHEMA_PATH)
