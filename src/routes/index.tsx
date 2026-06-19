import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState, useCallback } from "react";
import {
  Mail, Phone, MapPin, Sparkles, Workflow, Megaphone, Database,
  Globe, PenTool, ArrowRight, Quote, Award, Briefcase, ExternalLink,
  Github, Linkedin, Sun, Moon, ChevronLeft, ChevronRight,
} from "lucide-react";


export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Kazu Toribio — AI Automation Innovation Specialist" },
      { name: "description", content: "Portfolio of Kazu Toribio: AI Automation Innovation Specialist with 5+ years building workflows, CRM systems, and marketing automation." },
      { property: "og:title", content: "Kazu Toribio — AI Automation Innovation Specialist" },
      { property: "og:description", content: "AI workflows, CRM, and marketing systems that save time and drive results." },
    ],
  }),
  component: Portfolio,
});

const services = [
  { icon: Sparkles, title: "AI Automation", desc: "Build intelligent workflows with n8n, Make, Zapier, and OpenAI to eliminate repetitive work." },
  { icon: Megaphone, title: "Sales & Marketing", desc: "Run campaigns, manage leads, and grow audiences across email and social channels." },
  { icon: Database, title: "CRM Management", desc: "Configure and maintain Zoho, GoHighLevel, Brivity, and KW Command for clean pipelines." },
  { icon: Globe, title: "Web & Landing Pages", desc: "Design and manage WordPress sites, blogs, and high-converting landing pages." },
  { icon: PenTool, title: "Content & Design", desc: "Create flyers, decks, newsletters, and social media graphics using Canva and Adobe." },
  { icon: Workflow, title: "Process & SOPs", desc: "Document workflows, build process maps, and standardize operations end-to-end." },
];

const experience = [
  {
    company: "AI Automation Innovation Specialist",
    role: "Sales & Marketing Assistant · AI Automation",
    period: "2025 — Present",
    points: [
      "Support sales & marketing operations through campaigns, lead tracking, and customer engagement.",
      "Maintain WordPress sites, landing pages, and product content.",
      "Implement AI-powered automations using n8n, Make, Zapier, Airtable, and GoHighLevel.",
      "Build SOPs, workflow documentation, and process maps for the team.",
    ],
  },
  {
    company: "Technical Virtual Assistant",
    role: "Marketing Assistant · Technical VA",
    period: "2021 — 2025",
    points: [
      "Managed social media, content, Facebook ads, and customer inquiries.",
      "Handled email campaigns, CRM databases, and lead management.",
      "Produced flyers, banners, presentations, and analytics reports.",
      "Managed websites, landing pages, blogs, and CRM integrations.",
    ],
  },
];

const works = [
  { title: "AI Lead Routing Workflow", tag: "n8n · GoHighLevel", desc: "Automated qualification and assignment of inbound leads, cutting response time by 80%." },
  { title: "Email Nurture System", tag: "Mailchimp · Airtable", desc: "Multi-touch nurture sequences with audience segmentation and dynamic content." },
  { title: "WordPress Product Site", tag: "WordPress · SEO", desc: "Redesigned product website with optimized landing pages and CRM-connected forms." },
  { title: "Social Campaign Suite", tag: "Canva · Meta Ads", desc: "Full set of branded creatives, flyers, and ad assets for a monthly campaign rollout." },
  { title: "CRM Migration & Cleanup", tag: "Zoho · GoHighLevel", desc: "Migrated 10k+ contacts, restructured pipelines, and trained the team on new workflows." },
  { title: "AI Content Pipeline", tag: "ChatGPT · Make", desc: "End-to-end content generation, review, and publishing pipeline with human-in-the-loop." },
];

const testimonials = [
  { name: "Marco", quote: "Kazu is spectacular in every way. He is polite and attentive, eager to jump on tasks, and an asset in all aspects of our team." },
  { name: "Jenna", quote: "Working with Kazu has significantly improved our workflow efficiency. His expertise in automation, lead management, and digital marketing has saved us countless hours." },
  { name: "Daniel", quote: "Reliable, resourceful, and highly skilled in managing websites, CRM systems, and marketing campaigns. He always exceeds expectations." },
  { name: "Priya", quote: "Kazu helped transform our manual workflows into automated systems, improving accuracy and saving valuable time across our organization." },
  { name: "Liam", quote: "Professional, detail-oriented, and results-driven. Kazu consistently delivers quality work with excellent communication." },
];

