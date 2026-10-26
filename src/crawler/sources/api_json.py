"""Source de collecte API JSON : GET d'un endpoint JSON et sérialisation en bytes."""

from __future__ import annotations

import json

from src.crawler.sources.base import BaseSource
from src.shared.logging import get_logger

logger = get_logger("api_json_source")


class ApiJsonSource(BaseSource):
    """Collecte la réponse JSON d'une API REST et la sérialise en bytes."""

    def fetch(self, config: dict) -> list[tuple[bytes, str]]:
        """Effectue un GET sur l'URL configurée et retourne le JSON sérialisé.

        Args:
            config: Doit contenir ``url`` (str).
                    Optionnel : ``headers`` (dict), ``timeout`` (int, défaut 10).

        Returns:
            Liste de (json_bytes, url).
        """
        import requests

        url: str = config.get("url", "")
        if not url:
            logger.warning("api_json_source_no_url")
            return []

        headers: dict = config.get("headers", {})
        timeout: int = int(config.get("timeout", 10))

        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            content = json.dumps(data, ensure_ascii=False).encode("utf-8")
            return [(content, url)]
        except Exception as exc:
            logger.warning("api_json_fetch_error", url=url, error=str(exc))
            return []
