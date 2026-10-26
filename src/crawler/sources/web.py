"""Source de collecte web : GET HTTP avec respect de robots.txt et rate-limit."""

from __future__ import annotations

import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from src.crawler.sources.base import BaseSource
from src.shared.logging import get_logger

logger = get_logger("web_source")


class WebSource(BaseSource):
    """Collecte une page web en respectant robots.txt et la limite de débit."""

    def fetch(self, config: dict) -> list[tuple[bytes, str]]:
        """Effectue un GET sur l'URL configurée.

        Args:
            config: Doit contenir ``url`` (str).
                    Optionnel : ``rate_limit_per_sec`` (float, défaut 1.0),
                    ``timeout`` (int, défaut 10), ``allowed_sources`` (list[str]).

        Returns:
            Liste de (contenu_bytes, url).
        """
        import requests

        url: str = config.get("url", "")
        if not url:
            logger.warning("web_source_no_url")
            return []

        rate_limit: float = float(config.get("rate_limit_per_sec", 1.0))
        timeout: int = int(config.get("timeout", 10))

        # Vérification allowed_sources
        allowed_sources: list[str] = config.get("allowed_sources", [])
        if allowed_sources and url not in allowed_sources:
            logger.info("web_source_not_allowed", url=url)
            return []

        # Respect de robots.txt
        if not self._is_allowed(url):
            logger.info("web_source_robots_denied", url=url)
            return []

        # Rate-limit
        if rate_limit > 0:
            time.sleep(1.0 / rate_limit)

        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return [(response.content, url)]
        except Exception as exc:
            logger.warning("web_source_fetch_error", url=url, error=str(exc))
            return []

    def _is_allowed(self, url: str) -> bool:
        """Vérifie que l'URL est autorisée par robots.txt."""
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            return rp.can_fetch("*", url)
        except Exception as exc:
            logger.warning("robots_txt_check_failed", url=url, error=str(exc))
            # En cas d'erreur, on autorise par défaut
            return True
