"""Classe de base abstraite pour toutes les sources de collecte."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseSource(ABC):
    """Interface commune à toutes les sources de collecte."""

    @abstractmethod
    def fetch(self, config: dict) -> list[tuple[bytes, str]]:
        """Collecte des documents depuis la source.

        Args:
            config: Configuration spécifique à la source (url, path, query…).

        Returns:
            Liste de tuples (contenu_brut, identifiant_source).
        """
        ...
