import os, json

ROOT = "C:\\realai"
PLAN_DIR = os.path.join(ROOT, "phase4_tools", "plan_phase4_preview")
PLAN_JSON = os.path.join(PLAN_DIR, "phase4_preview.json")
SUMMARY_TXT = os.path.join(PLAN_DIR, "phase4_preview_summary.txt")
OUT = os.path.join(ROOT, "scan_results", "dds10_merge_plan_validator.json")

def safe_read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except:
        return ""

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

def collect_all_files(root):
    found = set()
    for dp, _, files in os.walk(root):
        for f in files:
            rel = os.path.relpath(os.path.join(dp, f), root)
            found.add(rel.replace("\\", "/"))
    return found

def run_scan():
    results = []

    if not os.path.exists(PLAN_JSON):
        results.append({
            "type": "missing_plan_json",
            "path": PLAN_JSON
        })
        return results

    plan = load_json(PLAN_JSON)
    if plan is None:
        results.append({
            "type": "invalid_plan_json",
            "path": PLAN_JSON
        })
        return results

    all_files = collect_all_files(ROOT)

    actions = plan.get("actions") or plan.get("plan") or []
    if not isinstance(actions, list):
        results.append({
            "type": "invalid_actions_structure",
            "detail": "Expected list of actions"
        })
        return results

    for idx, action in enumerate(actions):
        if not isinstance(action, dict):
            results.append({
                "type": "invalid_action_entry",
                "index": idx
            })
            continue

        kind = action.get("type") or action.get("action") or "unknown"
        src = action.get("source") or action.get("src") or ""
        dst = action.get("target") or action.get("dst") or ""

        src = str(src).replace("\\", "/")
        dst = str(dst).replace("\\", "/")

        # Check source existence for merge/rewrite/archive
        if kind in ("merge", "rewrite", "archive"):
            if src and src not in all_files:
                results.append({
                    "type": "missing_source",
                    "action_type": kind,
                    "index": idx,
                    "source": src
                })

        # Check target existence for merge/rewrite
        if kind in ("merge", "rewrite"):
            # Target may not exist yet (to be created), but if it exists, note it
            if dst and dst in all_files:
                results.append({
                    "type": "target_already_exists",
                    "action_type": kind,
                    "index": idx,
                    "target": dst
                })

        # Basic sanity: require at least src or dst
        if not src and not dst:
            results.append({
                "type": "empty_action_paths",
                "action_type": kind,
                "index": idx
            })

    # Check summary presence
    if not os.path.exists(SUMMARY_TXT):
        results.append({
            "type": "missing_summary_txt",
            "path": SUMMARY_TXT
        })

    return results

if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    results = run_scan()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[DDS-10] Merge-Plan Validation Complete → {OUT}")
