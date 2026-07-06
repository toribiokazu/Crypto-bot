import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { ArrowLeft, Github, ExternalLink } from "lucide-react";
import { works } from "@/lib/works";
import { useTheme } from "@/lib/useTheme";

export const Route = createFileRoute("/projects/$slug")({
  loader: ({ params }) => {
    const work = works.find((w) => w.slug === params.slug);
    if (!work) throw notFound();
    return work;
  },
  head: ({ loaderData }) => {
    if (!loaderData) return {};
    const title = `${loaderData.title} — Kazu Toribio`;
    const url = `https://toribiokazu.vercel.app/projects/${loaderData.slug}`;
    return {
      meta: [
        { title },
        { name: "description", content: loaderData.desc },
        { property: "og:title", content: title },
        { property: "og:description", content: loaderData.desc },
        { property: "og:url", content: url },
        ...(loaderData.image
          ? [{ property: "og:image", content: `https://toribiokazu.vercel.app${loaderData.image}` }]
          : []),
      ],
      links: [{ rel: "canonical", href: url }],
    };
  },
  component: ProjectPage,
});

function ProjectPage() {
  const work = Route.useLoaderData();
  useTheme();

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CreativeWork",
    name: work.title,
    description: work.desc,
    author: { "@type": "Person", name: "Kazu Toribio", url: "https://toribiokazu.vercel.app/" },
    keywords: work.tag,
    ...(work.url ? { codeRepository: work.url } : {}),
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <header className="sticky top-0 z-50 backdrop-blur-xl bg-background/70 border-b border-border">
        <div className="mx-auto flex max-w-3xl items-center px-6 py-4">
          <Link to="/" hash="works" className="inline-flex items-center gap-2 text-sm font-semibold hover:text-primary transition">
            <ArrowLeft className="h-4 w-4" /> Back to all projects
          </Link>
        </div>
      </header>

      <article className="mx-auto max-w-3xl px-6 py-16">
        {work.image && (
          <div className="relative w-full overflow-hidden rounded-2xl border border-border bg-card">
            <img src={work.image} alt={`${work.title} workflow preview`} className="w-full h-auto object-contain" />
          </div>
        )}

        <div className="mt-8 text-xs font-semibold uppercase tracking-[0.18em] text-primary">{work.tag}</div>
        <h1 className="mt-2 font-display text-3xl md:text-4xl font-bold leading-tight">{work.title}</h1>
        <p className="mt-4 text-lg text-muted-foreground leading-relaxed">{work.desc}</p>

        <div className="mt-10 space-y-8">
          <div>
            <h2 className="font-display text-lg font-semibold">The problem</h2>
            <p className="mt-2 text-muted-foreground leading-relaxed">{work.problem}</p>
          </div>
          <div>
            <h2 className="font-display text-lg font-semibold">What I built</h2>
            <p className="mt-2 text-muted-foreground leading-relaxed">{work.build}</p>
          </div>
          <div>
            <h2 className="font-display text-lg font-semibold">The result</h2>
            <p className="mt-2 text-muted-foreground leading-relaxed">{work.result}</p>
          </div>
        </div>

        <div className="mt-10 flex flex-wrap gap-3">
          {work.url && (
            <a
              href={work.url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:opacity-90 transition"
            >
              <Github className="h-4 w-4" /> View on GitHub
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
          <Link
            to="/"
            hash="contact"
            className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-5 py-2.5 text-sm font-semibold hover:border-primary/50 transition"
          >
            Discuss a similar project
          </Link>
        </div>
      </article>
    </div>
  );
}
