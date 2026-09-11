"use client";

import type { ReactNode } from "react";
import { Toaster } from "sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

/**
 * App-wide client provider mounted once near the top of `<body>`
 * (`src/routes/__root.tsx`):
 *
 *   <AuthProvider><Outlet /></AuthProvider>
 *
 * Better Auth's React client (`@/lib/auth/client`) needs NO context provider —
 * its `useSession()` works standalone — so this is the stable mount point for
 * client-side providers (tooltip, toast).
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  return (
    <TooltipProvider>
      {children}
      <Toaster
        theme="dark"
        position="bottom-center"
        toastOptions={{
          className: "font-sans",
          style: {
            background: "var(--color-raised)",
            color: "var(--color-fg)",
            border: "1px solid var(--color-border)",
          },
        }}
      />
    </TooltipProvider>
  );
}
