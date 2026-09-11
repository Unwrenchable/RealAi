import os
os.environ["REALAI_SELF_IMPROVE"] = "true"

from realai.plugins.self_improvement import (
    PerformanceEvaluator,
    TrainingExample,
    TrainingDataGenerator,
)
from realai.plugins.local_models import get_llm_engine

def main():
    ev = PerformanceEvaluator()
    scores = ev.evaluate()
    print("=== scores ===")
    for k, v in scores.items():
        print(f"  {k}: {v}")

    overall = float(scores.get("overall") or 0)
    agent = float(scores.get("agent") or 0)
    coverage = float(scores.get("ability_coverage_pct") or 0)

    eng = get_llm_engine()
    if not eng.is_loaded():
        print("loading qwen-coder-7b...", eng.load_model("qwen-coder-7b"))
    print("model:", eng.get_current_model(), "loaded:", eng.is_loaded())

    prompt = (
        f"RealAI metrics: overall={overall:.2f}, agent={agent:.2f}, "
        f"coverage={coverage:.2f}. In two short sentences, what is the "
        f"highest-leverage next self-improvement step?"
    )
    idea = eng.generate(prompt, max_tokens=100)
    print("=== local idea ===")
    print(idea if idea else "(no text)")

    ex = TrainingExample(
        id="si-smoke-001",
        messages=[{"role": "user", "content": prompt}],
        response={"role": "assistant", "content": idea if idea else "(no text)"},
        quality_score=0.85 if idea else 0.2,
        label="good" if idea else "bad",
    )
    print("=== TrainingExample ===")
    print(ex.id, ex.label, "score=", ex.quality_score)

    gen = TrainingDataGenerator()
    out = gen.export_jsonl([ex], "recovered/si_smoke_example.jsonl")
    print("exported:", out)
    print("Short self-improve loop OK.")

if __name__ == "__main__":
    main()