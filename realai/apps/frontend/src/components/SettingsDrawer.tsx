"use client";

import { X, ChevronDown, Check } from "lucide-react";
import { useState } from "react";
import type { Settings, ModelOption } from "@/lib/types";
import { DEFAULT_MODELS } from "@/lib/types";

interface SettingsDrawerProps {
  open: boolean;
  onClose: () => void;
  settings: Settings;
  onChange: (s: Settings) => void;
}

function ModelPicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const selected = DEFAULT_MODELS.find((m) => m.id === value) ?? DEFAULT_MODELS[0];

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center justify-between w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700
                   text-sm text-slate-100 hover:border-brand-600 transition-colors"
      >
        <span>{selected.label}</span>
        <ChevronDown
          size={14}
          className={`text-slate-400 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-xl bg-slate-800 border border-slate-700 shadow-2xl overflow-hidden">
          {DEFAULT_MODELS.map((model) => (
            <button
              key={model.id}
              onClick={() => {
                onChange(model.id);
                setOpen(false);
              }}
              className="flex items-start gap-2 w-full px-3 py-2.5 hover:bg-slate-700 transition-colors text-left"
            >
              <Check
                size={13}
                className={`mt-0.5 shrink-0 ${value === model.id ? "text-brand-400" : "opacity-0"}`}
              />
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-slate-100">{model.label}</span>
                  {model.badge && (
                    <span className="text-xs font-medium text-brand-300 bg-brand-900/40 px-1.5 py-0.5 rounded">
                      {model.badge}
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-0.5">{model.description}</p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SettingsDrawer({
  open,
  onClose,
  settings,
  onChange,
}: SettingsDrawerProps) {
  function update<K extends keyof Settings>(key: K, value: Settings[K]) {
    onChange({ ...settings, [key]: value });
  }

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
          onClick={onClose}
        />
      )}

      {/* Drawer */}
      <div
        className={[
          "fixed right-0 top-0 h-full z-50 w-80 bg-slate-900 border-l border-slate-800 flex flex-col",
          "transition-transform duration-300",
          open ? "translate-x-0" : "translate-x-full",
        ].join(" ")}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
          <h2 className="font-semibold text-slate-100">Settings</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-100 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-6">
          {/* Model */}
          <section>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Model
            </label>
            <ModelPicker
              value={settings.model}
              onChange={(id) => update("model", id)}
            />
          </section>

          {/* System Prompt */}
          <section>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              System Prompt
            </label>
            <textarea
              value={settings.systemPrompt}
              onChange={(e) => update("systemPrompt", e.target.value)}
              rows={5}
              placeholder="Give RealAI a persona or set context for this conversation…"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm
                         text-slate-100 placeholder-slate-500 resize-none focus:outline-none
                         focus:border-brand-600 transition-colors"
            />
          </section>

          {/* Temperature */}
          <section>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Temperature
              <span className="ml-auto float-right text-brand-400 font-mono">
                {settings.temperature.toFixed(1)}
              </span>
            </label>
            <input
              type="range"
              min={0}
              max={2}
              step={0.1}
              value={settings.temperature}
              onChange={(e) => update("temperature", parseFloat(e.target.value))}
              className="w-full accent-brand-500 cursor-pointer"
            />
            <div className="flex justify-between text-xs text-slate-600 mt-1">
              <span>Precise</span>
              <span>Creative</span>
            </div>
          </section>

          {/* Max Tokens */}
          <section>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Max Tokens
              <span className="ml-auto float-right text-brand-400 font-mono">
                {settings.maxTokens.toLocaleString()}
              </span>
            </label>
            <input
              type="range"
              min={256}
              max={8192}
              step={256}
              value={settings.maxTokens}
              onChange={(e) => update("maxTokens", parseInt(e.target.value, 10))}
              className="w-full accent-brand-500 cursor-pointer"
            />
            <div className="flex justify-between text-xs text-slate-600 mt-1">
              <span>256</span>
              <span>8 192</span>
            </div>
          </section>

          {/* API Key */}
          <section>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              API Key <span className="text-slate-600">(optional)</span>
            </label>
            <input
              type="password"
              value={settings.apiKey}
              onChange={(e) => update("apiKey", e.target.value)}
              placeholder="sk-…  or leave blank to use server key"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm
                         text-slate-100 placeholder-slate-500 focus:outline-none
                         focus:border-brand-600 transition-colors font-mono"
            />
            <p className="text-xs text-slate-600 mt-1.5">
              Stored in memory only — never sent to third parties.
            </p>
          </section>
        </div>

        {/* Footer */}
        <div className="border-t border-slate-800 px-5 py-4">
          <button
            onClick={onClose}
            className="w-full py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium transition-colors"
          >
            Save &amp; Close
          </button>
        </div>
      </div>
    </>
  );
}
