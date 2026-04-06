# Naming & Terminology Guide

Status: Active standard (from 2026-04-06)
Scope: Python code, TypeScript edge functions, SQL schema, UI texts, logs, docs

## 1) Core rule
- Code identifiers are English.
- User-facing UI texts are localized via i18n.
- German may appear in docs and translation files, but not in new code symbol names.

## 2) Naming conventions by layer

### Python
- modules/files: lower_snake_case (`license_client.py`)
- classes: PascalCase (`LicenseManager`)
- functions/methods/variables: snake_case (`fetch_license`, `max_devices`)
- constants: UPPER_SNAKE_CASE (`MAX_RETRY_WAIT_SECONDS`)
- private members: leading underscore (`_cache_snapshot`)

### TypeScript / Deno edge functions
- files: kebab-case (`exchange-license-key/index.ts`)
- variables/functions: camelCase (`licenseData`, `signPayload`)
- constants: UPPER_SNAKE_CASE for env names (`LICENSE_SIGNING_PRIVATE_KEY`)

### SQL
- tables/columns/functions: lower_snake_case (`active_devices`, `expires_at`)
- status enums: lowercase English values (`active`, `suspended`, `expired`)

### Logs and errors
- Internal log fields and error codes: English
- User dialogs/messages: localized via i18n keys

## 3) UI and i18n policy
- No hardcoded user-visible strings in business logic where translation exists.
- i18n keys use stable English identifiers (`license_supabase_not_configured`).
- Translation values can be German/English in locale files.

## 4) Canonical term map (must stay consistent)
- license key: activation code entered by user
- license id: canonical backend id
- plan: license tier (`basic`, `pro`, ...)
- status: lifecycle state (`active`, `suspended`, `expired`)
- device: registered machine entry
- snapshot: locally cached signed license payload
- signature: Ed25519 Base64 signature for payload integrity
- grace period: offline validity window

## 5) Avoid these mixed patterns
- New symbols like `lizenz_*`, `geraet_*`, `ablauf_*`
- German + English in one identifier (`lizenz_status`, `geraet_status`)
- Same concept with multiple names (`license_type` vs `plan`) without alias rationale

## 6) Migration strategy for legacy names
- Do not mass-rename working legacy code in one sweep.
- Rename only when touching a module for feature work/fixes.
- Preserve public API compatibility with aliases/wrappers if required.
- Document larger renames in changelog/backlog.

## 7) Definition of done for naming changes
- New code follows this guide.
- New UI strings routed via i18n.
- No new mixed-language identifiers introduced.
- Unit tests and static checks stay green.
