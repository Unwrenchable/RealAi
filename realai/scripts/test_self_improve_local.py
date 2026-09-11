"""
Smoke test: self_improvement + local_models (fixed)
"""
import os
os.environ["REALAI_SELF_IMPROVE"] = "true"

from realai.plugins.self_improvement import (
    TrainingExample,
    PerformanceEvaluator,
    TrainingDataGenerator,
    FineTuneOrchestrator,
)
from realai.plugins.local_models import (
    LocalModelManager,
    LocalLLMEngine,
    LocalModelType,
)

def main():
    print("=== local_models ===")
    mgr = LocalModelManager()
    print("models_dir:", mgr.models_dir)
    models = mgr.list_models()
    print(f"available models ({len(models)}):")
    for m in models:
        print(f"  - {m.get('name')}  ({m.get('type')})  path={m.get('path')}")

    # get_preference requires a key
    for key in ["default_llm", "llm", "preferred", "default"]:
        try:
            pref = mgr.get_preference(key)
            print(f"preference[{key!r}]:", pref)
        except Exception as e:
            print(f"preference[{key!r}]: {type(e).__name__}")

    engine = LocalLLMEngine(mgr)
    print("engine loaded:", engine.is_loaded())
    print("current model:", engine.get_current_model())

    print("\n=== self_improvement ===")
    evaluator = PerformanceEvaluator()
    try:
        scores = evaluator.evaluate()
        print("evaluate():", scores)
    except Exception as e:
        print("evaluate() raised:", type(e).__name__, "-", e)

    gen = TrainingDataGenerator()
    print("TrainingDataGenerator ready")

    ex = TrainingExample(
        id="ex1",
        messages=[{"role": "user", "content": "hello"}],
        response={"role": "assistant", "content": "hi"},
        quality_score=0.9,
        label="good",
    )
    print("TrainingExample:", ex.id, ex.label, ex.quality_score)

    orch = FineTuneOrchestrator()
    print("FineTuneOrchestrator ready")

    print("\nSmoke test complete.")

if __name__ == "__main__":
    main()
