/// <reference lib="deno.ns" />

// ============================================================
// PhotoCleaner - Automatic License Generation Webhook
// ============================================================
// Supabase Edge Function für automatische Lizenz-Erstellung
// Deployed at: https://YOUR_PROJECT.supabase.co/functions/v1/license-webhook
//
// Workflow:
// 1. Stripe sendet Webhook bei erfolgreicher Zahlung
// 2. Edge Function erstellt Lizenz-Key
// 3. Registriert in Supabase licenses Tabelle
// 4. Sendet Email mit Aktivierungs-Link
// ============================================================

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.0";
import { Pool } from "https://deno.land/x/postgres@v0.17.0/mod.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
};

// Stripe Webhook Secret (aus Stripe Dashboard)
const STRIPE_WEBHOOK_SECRET = Deno.env.get("STRIPE_WEBHOOK_SECRET")!;
const STRIPE_ALLOW_MISSING_SIGNATURE =
  Deno.env.get("STRIPE_ALLOW_MISSING_SIGNATURE") === "true";
const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const SUPABASE_DB_URL = Deno.env.get("SUPABASE_DB_URL") || "";
const TEST_EMAIL_OVERRIDE = Deno.env.get("TEST_EMAIL_OVERRIDE") || "";

// Resend API für Email-Versand (alternativ: SendGrid, Mailgun)
const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY") || "";
const RESEND_FROM =
  Deno.env.get("RESEND_FROM") || "PhotoCleaner <onboarding@resend.dev>";

interface PurchaseData {
  email: string;
  name: string;
  plan: "pro" | "enterprise";
  stripe_payment_id: string;
  amount: number;
}

const RETRY_BACKOFF_MS = [500, 1000, 2000, 2000];

