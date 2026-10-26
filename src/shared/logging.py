"""
Logging structuré JSON pour la plateforme GraphMind.

Usage::

    from src.shared.logging import get_logger
    logger = get_logger("crawler")
    logger.info("document_collected", source="https://example.com", hash="abc123")

Configuration :
- Processeurs : add_log_level → add_timestamp (ISO 8601) → JSONRenderer
- Les clés sensibles (LLM_API_KEY, JWT_SECRET, ADMIN_PASSWORD) sont filtrées
  avant le rendu final.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

# ---------------------------------------------------------------------------
# Clés à filtrer pour ne jamais logger de secrets
# ---------------------------------------------------------------------------

_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {"llm_api_key", "jwt_secret", "admin_password", "password", "secret"}
)


def _filter_secrets(
    logger: Any,  # noqa: ANN401
    method: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Processeur structlog : remplace les valeurs sensibles par '[FILTERED]'."""
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "[FILTERED]"
    return event_dict


# ---------------------------------------------------------------------------
# Configuration structlog (idempotente — peut être appelée plusieurs fois)
# ---------------------------------------------------------------------------

def _configure_structlog() -> None:
    """Configure structlog avec des processeurs JSON et un handler stdlib."""
    # Handler stdlib → stderr
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))

    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _filter_secrets,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


_configure_structlog()


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def get_logger(component: str) -> structlog.stdlib.BoundLogger:
    """Retourne un logger pré-bindé avec le champ *component*.

    Args:
        component: Nom du composant (ex. "crawler", "extraction", "graphrag").

    Returns:
        Logger structlog prêt à l'emploi.
    """
    return structlog.get_logger().bind(component=component)
