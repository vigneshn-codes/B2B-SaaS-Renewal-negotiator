import { TrendingDown, PiggyBank } from "lucide-react";
import { OutcomeBadge } from "./OutcomeBadge";

const fmt = (n) =>
  n == null || n < 0 ? "—" : `$${Number(n).toLocaleString("en-US")}`;

export function SummaryPanel({ vendors, totalSavings }) {
  const totalOriginal = vendors.reduce((s, v) => s + (v.originalArr ?? 0), 0);
  const savings = totalSavings ?? vendors.reduce((s, v) => s + (v.savings ?? 0), 0);
  const pct = totalOriginal > 0 ? (savings / totalOriginal) * 100 : 0;

  return (
    <section className="glass p-5">
      <div className="mb-4 flex items-center gap-2">
        <PiggyBank className="h-5 w-5 text-primary" aria-hidden="true" />
        <h2 className="text-base font-bold tracking-tight">Renewal Summary</h2>
      </div>

      {/* Results table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wide text-white/40">
              <th className="py-2 pr-4 font-medium">Vendor</th>
              <th className="py-2 pr-4 font-medium">Outcome</th>
              <th className="py-2 pr-4 text-right font-medium">Original ARR</th>
              <th className="py-2 pr-4 text-right font-medium">Final</th>
              <th className="py-2 pr-4 text-right font-medium">Savings</th>
              <th className="py-2 text-right font-medium">Rounds</th>
            </tr>
          </thead>
          <tbody>
            {vendors.map((v) => (
              <tr key={v.vendor} className="border-b border-white/5 last:border-0">
                <td className="py-2.5 pr-4 font-semibold">{v.vendor}</td>
                <td className="py-2.5 pr-4">
                  <OutcomeBadge status={v.status ?? "idle"} />
                </td>
                <td className="tnum py-2.5 pr-4 text-right text-white/70">
                  {fmt(v.originalArr)}
                </td>
                <td className="tnum py-2.5 pr-4 text-right text-white/70">
                  {fmt(v.finalPrice)}
                </td>
                <td className="tnum py-2.5 pr-4 text-right font-semibold text-success">
                  {v.savings > 0 ? fmt(v.savings) : "—"}
                </td>
                <td className="tnum py-2.5 text-right text-white/50">
                  {v.rounds ?? "—"}
                </td>
              </tr>
            ))}
            {vendors.length === 0 && (
              <tr>
                <td colSpan={6} className="py-6 text-center text-white/40">
                  No negotiations yet — press “Start negotiations”.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Bottom line */}
      <div className="mt-5 flex flex-col items-start justify-between gap-3 rounded-xl border border-success/30 bg-success/[0.08] p-4 sm:flex-row sm:items-center">
        <div className="flex items-center gap-2 text-sm text-white/70">
          <TrendingDown className="h-4 w-4 text-success" aria-hidden="true" />
          Total savings across {vendors.length || 0} renewals
        </div>
        <div className="text-right">
          <div className="tnum text-2xl font-extrabold text-success">
            {fmt(savings)}
          </div>
          {totalOriginal > 0 && (
            <div className="tnum text-xs text-white/50">
              {pct.toFixed(1)}% off ${totalOriginal.toLocaleString("en-US")} combined ARR
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
