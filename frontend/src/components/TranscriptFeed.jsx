import { useEffect, useRef } from "react";
import { Building2, ShoppingCart } from "lucide-react";

const fmt = (n) =>
  n == null || n < 0 ? null : `$${Number(n).toLocaleString("en-US")}`;

// Static class maps so Tailwind's JIT can see them (no dynamic interpolation).
const ROLE = {
  procurement: {
    Icon: ShoppingCart,
    label: "Procurement",
    head: "text-procurement",
    bubble: "border-procurement/20 bg-procurement/[0.06]",
  },
  vendor: {
    Icon: Building2,
    label: "Vendor",
    head: "text-vendor",
    bubble: "border-vendor/20 bg-vendor/[0.06]",
  },
};

function MessageRow({ msg }) {
  const role = ROLE[msg.role] ?? ROLE.vendor;
  const { Icon } = role;
  const price = msg.offer ? fmt(msg.offer.price) : null;

  return (
    <div className="animate-fade-up">
      <div
        className={`flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide ${role.head}`}
      >
        <Icon className="h-3.5 w-3.5" aria-hidden="true" />
        <span>
          R{msg.round} · {role.label}
        </span>
      </div>
      <div
        className={`mt-1 rounded-xl border p-3 text-sm leading-relaxed text-white/85 ${role.bubble}`}
      >
        <p className="whitespace-pre-wrap">{msg.text}</p>
        {price && (
          <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-white/10 pt-2 text-xs text-white/70">
            <span className="tnum font-semibold text-white">{price}</span>
            {msg.offer?.seats != null && msg.offer.seats > 0 && (
              <span className="tnum">· {msg.offer.seats} seats</span>
            )}
            {msg.offer?.term_months && (
              <span className="tnum">· {msg.offer.term_months}mo</span>
            )}
            {msg.offer?.notes && (
              <span className="italic text-white/50">· {msg.offer.notes}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function TranscriptFeed({ messages }) {
  const endRef = useRef(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length]);

  if (!messages.length) {
    return (
      <div className="flex h-full min-h-[8rem] items-center justify-center text-sm text-white/40">
        Waiting for first offer…
      </div>
    );
  }

  return (
    <div className="scroll-thin flex max-h-[26rem] flex-col gap-3 overflow-y-auto pr-1">
      {messages.map((m) => (
        <MessageRow key={m.id} msg={m} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
