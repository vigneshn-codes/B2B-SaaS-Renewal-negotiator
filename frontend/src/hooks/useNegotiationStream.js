import { useCallback, useRef, useState } from "react";

/**
 * Drives the negotiation run and consumes the SSE event stream.
 *
 * State shape per vendor:
 *   { vendor, status, originalArr, finalPrice, savings, rounds, summary, messages: [] }
 */
export function useNegotiationStream() {
  const [vendors, setVendors] = useState({});
  const [totalSavings, setTotalSavings] = useState(null);
  const [phase, setPhase] = useState("idle"); // idle | running | done | error
  const [error, setError] = useState(null);
  const esRef = useRef(null);

  const upsertVendor = useCallback((name, patch) => {
    setVendors((prev) => ({
      ...prev,
      [name]: { ...(prev[name] ?? { vendor: name, messages: [] }), ...patch },
    }));
  }, []);

  const handleEvent = useCallback(
    (evt) => {
      switch (evt.type) {
        case "negotiation_started":
          upsertVendor(evt.vendor, {
            status: "in_progress",
            originalArr: evt.original_arr,
            messages: [],
          });
          break;
        case "round_message":
          setVendors((prev) => {
            const v = prev[evt.vendor] ?? { vendor: evt.vendor, messages: [] };
            return {
              ...prev,
              [evt.vendor]: {
                ...v,
                rounds: evt.round,
                messages: [
                  ...v.messages,
                  {
                    id: `${evt.vendor}-${evt.round}-${evt.role}-${v.messages.length}`,
                    round: evt.round,
                    role: evt.role,
                    text: evt.text,
                    offer: evt.offer,
                  },
                ],
              },
            };
          });
          break;
        case "negotiation_complete":
          upsertVendor(evt.vendor, {
            status: evt.outcome,
            finalPrice: evt.final_price,
            savings: evt.savings,
            rounds: evt.rounds,
            summary: evt.summary,
          });
          break;
        case "all_complete":
          setTotalSavings(evt.total_savings);
          setPhase("done");
          esRef.current?.close();
          break;
        case "error":
          setError(evt.message);
          setPhase("error");
          esRef.current?.close();
          break;
        default:
          break;
      }
    },
    [upsertVendor]
  );

  const start = useCallback(async () => {
    if (phase === "running") return;
    setVendors({});
    setTotalSavings(null);
    setError(null);
    setPhase("running");

    // Open SSE stream first, then trigger the run
    const es = new EventSource("/api/stream");
    esRef.current = es;
    es.onmessage = (e) => {
      try {
        handleEvent(JSON.parse(e.data));
      } catch {
        /* ignore keepalives */
      }
    };
    es.onerror = () => {
      // Stream closes normally on completion; only flag if still running
      setPhase((p) => (p === "running" ? "error" : p));
    };

    try {
      await fetch("/api/start", { method: "POST" });
    } catch (err) {
      setError(String(err));
      setPhase("error");
      es.close();
    }
  }, [phase, handleEvent]);

  return {
    vendors: Object.values(vendors),
    totalSavings,
    phase,
    error,
    start,
  };
}
