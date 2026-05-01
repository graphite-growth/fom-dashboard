"use client";

import { GraphiteLogo } from "@/components/ui/graphite-logo";

export function LoadingOverlay() {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Loading"
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
    >
      <div className="flex flex-col items-center gap-4">
        <div className="animate-pulse">
          <div className="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-12 items-center justify-center rounded-lg">
            <GraphiteLogo className="size-6" />
          </div>
        </div>
        <span className="text-xs text-muted-foreground">Loading…</span>
      </div>
    </div>
  );
}
