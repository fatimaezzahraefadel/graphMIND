"""
Hiérarchie d'exceptions de la plateforme GraphMind.

Toutes les exceptions héritent de PlatformError qui porte deux attributs
de contexte : component (str) et context (dict).
"""


class PlatformError(Exception):
    """Erreur de base de la plateforme."""

    def __init__(self, message: str = "", component: str = "", context: dict | None = None):
        super().__init__(message)
        self.component: str = component
        self.context: dict = context or {}

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"{self.__class__.__name__}("
            f"message={str(self)!r}, "
            f"component={self.component!r}, "
            f"context={self.context!r})"
        )


# ---------------------------------------------------------------------------
# Crawler
# ---------------------------------------------------------------------------

class CrawlerError(PlatformError):
    """Erreur générique du Crawler."""


class UnsupportedDocumentTypeError(CrawlerError):
    """Le type de document n'est pas pris en charge."""


class CorruptedFileError(CrawlerError):
    """Le fichier est corrompu ou illisible."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class ConfigError(PlatformError):
    """Erreur de configuration générale (variable d'environnement manquante ou invalide)."""


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

class LLMConfigError(PlatformError):
    """Configuration LLM invalide ou variable d'environnement manquante."""


class LLMCallError(PlatformError):
    """Échec d'un appel LLM (réseau, timeout, rate-limit…)."""


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

class ExtractionParseError(PlatformError):
    """La sortie du LLM ne respecte pas le format attendu.

    Note : intentionnellement nommée ExtractionParseError et non
    ValidationError pour éviter toute confusion avec pydantic.ValidationError.
    """


class SchemaViolationError(PlatformError):
    """Un nœud ou une relation viole le Graph_Schema."""


# ---------------------------------------------------------------------------
# Résolution d'entités
# ---------------------------------------------------------------------------

class EntityResolutionError(PlatformError):
    """Erreur lors de la résolution / fusion d'entités."""


# ---------------------------------------------------------------------------
# ETL Spark
# ---------------------------------------------------------------------------

class SparkETLError(PlatformError):
    """Erreur lors du traitement Spark ETL."""


# ---------------------------------------------------------------------------
# Neo4j
# ---------------------------------------------------------------------------

class Neo4jLoadError(PlatformError):
    """Erreur lors du chargement dans Neo4j."""


# ---------------------------------------------------------------------------
# Graph Analytics
# ---------------------------------------------------------------------------

class GraphAnalyticsError(PlatformError):
    """Erreur lors d'une analyse de graphe."""


class Text2CypherWriteClauseError(GraphAnalyticsError):
    """La requête Cypher générée contient une clause d'écriture interdite."""


# ---------------------------------------------------------------------------
# GraphRAG
# ---------------------------------------------------------------------------

class GraphRAGError(PlatformError):
    """Erreur dans le service GraphRAG."""


# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------

class AuthError(PlatformError):
    """Erreur d'authentification ou d'autorisation."""
