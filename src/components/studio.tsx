"use client";

import { useEffect, useState } from "react";
import { AudioLines } from "lucide-react";
import { EngineRack } from "@/components/engine-rack";
import { SpeakDeck } from "@/components/speak-deck";
import { CloneDeck } from "@/components/clone-deck";
import { PipelineCard } from "@/components/pipeline-card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ENGINES } from "@/lib/engines";
import { useLab } from "@/lib/store";

export function Studio() {
  const [ready, setReady] = useState(false);
  const engineId = useLab((s) => s.engineId);
  const engine = ENGINES.find((e) => e.id === engineId) ?? ENGINES[0];

  useEffect(() => {
    void Promise.resolve(useLab.persist.rehydrate()).then(() => setReady(true));
  }, []);

  if (!ready) {
    return (
      <div className="min-h-dvh bg-bg text-fg">
        <header className="border-b border-border">
          <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-5 sm:px-6">
            <span className="flex size-10 items-center justify-center rounded-md bg-raised shadow-[var(--shadow-border)]">
              <AudioLines className="size-5 text-accent" />
            </span>
            <div>
              <p className="font-mono text-xs tracking-widest text-subtle uppercase">RealAI</p>
              <h1 className="font-display text-2xl font-semibold tracking-tight">Voice Lab</h1>
            </div>
          </div>
        </header>
      </div>
    );
  }

  return (
    <div className="min-h-dvh overflow-x-hidden bg-bg text-fg">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-md bg-raised shadow-[var(--shadow-border)]">
              <AudioLines className="size-5 text-accent" />
            </span>
            <div className="min-w-0">
              <p className="font-mono text-xs tracking-widest text-subtle uppercase">RealAI</p>
              <h1 className="font-display text-2xl font-semibold tracking-tight">Voice Lab</h1>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="led">Live rack</Badge>
            <Badge>{engine.name}</Badge>
            <Badge>RX 6700 XT</Badge>
          </div>
        </div>
      </header>

      <main className="mx-auto grid min-w-0 max-w-6xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[minmax(16rem,19rem)_minmax(0,1fr)] lg:py-8">
        <EngineRack />

        <div className="flex min-w-0 flex-col gap-6">
          <Tabs defaultValue="speak">
            <TabsList>
              <TabsTrigger value="speak">Speak</TabsTrigger>
              <TabsTrigger value="clone">Clone</TabsTrigger>
              <TabsTrigger value="pipeline">Pipeline</TabsTrigger>
            </TabsList>
            <TabsContent
              value="speak"
              className="rounded-xl bg-surface p-4 shadow-[var(--shadow-border)] sm:p-5"
            >
              <SpeakDeck />
            </TabsContent>
            <TabsContent
              value="clone"
              className="rounded-xl bg-surface p-4 shadow-[var(--shadow-border)] sm:p-5"
            >
              <CloneDeck />
            </TabsContent>
            <TabsContent value="pipeline">
              <PipelineCard />
            </TabsContent>
          </Tabs>
        </div>
      </main>
    </div>
  );
}
