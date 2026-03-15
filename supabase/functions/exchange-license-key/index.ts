/// <reference lib="deno.ns" />

/**
 * Supabase Edge Function: exchange-license-key
 * Produktiver Pfad: Liest Lizenzen aus der DB, prüft Status/Expiry/Device-Limit
 * und registriert das Gerät in active_devices. Liefert ein normalisiertes
 * license_data-Objekt zurück (license_type = plan).
 */

import { serve } from "https://deno.land/std@0.224.0/http/server.ts";
import { decodeBase64, encodeBase64 } from "https://deno.land/std@0.224.0/encoding/base64.ts";
import postgres from "https://deno.land/x/postgresjs@v3.4.3/mod.js";
import { sign } from "https://esm.sh/@noble/ed25519@2.1.0";

const databaseUrl =
  Deno.env.get("SUPABASE_DB_URL") ||
  Deno.env.get("SUPABASE_DB_CONNECTION_STRING") ||
  Deno.env.get("DATABASE_URL");

const signingKeyB64 = Deno.env.get("LICENSE_SIGNING_PRIVATE_KEY") || "";

if (!databaseUrl) {
  console.error("Missing database connection string (SUPABASE_DB_URL/connection string)");
}

// Direkter Postgres-Zugriff, um PostgREST-Schema-Cache-Probleme zu vermeiden
const sql = databaseUrl ? postgres(databaseUrl, { prepare: true, idle_timeout: 10 }) : null;

export async function handler(req: Request) {
  if (req.method !== "POST") {
    return json({ ok: false, error: "Method not allowed" }, 405);
  }

  if (!sql) {
    return json({ ok: false, error: "Server misconfigured (db url missing)" }, 500);
  }
  if (!signingKeyB64) {
    return json({ ok: false, error: "Server misconfigured (signing key missing)" }, 500);
  }

  try {
    const body = await req.json();
    const { license_key, device_info } = body ?? {};

    if (!license_key || !device_info) {
      return json({ ok: false, error: "Missing license_key or device_info" }, 400);
    }

    const deviceId = device_info.machine_id || device_info.device_id || "unknown-device";
    const deviceName = device_info.hostname || device_info.device_name || "unknown-host";
    const deviceOs = device_info.platform || device_info.os || "unknown-os";

    // 1) Lizenz holen
    const licenseRows = await sql`select license_id, plan, status, expires_at, max_devices, created_at from licenses where license_id = ${license_key} limit 1`;
    const license = licenseRows[0];

    if (!license) {
      return json({ ok: false, error: "Invalid license key" }, 401);
    }

    if (license.status !== "active") {
      return json({ ok: false, error: `License status: ${license.status}` }, 403);
    }

    const expiresAt = new Date(license.expires_at as string);
    if (expiresAt < new Date()) {
      return json({ ok: false, error: "License expired" }, 403);
    }

    // 2) Device-Limit prüfen
    const deviceCountRows = await sql`select count(*)::int as cnt from active_devices where license_id = ${license.license_id}`;
    const deviceCount = deviceCountRows[0]?.cnt ?? 0;

    const maxDevices = (license.max_devices as number) ?? 3;
    if (deviceCount >= maxDevices) {
      return json({ ok: false, error: `Device limit exceeded (${deviceCount}/${maxDevices})` }, 403);
    }

    // 3) Gerät registrieren/updaten
    await sql`
      insert into active_devices (license_id, device_id, device_name, os, last_seen)
      values (${license.license_id}, ${deviceId}, ${deviceName}, ${deviceOs}, now())
      on conflict (license_id, device_id)
      do update set device_name = excluded.device_name,
                    os = excluded.os,
                    last_seen = excluded.last_seen;
    `;

    const licenseData = {
      license_id: license.license_id,
      license_type: license.plan, // Normalisiertes Feld für die App
      plan: license.plan,
      status: license.status,
      max_devices: maxDevices,
      expires_at: license.expires_at,
      created_at: license.created_at,
    };

    const signature = await signPayload(licenseData, signingKeyB64);

    return json({
      ok: true,
      license_id: license.license_id,
      license_data: licenseData,
      signature,
    });
  } catch (error) {
    console.error("Error:", error instanceof Error ? error.message : String(error));
    return json({ ok: false, error: "Internal server error" }, 500);
  }
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function canonicalize(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(canonicalize);
  }
  if (value && typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const sorted: Record<string, unknown> = {};
    for (const key of Object.keys(obj).sort()) {
      sorted[key] = canonicalize(obj[key]);
    }
    return sorted;
  }
  return value;
}

async function signPayload(payload: Record<string, unknown>, keyB64: string): Promise<string> {
  const canonical = JSON.stringify(canonicalize(payload));
  const message = new TextEncoder().encode(canonical);
  const keyBytes = decodeBase64(keyB64);
  const sig = await sign(message, keyBytes);
  return encodeBase64(sig);
}

serve(handler);
export default handler;
