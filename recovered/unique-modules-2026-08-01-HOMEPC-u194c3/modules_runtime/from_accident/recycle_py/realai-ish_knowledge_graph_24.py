"""
RealAI Knowledge Graph
=======================
In-memory knowledge graph with entity management, relationship queries,
transitive inference, and natural language synthesis.

Usage::

    from realai.knowledge_graph import KNOWLEDGE_GRAPH, Entity, Relationship

    KNOWLEDGE_GRAPH.add_entity(Entity("e1", "Python", "language", {}))
    KNOWLEDGE_GRAPH.add_entity(Entity("e2", "Programming", "concept", {}))
    KNOWLEDGE_GRAPH.add_relationship(Relationship("r1", "e1", "is_a", "e2"))
"""

from __future__ import annotations

import uuid as _uuid_module
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Entity:
    """A node in the knowledge graph.

    Attributes:
        id: Unique identifier.
        name: Human-readable entity name.
        entity_type: Category of entity (e.g. "person", "concept").
        attributes: Dict of additional attributes.
        embedding: Optional float vector embedding.
    """

    id: str
    name: str
    entity_type: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class Relationship:
    """A directed edge in the knowledge graph.

    Attributes:
        id: Unique identifier.
        subject_id: Source entity ID.
        predicate: Relationship type (e.g. "is_a", "part_of").
        object_id: Target entity ID.
        confidence: Confidence score (0.0-1.0).
        source: Optional provenance string.
    """

    id: str
    subject_id: str
    predicate: str
    object_id: str
    confidence: float = 1.0
    source: str = ""


class KnowledgeGraph:
    """In-memory knowledge graph backed by plain dicts.

    Supports entity and relationship CRUD, multi-predicate queries,
    and transitive relationship inference.
    """

    def __init__(self) -> None:
        """Initialize an empty knowledge graph."""
        self._entities: Dict[str, Entity] = {}
        self._relationships: Dict[str, Relationship] = {}

    def add_entity(self, entity: Entity) -> None:
        """Add or update an entity.

        Args:
            entity: Entity to add.
        """
        self._entities[entity.id] = entity

    def add_relationship(self, rel: Relationship) -> None:
        """Add or update a relationship.

        Args:
            rel: Relationship to add.
        """
        self._relationships[rel.id] = rel

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve an entity by ID.

        Args:
            entity_id: Entity ID to look up.

        Returns:
            Entity or None.
        """
        return self._entities.get(entity_id)

    def query(
        self,
        subject_id: Optional[str] = None,
        predicate: Optional[str] = None,
        object_id: Optional[str] = None,
    ) -> List[Relationship]:
        """Query relationships by optional subject, predicate, and/or object.

        Args:
            subject_id: Filter by subject entity ID.
            predicate: Filter by predicate string.
            object_id: Filter by object entity ID.

        Returns:
            List of matching Relationship objects.
        """
        results = []
        for rel in self._relationships.values():
            if subject_id is not None and rel.subject_id != subject_id:
                continue
            if predicate is not None and rel.predicate != predicate:
                continue
            if object_id is not None and rel.object_id != object_id:
                continue
            results.append(rel)
        return results

    def infer_relationships(self, max_hops: int = 2) -> List[Relationship]:
        """Infer transitive relationships up to max_hops.

        For each predicate, if A->B and B->C, infers A->C with lower confidence.

        Args:
            max_hops: Maximum chain length for inference.

        Returns:
            List of newly inferred Relationship objects.
        """
        inferred = []
        existing_keys = set(
            (r.subject_id, r.predicate, r.object_id)
            for r in self._relationships.values()
        )

        for _ in range(max_hops - 1):
            new_rels = []
            rels = list(self._relationships.values()) + inferred
            for rel_a in rels:
                for rel_b in rels:
                    if (
                        rel_a.predicate == rel_b.predicate
                        and rel_a.object_id == rel_b.subject_id
                    ):
                        key = (rel_a.subject_id, rel_a.predicate, rel_b.object_id)
                        if key not in existing_keys:
                            existing_keys.add(key)
                            new_rel = Relationship(
                                id="inferred-" + str(_uuid_module.uuid4())[:8],
                                subject_id=rel_a.subject_id,
                                predicate=rel_a.predicate,
                                object_id=rel_b.object_id,
                                confidence=rel_a.confidence * rel_b.confidence * 0.8,
                                source="inferred",
                            )
                            new_rels.append(new_rel)
            inferred.extend(new_rels)

        return inferred

    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity and all its relationships.

        Args:
            entity_id: Entity ID to remove.

        Returns:
            True if the entity was found and removed.
        """
        if entity_id not in self._entities:
            return False
        del self._entities[entity_id]
        # Remove related relationships
        to_remove = [
            rid
            for rid, r in self._relationships.items()
            if r.subject_id == entity_id or r.object_id == entity_id
        ]
        for rid in to_remove:
            del self._relationships[rid]
        return True

    def stats(self) -> Dict[str, int]:
        """Return graph statistics.

        Returns:
            Dict with "entities" and "relationships" counts.
        """
        return {
            "entities": len(self._entities),
            "relationships": len(self._relationships),
        }


