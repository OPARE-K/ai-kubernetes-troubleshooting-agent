"use client";

import { useEffect, useState } from "react";

import { insforge } from "@/lib/insforge";
import type { ProgressEvent } from "@/types/api";
import { INVESTIGATION_STEPS } from "@/types/api";

export function useInvestigationRealtime(investigationId: string | null) {
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
  const [runningStep, setRunningStep] = useState<string | null>(null);

  useEffect(() => {
    if (!investigationId) {
      setCompletedSteps(new Set());
      setRunningStep(null);
      return;
    }

    let active = true;
    const channel = `investigation:${investigationId}`;

    const handleProgress = (payload: ProgressEvent) => {
      if (!active) return;
      if (payload.status === "running") {
        setRunningStep(payload.step);
        return;
      }
      setCompletedSteps((prev) => new Set(prev).add(payload.step));
      setRunningStep((current) => (current === payload.step ? null : current));
    };

    const setup = async () => {
      try {
        await insforge.realtime.connect();
        const response = await insforge.realtime.subscribe(channel);
        if (!response.ok) {
          console.warn("Realtime subscribe failed:", response.error?.message);
          return;
        }
        insforge.realtime.on("progress", handleProgress);
      } catch (error) {
        console.warn("Realtime setup failed:", error);
      }
    };

    setup();

    return () => {
      active = false;
      insforge.realtime.off("progress", handleProgress);
      insforge.realtime.unsubscribe(channel);
    };
  }, [investigationId]);

  const steps = INVESTIGATION_STEPS.map((step) => ({
    ...step,
    status: completedSteps.has(step.id)
      ? ("complete" as const)
      : runningStep === step.id
        ? ("running" as const)
        : ("pending" as const),
  }));

  return { steps, completedSteps, runningStep };
}
