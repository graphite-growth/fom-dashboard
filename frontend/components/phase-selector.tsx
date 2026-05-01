"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Phase } from "@/lib/dashboard-data";

interface PhaseSelectorProps {
  phases: Phase[];
  value: string;
  onChange: (phaseId: string) => void;
}

export function PhaseSelector({ phases, value, onChange }: PhaseSelectorProps) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger size="sm" className="w-[170px]">
        <SelectValue placeholder="Select phase" />
      </SelectTrigger>
      <SelectContent>
        {phases.map((p) => (
          <SelectItem key={p.id} value={p.id}>
            {p.label}
            {p.status === "in-progress" && (
              <span className="ml-1.5 text-[10px] text-emerald-400">
                · live
              </span>
            )}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
