import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";

const ContactSchema = z.object({
  name: z.string().trim().min(1).max(100),
  email: z.string().trim().email().max(255),
  message: z.string().trim().min(1).max(2000),
});

const TO_EMAIL = "toribiokazu@gmail.com";

export const Route = createFileRoute("/api/contact")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        try {
          const body = await request.json();
          const parsed = ContactSchema.safeParse(body);
          if (!parsed.success) {
            return Response.json(
              { error: "Invalid input", details: parsed.error.flatten() },
              { status: 400 },
            );
          }
          const { name, email, message } = parsed.data;

          const apiKey = process.env.RESEND_API_KEY;
          if (!apiKey) {
            console.error("[/api/contact] RESEND_API_KEY missing");
            return Response.json({ error: "Email service not configured" }, { status: 500 });
          }

          const safe = (s: string) =>
            s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));

          const html = `
            <div style="font-family:Arial,sans-serif;color:#111;line-height:1.6">
              <h2 style="margin:0 0 12px">New portfolio contact</h2>
              <p><strong>Name:</strong> ${safe(name)}</p>
              <p><strong>Email:</strong> ${safe(email)}</p>
              <p><strong>Message:</strong></p>
              <p style="white-space:pre-wrap;background:#f6f6f6;padding:12px;border-radius:8px">${safe(message)}</p>
            </div>`;

          const res = await fetch("https://api.resend.com/emails", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${apiKey}`,
            },
            body: JSON.stringify({
              from: "Portfolio Contact <onboarding@resend.dev>",
              to: [TO_EMAIL],
              reply_to: email,
              subject: `Portfolio inquiry from ${name}`,
              html,
              text: `From: ${name} <${email}>\n\n${message}`,
            }),
          });

          if (!res.ok) {
            const errBody = await res.text();
            console.error("[/api/contact] Resend error:", res.status, errBody);
            return Response.json({ error: "Failed to send email" }, { status: 502 });
          }

          return Response.json({ ok: true });
        } catch (e) {
          console.error("[/api/contact] Unhandled error:", e);
          return Response.json({ error: "Server error" }, { status: 500 });
        }
      },
    },
  },
});
