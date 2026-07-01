import { useEffect } from "react";

const CALENDLY_SRC = "https://assets.calendly.com/assets/external/widget.js";
const CALENDLY_URL =
  "https://calendly.com/toribiokazu/discovery-call?hide_event_type_details=1&hide_gdpr_banner=1";

export default function CalendlyEmbed() {
  useEffect(() => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${CALENDLY_SRC}"]`,
    );
    if (existing) {
      // If widget global exists, re-init any uninitialized embeds.
      const w = window as unknown as { Calendly?: { initInlineWidgets?: () => void } };
      w.Calendly?.initInlineWidgets?.();
      return;
    }
    const script = document.createElement("script");
    script.src = CALENDLY_SRC;
    script.async = true;
    document.body.appendChild(script);
  }, []);

  return (
    <div className="reveal rounded-2xl border border-border bg-card overflow-hidden shadow-[var(--shadow-card)]">
      <div
        className="calendly-inline-widget"
        data-url={CALENDLY_URL}
        style={{ minWidth: 320, height: 700 }}
      />
    </div>
  );
}
