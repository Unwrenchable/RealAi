"use client";

import { useState } from "react";
import { Brain, Activity, FileText, Zap } from "lucide-react";

export default function RightPanel() {
  const [activeTab, setActiveTab] = useState("memory");

  return (
    <div className="w-80 border-l border-zinc-800 bg-zinc-950 flex flex-col">
      <div className="p-4 border-b border-zinc-800">
        <h3 className="text-lg font-semibold">Intelligence Dashboard</h3>
      </div>

      <div className="flex border-b border-zinc-800">
        {[
          { id: "memory", label: "Memory", icon: Brain },
          { id: "agents", label: "Agents", icon: Activity },
          { id: "audit", label: "Audit", icon: FileText },
          { id: "system", label: "System", icon: Zap },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 py-3 px-2 text-center text-sm font-medium transition-colors ${
              activeTab === tab.id ? "text-violet-400 border-b-2 border-violet-400" : "text-zinc-400 hover:text-white"
            }`}
          >
            <tab.icon className="w-4 h-4 mx-auto mb-1" />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === "memory" && (
          <div className="space-y-4">
            <div className="bg-zinc-900 rounded-xl p-4">
              <p className="text-sm font-medium mb-2">Recent Memories</p>
              <div className="space-y-2 text-xs text-zinc-400">
                <p>• Built llama.cpp integration</p>
                <p>• Created Aura cognitive architecture</p>
                <p>• Upgraded frontend to OS interface</p>
              </div>
            </div>
            <button className="w-full py-2 bg-violet-600 hover:bg-violet-500 rounded-xl text-sm font-medium">
              Weekly Reflection
            </button>
          </div>
        )}

        {activeTab === "agents" && (
          <div className="space-y-4">
            <div className="bg-zinc-900 rounded-xl p-4">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span className="font-medium">Planner Agent</span>
              </div>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-3 h-3 bg-yellow-500 rounded-full animate-pulse"></div>
                <span className="font-medium">Researcher Agent</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 bg-zinc-600 rounded-full"></div>
                <span className="font-medium">Executor Agent</span>
              </div>
            </div>
          </div>
        )}

        {activeTab === "audit" && (
          <div className="space-y-3">
            <div className="bg-zinc-900 rounded-xl p-3">
              <p className="text-sm">Tool execution: Web Search</p>
              <p className="text-xs text-zinc-400">2 minutes ago</p>
            </div>
            <div className="bg-zinc-900 rounded-xl p-3">
              <p className="text-sm">File created: aura/main.py</p>
              <p className="text-xs text-zinc-400">5 minutes ago</p>
            </div>
          </div>
        )}

        {activeTab === "system" && (
          <div className="space-y-4">
            <div className="bg-zinc-900 rounded-xl p-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium">Model Status</span>
                <span className="text-green-400 text-xs">Online</span>
              </div>
              <p className="text-xs text-zinc-400">Local Llama 3.2 1B</p>
            </div>
            <div className="bg-zinc-900 rounded-xl p-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium">CPU Usage</span>
                <span className="text-blue-400 text-xs">45%</span>
              </div>
              <div className="w-full bg-zinc-700 rounded-full h-2">
                <div className="bg-blue-400 h-2 rounded-full" style={{ width: "45%" }}></div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}