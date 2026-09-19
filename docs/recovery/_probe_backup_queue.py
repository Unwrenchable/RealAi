import json

d = json.load(open(r"scan_results/backup_unique_promote_queue.json", encoding="utf-8"))
print("missing", d["missing_count"])
for m in d["missing"]:
    print(" M", m["rel"], m["size"])
print("richer", d["richer_count"])
rich = list(d["richer"])
rich.sort(key=lambda x: x["size_src"] - x["size_live"], reverse=True)
for r in rich[:40]:
    delta = r["size_src"] - r["size_live"]
    print(
        f" R +{delta:6d}  {r['rel']}  backup={r['size_src']} live={r['size_live']} -> {r['dest']}"
    )
