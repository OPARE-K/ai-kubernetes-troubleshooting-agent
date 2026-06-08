"use client";

import { getDiagnosisCommands } from "@/lib/diagnosisCommands";
import type { Diagnosis } from "@/types/api";

function ConfidenceBar({ value }: { value: number | null | undefined }) {
  const confidence =
    typeof value === "number" && Number.isFinite(value)
      ? Math.max(0, Math.min(100, value))
      : 0;
  const color =
    confidence >= 70
      ? "from-emerald-500 to-green-400"
      : confidence >= 40
        ? "from-amber-500 to-yellow-400"
        : "from-red-500 to-orange-400";

  return (
    <div className="mt-2">
      <div className="flex items-center justify-between text-xs text-slate-400">
        <span>Confidence</span>
        <span className="font-medium text-white">{confidence}%</span>
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-800/80">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${color} transition-all duration-700`}
          style={{ width: `${confidence}%` }}
        />
      </div>
    </div>
  );
}

export function DiagnosisCard({
  diagnosis,
  clusterHealthy,
  warnings,
  clusterContext,
}: {
  diagnosis: Diagnosis | null;
  clusterHealthy?: boolean | null;
  warnings?: string[];
  clusterContext?: string | null;
}) {
  if (!diagnosis) return null;

  const commands = getDiagnosisCommands(diagnosis);
  const aiUnavailable = diagnosis.root_cause === "AI diagnosis unavailable";
  const healthy = clusterHealthy === true;

  const cardClass = healthy
    ? "border-emerald-500/25 bg-emerald-950/15"
    : aiUnavailable
      ? "border-amber-500/25 bg-amber-950/15"
      : "border-white/10 bg-slate-900/50";

  return (
    <section className={`glass-card animate-fade-in border p-6 ${cardClass}`}>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <h2 className="section-title">Diagnosis</h2>
        {clusterContext ? (
          <span className="badge border-sky-500/25 bg-sky-500/10 text-sky-200">
            {clusterContext}
          </span>
        ) : null}
      </div>

      {healthy ? (
        <div className="alert-success mb-5">
          <p className="font-medium">No critical Kubernetes issues detected.</p>
          <p className="mt-1 text-emerald-200/80">Cluster appears healthy.</p>
        </div>
      ) : null}

      {aiUnavailable ? (
        <div className="alert-warning mb-5">
          AI reasoning was unavailable for this run. Review the evidence below and retry if needed.
        </div>
      ) : null}

      {warnings && warnings.length > 0 ? (
        <div className="alert-warning mb-5">
          <p className="font-medium">Warnings</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-amber-200/90">
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="space-y-5">
        <div className="rounded-xl border border-white/5 bg-slate-950/40 p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Root Cause</p>
          <p className="mt-2 text-base font-medium leading-relaxed text-white">
            {diagnosis.root_cause}
          </p>
        </div>

        <div className="rounded-xl border border-white/5 bg-slate-950/40 p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Explanation</p>
          <p className="mt-2 whitespace-pre-line leading-relaxed text-slate-300">
            {diagnosis.explanation}
          </p>
        </div>

        <div className="rounded-xl border border-sky-500/10 bg-sky-950/20 p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-sky-400/80">
            Suggested Fix
          </p>
          <p className="mt-2 whitespace-pre-line leading-relaxed text-slate-200">
            {diagnosis.fix}
          </p>
        </div>

        {commands.length > 0 ? (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Command</p>
            <div className="mt-2 space-y-2">
              {commands.map((command) => (
                <code
                  key={command}
                  className="block overflow-x-auto rounded-xl border border-emerald-500/20 bg-slate-950 px-4 py-3 font-mono text-xs text-emerald-300"
                >
                  {command}
                </code>
              ))}
            </div>
          </div>
        ) : null}

        <ConfidenceBar value={diagnosis.confidence} />
      </div>
    </section>
  );
}
