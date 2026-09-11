"use client";

const personas = [
  { id: "limitless", name: "Limitless", icon: "🌌", color: "violet" },
  { id: "builder", name: "Business Builder", icon: "🏗️", color: "amber" },
  { id: "therapist", name: "Therapist", icon: "🧠", color: "emerald" },
  { id: "researcher", name: "Deep Researcher", icon: "🔍", color: "sky" },
  { id: "godmode", name: "God Mode", icon: "⚡", color: "rose" },
];

export default function LeftSidebar({ activePersona, onPersonaChange }: any) {
  return (
    <div className="w-72 border-r border-zinc-800 bg-zinc-950 flex flex-col">
      <div className="p-6 border-b border-zinc-800">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-violet-400 via-fuchsia-400 to-rose-400 bg-clip-text text-transparent">
          RealAI
        </h1>
        <p className="text-sm text-zinc-500 mt-1">All models want to be me</p>
      </div>

      <div className="p-4">
        <p className="uppercase text-xs tracking-widest text-zinc-500 mb-3 px-2">Personas</p>
        {personas.map((p) => (
          <button
            key={p.id}
            onClick={() => onPersonaChange(p.id)}
            className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-2xl mb-1 text-left transition-all hover:bg-zinc-900 ${
              activePersona === p.id ? "bg-zinc-800 ring-1 ring-violet-500" : ""
            }`}
          >
            <span className="text-2xl">{p.icon}</span>
            <span className="font-medium">{p.name}</span>
          </button>
        ))}
      </div>

      <div className="mt-auto p-4 border-t border-zinc-800">
        <button className="w-full py-4 bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 rounded-2xl font-semibold flex items-center justify-center gap-2 text-lg">
          🚀 New Project
        </button>
      </div>
    </div>
  );
}