serve(async (req) => {
  // CORS Preflight
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    // 1. Verify Stripe Webhook Signature (optional in test mode)
    const signature = req.headers.get("stripe-signature");
    const body = await req.text();
    
    if (!signature) {
      if (!STRIPE_ALLOW_MISSING_SIGNATURE) {
        throw new Error(
          "Missing stripe-signature header. Ensure Stripe Webhook endpoint is used, or set STRIPE_ALLOW_MISSING_SIGNATURE=true for test mode."
        );
      }
      console.warn(
        "stripe-signature header missing; proceeding because STRIPE_ALLOW_MISSING_SIGNATURE=true"
      );
    }

    // Stripe Webhook Verification (vereinfacht für Demo)
    // In Produktion: stripe.webhooks.constructEvent(body, signature, secret)
    const event = JSON.parse(body);

    console.log("Webhook received:", event.type);

    // 2. Handle payment_intent.succeeded event
    if (event.type === "checkout.session.completed") {
      const session = event.data.object;
      
      const email =
        TEST_EMAIL_OVERRIDE ||
        session.customer_email ||
        session.customer_details?.email ||
        "unknown@customer.local";
      const purchaseData: PurchaseData = {
        email,
        name: session.customer_details?.name || "Customer",
        plan: session.metadata?.plan || "pro", // pro oder enterprise
        stripe_payment_id: session.payment_intent,
        amount: session.amount_total / 100, // Cent to Euro
      };

      console.log("Processing purchase:", purchaseData);

      // 3. Generate License Key
      const licenseKey = generateLicenseKey(purchaseData.plan);
      console.log("Generated license key:", licenseKey);

      // 4. Register in Supabase
      const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
        auth: { persistSession: false },
        global: {
          headers: {
            Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`,
          },
        },
      });
      
      const expiresAt = new Date();
      if (purchaseData.plan === "pro") {
        expiresAt.setFullYear(expiresAt.getFullYear() + 1); // 1 Jahr
      } else if (purchaseData.plan === "enterprise") {
        expiresAt.setFullYear(expiresAt.getFullYear() + 2); // 2 Jahre
      }

      const maxDevices = purchaseData.plan === "enterprise" ? 10 : 3;

      let license: Record<string, unknown> | null = null;
      let dbError: { message: string } | null = null;

      for (let attempt = 0; attempt <= RETRY_BACKOFF_MS.length; attempt++) {
        const result = await supabase
          .from("licenses")
          .insert({
            license_id: licenseKey,
            plan: purchaseData.plan,
            status: "active",
            expires_at: expiresAt.toISOString(),
            max_devices: maxDevices,
            assigned_to: purchaseData.email,
            licensee: purchaseData.name,
            stripe_payment_id: purchaseData.stripe_payment_id,
          })
          .select()
          .single();

        if (!result.error) {
          license = result.data as Record<string, unknown>;
          dbError = null;
          break;
        }

        dbError = { message: result.error.message };
        const shouldRetry = result.error.message
          .toLowerCase()
          .includes("schema cache");

        if (!shouldRetry || attempt >= RETRY_BACKOFF_MS.length) {
          break;
        }

        const delay = RETRY_BACKOFF_MS[attempt];
        console.warn(
          `Schema cache error, retrying in ${delay}ms (attempt ${attempt + 1})`
        );
        await new Promise((resolve) => setTimeout(resolve, delay));
      }

      if (dbError || !license) {
        const message = dbError?.message || "unknown";
        console.error("Database error:", dbError);

        if (message.toLowerCase().includes("schema cache") && SUPABASE_DB_URL) {
          console.warn(
            "PostgREST schema cache error detected. Falling back to direct SQL insert."
          );
          license = await insertLicenseDirect(
            SUPABASE_DB_URL,
            licenseKey,
            purchaseData,
            expiresAt,
            maxDevices
          );
        } else {
          throw new Error(`Failed to create license: ${message}`);
        }
      }

      console.log("License registered in database:", license);

      // 5. Send Email with License Key
      let emailSent = false;
      if (RESEND_API_KEY) {
        try {
          await sendActivationEmail(purchaseData, licenseKey, expiresAt);
          console.log("Activation email sent to:", purchaseData.email);
          emailSent = true;
        } catch (emailErr) {
          console.error("Email sending failed; continuing without email:", emailErr);
        }
      } else {
        console.warn(
          "RESEND_API_KEY not set; skipping email إرسال".replace(" إرسال", "")
        );
      }

      return new Response(
        JSON.stringify({
          success: true,
          license_key: licenseKey,
          message: emailSent
            ? "License created and email sent"
            : "License created (email not sent)",
          email_sent: emailSent,
        }),
        {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
          status: 200,
        }
      );
    }

    // Other webhook events
    return new Response(
      JSON.stringify({ received: true }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (error) {
    console.error("Webhook error:", error);
    return new Response(
      JSON.stringify({
        error: error.message,
        stack: error.stack,
      }),
      {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 400,
      }
    );
  }
});

// ============================================================
// License Key Generator
// ============================================================
function generateLicenseKey(plan: "pro" | "enterprise"): string {
  const prefix = plan === "enterprise" ? "ENT" : "PRO";
  const timestamp = new Date().toISOString().split("T")[0].replace(/-/g, "");
  const random = Math.random().toString(36).substring(2, 8).toUpperCase();
  
  return `${prefix}-${timestamp}-${random}`;
}

// ============================================================
// Email Sender (via Resend API)
// ============================================================
async function sendActivationEmail(
  purchase: PurchaseData,
  licenseKey: string,
  expiresAt: Date
): Promise<void> {
  const planName = purchase.plan === "enterprise" ? "ENTERPRISE" : "PRO";
  const planEmoji = purchase.plan === "enterprise" ? "🏢" : "⭐";

  const emailHtml = `
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PhotoCleaner ${planName} Lizenz</title>
  <style>
    * { margin: 0; padding: 0; }
    body { 
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
      line-height: 1.6;
      color: #2d3748;
      background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
      padding: 20px;
    }
    .container { 
      max-width: 620px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 4px 20px rgba(102, 126, 234, 0.15);
    }
    .header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: #ffffff;
      padding: 50px 40px;
      text-align: center;
    }
    .header h1 {
      font-size: 32px;
      margin-bottom: 10px;
      font-weight: 700;
      letter-spacing: -0.5px;
    }
    .header p {
      font-size: 16px;
      opacity: 0.95;
      font-weight: 500;
    }
    .content {
      padding: 40px;
    }
    .greeting {
      font-size: 16px;
      margin-bottom: 10px;
      color: #2d3748;
    }
    .greeting strong {
      font-weight: 600;
      color: #1a202c;
    }
    .intro-text {
      font-size: 15px;
      margin-bottom: 35px;
      color: #4a5568;
      line-height: 1.7;
    }
    .license-section {
      background: linear-gradient(135deg, #667eea08 0%, #764ba208 100%);
      border: 2px solid #667eea;
      border-radius: 10px;
      padding: 30px;
      margin-bottom: 35px;
      text-align: center;
    }
    .license-label {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: #667eea;
      font-weight: 600;
      margin-bottom: 12px;
    }
    .license-key {
      font-size: 28px;
      font-weight: 700;
      color: #667eea;
      letter-spacing: 3px;
      font-family: 'Monaco', 'Courier New', monospace;
      margin: 15px 0;
      word-break: break-all;
    }
    .license-validity {
      font-size: 13px;
      color: #718096;
      margin-top: 15px;
      font-weight: 500;
    }
    .copy-button {
      display: inline-block;
      background: #667eea;
      color: white;
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      text-decoration: none;
      margin-top: 12px;
      cursor: pointer;
      border: none;
    }
    .steps-section {
      margin-bottom: 35px;
    }
    .steps-title {
      font-size: 18px;
      font-weight: 700;
      margin-bottom: 20px;
      color: #1a202c;
    }
    .steps-container {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .step {
      background: #f7fafc;
      border-left: 4px solid #667eea;
      padding: 18px;
      border-radius: 6px;
      position: relative;
    }
    .step-number {
      display: inline-block;
      background: #667eea;
      color: white;
      width: 32px;
      height: 32px;
      border-radius: 50%;
      text-align: center;
      line-height: 32px;
      font-weight: 700;
      margin-right: 12px;
      font-size: 14px;
    }
    .step-title {
      font-weight: 600;
      color: #2d3748;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
    }
    .step-desc {
      color: #4a5568;
      font-size: 14px;
      margin-left: 44px;
    }
    .cta-button {
      display: inline-block;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 14px 40px;
      text-decoration: none;
      border-radius: 8px;
      font-weight: 600;
      font-size: 15px;
      text-align: center;
      width: 100%;
      box-sizing: border-box;
      transition: transform 0.2s, box-shadow 0.2s;
      margin-bottom: 35px;
      border: none;
      cursor: pointer;
    }
    .cta-button:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    .features-section {
      background: #f7fafc;
      border-radius: 10px;
      padding: 24px;
      margin-bottom: 35px;
    }
    .features-title {
      font-size: 16px;
      font-weight: 700;
      color: #1a202c;
      margin-bottom: 16px;
    }
    .features-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .feature-item {
      font-size: 14px;
      color: #2d3748;
      padding: 8px 0;
      display: flex;
      align-items: center;
    }
    .feature-item::before {
      content: "✓";
      color: #48bb78;
      font-weight: bold;
      margin-right: 8px;
      font-size: 16px;
    }
    .tips-section {
      background: linear-gradient(135deg, #fef5e7 0%, #fef9e7 100%);
      border-left: 4px solid #f6ad55;
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 35px;
    }
    .tips-title {
      font-size: 15px;
      font-weight: 700;
      color: #d97706;
      margin-bottom: 12px;
    }
    .tips-list {
      font-size: 14px;
      color: #78350f;
      line-height: 1.8;
    }
    .tips-list li {
      margin-bottom: 8px;
    }
    .support-section {
      background: #edf2f7;
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 25px;
      text-align: center;
    }
    .support-title {
      font-size: 15px;
      font-weight: 700;
      color: #2d3748;
      margin-bottom: 12px;
    }
    .support-link {
      display: inline-block;
      font-size: 14px;
      color: #667eea;
      text-decoration: none;
      font-weight: 500;
      margin: 0 12px;
    }
    .support-link:hover {
      text-decoration: underline;
    }
    .footer {
      background: #f7fafc;
      border-top: 1px solid #e2e8f0;
      padding: 24px;
      text-align: center;
      font-size: 12px;
      color: #718096;
      line-height: 1.6;
    }
    .footer-text {
      margin: 6px 0;
    }
    .divider {
      height: 1px;
      background: #e2e8f0;
      margin: 20px 0;
    }
    @media (max-width: 600px) {
      .header { padding: 35px 25px; }
      .header h1 { font-size: 26px; }
      .content { padding: 25px; }
      .features-grid { grid-template-columns: 1fr; }
      .license-section { padding: 20px; }
      .license-key { font-size: 22px; }
    }
  </style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <div class="header">
      <h1>${planEmoji} PhotoCleaner ${planName}</h1>
      <p>Glückwunsch! Ihre Lizenz ist bereit 🎉</p>
    </div>

    <!-- Main Content -->
    <div class="content">
      <!-- Greeting -->
      <p class="greeting">Hallo <strong>${purchase.name}</strong>,</p>
      <p class="intro-text">vielen Dank für Ihren Kauf von <strong>PhotoCleaner ${planName}</strong>! Ihre Lizenz wurde erfolgreich erstellt und ist sofort einsatzbereit.</p>

      <!-- License Key -->
      <div class="license-section">
        <div class="license-label">Ihr Lizenz-Schlüssel</div>
        <div class="license-key">${licenseKey}</div>
        <div class="license-validity">✓ Gültig bis ${expiresAt.toLocaleDateString("de-DE", { year: "numeric", month: "long", day: "numeric" })}</div>
        <button class="copy-button" onclick="navigator.clipboard.writeText('${licenseKey}')">📋 In Zwischenablage kopieren</button>
      </div>

      <!-- Quick Start Steps -->
      <div class="steps-section">
        <div class="steps-title">⚡ Aktivierung in 3 einfachen Schritten</div>
        <div class="steps-container">
          <div class="step">
            <div class="step-title"><span class="step-number">1</span>PhotoCleaner starten</div>
            <div class="step-desc">Öffnen Sie PhotoCleaner auf Ihrem Computer</div>
          </div>
          <div class="step">
            <div class="step-title"><span class="step-number">2</span>Zu Lizenzverwaltung gehen</div>
            <div class="step-desc">Menü → Einstellungen → "Lizenz & Konto" → "Lizenzen verwalten"</div>
          </div>
          <div class="step">
            <div class="step-title"><span class="step-number">3</span>Lizenz-Key aktivieren</div>
            <div class="step-desc">Geben Sie Ihren Lizenz-Schlüssel ein und klicken Sie auf "Aktivieren"</div>
          </div>
        </div>
      </div>

      <!-- CTA Button -->
      <a href="https://photocleaner.com/docs/activation" class="cta-button">📖 Zur Aktivierungs-Anleitung</a>

      <!-- Features -->
      <div class="features-section">
        <div class="features-title">🎁 Ihre ${planName} Features</div>
        <div class="features-grid">
          ${purchase.plan === "enterprise" ? `
            <div class="feature-item">Unbegrenzte Bilder</div>
            <div class="feature-item">Batch-Verarbeitung</div>
            <div class="feature-item">Qualitätsanalyse</div>
            <div class="feature-item">HEIC/HEIF Support</div>
            <div class="feature-item">2-8x Caching</div>
            <div class="feature-item">REST API</div>
            <div class="feature-item">Cloud-Backup</div>
            <div class="feature-item">10 Geräte</div>
          ` : `
            <div class="feature-item">Unbegrenzte Bilder</div>
            <div class="feature-item">Batch-Verarbeitung</div>
            <div class="feature-item">Qualitätsanalyse</div>
            <div class="feature-item">HEIC/HEIF Support</div>
            <div class="feature-item">2-8x Caching</div>
            <div class="feature-item">3 Geräte</div>
          `}
        </div>
      </div>

      <!-- Tips -->
      <div class="tips-section">
        <div class="tips-title">💡 Pro Tipps zum Einstieg</div>
        <ul class="tips-list">
          <li><strong>Test-Ordner:</strong> Bereiten Sie einen Ordner mit 1000+ Testfotos vor</li>
          <li><strong>Batch-Verarbeitung:</strong> Spart bis zu 10 Stunden bei großen Projekten</li>
          <li><strong>Auto-Select:</strong> Lassen Sie PhotoCleaner automatisch die besten Bilder auswählen</li>
          <li><strong>Performance:</strong> Speichern Sie Ihre Fotos auf einer SSD für optimale Geschwindigkeit</li>
        </ul>
      </div>

      <!-- Support -->
      <div class="support-section">
        <div class="support-title">❓ Sie brauchen Hilfe?</div>
        <div>
          <a href="mailto:support@photocleaner.com" class="support-link">📧 support@photocleaner.com</a>
          <a href="https://photocleaner.com/docs" class="support-link">📖 Dokumentation</a>
          <a href="https://discord.gg/photocleaner" class="support-link">💬 Community</a>
        </div>
      </div>

      <!-- Footer -->
      <div class="footer">
        <div class="footer-text"><strong>PhotoCleaner ${planName}</strong> • ${purchase.amount}€ • Lizenz gültig bis ${expiresAt.toLocaleDateString("de-DE")}</div>
        <div class="footer-text">Zahlungs-ID: <code>${purchase.stripe_payment_id}</code></div>
        <div class="divider"></div>
        <div class="footer-text">Diese Email wurde automatisch generiert. Bei Fragen antworten Sie einfach auf diese Email.</div>
        <div class="footer-text">© 2026 PhotoCleaner • Intelligente Foto-Verwaltung</div>
      </div>
    </div>
  </div>
</body>
</html>
  `;

  // Send via Resend API
  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: RESEND_FROM,
      to: [purchase.email],
      subject: `🎉 Ihre PhotoCleaner ${planName} Lizenz ist bereit!`,
      html: emailHtml,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Email sending failed: ${error}`);
  }

  console.log("Email sent successfully via Resend");
}

// ============================================================
// Direct SQL Insert (Fallback)
// ============================================================
async function insertLicenseDirect(
  dbUrl: string,
  licenseKey: string,
  purchase: PurchaseData,
  expiresAt: Date,
  maxDevices: number
): Promise<Record<string, unknown>> {
  const pool = new Pool(dbUrl, 1, true);
  const client = await pool.connect();

  try {
    await client.queryArray(
      `
      INSERT INTO licenses
      (license_id, plan, status, expires_at, max_devices, assigned_to, licensee, stripe_payment_id)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      `,
      [
        licenseKey,
        purchase.plan,
        "active",
        expiresAt.toISOString(),
        maxDevices,
        purchase.email,
        purchase.name,
        purchase.stripe_payment_id,
      ]
    );

    const result = await client.queryObject<Record<string, unknown>>(
      "SELECT * FROM licenses WHERE license_id = $1",
      [licenseKey]
    );

    return result.rows[0] ?? { license_id: licenseKey };
  } finally {
    client.release();
    await pool.end();
  }
}
