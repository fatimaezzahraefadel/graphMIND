"""
Chargement et validation du Graph_Schema partagé.

Usage::

    from src.shared.graph_schema import GraphSchema
    schema = GraphSchema.load("config/graph_schema.yaml")
    schema.validate_node({"id": "abc", "label": "Alice", "type": "Person"})
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml

from src.shared.exceptions import SchemaViolationError


@dataclass
class NodeTypeSpec:
    """Spécification d'un type de nœud."""

    name: str
    required_props: list[str] = field(default_factory=list)
    optional_props: list[str] = field(default_factory=list)


@dataclass
class RelationTypeSpec:
    """Spécification d'un type de relation."""

    name: str
    source_types: list[str] = field(default_factory=list)
    target_types: list[str] = field(default_factory=list)
    properties: list[str] = field(default_factory=list)


class GraphSchema:
    """Schéma de graphe versionné chargé depuis un fichier YAML."""

    def __init__(self) -> None:
        self.version: str = ""
        self.node_types: dict[str, NodeTypeSpec] = {}
        self.relation_types: dict[str, RelationTypeSpec] = {}

    # ------------------------------------------------------------------
    # Chargement
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: str) -> "GraphSchema":
        """Charge le YAML, construit les dataclasses et retourne l'instance.

        Args:
            path: Chemin vers le fichier ``config/graph_schema.yaml``.

        Returns:
            Instance de GraphSchema entièrement peuplée.
        """
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        schema = cls()
        schema.version = data.get("version", "")

        for name, spec in (data.get("node_types") or {}).items():
            schema.node_types[name] = NodeTypeSpec(
                name=name,
                required_props=list(spec.get("required") or []),
                optional_props=list(spec.get("optional") or []),
            )

        for name, spec in (data.get("relation_types") or {}).items():
            schema.relation_types[name] = RelationTypeSpec(
                name=name,
                source_types=list(spec.get("source") or []),
                target_types=list(spec.get("target") or []),
                properties=list(spec.get("properties") or []),
            )

        return schema

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_node(self, node: dict[str, Any]) -> bool:
        """Vérifie que le nœud est conforme au schéma.

        Args:
            node: Dictionnaire représentant un nœud, doit contenir au
                  minimum ``type`` et toutes les propriétés obligatoires
                  de ce type.

        Returns:
            ``True`` si le nœud est valide, ``False`` sinon.
        """
        node_type = node.get("type")
        if node_type not in self.node_types:
            return False
        spec = self.node_types[node_type]
        return all(prop in node for prop in spec.required_props)

    def validate_relation(
        self,
        relation: dict[str, Any],
        src_type: str,
        tgt_type: str,
    ) -> bool:
        """Vérifie qu'une relation est conforme au schéma.

        Args:
            relation: Dictionnaire représentant une relation, doit
                      contenir ``relation_type``.
            src_type: Type du nœud source.
            tgt_type: Type du nœud cible.

        Returns:
            ``True`` si la relation est valide, ``False`` sinon.
        """
        rel_type = relation.get("relation_type")
        if rel_type not in self.relation_types:
            return False
        spec = self.relation_types[rel_type]
        return src_type in spec.source_types and tgt_type in spec.target_types

    # ------------------------------------------------------------------
    # Compatibilité
    # ------------------------------------------------------------------

    def is_compatible(self, other: "GraphSchema") -> bool:
        """Vérifie que self est un sous-ensemble de *other*.

        Un schéma A est compatible avec B si tous les types de nœuds et
        de relations de A sont présents dans B.

        Args:
            other: Autre instance de GraphSchema.

        Returns:
            ``True`` si self ⊆ other, ``False`` sinon.
        """
        for node_name in self.node_types:
            if node_name not in other.node_types:
                return False
        for rel_name in self.relation_types:
            if rel_name not in other.relation_types:
                return False
        return True

    # ------------------------------------------------------------------
    # Assertions (liste blanche)
    # ------------------------------------------------------------------

    def assert_node_type(self, name: str) -> str:
        """Retourne *name* s'il est un type de nœud valide.

        Args:
            name: Nom du type de nœud à vérifier.

        Returns:
            Le nom tel quel si valide.

        Raises:
            SchemaViolationError: Si le type n'existe pas dans le schéma.
        """
        if name not in self.node_types:
            raise SchemaViolationError(
                f"Type de nœud inconnu : {name!r}",
                component="graph_schema",
                context={"invalid_node_type": name, "valid_types": list(self.node_types.keys())},
            )
        return name

    def assert_relation_type(self, name: str) -> str:
        """Retourne *name* s'il est un type de relation valide.

        Args:
            name: Nom du type de relation à vérifier.

        Returns:
            Le nom tel quel si valide.

        Raises:
            SchemaViolationError: Si le type n'existe pas dans le schéma.
        """
        if name not in self.relation_types:
            raise SchemaViolationError(
                f"Type de relation inconnu : {name!r}",
                component="graph_schema",
                context={"invalid_relation_type": name, "valid_types": list(self.relation_types.keys())},
            )
        return name
