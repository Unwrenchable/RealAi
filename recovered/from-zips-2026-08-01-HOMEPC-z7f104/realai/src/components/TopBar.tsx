import { Settings, Mic, PanelRight } from "lucide-react";

export default function TopBar({ persona, godMode, onGodModeToggle, onToggleRightPanel, rightPanelOpen }: any) {
  return (
    <div className="h-14 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-md flex items-center px-6 z-10">
      <div className="flex-1 flex items-center gap-4">
        <div className="px-3 py-1 bg-zinc-900 rounded-full text-sm font-medium capitalize flex items-center gap-2">
          {persona} Mode
          {godMode && <span className="text-rose-400 text-xs">⚡ GOD MODE</span>}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={onGodModeToggle}
          className={`px-4 py-1.5 rounded-xl text-sm font-medium transition ${godMode ? "bg-rose-500/20 text-rose-400" : "hover:bg-zinc-800"}`}
        >
          God Mode
        </button>

        <button className="p-2 hover:bg-zinc-900 rounded-xl">
          <Mic className="w-5 h-5" />
        </button>

        <button onClick={onToggleRightPanel} className="p-2 hover:bg-zinc-900 rounded-xl">
          <PanelRight className="w-5 h-5" />
        </button>

        <button className="p-2 hover:bg-zinc-900 rounded-xl">
          <Settings className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}