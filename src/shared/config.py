"""
Configuration centralisée via variables d'environnement.

Toutes les variables sont lues depuis l'environnement (ou un fichier .env).
Les secrets (LLM_API_KEY, JWT_SECRET, ADMIN_PASSWORD) n'ont pas de valeur
par défaut et doivent être fournis explicitement ; ils valent None si absents.

Usage::

    from src.shared.config import Settings, require_env
    settings = Settings.get()
    print(settings.neo4j_uri)
    api_key = settings.require_llm_api_key()
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.shared.exceptions import ConfigError


def require_env(name: str, value: Optional[str], app_env: str) -> str:
    """Valide qu'une variable d'environnement est présente et configurée.

    Args:
        name: Nom de la variable d'environnement (pour le message d'erreur).
        value: Valeur actuelle de la variable (peut être None).
        app_env: Environnement applicatif courant ('dev', 'prod', etc.).

    Returns:
        La valeur de la variable si elle est valide.

    Raises:
        ConfigError: Si la valeur est absente, vide, ou vaut 'changeme' en dehors de 'dev'.
    """
    if value is None or value == "":
        raise ConfigError(f"Variable d'environnement manquante ou vide : {name}")
    if value == "changeme" and app_env != "dev":
        raise ConfigError(f"Variable d'environnement non configurée pour la production : {name}")
    return value


class Settings(BaseSettings):
    """Paramètres de la plateforme lus depuis l'environnement.

    Les secrets (LLM_API_KEY, JWT_SECRET, ADMIN_PASSWORD) sont optionnels
    et valent None si non fournis — le code applicatif doit les vérifier
    avant usage et lever LLMConfigError / AuthError le cas échéant.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------
    llm_provider: str = Field(default="openai", description="openai | anthropic | ollama")
    llm_model: str = Field(default="gpt-4o-mini")
    llm_api_key: Optional[str] = Field(default=None, description="Clé API LLM — aucune valeur par défaut")
    llm_base_url: str = Field(default="", description="URL de base (ex. http://ollama:11434)")
    mock_llm: bool = Field(default=True)
    mock_crawler: bool = Field(default=True)
    mock_embeddings: bool = Field(default=True)
    prompt_version: int = Field(default=1)

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------
    embedding_model: str = Field(default="paraphrase-multilingual-MiniLM-L12-v2")
    embedding_dim: int = Field(default=384)

    # ------------------------------------------------------------------
    # Résolution d'entités
    # ------------------------------------------------------------------
    enable_entity_resolution: bool = Field(default=True)
    similarity_threshold: float = Field(default=0.85)

    # ------------------------------------------------------------------
    # Infrastructure
    # ------------------------------------------------------------------
    neo4j_uri: str = Field(default="bolt://neo4j:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="changeme")
    hdfs_namenode_url: str = Field(default="http://namenode:9870")
    spark_master_url: str = Field(default="spark://spark-master:7077")

    # ------------------------------------------------------------------
    # GraphRAG
    # ------------------------------------------------------------------
    retrieval_mode: str = Field(default="hybrid", description="vector | neighborhood | text2cypher | hybrid")
    max_context_nodes: int = Field(default=50)
    neighborhood_depth: int = Field(default=2)

    # ------------------------------------------------------------------
    # Crawler
    # ------------------------------------------------------------------
    allowed_sources: str = Field(default="", description="Liste séparée par des virgules")
    crawl_rate_limit_per_sec: float = Field(default=1.0)

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------
    jwt_secret: Optional[str] = Field(default=None, description="Secret JWT — aucune valeur par défaut")
    jwt_expire_minutes: int = Field(default=60)
    admin_username: str = Field(default="admin")
    admin_password: Optional[str] = Field(default=None, description="Mot de passe admin — aucune valeur par défaut")

    # ------------------------------------------------------------------
    # Évaluation
    # ------------------------------------------------------------------
    judge_enabled: bool = Field(default=False)
    llm_price_in_per_1k: float = Field(default=0.0)
    llm_price_out_per_1k: float = Field(default=0.0)

    # ------------------------------------------------------------------
    # Environnement
    # ------------------------------------------------------------------
    app_env: str = Field(default="dev", description="dev | prod — en prod, les secrets 'changeme' sont refusés")

    # ------------------------------------------------------------------
    # Méthodes de validation des secrets (appelées à la demande, pas au chargement)
    # ------------------------------------------------------------------

    def require_llm_api_key(self) -> str:
        """Retourne la clé API LLM après validation.

        Aucune clé n'est requise si ``mock_llm=True`` ou ``llm_provider='ollama'``.

        Returns:
            La clé API LLM validée.

        Raises:
            ConfigError: Si la clé est absente/invalide et qu'elle est requise.
        """
        if self.mock_llm or self.llm_provider.lower() == "ollama":
            return self.llm_api_key or ""
        return require_env("LLM_API_KEY", self.llm_api_key, self.app_env)

    def require_jwt_secret(self) -> str:
        """Retourne le secret JWT après validation.

        Returns:
            Le secret JWT validé.

        Raises:
            ConfigError: Si le secret est absent ou invalide.
        """
        return require_env("JWT_SECRET", self.jwt_secret, self.app_env)

    def require_admin_password(self) -> str:
        """Retourne le mot de passe admin après validation.

        Returns:
            Le mot de passe admin validé.

        Raises:
            ConfigError: Si le mot de passe est absent ou invalide.
        """
        return require_env("ADMIN_PASSWORD", self.admin_password, self.app_env)

    # ------------------------------------------------------------------
    # Méthode de classe singleton
    # ------------------------------------------------------------------

    @classmethod
    @lru_cache(maxsize=1)
    def get(cls) -> "Settings":
        """Retourne l'instance singleton des paramètres.

        L'instance est mise en cache après le premier appel grâce à
        ``@lru_cache``.  Appeler ``Settings.get.cache_clear()`` dans les
        tests pour forcer le rechargement.

        Returns:
            Instance de Settings.
        """
        return cls()
