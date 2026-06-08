"use client";

import type { InvestigationRecord } from "@/types/api";

function confidenceColor(confidence: number | null) {
  const value = confidence ?? 0;
  if (value >= 70) return "text-emerald-400";
  if (value >= 40) return "text-amber-400";
  return "text-red-400";
}

export function InvestigationHistory({
  history,
  isLoading,
}: {
  history: InvestigationRecord[];
  isLoading: boolean;
}) {
  return (
    <section className="glass-card animate-fade-in p-6">
      <h2 className="section-title mb-1">Recent Investigations</h2>
      <p className="section-subtitle mb-5">Past diagnoses saved to your account.</p>

      {isLoading ? (
        <div className="space-y-3">
          <div className="skeleton-line w-full" />
          <div className="skeleton-line w-5/6" />
          <div className="skeleton-line w-4/6" />
        </div>
      ) : history.length === 0 ? (
        <div className="rounded-xl border border-dashed border-white/10 bg-slate-950/30 px-6 py-10 text-center">
          <p className="text-sm text-slate-400">No investigations yet.</p>
          <p className="mt-1 text-xs text-slate-500">
            Run your first cluster investigation above.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-white/5">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/5 bg-slate-950/50 text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-4 py-3 font-medium">Root Cause</th>
                  <th className="px-4 py-3 font-medium">Namespace</th>
                  <th className="px-4 py-3 font-medium">Confidence</th>
                  <th className="px-4 py-3 font-medium">When</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item, index) => (
                  <tr
                    key={item.id}
                    className={`border-b border-white/5 transition-colors hover:bg-white/[0.02] ${
                      index % 2 === 0 ? "bg-transparent" : "bg-slate-950/20"
                    }`}
                  >
                    <td className="max-w-xs truncate px-4 py-3.5 font-medium text-slate-200">
                      {item.root_cause ?? "—"}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="badge border-white/10 bg-slate-800/50 text-slate-300">
                        {item.namespace ?? "—"}
                      </span>
                    </td>
                    <td className={`px-4 py-3.5 font-medium ${confidenceColor(item.confidence)}`}>
                      {item.confidence ?? 0}%
                    </td>
                    <td className="px-4 py-3.5 text-slate-500">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
