import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport, type UIMessage } from "ai";
import { useEffect, useRef, useState } from "react";
import { MessageCircle, Send, X, Calendar } from "lucide-react";
import kazuAvatar from "@/assets/kazu-profile.png.asset.json";

const SUGGESTIONS = [
  "Give me a summary of Kazu",
  "What services does Kazu offer?",
  "Show me his recent projects",
  "Book a discovery call",
];

function FollowingAvatar({ size = 48 }: { size?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      const el = ref.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      const cy = r.top + r.height / 2;
      const dx = e.clientX - cx;
      const dy = e.clientY - cy;
      const dist = Math.hypot(dx, dy) || 1;
      const max = 6;
      const m = Math.min(dist / 80, 1) * max;
      setOffset({ x: (dx / dist) * m, y: (dy / dist) * m });
    };
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, []);

  return (
    <div
      ref={ref}
      className="relative shrink-0 overflow-hidden rounded-full border-2 border-primary/40 shadow-lg"
      style={{ width: size, height: size, background: "var(--gradient-amber)" }}
    >
      <img
        src={kazuAvatar.url}
        alt="Kazu"
        className="absolute inset-0 h-full w-full object-cover transition-transform duration-150 ease-out"
        style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(1.1)` }}
      />
    </div>
  );
}

export default function PortfolioChat() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const panelRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const transport = useRef(new DefaultChatTransport({ api: "/api/chat" })).current;
  const { messages, sendMessage, status } = useChat({ transport });

  const isLoading = status === "submitted" || status === "streaming";

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, status]);

  // gradient that follows mouse inside panel
  useEffect(() => {
    const el = panelRef.current;
    if (!el || !open) return;
    const onMove = (e: MouseEvent) => {
      const r = el.getBoundingClientRect();
      el.style.setProperty("--mx", `${e.clientX - r.left}px`);
      el.style.setProperty("--my", `${e.clientY - r.top}px`);
    };
    el.addEventListener("mousemove", onMove);
    return () => el.removeEventListener("mousemove", onMove);
  }, [open]);

  const send = (text: string) => {
    const t = text.trim();
    if (!t || isLoading) return;
    void sendMessage({ text: t });
    setInput("");
  };

  const renderText = (m: UIMessage) =>
    m.parts.map((p, i) =>
      p.type === "text" ? <span key={i} className="whitespace-pre-wrap">{p.text}</span> : null
    );

  return (
    <>
      {/* Launcher */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          aria-label="Open chat"
          className="fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-full bg-card border border-border pl-2 pr-5 py-2 shadow-xl hover:shadow-2xl transition-all hover:-translate-y-0.5"
        >
          <FollowingAvatar size={40} />
          <span className="text-sm font-semibold">Chat with Kazu</span>
          <span className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-primary animate-pulse" />
        </button>
      )}

      {/* Panel */}
      {open && (
        <div
          ref={panelRef}
          className="fixed bottom-6 right-6 z-50 w-[min(380px,calc(100vw-3rem))] h-[min(560px,calc(100vh-3rem))] flex flex-col rounded-2xl border border-border bg-card shadow-2xl overflow-hidden"
          style={{
            backgroundImage:
              "radial-gradient(360px circle at var(--mx,50%) var(--my,50%), oklch(0.78 0.17 65 / 0.22), transparent 60%)",
          }}
        >
          {/* Header */}
          <div className="flex items-center gap-3 border-b border-border bg-card/80 backdrop-blur px-4 py-3">
            <FollowingAvatar size={44} />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold">Kazu's Assistant</div>
              <div className="text-xs text-muted-foreground flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-green-500" /> Online
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              aria-label="Close chat"
              className="grid h-8 w-8 place-items-center rounded-full hover:bg-muted transition"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
            {messages.length === 0 && (
              <div className="space-y-3">
                <div className="rounded-2xl rounded-tl-sm bg-muted px-3 py-2 text-sm max-w-[85%]">
                  Hi! I'm Kazu's portfolio assistant. Ask me anything about his work, services, or book a discovery call. 👋
                </div>
                <div className="text-xs text-muted-foreground pt-1">Try one of these:</div>
                <div className="flex flex-wrap gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="text-xs rounded-full border border-border bg-background px-3 py-1.5 hover:border-primary/50 hover:text-foreground transition"
                    >
                      {s}
                    </button>
                  ))}
                </div>
                <a
                  href="https://calendly.com/toribiokazu/discovery-call"
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:opacity-90 transition"
                >
                  <Calendar className="h-3.5 w-3.5" /> Book a discovery call
                </a>
              </div>
            )}

            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                    m.role === "user"
                      ? "bg-primary text-primary-foreground rounded-tr-sm"
                      : "bg-muted text-foreground rounded-tl-sm"
                  }`}
                >
                  {renderText(m)}
                </div>
              </div>
            ))}

            {isLoading && messages[messages.length - 1]?.role === "user" && (
              <div className="flex justify-start">
                <div className="bg-muted rounded-2xl rounded-tl-sm px-3 py-2 text-sm">
                  <span className="inline-flex gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-foreground/40 animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="h-1.5 w-1.5 rounded-full bg-foreground/40 animate-bounce" style={{ animationDelay: "120ms" }} />
                    <span className="h-1.5 w-1.5 rounded-full bg-foreground/40 animate-bounce" style={{ animationDelay: "240ms" }} />
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Quick action */}
          {messages.length > 0 && (
            <div className="px-4 pb-2">
              <a
                href="https://calendly.com/toribiokazu/discovery-call"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-xs rounded-full border border-primary/40 bg-primary/10 text-primary px-3 py-1 hover:bg-primary/20 transition"
              >
                <Calendar className="h-3 w-3" /> Book a discovery call
              </a>
            </div>
          )}

          {/* Composer */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="border-t border-border bg-card/80 backdrop-blur p-3 flex items-center gap-2"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about Kazu's work..."
              disabled={isLoading}
              className="flex-1 rounded-full border border-input bg-background px-4 py-2 text-sm outline-none focus:border-primary transition disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              aria-label="Send"
              className="grid h-9 w-9 place-items-center rounded-full bg-primary text-primary-foreground hover:opacity-90 transition disabled:opacity-40"
            >
              <Send className="h-4 w-4" />
            </button>
            <button
              type="button"
              aria-label="Chat info"
              className="hidden"
            >
              <MessageCircle />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