const skills = [
  "n8n", "Make", "Zapier", "Airtable", "GoHighLevel", "ChatGPT", "OpenAI",
  "Zoho CRM", "Brivity", "KW Command", "WordPress", "Canva", "Adobe Photoshop",
  "After Effects", "Google Analytics", "DocuSign", "Calendly", "RingCentral",
];

function TestimonialCarousel() {
  const [active, setActive] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  const next = useCallback(() => {
    setActive((prev) => (prev + 1) % testimonials.length);
  }, []);

  const prev = useCallback(() => {
    setActive((prev) => (prev - 1 + testimonials.length) % testimonials.length);
  }, []);

  useEffect(() => {
    if (isPaused) return;
    const id = setInterval(next, 5000);
    return () => clearInterval(id);
  }, [isPaused, next]);

  return (
    <div
      className="mt-12 relative"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <div className="overflow-hidden rounded-2xl">
        <div
          className="flex transition-transform duration-700 ease-[cubic-bezier(0.22,1,0.36,1)]"
          style={{ transform: `translateX(-${active * 100}%)` }}
        >
          {testimonials.map((t, i) => (
            <figure
              key={i}
              className="w-full shrink-0 card-elevated rounded-2xl p-8 md:p-10"
            >
              <Quote className="h-8 w-8 text-primary/60" />
              <blockquote className="mt-4 text-base md:text-lg leading-relaxed text-foreground/90">
                "{t.quote}"
              </blockquote>
              <figcaption className="mt-6 flex items-center gap-3 border-t border-border pt-4">
                <div className="grid h-10 w-10 place-items-center rounded-full bg-primary/10 text-primary font-semibold">
                  {t.name[0]}
                </div>
                <div className="text-sm font-semibold">{t.name}</div>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>

      {/* Arrows */}
      <button
        onClick={prev}
        className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-3 md:-translate-x-5 grid h-10 w-10 place-items-center rounded-full border border-border bg-card shadow-md hover:border-primary/50 transition"
        aria-label="Previous testimonial"
      >
        <ChevronLeft className="h-5 w-5" />
      </button>
      <button
        onClick={next}
        className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-3 md:translate-x-5 grid h-10 w-10 place-items-center rounded-full border border-border bg-card shadow-md hover:border-primary/50 transition"
        aria-label="Next testimonial"
      >
        <ChevronRight className="h-5 w-5" />
      </button>

      {/* Dots */}
      <div className="mt-6 flex items-center justify-center gap-2">
        {testimonials.map((_, i) => (
          <button
            key={i}
            onClick={() => setActive(i)}
            className={`h-2 rounded-full transition-all duration-300 ${
              i === active ? "w-6 bg-primary" : "w-2 bg-border hover:bg-primary/50"
            }`}
            aria-label={`Go to testimonial ${i + 1}`}
          />
        ))}
      </div>
    </div>
  );
}

function Logo() {
  return (
    <a href="#top" className="group inline-flex items-center gap-2">
      <span className="grid h-9 w-9 place-items-center rounded-lg text-primary-foreground font-display text-lg font-bold transition-transform group-hover:rotate-6" style={{ background: "var(--gradient-amber)" }}>
        K
      </span>
      <span className="font-display text-lg font-semibold tracking-tight">
        Kazu<span className="text-primary">.</span>Toribio
      </span>
    </a>
  );
}

function useTheme() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  useEffect(() => {
    const stored = (typeof localStorage !== "undefined" && localStorage.getItem("theme")) as "light" | "dark" | null;
    const initial = stored ?? "light";
    setTheme(initial);
    document.documentElement.classList.toggle("dark", initial === "dark");
  }, []);
  const toggle = () => {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    document.documentElement.classList.toggle("dark", next === "dark");
    localStorage.setItem("theme", next);
  };
  return { theme, toggle };
}

function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      onClick={toggle}
      aria-label="Toggle theme"
      className="ripple grid h-9 w-9 place-items-center rounded-full border border-border bg-card hover:border-primary/50 transition"
      onMouseDown={addRipple}
    >
      {theme === "light" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
    </button>
  );
}

function addRipple(e: React.MouseEvent<HTMLElement>) {
  const el = e.currentTarget;
  const rect = el.getBoundingClientRect();
  el.style.setProperty("--rx", `${e.clientX - rect.left}px`);
  el.style.setProperty("--ry", `${e.clientY - rect.top}px`);
  el.classList.remove("is-rippling");
  // force reflow
  void el.offsetWidth;
  el.classList.add("is-rippling");
  setTimeout(() => el.classList.remove("is-rippling"), 600);
}

function useReveal() {
  useEffect(() => {
    const els = document.querySelectorAll(".reveal");
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
}

function Portfolio() {
  useReveal();
  return (
    <div id="top" className="min-h-screen bg-background text-foreground">
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />

      {/* NAV */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-background/70 border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Logo />
          <nav className="hidden md:flex items-center gap-8 text-sm text-muted-foreground">
            <a href="#services" className="hover:text-foreground transition-colors">Services</a>
            <a href="#experience" className="hover:text-foreground transition-colors">Experience</a>
            <a href="#works" className="hover:text-foreground transition-colors">Works</a>
            <a href="#testimonials" className="hover:text-foreground transition-colors">Testimonials</a>
            <a href="#contact" className="hover:text-foreground transition-colors">Contact</a>
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <a href="#contact" onMouseDown={addRipple} className="ripple hidden md:inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 transition">
              Hire me <ArrowRight className="h-4 w-4" />
            </a>
          </div>
        </div>
      </header>

      {/* HERO */}
      <section className="relative bg-hero-glow overflow-hidden">
        <div className="mx-auto max-w-6xl px-6 pt-20 pb-28 grid gap-12 lg:grid-cols-[1.4fr_1fr] items-center">
          <div className="reveal">
            <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card/70 px-4 py-1.5 text-xs text-muted-foreground">
              <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
              Available for new projects
            </div>
            <h1 className="mt-6 font-display text-5xl sm:text-6xl md:text-7xl font-bold leading-[1.05]">
              I build <span className="text-gradient">AI workflows</span> and marketing systems that actually save you time.
            </h1>
            <p className="mt-6 max-w-2xl text-lg text-muted-foreground">
              Hi, I'm Kazu — an AI Automation Innovation Specialist with 5+ years of experience in CRM management, campaign execution, and process automation.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a href="https://calendly.com/toribiokazu/discovery-call" target="_blank" rel="noreferrer" onMouseDown={addRipple} className="ripple inline-flex items-center gap-2 rounded-full bg-primary px-6 py-3 font-semibold text-primary-foreground hover:opacity-90 transition" style={{ boxShadow: "var(--shadow-glow)" }}>
                Book a discovery call <ArrowRight className="h-4 w-4" />
              </a>
              <a href="#works" onMouseDown={addRipple} className="ripple inline-flex items-center gap-2 rounded-full border border-border bg-card px-6 py-3 font-semibold hover:border-primary/50 transition">
                View my work
              </a>
              <a href="#contact" onMouseDown={addRipple} className="ripple inline-flex items-center gap-2 rounded-full border border-border bg-card px-6 py-3 font-semibold hover:border-primary/50 transition">
                Get in touch
              </a>
            </div>
          </div>

          <div className="reveal relative mx-auto" style={{ perspective: "1200px" }}>
            {/* Color splash layers behind photo */}
            <div className="absolute -inset-12 rounded-[3rem] blur-[80px] opacity-60 pointer-events-none"
              style={{ background: "radial-gradient(circle at 25% 25%, oklch(0.78 0.22 55), transparent 55%), radial-gradient(circle at 75% 75%, oklch(0.72 0.20 35), transparent 55%), radial-gradient(circle at 50% 50%, oklch(0.80 0.18 75), transparent 50%)" }} />
            <div className="absolute -inset-6 rounded-[2.5rem] blur-[50px] opacity-50 pointer-events-none"
              style={{ background: "conic-gradient(from 180deg at 50% 50%, oklch(0.78 0.17 65), oklch(0.70 0.18 30), oklch(0.75 0.16 55), oklch(0.78 0.17 65))" }} />

            <div className="relative animate-float group" style={{ transformStyle: "preserve-3d" }}>
              {/* 3D tilted frame */}
              <div className="rounded-[2rem] p-1.5 transition-transform duration-500 ease-out hover:[transform:rotateY(-8deg)_rotateX(5deg)_scale(1.02)]"
                style={{ background: "var(--gradient-amber)", transformStyle: "preserve-3d" }}>
                <img
                  src="/kazu-hero.png"
                  alt="Kazu Toribio"
                  style={{ width: "300px", height: "auto" }}
                />
              </div>
              {/* Floating badge */}
              <div className="absolute -bottom-4 -left-4 rounded-2xl bg-card border border-border px-4 py-3 shadow-xl transition-transform duration-500 ease-out group-hover:translate-z-[40px]"
                style={{ transform: "translateZ(30px)", transformStyle: "preserve-3d" }}>
                <div className="text-xs text-muted-foreground">Specialist</div>
                <div className="text-sm font-semibold">AI Automation</div>
              </div>
            </div>
          </div>
        </div>

        <div className="mx-auto max-w-6xl px-6 pb-20 grid grid-cols-2 md:grid-cols-4 gap-6">
          {[
            { k: "5+", v: "Years experience" },
            { k: "50+", v: "Workflows automated" },
            { k: "10k+", v: "Leads managed" },
            { k: "100%", v: "Client satisfaction" },
          ].map((s) => (
            <div key={s.v} className="reveal card-elevated rounded-2xl p-5">
              <div className="font-display text-3xl font-bold text-gradient">{s.k}</div>
              <div className="mt-1 text-sm text-muted-foreground">{s.v}</div>
            </div>
          ))}
        </div>
      </section>

      {/* SERVICES */}
      <section id="services" className="mx-auto max-w-6xl px-6 py-24">
        <SectionHeader eyebrow="Services" title="What I can do for you" />
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {services.map((s) => (
            <div key={s.title} onMouseDown={addRipple} className="reveal ripple card-elevated rounded-2xl p-6 cursor-pointer">
              <div className="grid h-12 w-12 place-items-center rounded-xl bg-primary/10 text-primary">
                <s.icon className="h-6 w-6" />
              </div>
              <h3 className="mt-5 text-xl font-semibold">{s.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* EXPERIENCE */}
      <section id="experience" className="border-y border-border bg-card/40">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <SectionHeader eyebrow="Work Experience" title="Where I've made an impact" />
          <div className="mt-12 space-y-6">
            {experience.map((e) => (
              <div key={e.company} className="reveal card-elevated rounded-2xl p-8 grid gap-6 md:grid-cols-[1fr_2fr]">
                <div>
                  <div className="inline-flex items-center gap-2 text-xs text-primary font-medium">
                    <Briefcase className="h-4 w-4" /> {e.period}
                  </div>
                  <h3 className="mt-3 font-display text-2xl font-bold">{e.company}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{e.role}</p>
                </div>
                <ul className="space-y-3">
                  {e.points.map((p) => (
                    <li key={p} className="flex gap-3 text-sm text-muted-foreground">
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                      <span>{p}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="reveal mt-10 flex flex-wrap gap-2">
            {skills.map((s) => (
              <span key={s} className="rounded-full border border-border bg-background px-3 py-1.5 text-xs text-muted-foreground hover:border-primary/50 hover:text-foreground transition">
                {s}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* WORKS */}
      <section id="works" className="mx-auto max-w-6xl px-6 py-24">
        <SectionHeader eyebrow="Previous Works" title="Selected projects & systems" />
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {works.map((w, i) => (
            <article key={w.title} onMouseDown={addRipple} className="reveal ripple card-elevated group rounded-2xl overflow-hidden cursor-pointer">
              <div className="relative aspect-[4/3] overflow-hidden" style={{ background: `linear-gradient(135deg, oklch(0.${75+i} 0.${12+i} ${40+i*40}), oklch(0.85 0.08 ${260-i*30}))` }}>
                <div className="absolute inset-0 grid place-items-center font-display text-6xl font-bold text-foreground/15">
                  {String(i + 1).padStart(2, "0")}
                </div>
              </div>
              <div className="p-6">
                <div className="text-xs font-medium text-primary">{w.tag}</div>
                <h3 className="mt-2 text-lg font-semibold">{w.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{w.desc}</p>
              </div>
            </article>
          ))}
        </div>
        <div className="mt-10 text-center">
          <a href="https://drive.google.com/file/d/1hD7lsTcMsGr2B9_wW-Rg7BTqrG_upjgg/view" target="_blank" rel="noreferrer" onMouseDown={addRipple} className="ripple inline-flex items-center gap-2 rounded-full border border-border bg-card px-6 py-3 font-semibold hover:border-primary/50 transition">
            View full portfolio <ExternalLink className="h-4 w-4" />
          </a>
        </div>
      </section>

      {/* TESTIMONIALS */}
      <section id="testimonials" className="border-y border-border bg-card/40">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <SectionHeader eyebrow="Testimonials" title="What clients say" />
          <TestimonialCarousel />

          <div className="mt-12 flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <Award className="h-4 w-4 text-primary" />
            Google Analytics Advanced Certified · Best in Web Designing Awardee
          </div>
        </div>
      </section>

      {/* CONTACT */}
      <section id="contact" className="mx-auto max-w-6xl px-6 py-24">
        <SectionHeader eyebrow="Contact" title="Let's build something great" />
        <div className="mt-12 grid gap-10 lg:grid-cols-2">
          <div className="reveal">
            <p className="text-lg text-muted-foreground leading-relaxed">
              Have a workflow to automate, a campaign to launch, or a CRM to clean up?
              Send me a message — I usually reply within a day.
            </p>
            <div className="mt-8 space-y-4">
              <ContactRow icon={Mail} label="Email" value="toribiokazu@gmail.com" href="mailto:toribiokazu@gmail.com" />
              <ContactRow icon={Phone} label="Phone" value="+63 956 897 1143" href="tel:+639568971143" />
              <ContactRow icon={MapPin} label="Location" value="Naic, Cavite, Philippines" />
            </div>
            <a href="https://calendly.com/toribiokazu/discovery-call" target="_blank" rel="noreferrer" onMouseDown={addRipple} className="ripple mt-6 inline-flex items-center gap-2 rounded-full bg-primary px-6 py-3 font-semibold text-primary-foreground hover:opacity-90 transition" style={{ boxShadow: "var(--shadow-glow)" }}>
              Book a discovery call <ArrowRight className="h-4 w-4" />
            </a>
          </div>

          <form className="reveal card-elevated rounded-2xl p-6 space-y-4" onSubmit={(e) => { e.preventDefault(); window.location.href = `mailto:toribiokazu@gmail.com`; }}>
            <Field label="Name" type="text" placeholder="Your name" />
            <Field label="Email" type="email" placeholder="you@email.com" />
            <div>
              <label className="text-xs font-medium text-muted-foreground">Message</label>
              <textarea rows={5} className="mt-1.5 w-full rounded-lg border border-input bg-background px-4 py-3 text-sm outline-none focus:border-primary transition" placeholder="Tell me about your project..." />
            </div>
            <button type="submit" onMouseDown={addRipple} className="ripple w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-6 py-3 font-semibold text-primary-foreground hover:opacity-90 transition">
              Send message <ArrowRight className="h-4 w-4" />
            </button>
          </form>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-border">
        <div className="mx-auto max-w-6xl px-6 py-10 flex flex-col md:flex-row items-center justify-between gap-4">
          <Logo />
          <p className="text-xs text-muted-foreground">© {new Date().getFullYear()} Kazu Toribio. Crafted with care.</p>
          <div className="flex items-center gap-3 text-muted-foreground">
            <a href="mailto:toribiokazu@gmail.com" className="hover:text-primary"><Mail className="h-4 w-4" /></a>
            <a href="#" className="hover:text-primary"><Linkedin className="h-4 w-4" /></a>
            <a href="#" className="hover:text-primary"><Github className="h-4 w-4" /></a>
          </div>
        </div>
      </footer>
    </div>
  );
}

function SectionHeader({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div className="reveal max-w-2xl">
      <div className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">{eyebrow}</div>
      <h2 className="mt-3 font-display text-4xl sm:text-5xl font-bold">{title}</h2>
    </div>
  );
}

function ContactRow({ icon: Icon, label, value, href }: { icon: any; label: string; value: string; href?: string }) {
  const Wrap: any = href ? "a" : "div";
  return (
    <Wrap href={href} className="flex items-center gap-4 rounded-xl border border-border bg-card p-4 hover:border-primary/50 transition">
      <div className="grid h-11 w-11 place-items-center rounded-lg bg-primary/10 text-primary">
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="text-sm font-medium">{value}</div>
      </div>
    </Wrap>
  );
}

function Field({ label, type, placeholder }: { label: string; type: string; placeholder: string }) {
  return (
    <div>
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      <input type={type} placeholder={placeholder} className="mt-1.5 w-full rounded-lg border border-input bg-background px-4 py-3 text-sm outline-none focus:border-primary transition" />
    </div>
  );
}
