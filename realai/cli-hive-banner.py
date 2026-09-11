"""Hive CLI identity banner and status assembly."""
from __future__ import annotations

from typing import Any, Dict

from realai.cli.hive.format import kv


BANNER_MARK = "════ RealAI Hive CLI ════"


def render_banner(status: Dict[str, Any]) -> str:
    orch = status.get("orchestrator") or {}
    vulkan = status.get("vulkan") or {}
    hive = status.get("hive") or {}
    caps = status.get("capabilities") or {}
    workspace = status.get("workspace") or ""
    gpu = status.get("gpu") or {}

    orch_ok = bool(orch.get("ok"))
    vul_ok = bool(vulkan.get("ok"))
    overall = status.get("status") or (
        "ok" if orch_ok and vul_ok else "degraded" if orch_ok else "down"
    )

    hive_mode = hive.get("hive_mode") if "hive_mode" in hive else hive.get("mode")
    present = hive.get("present") or []
    required = hive.get("required") or []
    if hive_mode:
        hive_txt = f"ON   archetypes {len(present)}/{len(required) or 7}"
    else:
        missing = hive.get("missing") or []
        hive_txt = f"OFF  missing={','.join(missing) or 'n/a'}"

    live = ((caps.get("by_status") or {}).get("LIVE"))
    agents_n = status.get("agent_count")
    tools_n = status.get("tool_count")
    weighted = caps.get("weighted_pct")

    orch_port = orch.get("port") or 8001
    vul_port = vulkan.get("port") or 8080
    model = (gpu.get("paths") or {}).get("default_resume_gguf") or ""

    lines = [
        BANNER_MARK,
        f"orchestrator  :{orch_port}  [{'UP' if orch_ok else 'DOWN'}]    "
        f"vulkan  :{vul_port}  [{'UP' if vul_ok else 'DOWN'}]",
        kv("workspace", workspace),
        kv("hive", hive_txt),
        kv(
            "surface",
            f"{overall}   "
            f"abilities {live if live is not None else '?'} LIVE"
            + (f" ({weighted}%)" if weighted is not None else "")
            + f"  · agents {agents_n if agents_n is not None else '?'}"
            + f"  · tools {tools_n if tools_n is not None else '?'}",
        ),
    ]
    if model:
        lines.append(kv("gguf", model))
    if status.get("hint"):
        lines.append(kv("hint", status["hint"]))
    lines.append("commands     status · route · run · multi · agents · ability · gpu · world · heal · quarantine")
    return "\n".join(lines)


def collect_status(ctx) -> Dict[str, Any]:
    """Build status dict from HTTP + local bridge/vulkan (best-effort)."""
    from pathlib import Path

    out: Dict[str, Any] = {
        "workspace": str(getattr(ctx, "workspace", "") or ""),
        "api_url": ctx.api_url,
        "orchestrator": {"ok": False},
        "vulkan": {"ok": False},
        "hive": {},
        "capabilities": {},
        "gpu": {},
        "status": "down",
    }

    try:
        health = ctx.client.health()
        out["orchestrator"] = {
            "ok": True,
            "status": health.get("status"),
            "port": health.get("port") or 8001,
            "service": health.get("service"),
            "body": health,
        }
        vul = health.get("vulkan") or {}
        out["vulkan"] = {
            "ok": bool(vul.get("ok")),
            "port": 8080,
            "base": vul.get("base"),
            "body": vul.get("body"),
        }
        out["status"] = health.get("status") or ("ok" if vul.get("ok") else "degraded")
    except Exception as e:
        out["orchestrator"] = {"ok": False, "error": str(e), "port": 8001}
        out["hint"] = "realai stack up"

    if out["orchestrator"].get("ok"):
        try:
            caps = ctx.client.capabilities()
            out["capabilities"] = {
                "ability_count": caps.get("ability_count"),
                "by_status": caps.get("by_status") or (caps.get("coverage") or {}).get("by_status"),
                "weighted_pct": caps.get("weighted_pct"),
            }
        except Exception:
            pass
        try:
            tools = ctx.client.tools()
            tlist = tools.get("tools") if isinstance(tools, dict) else None
            out["tool_count"] = len(tlist) if isinstance(tlist, list) else None
        except Exception:
            pass
        try:
            agents = ctx.client.tool_execute("list_agents", {"limit": 200})
            res = agents.get("result") if isinstance(agents, dict) else {}
            if isinstance(res, dict):
                out["agent_count"] = res.get("count")
                if res.get("hive"):
                    out["hive"] = res["hive"]
        except Exception:
            pass

    try:
        from realai.v3_runtime_bridge import hive_agents_status

        hs = hive_agents_status()
        if not out.get("hive"):
            out["hive"] = {
                "hive_mode": hs.get("hive_mode"),
                "mode": hs.get("hive_mode"),
                "present": hs.get("present"),
                "missing": hs.get("missing"),
                "required": hs.get("required"),
            }
        else:
            out["hive"].setdefault("required", hs.get("required"))
            out["hive"].setdefault("present", hs.get("present"))
            out["hive"].setdefault("missing", hs.get("missing"))
            out["hive"].setdefault("hive_mode", hs.get("hive_mode"))
            out["hive"].setdefault("mode", hs.get("hive_mode"))
    except Exception:
        pass

    try:
        from realai.cli.hive.gpu_inspector import inspect as gpu_inspect

        ws = Path(out["workspace"] or ".")
        gpu = gpu_inspect(ws)
        out["gpu"] = gpu
        if not out["vulkan"].get("ok") and gpu.get("ok"):
            out["vulkan"]["ok"] = True
            out["vulkan"]["port"] = 8080
    except Exception:
        pass

    return out
