// Safe to embed inside a <script type="application/ld+json"> tag — escapes
// "<" so a value containing "</script>" can't break out of the tag.
export function jsonLdScript(data: unknown): string {
  return JSON.stringify(data).replace(/</g, "\\u003c");
}
