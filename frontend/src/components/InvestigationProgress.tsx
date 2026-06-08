"use client";

type StepStatus = "pending" | "running" | "complete" | "failed";

interface StepView {
  id: string;
  label: string;
  status: StepStatus;
}

function StepIcon({ status }: { status: StepStatus }) {
  if (status === "complete") {
    return (
      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500/15 text-sm text-emerald-400 ring-1 ring-emerald-500/30">
        ✓
      </span>
    );
  }
  if (status === "running") {
    return (
      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-sky-500/15 ring-1 ring-sky-500/40">
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-sky-400/30 border-t-sky-300" />
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-red-500/15 text-sm text-red-400 ring-1 ring-red-500/30">
        ✗
      </span>
    );
  }
  return (
    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-800/80 text-xs text-slate-500 ring-1 ring-white/5">
      ○
    </span>
  );
}

export function InvestigationProgress({
  steps,
  isActive,
  title,
}: {
  steps: StepView[];
  isActive: boolean;
  title?: string;
}) {
  if (!isActive && steps.every((step) => step.status === "pending")) {
    return null;
  }

  const completedCount = steps.filter((step) => step.status === "complete").length;
  const progressPercent = Math.round((completedCount / steps.length) * 100);

  return (
    <section className="glass-card animate-fade-in p-6">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="section-title">{title ?? "Investigation Status"}</h2>
          {isActive && !steps.every((step) => step.status === "complete") ? (
            <p className="mt-1 text-sm text-sky-300/90">Investigating Kubernetes Cluster...</p>
          ) : null}
        </div>
        <span className="text-xs font-medium text-slate-500">
          {completedCount} / {steps.length} steps
        </span>
      </div>

      <div className="mb-6 h-1.5 overflow-hidden rounded-full bg-slate-800/80">
        <div
          className="h-full rounded-full bg-gradient-to-r from-sky-600 to-blue-500 transition-all duration-500 ease-out"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      <ul className="space-y-1">
        {steps.map((step, index) => (
          <li
            key={step.id}
            className={`flex items-center gap-4 rounded-xl px-3 py-2.5 transition-colors ${
              step.status === "running" ? "bg-sky-500/5" : ""
            }`}
          >
            <div className="relative flex flex-col items-center">
              <StepIcon status={step.status} />
              {index < steps.length - 1 ? (
                <span
                  className={`absolute top-8 h-6 w-px ${
                    step.status === "complete" ? "bg-emerald-500/30" : "bg-white/5"
                  }`}
                />
              ) : null}
            </div>
            <span
              className={`text-sm ${
                step.status === "pending"
                  ? "text-slate-500"
                  : step.status === "running"
                    ? "font-medium text-sky-100"
                    : "text-slate-200"
              }`}
            >
              {step.label}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export type { StepView, StepStatus };
