"use client";

import { useState } from "react";
import LeftSidebar from "@/components/LeftSidebar";
import TopBar from "@/components/TopBar";
import ChatArena from "@/components/ChatArena";
import RightPanel from "@/components/RightPanel";
import VoiceFab from "@/components/VoiceFab";
import { Toaster } from "sonner";

export default function RealAI() {
    const [activePersona, setActivePersona] = useState<"limitless" | "builder" | "therapist" | "researcher" | "godmode">("limitless");
    const [rightPanelOpen, setRightPanelOpen] = useState(true);
    const [godMode, setGodMode] = useState(false);
    const [currentModelTier, setCurrentModelTier] = useState<"local" | "hybrid" | "cloud">("local");

    return (
        <div className="flex h-screen bg-zinc-950 text-white overflow-hidden">
            {/* Left Sidebar - Navigation & Personas */}
            <LeftSidebar
                activePersona={activePersona}
                onPersonaChange={setActivePersona}
            />

            {/* Main Content Area */}
            <div className="flex flex-col flex-1 min-w-0">
                <TopBar
                    persona={activePersona}
                    godMode={godMode}
                    modelTier={currentModelTier}
                    onGodModeToggle={() => setGodMode(!godMode)}
                    onToggleRightPanel={() => setRightPanelOpen(!rightPanelOpen)}
                    rightPanelOpen={rightPanelOpen}
                />

                <div className="flex flex-1 overflow-hidden relative">
                    {/* Chat Arena - The main experience */}
                    <ChatArena
                        persona={activePersona}
                        godMode={godMode}
                        modelTier={currentModelTier}
                    />

                    {/* Right Intelligence Panel */}
                    {rightPanelOpen && (
                        <RightPanel
                            persona={activePersona}
                            godMode={godMode}
                        />
                    )}
                </div>
            </div>

            {/* Floating Voice Button */}
            <VoiceFab />

            {/* Toast Notifications */}
            <Toaster
                position="top-center"
                richColors
                closeButton
                theme="dark"
            />
        </div>
    );
}