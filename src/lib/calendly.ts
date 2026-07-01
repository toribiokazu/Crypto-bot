const CALENDLY_URL = "https://calendly.com/toribiokazu/discovery-call";
const CALENDLY_SCRIPT_SRC = "https://assets.calendly.com/assets/external/widget.js";
const CALENDLY_CSS_HREF = "https://assets.calendly.com/assets/external/widget.css";

declare global {
  interface Window {
    Calendly?: {
      initPopupWidget?: (options: { url: string }) => void;
      initInlineWidgets?: () => void;
    };
  }
}

function ensureCalendlyAssets() {
  if (!document.querySelector(`link[href="${CALENDLY_CSS_HREF}"]`)) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = CALENDLY_CSS_HREF;
    document.head.appendChild(link);
  }

  return new Promise<void>((resolve) => {
    if (window.Calendly?.initPopupWidget) {
      resolve();
      return;
    }
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${CALENDLY_SCRIPT_SRC}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = CALENDLY_SCRIPT_SRC;
    script.async = true;
    script.addEventListener("load", () => resolve(), { once: true });
    document.body.appendChild(script);
  });
}

export function openCalendlyPopup() {
  void ensureCalendlyAssets().then(() => {
    window.Calendly?.initPopupWidget?.({ url: CALENDLY_URL });
  });
}
