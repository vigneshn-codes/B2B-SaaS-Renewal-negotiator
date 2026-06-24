import { Handshake, Play, Loader2, Network } from "lucide-react";
import { useNegotiationStream } from "./hooks/useNegotiationStream";
import { NegotiationCard } from "./components/NegotiationCard";
import { SummaryPanel } from "./components/SummaryPanel";

export default function App() {
  const { vendors, totalSavings, phase, error, start } = useNegotiationStream();
  const running = phase === "running";

  return (
    <div className="mx-auto min-h-dvh max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <header className="mb-8 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl border border-white/10 bg-gradient-to-br from-primary/30 to-accent/30">
            <Handshake className="h-6 w-6 text-white" aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-xl font-extrabold tracking-tight sm:text-2xl">
              B2B SaaS Renewal Negotiator
            </h1>
            <p className="mt-0.5 flex items-center gap-1.5 text-xs text-white/50">
              <Network className="h-3.5 w-3.5" aria-hidden="true" />
              Parallel agent-to-agent (A2A) renewal negotiations
            </p>
          </div>
        </div>

        <button
          onClick={start}
          disabled={running}
          className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-accent/40 bg-accent/20 px-4 py-2.5 text-sm font-semibold text-white transition-all duration-200 hover:bg-accent/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:cursor-not-allowed disabled:opacity-50"
        >
          {running ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Negotiating…
            </>
          ) : (
            <>
              <Play className="h-4 w-4" aria-hidden="true" />
              Start negotiations
            </>
          )}
        </button>
      </header>

      {error && (
        <div
          role="alert"
          className="mb-6 rounded-xl border border-danger/40 bg-danger/15 p-4 text-sm text-red-300"
        >
          Error: {error}
        </div>
      )}

      {/* Bento grid of live negotiations */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
        {vendors.length === 0 ? (
          <div className="glass col-span-full grid min-h-[16rem] place-items-center p-8 text-center">
            <div>
              <Network className="mx-auto mb-3 h-10 w-10 text-white/30" aria-hidden="true" />
              <p className="text-sm text-white/50">
                Press <span className="font-semibold text-white/80">Start negotiations</span> to
                launch parallel renewals with Salesforce, Notion &amp; Datadog.
              </p>
            </div>
          </div>
        ) : (
          vendors.map((v) => <NegotiationCard key={v.vendor} data={v} />)
        )}
      </div>

      {/* Summary */}
      {vendors.length > 0 && (
        <div className="mt-6">
          <SummaryPanel vendors={vendors} totalSavings={totalSavings} />
        </div>
      )}

      <footer className="mt-10 text-center text-xs text-white/30">
        Procurement agent vs. vendor sales agents · GPT-4o-mini · A2A protocol over HTTP
      </footer>
    </div>
  );
}
