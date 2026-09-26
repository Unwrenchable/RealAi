"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, RefreshCw, Wrench, Database, Shield } from "lucide-react";

type AnyObj = Record<string, unknown>;

async function fetchJson(url: string): Promise<AnyObj> {
  const res = await fetch(url, { cache: "no-store" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    return { error: data?.error || res.statusText, ...data };
  }
  return data;
}

function Pill({ ok, label }: { ok?: boolean; label: string }) {
  const color =
    ok === true
      ? "bg-emerald-900/50 text-emerald-300 border-emerald-700"
      : ok === false
        ? "bg-red-900/40 text-red-300 border-red-800"
        : "bg-slate-800 text-slate-400 border-slate-700";
  return (
    <span className={`text-xs px-2 py-0.5 rounded border ${color}`}>{label}</span>
  );
}

export default function SystemStatusPanel() {
  const [training, setTraining] = useState<AnyObj | null>(null);
  const [selfImprove, setSelfImprove] = useState<AnyObj | null>(null);
  const [selfHeal, setSelfHeal] = useState<AnyObj | null>(null);
  const [agents, setAgents] = useState<AnyObj | null>(null);
  const [loading, setLoading] = useState(false);
  const [cycleMsg, setCycleMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [t, s, h, a] = await Promise.all([
        fetchJson("/api/training/status"),
        fetchJson("/api/self-improve/status"),
        fetchJson("/api/self-heal/status"),
        fetchJson("/api/agents"),
      ]);
      setTraining(t);
      setSelfImprove(s);
      setSelfHeal(h);
      setAgents(a);
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function runCycle(apply: boolean) {
    setCycleMsg(apply ? "Running self-heal cycle (apply)…" : "Running self-heal cycle (dry)…");
    setError(null);
    try {
      const res = await fetch("/api/self-heal/cycle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ apply }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data?.error || res.statusText);
        setCycleMsg(null);
        return;
      }
      setCycleMsg(
        data?.ok
          ? `Cycle done. Promote apply=${Boolean(apply)}.`
          : `Cycle finished with issues. See orchestrator logs.`
      );
      await refresh();
    } catch (e: any) {
      setError(String(e?.message || e));
      setCycleMsg(null);
    }
  }

  const healAbilities = (selfHeal?.abilities || {}) as Record<string, boolean>;
  const trainFiles = (training?.files as AnyObj[]) || [];

  return (
    <div className="space-y-4 border-t border-slate-800 pt-4 mt-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
          <Activity size={16} className="text-brand-400" />
          RealAI Self-Heal & Training
        </div>
        <button
          type="button"
          onClick={refresh}
          disabled={loading}
          className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400"
          title="Refresh"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      <p className="text-xs text-slate-500 leading-relaxed">
        Same loop we used to unify the multi-era super-repo: discover → assemble gold →
        promote uniques → verify. Gated by{" "}
        <code className="text-slate-400">REALAI_SELF_IMPROVE</code>.
      </p>

      {error && (
        <div className="text-xs text-red-300 bg-red-950/40 border border-red-900 rounded-lg p-2">
          {error}
        </div>
      )}
      {cycleMsg && (
        <div className="text-xs text-emerald-300 bg-emerald-950/30 border border-emerald-900 rounded-lg p-2">
          {cycleMsg}
        </div>
      )}

      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Database size={13} /> Training
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Pill ok={Boolean(training?.finetune_dataset)} label="finetune jsonl" />
          <Pill ok={Boolean(training?.agent_manifests)} label="agent manifests" />
          <Pill
            ok={typeof agents?.count === "number" && (agents.count as number) > 0}
            label={
              typeof agents?.count === "number"
                ? `${agents.count} agents`
                : "agents ?"
            }
          />
          <Pill
            ok={Boolean(selfImprove?.enabled ?? selfHeal?.enabled)}
            label={
              selfImprove?.enabled || selfHeal?.enabled
                ? "self-improve ON"
                : "self-improve OFF"
            }
          />
        </div>
        {trainFiles.length > 0 && (
          <ul className="text-xs text-slate-500 space-y-0.5 max-h-20 overflow-auto">
            {trainFiles.map((f) => (
              <li key={String(f.name)}>
                {String(f.name)}
                {typeof f.lines === "number" && f.lines > 0 ? ` · ${f.lines} lines` : ""}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Shield size={13} /> Self-heal abilities
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Pill ok={Boolean(healAbilities.scan_messy_repo)} label="scan messy repo" />
          <Pill ok={Boolean(healAbilities.assemble_gold)} label="assemble gold" />
          <Pill ok={Boolean(healAbilities.promote_gold)} label="promote gold" />
          <Pill ok={Boolean(healAbilities.training_data)} label="training data" />
          <Pill ok={Boolean(healAbilities.self_improvement)} label="self-improve mod" />
        </div>
        {typeof selfHeal?.promote_queue_items === "number" && (
          <p className="text-xs text-slate-500">
            Promote queue: {String(selfHeal.promote_queue_items)} items · actionable{" "}
            {String(selfHeal.promote_actionable ?? "?")}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <button
          type="button"
          onClick={() => runCycle(false)}
          className="flex items-center justify-center gap-2 w-full px-3 py-2 rounded-lg
                     bg-slate-800 border border-slate-700 text-xs text-slate-100
                     hover:border-brand-600 transition-colors"
        >
          <Wrench size={13} />
          Run self-heal cycle (dry-run)
        </button>
        <button
          type="button"
          onClick={() => {
            if (
              confirm(
                "Apply curated promote from queue? Will not bulk-merge. Memory stays in recovered/."
              )
            ) {
              runCycle(true);
            }
          }}
          className="flex items-center justify-center gap-2 w-full px-3 py-2 rounded-lg
                     bg-brand-900/40 border border-brand-700 text-xs text-brand-100
                     hover:bg-brand-900/60 transition-colors"
        >
          <Wrench size={13} />
          Run self-heal cycle (apply promote)
        </button>
      </div>
    </div>
  );
}
