export type Work = {
  slug: string;
  title: string;
  tag: string;
  desc: string;
  problem: string;
  build: string;
  result: string;
  image?: string;
  url?: string;
};

export const works: Work[] = [
  {
    slug: "ai-lead-routing-workflow",
    title: "AI Lead Routing Workflow",
    tag: "n8n · GoHighLevel · Groq AI",
    desc: "Webhook-driven n8n workflow that qualifies inbound GHL leads with AI, tags them hot/warm/cold, creates opportunities and tasks, and pings Slack — cutting response time by 80%.",
    problem: "Inbound leads landing in GoHighLevel had no automatic qualification — every lead needed a person to read it, judge how hot it was, and manually create a follow-up task, which slowed down response time.",
    build: "Built a webhook-driven n8n workflow that receives new GHL leads, uses Groq AI to qualify and tag each one hot, warm, or cold, automatically creates the matching opportunity and follow-up task in GoHighLevel, and pings the sales team on Slack the moment a hot lead comes in.",
    result: "Lead response time dropped by 80%, since hot leads are tagged, routed, and flagged to the team automatically instead of waiting for manual triage.",
    image: "/ai-lead-routing.webp",
    url: "https://github.com/toribiokazu/ai-lead-routing-ghl",
  },
  {
    slug: "xero-asana-transaction-export",
    title: "Xero → Asana Transaction Export",
    tag: "Make.com · Xero · Asana · Google Sheets",
    desc: "Make.com scenario that exports Xero account transactions to a CSV via Google Sheets and uploads it back to the originating Asana task as an attachment when marked complete.",
    problem: "Finance transactions from Xero needed to be manually exported and attached to the right Asana task whenever a task was marked complete — a repetitive, error-prone step in the bookkeeping workflow.",
    build: "Built a Make.com scenario that pulls the relevant Xero account transactions, formats them into a CSV via Google Sheets, and automatically uploads the file back onto the originating Asana task the moment it's marked complete.",
    result: "Removed the manual export-and-attach step entirely, so finished tasks always have their transaction records attached automatically and consistently.",
    image: "/xero-asana.webp",
    url: "https://github.com/toribiokazu/xero-asana-transaction-export-automation",
  },
  {
    slug: "email-nurture-system",
    title: "Email Nurture System",
    tag: "Mailchimp · Airtable",
    desc: "Built an automated email nurture system using n8n, Mailchimp, and Airtable to manage subscribers, organize campaigns, eliminate duplicate enrollments, and streamline marketing workflows.",
    problem: "Subscriber and campaign management was manual and prone to duplicate enrollments, making it hard to run consistent, organized nurture campaigns.",
    build: "Built an automated system connecting n8n, Mailchimp, and Airtable to manage subscribers, organize campaign sequences, and check for duplicate enrollments before adding someone to a nurture flow.",
    result: "Marketing campaigns run on a streamlined, duplicate-free subscriber base, cutting down manual list cleanup.",
    image: "/mailchimp-airtable.webp",
    url: "https://github.com/toribiokazu/email-nurture-system",
  },
  {
    slug: "wordpress-product-site",
    title: "WordPress Product Site",
    tag: "WordPress · SEO",
    desc: "Redesigned a WordPress website with optimized landing pages and automated GoHighLevel CRM integration for efficient lead capture and sales automation.",
    problem: "The existing WordPress site wasn't converting visitors into leads efficiently, and there was no CRM automation connecting form submissions to sales follow-up.",
    build: "Redesigned the WordPress site with conversion-focused landing pages and integrated GoHighLevel CRM so every form submission automatically becomes a tracked lead.",
    result: "Lead capture and sales follow-up became automated end-to-end, from the landing page to the CRM pipeline.",
    image: "/Wordpress-GHL.webp",
  },
  {
    slug: "crm-migration-cleanup",
    title: "CRM Migration & Cleanup",
    tag: "Zoho · GoHighLevel",
    desc: "Migrated 10,000+ contacts from Zoho to GoHighLevel, cleaned and standardized CRM data, restructured sales pipelines, and implemented improved workflows for a more efficient sales process.",
    problem: "The business needed to move off Zoho CRM to GoHighLevel, but the existing contact data was inconsistent and the sales pipeline structure no longer matched how the team actually sold.",
    build: "Migrated 10,000+ contacts from Zoho to GoHighLevel, cleaning and standardizing the data during the move, then restructured the sales pipelines and workflows to match the team's actual sales process.",
    result: "The team now runs on a single, clean CRM with pipelines and workflows built around how they actually sell — improving overall efficiency.",
    image: "/zoho-ghl.webp",
  },
  {
    slug: "ai-content-pipeline",
    title: "AI Content Pipeline",
    tag: "ChatGPT · Make",
    desc: "An AI-driven content pipeline built with ChatGPT, n8n, Airtable, Slack, and WordPress that automates content generation, review, approval, and publishing through a structured human-in-the-loop workflow.",
    problem: "Producing and publishing content consistently required manually generating drafts, chasing approvals, and publishing each piece by hand — slow and hard to scale.",
    build: "Built an AI-driven pipeline with ChatGPT, n8n, Airtable, Slack, and WordPress that generates content drafts, routes them through a structured review and approval step with the team in Slack, and publishes approved content to WordPress automatically.",
    result: "Content moves through generation, human review, and publishing as one connected workflow instead of a manual, ad hoc process.",
    image: "/ai-content-pipeline.webp",
    url: "https://github.com/toribiokazu/ai-content-pipeline",
  },
];
