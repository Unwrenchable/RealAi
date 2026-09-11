"""
RealAI Self-Improvement Engine
================================
Training data generation, performance evaluation, fine-tuning orchestration,
and version management.

SECURITY NOTE: All self-improvement operations require the REALAI_SELF_IMPROVE
environment variable to be set to "1", "true", or "yes".

Usage::

    import os
    os.environ["REALAI_SELF_IMPROVE"] = "true"
    from realai.self_improvement import PerformanceEvaluator

    evaluator = PerformanceEvaluator()
    scores = evaluator.evaluate()
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _self_improve_enabled() -> bool:
    """Check if self-improvement is enabled via environment variable.

    Returns:
        True if REALAI_SELF_IMPROVE is set to '1', 'true', or 'yes'.
    """
    return os.environ.get("REALAI_SELF_IMPROVE", "").lower() in ("1", "true", "yes")


def _require_enabled() -> None:
    """Raise PermissionError if self-improvement is not enabled."""
    if not _self_improve_enabled():
        raise PermissionError("Set REALAI_SELF_IMPROVE=true to enable")


@dataclass
class TrainingExample:
    """A single training example for fine-tuning.

    Attributes:
        id: Unique identifier.
        messages: List of message dicts (OpenAI format).
        response: Response dict.
        quality_score: Quality score (0.0-1.0).
        label: Quality label (good/bad/neutral).
    """

    id: str
    messages: List[Dict]
    response: Dict
    quality_score: float
    label: str


class TrainingDataGenerator:
    """Generates training data from memory engine history.

    Requires REALAI_SELF_IMPROVE=true.
    """

    def generate_from_history(
        self,
        memory_engine: Any,
        min_score: float = 0.7,
    ) -> List[TrainingExample]:
        """Generate training examples from episodic memory.

        Args:
            memory_engine: MemoryEngine instance to read from.
            min_score: Minimum quality score threshold for 'good' label.

        Returns:
            List of TrainingExample objects.

        Raises:
            PermissionError: If REALAI_SELF_IMPROVE is not set.
        """
        _require_enabled()
        examples = []

        try:
            items = memory_engine.episodic.all()
        except Exception:
            items = []

        for item in items:
            label = "good" if item.score >= min_score else "bad"
            if 0.4 <= item.score < min_score:
                label = "neutral"

            example = TrainingExample(
                id=str(uuid.uuid4()),
                messages=[{"role": "user", "content": item.content}],
                response={"role": "assistant", "content": item.content},
                quality_score=item.score,
                label=label,
            )
            examples.append(example)

        return examples

    def export_jsonl(
        self,
        examples: List[TrainingExample],
        path: str,
    ) -> str:
        """Export training examples to OpenAI fine-tuning JSONL format.

        Args:
            examples: List of TrainingExample objects.
            path: Output file path.

        Returns:
            The output file path.

        Raises:
            PermissionError: If REALAI_SELF_IMPROVE is not set.
        """
        _require_enabled()
        with open(path, "w") as f:
            for ex in examples:
                record = {
                    "messages": ex.messages + [ex.response],
                }
                f.write(json.dumps(record) + "\n")
        return path


class PerformanceEvaluator:
    """Evaluates model performance using benchmarks.

    Requires REALAI_SELF_IMPROVE=true.
    """

    def evaluate(self, model: Any = None) -> Dict[str, float]:
        """Run benchmarks and return per-metric scores.

        Args:
            model: Optional RealAI model instance.

        Returns:
            Dict mapping benchmark name to score float.

        Raises:
            PermissionError: If REALAI_SELF_IMPROVE is not set.
        """
        _require_enabled()
        try:
            from benchmarks.runner import run_all_benchmarks
            report = run_all_benchmarks(model=model)
            scores = {b["name"]: b["score"] for b in report.get("benchmarks", [])}
            scores["overall"] = report.get("overall_score", 0.0)
            return scores
        except Exception as e:
            return {"overall": 0.0, "error_note": str(e)}

    def delta(
        self,
        current: Dict[str, float],
        baseline: Dict[str, float],
    ) -> Dict[str, float]:
        """Compute per-metric delta between current and baseline scores.

        Args:
            current: Current score dict.
            baseline: Baseline score dict.

        Returns:
            Dict mapping metric name to (current - baseline) delta.
        """
        all_keys = set(current.keys()) | set(baseline.keys())
        return {
            k: current.get(k, 0.0) - baseline.get(k, 0.0)
            for k in all_keys
        }


class FineTuneOrchestrator:
    """Orchestrates fine-tuning jobs on OpenAI or similar APIs.

    Requires REALAI_SELF_IMPROVE=true.
    """

    def submit_openai_job(
        self,
        training_file_path: str,
        api_key: str,
        model: str = "gpt-3.5-turbo",
    ) -> Dict[str, Any]:
        """Submit a fine-tuning job to OpenAI.

        Args:
            training_file_path: Path to the JSONL training file.
            api_key: OpenAI API key.
            model: Base model to fine-tune.

        Returns:
            Dict with job_id and status.

        Raises:
            PermissionError: If REALAI_SELF_IMPROVE is not set.
        """
        _require_enabled()
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            with open(training_file_path, "rb") as f:
                upload = client.files.create(file=f, purpose="fine-tune")
            job = client.fine_tuning.jobs.create(
                training_file=upload.id,
                model=model,
            )
            return {"job_id": job.id, "status": job.status}
        except ImportError:
            pass
        except Exception as e:
            return {"job_id": None, "status": "error", "error": str(e)}

        # Fallback: mock job
        return {
            "job_id": "mock-job-{0}".format(str(uuid.uuid4())[:8]),
            "status": "pending",
            "note": "Install openai package for real fine-tuning",
        }

    def get_job_status(self, job_id: str, api_key: str) -> Dict[str, Any]:
        """Get the status of a fine-tuning job.

        Args:
            job_id: Fine-tuning job ID.
            api_key: OpenAI API key.

        Returns:
            Dict with job_id and status.

        Raises:
            PermissionError: If REALAI_SELF_IMPROVE is not set.
        """
        _require_enabled()
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            job = client.fine_tuning.jobs.retrieve(job_id)
            return {"job_id": job_id, "status": job.status}
        except ImportError:
            pass
        except Exception as e:
            return {"job_id": job_id, "status": "error", "error": str(e)}

        return {
            "job_id": job_id,
            "status": "unknown",
            "note": "Install openai package for real job status",
        }


class VersionManager:
    """Manages version tagging and changelog generation.

    Requires REALAI_SELF_IMPROVE=true for mutating operations.
    """

    def current_version(self, repo_path: str = ".") -> str:
        """Read the current version from setup.py or __version__.

        Args:
            repo_path: Path to the repository root.

        Returns:
            Version string, or "unknown" if not found.
        """
        # Try setup.py
        setup_path = os.path.join(repo_path, "setup.py")
        if os.path.exists(setup_path):
            try:
                with open(setup_path, "r") as f:
                    content = f.read()
                match = re.search(r'version=["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
            except Exception:
                pass

        # Try __init__.py
        init_path = os.path.join(repo_path, "__init__.py")
        if os.path.exists(init_path):
            try:
                with open(init_path, "r") as f:
                    content = f.read()
                match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
            except Exception:
                pass

        return "unknown"

    def tag_version(self, version: str, repo_path: str = ".") -> Dict[str, Any]:
        """Create a git tag for the given version.

        Args:
            version: Version string to tag.
            repo_path: Repository path.

        Returns:
            Dict with tagged bool and version.

        Raises:
            PermissionError: If REALAI_SELF_IMPROVE is not set.
        """
        _require_enabled()
        try:
            result = subprocess.run(
                ["git", "tag", "v{0}".format(version)],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return {"tagged": True, "version": version}
            return {
                "tagged": False,
                "version": version,
                "error": result.stderr.strip(),
            }
        except Exception as e:
            return {"tagged": False, "version": version, "error": str(e)}

    def generate_changelog(
        self,
        memory_engine: Any,
        from_version: str,
        to_version: str,
    ) -> str:
        """Generate a markdown changelog from release-tagged memory items.

        Args:
            memory_engine: MemoryEngine instance.
            from_version: Starting version string.
            to_version: Ending version string.

        Returns:
            Markdown changelog string.

        Raises:
            PermissionError: If REALAI_SELF_IMPROVE is not set.
        """
        _require_enabled()
        try:
            items = memory_engine.episodic.all()
            release_items = [
                item for item in items
                if "release" in item.tags
            ]
        except Exception:
            release_items = []

        lines = [
            "# Changelog",
            "",
            "## [{to}] vs [{from_}]".format(to=to_version, from_=from_version),
            "",
        ]

        if release_items:
            for item in release_items:
                lines.append("- {0}".format(item.content))
        else:
            lines.append("- No release notes found in memory.")

        return "\n".join(lines)
