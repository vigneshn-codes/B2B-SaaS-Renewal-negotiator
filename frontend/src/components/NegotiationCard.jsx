import { OutcomeBadge } from "./OutcomeBadge";
import { TranscriptFeed } from "./TranscriptFeed";

const fmt = (n) =>
  n == null || n < 0 ? "—" : `$${Number(n).toLocaleString("en-US")}`;

const MAX_ROUNDS = 6;

export function NegotiationCard({ data }) {
  const status = data.status ?? "idle";
  const isLive = status === "in_progress";
  const rounds = data.rounds ?? 0;
  const progress = Math.min((rounds / MAX_ROUNDS) * 100, 100);

  return (
    <article className="glass glass-hover flex flex-col gap-4 p-5">
      {/* Header */}
      <header className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            {isLive && (
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-accent" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
              </span>
            )}
            <h2 className="text-lg font-bold tracking-tight">{data.vendor}</h2>
          </div>
          <p className="mt-0.5 text-xs text-white/50 tnum">
            Current ARR {fmt(data.originalArr)}
          </p>
        </div>
        <OutcomeBadge status={status} />
      </header>

      {/* Progress bar */}
      <div>
        <div className="mb-1.5 flex items-center justify-between text-[11px] text-white/40">
          <span>Round {rounds} / {MAX_ROUNDS}</span>
          {data.finalPrice != null && data.finalPrice > 0 && (
            <span className="tnum text-white/70">
              Final {fmt(data.finalPrice)}
            </span>
          )}
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              status === "agreed"
                ? "bg-success"
                : status === "walked_away"
                ? "bg-danger"
                : status === "escalated"
                ? "bg-warning"
                : "bg-accent"
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Transcript */}
      <TranscriptFeed messages={data.messages ?? []} />

      {/* Summary footer */}
      {data.summary && (
        <footer className="rounded-xl border border-white/10 bg-black/20 p-3 text-xs text-white/60">
          {data.summary}
        </footer>
      )}
    </article>
  );
}