class EntityLinker:
    """Links text to entities in a knowledge graph via string matching.

    Performs case-insensitive substring matching.
    """

    def link(self, text: str, graph: KnowledgeGraph) -> Optional[Entity]:
        """Find the best matching entity for a text snippet.

        Args:
            text: Input text to match against entity names.
            graph: KnowledgeGraph to search.

        Returns:
            Best matching Entity, or None if no match found.
        """
        text_lower = text.lower()
        matches = []
        for entity in graph._entities.values():
            if entity.name.lower() in text_lower:
                matches.append(entity)
        if not matches:
            return None
        # Return entity with the longest name match (more specific)
        return max(matches, key=lambda e: len(e.name))


class SynthesisEngine:
    """Synthesizes natural language answers from knowledge graph traversal.

    Finds entities, traverses relationships, and returns a narrative summary.
    """

    def answer(
        self,
        query: str,
        graph: KnowledgeGraph,
        max_hops: int = 2,
    ) -> Dict[str, Any]:
        """Answer a natural language query using the knowledge graph.

        Args:
            query: Natural language query string.
            graph: KnowledgeGraph to query.
            max_hops: Maximum relationship traversal depth.

        Returns:
            Dict with entities_found, relationships, and synthesis narrative.
        """
        # Find all entities mentioned in the query
        found_entities = []
        for entity in graph._entities.values():
            if entity.name.lower() in query.lower():
                found_entities.append(entity)

        # Collect relationships involving found entities
        found_rels = []
        seen_rels = set()

        for entity in found_entities:
            rels = graph.query(subject_id=entity.id)
            rels += graph.query(object_id=entity.id)
            for rel in rels:
                if rel.id not in seen_rels:
                    seen_rels.add(rel.id)
                    found_rels.append(rel)

        # Simple narrative synthesis
        if not found_entities:
            synthesis = "No matching entities found in the knowledge graph."
        elif not found_rels:
            names = ", ".join(e.name for e in found_entities)
            synthesis = "Found entities: {0}. No relationships found.".format(names)
        else:
            parts = []
            for rel in found_rels[:5]:  # Limit narrative length
                subj = graph.get_entity(rel.subject_id)
                obj = graph.get_entity(rel.object_id)
                subj_name = subj.name if subj else rel.subject_id
                obj_name = obj.name if obj else rel.object_id
                parts.append("{0} {1} {2}".format(subj_name, rel.predicate, obj_name))
            synthesis = ". ".join(parts) + "."

        return {
            "entities_found": [
                {"id": e.id, "name": e.name, "type": e.entity_type}
                for e in found_entities
            ],
            "relationships": [
                {
                    "subject_id": r.subject_id,
                    "predicate": r.predicate,
                    "object_id": r.object_id,
                    "confidence": r.confidence,
                }
                for r in found_rels
            ],
            "synthesis": synthesis,
        }


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

KNOWLEDGE_GRAPH = KnowledgeGraph()
