"use client";

import type { ComponentProps } from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";

export const Tabs = TabsPrimitive.Root;

export function TabsList({ className, ...props }: ComponentProps<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      className={cn(
        "flex w-full gap-1 rounded-lg bg-surface p-1 shadow-[var(--shadow-border)]",
        className,
      )}
      {...props}
    />
  );
}

export function TabsTrigger({
  className,
  ...props
}: ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        "flex h-10 flex-1 items-center justify-center rounded-md px-3 text-sm font-medium text-muted",
        "transition-[background-color,color,transform] duration-150 ease-[var(--ease-smooth)]",
        "data-[state=active]:bg-raised data-[state=active]:text-fg data-[state=active]:shadow-[var(--shadow-border)]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50",
        className,
      )}
      {...props}
    />
  );
}

export function TabsContent({
  className,
  ...props
}: ComponentProps<typeof TabsPrimitive.Content>) {
  return (
    <TabsPrimitive.Content className={cn("mt-5 outline-none", className)} {...props} />
  );
}
