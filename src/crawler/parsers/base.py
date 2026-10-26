"""Classe de base abstraite pour tous les parseurs de documents."""

from abc import ABC, abstractmethod


class BaseParser(ABC):
    """Interface commune à tous les parseurs."""

    @abstractmethod
    def parse(self, content: bytes, source: str) -> str:
        """Extrait et retourne le texte brut du document.

        Args:
            content: Contenu binaire du document.
            source: URL ou chemin d'origine (utilisé pour les logs).

        Returns:
            Texte extrait.

        Raises:
            CorruptedFileError: Si le document ne peut pas être parsé.
        """
        ...

    @abstractmethod
    def can_parse(self, document_type: str) -> bool:
        """Indique si ce parseur prend en charge le type donné."""
        ...
