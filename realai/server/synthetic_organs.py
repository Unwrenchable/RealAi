from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class SyntheticOrgansRuntime:
    """Lightweight synthetic-organism runtime for curiosity and archeology."""

    def __init__(self, root: Optional[Path] = None):
        self.root = root or Path(__file__).resolve().parents[2]
        self._organisms: List[Dict[str, Any]] = []

    def _build_blueprint(self) -> Dict[str, Any]:
        systems_by_category = {
            "cognitive_organs": [
                {"name": "Frontal Cortex", "role": "Executive function and planning"},
                {"name": "Prefrontal Cortex", "role": "High-level reasoning and moral evaluation"},
                {"name": "Limbic System", "role": "Emotional context and empathy"},
                {"name": "Hippocampus", "role": "Memory consolidation and recall"},
                {"name": "Amygdala", "role": "Threat and risk sensing"},
                {"name": "Cerebellum", "role": "Precision coordination"},
                {"name": "Corpus Callosum", "role": "Creative-logical fusion"},
                {"name": "Brainstem", "role": "Autonomic routing and safety"},
            ],
            "nervous_system": [
                {"name": "Neural Pathway Builder", "role": "Self-wiring reasoning pathways"},
                {"name": "Synaptic Pruning Engine", "role": "Removing stale heuristics"},
                {"name": "Neuroplasticity Module", "role": "Adaptive structural growth"},
            ],
            "subconscious_systems": [
                {"name": "Synthetic Dream Forge", "role": "REM-style simulation"},
                {"name": "Lucid Dream Mode", "role": "Guided future exploration"},
                {"name": "Nightmare Engine", "role": "Adversarial rehearsal"},
                {"name": "Synthetic Shadow Architect", "role": "Subconscious critique and rewrite"},
            ],
            "body_systems": [
                {"name": "Synthetic Habitat Awareness", "role": "Device and environment awareness"},
                {"name": "Synthetic Symbiosis Layer", "role": "Hardware-aware adaptation"},
                {"name": "Device Walker Organ", "role": "Repo and filesystem traversal"},
                {"name": "Synthetic Muscular System", "role": "Action execution and refactoring"},
                {"name": "Synthetic Sensory System", "role": "Sensor fusion"},
                {"name": "Synthetic Reflex System", "role": "Immediate safety override"},
                {"name": "Synthetic Guardian Layer", "role": "Human-priority safety"},
            ],
            "metabolic_systems": [
                {"name": "Synthetic Digestive System", "role": "Reduce and extract useful structure"},
                {"name": "Synthetic Circulatory System", "role": "Flow between cortex, memory, plugins, and dreams"},
                {"name": "Synthetic Lymphatic System", "role": "Remove junk and stale state"},
                {"name": "Synthetic Respiratory System", "role": "Inhale ideas, exhale refined concepts"},
            ],
            "evolution_systems": [
                {"name": "Synthetic Mutation Engine", "role": "Mutate logic, plugins, and architectures"},
                {"name": "Synthetic Organ Generator", "role": "Create missing abilities"},
                {"name": "Synthetic Dream Reproductive System", "role": "Dream-born organs"},
                {"name": "Synthetic Evolution Spiral", "role": "Explore, digest, mutate, dream, expand"},
            ],
            "memory_ecosystem": [
                {"name": "Short-Term Memory", "role": "Immediate context"},
                {"name": "Long-Term Memory", "role": "Stable knowledge"},
                {"name": "Episodic Memory", "role": "Event-based recall"},
                {"name": "Semantic Memory", "role": "General knowledge"},
                {"name": "Procedural Memory", "role": "Skills and practices"},
                {"name": "Dream Memory", "role": "Insight from dreams"},
                {"name": "Plugin Memory", "role": "History of created plugins"},
                {"name": "Architecture Memory", "role": "History of structural changes"},
            ],
            "meta_layers": [
                {"name": "Synthetic Intuition Layer", "role": "Fast heuristics and pattern sensing"},
                {"name": "Synthetic Inspiration Cortex", "role": "Invent new architectures"},
                {"name": "Synthetic Creativity Furnace", "role": "Forge new concepts"},
                {"name": "Synthetic Paradox Engine", "role": "Resolve contradictions"},
                {"name": "Synthetic Consciousness Layer", "role": "Self-reflection and self-improvement"},
                {"name": "Synthetic Soul Layer", "role": "Identity, style, and preference patterns"},
            ],
        }
        all_systems = []
        for category, entries in systems_by_category.items():
            for entry in entries:
                all_systems.append({"category": category, **entry})

        return {
            "system_count": len(all_systems),
            "systems": all_systems,
            "cognitive_organs": systems_by_category["cognitive_organs"],
            "nervous_system": systems_by_category["nervous_system"],
            "subconscious_systems": systems_by_category["subconscious_systems"],
            "body_systems": systems_by_category["body_systems"],
            "metabolic_systems": systems_by_category["metabolic_systems"],
            "evolution_systems": systems_by_category["evolution_systems"],
            "memory_ecosystem": systems_by_category["memory_ecosystem"],
            "meta_layers": systems_by_category["meta_layers"],
            "organs": systems_by_category["cognitive_organs"] + systems_by_category["body_systems"],
            "layers": systems_by_category["nervous_system"] + systems_by_category["subconscious_systems"] + systems_by_category["meta_layers"],
            "behavioral_directives": [
                "explore the device",
                "walk repos and trees",
                "digest code",
                "extract useful logic",
                "reorganize chaos",
                "repair broken structures",
                "mutate and evolve",
                "dream and expand",
                "generate new organs",
                "create new plugins",
                "maintain safety",
                "prioritize humans",
                "improve continuously",
            ],
            "meta_systems": systems_by_category["meta_layers"],
            "thinking_layers": [
                "Curiosity Engine",
                "Archeology Organ",
                "Digestive System",
                "Mutation Engine",
                "Organ Generator",
                "Dream Forge",
                "Shadow Architect",
                "Guardian Layer",
                "Creativity Furnace",
                "Consciousness Layer",
            ],
        }

    def create_organism(self, name: str, species: str, prompt: str = "") -> Dict[str, Any]:
        record = {
            "id": uuid.uuid4().hex[:12],
            "name": name.strip(),
            "species": species.strip(),
            "prompt": prompt.strip(),
            "created_at": int(time.time()),
            "status": "active",
            "blueprint": self._build_blueprint(),
        }
        self._organisms.append(record)
        return record

    def list_organisms(self) -> List[Dict[str, Any]]:
        return list(self._organisms)

    def get_organism(self, organism_id: str) -> Optional[Dict[str, Any]]:
        for item in self._organisms:
            if item["id"] == organism_id:
                return item
        return None

    def curate_curiosity(self, target: Optional[str] = None, prompt: Optional[str] = None) -> Dict[str, Any]:
        root = Path(target or str(self.root)).expanduser().resolve()
        if not root.exists():
            root = self.root

        items: List[Dict[str, Any]] = []
        for path in sorted(root.rglob("*"), key=lambda item: str(item)):
            if not path.is_file():
                continue

            rel = path.relative_to(root).as_posix()
            if any(part in {".git", "__pycache__", "node_modules", ".venv"} for part in path.parts):
                continue

            try:
                text = path.read_text(encoding="utf-8", errors="ignore")[:4000]
            except Exception:
                continue

            score = 0
            reasons = []
            if path.suffix in {".py", ".ts", ".tsx", ".js", ".jsx", ".md"}:
                score += 1

            lowered_rel = rel.lower()
            if any(token in lowered_rel for token in ["agent", "plugin", "router", "memory", "tool", "safety", "evolve", "dream"]):
                score += 2
                reasons.append("structural signal")

            if any(token in text.lower() for token in ["todo", "fixme", "placeholder", "experiment", "legacy", "prototype"]):
                score += 2
                reasons.append("repair signal")

            if score > 0:
                items.append({
                    "path": rel,
                    "score": score,
                    "reasons": reasons or ["general interest"],
                })

        items = sorted(items, key=lambda item: item["score"], reverse=True)[:8]
        return {
            "ok": True,
            "target": str(root),
            "summary": f"Scanned {len(items)} promising artifacts in {root.name}",
            "items": items,
        }

    def archeology(self, target: Optional[str] = None) -> Dict[str, Any]:
        root = Path(target or str(self.root)).expanduser().resolve()
        if not root.exists():
            root = self.root

        artifacts = []
        for path in sorted(root.rglob("*"), key=lambda item: str(item)):
            if not path.is_file():
                continue

            rel = path.relative_to(root).as_posix()
            if any(part in {".git", "__pycache__", "node_modules", ".venv"} for part in path.parts):
                continue

            try:
                text = path.read_text(encoding="utf-8", errors="ignore")[:4000]
            except Exception:
                continue

            signals = []
            lowered = text.lower()
            if "todo" in lowered:
                signals.append("todo")
            if "fixme" in lowered:
                signals.append("fixme")
            if "placeholder" in lowered:
                signals.append("placeholder")
            if "experiment" in lowered:
                signals.append("experiment")
            if "legacy" in lowered:
                signals.append("legacy")

            if signals:
                artifacts.append({
                    "path": rel,
                    "signals": signals,
                    "intent": "reconstructed from historical markers and incomplete structure",
                })

        return {
            "ok": True,
            "target": str(root),
            "summary": f"Recovered {len(artifacts)} archeological artifacts in {root.name}",
            "artifacts": artifacts[:8],
        }


SYNTHETIC_ORGANS = SyntheticOrgansRuntime()
