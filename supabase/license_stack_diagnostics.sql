-- PhotoCleaner - License Stack Diagnostics (Supabase)
-- Run in Supabase SQL Editor.
-- Purpose: Verify schema, RLS/policies, grants, and function compatibility.

-- ==========================================================
-- 1) QUICK HEALTH CHECKS
-- ==========================================================

-- Tables available?
select table_schema, table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('licenses', 'active_devices', 'free_usage')
order by table_name;

-- Key columns + data types.
select table_name, column_name, data_type, is_nullable, column_default
from information_schema.columns
where table_schema = 'public'
  and table_name in ('licenses', 'active_devices', 'free_usage')
order by table_name, ordinal_position;

-- Constraints (PK/unique/check/foreign key).
select
  tc.table_name,
  tc.constraint_name,
  tc.constraint_type
from information_schema.table_constraints tc
where tc.table_schema = 'public'
  and tc.table_name in ('licenses', 'active_devices', 'free_usage')
order by tc.table_name, tc.constraint_type, tc.constraint_name;

-- RLS flags (portable across managed Postgres variants).
-- Note: some versions/views do not expose force-row-security in pg_tables.
select schemaname, tablename, rowsecurity
from pg_tables
where schemaname = 'public'
  and tablename in ('licenses', 'active_devices', 'free_usage')
order by tablename;

-- Policies actually present.
select schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'public'
  and tablename in ('licenses', 'active_devices', 'free_usage')
order by tablename, policyname;

-- Grants for anon/authenticated.
select grantee, table_schema, table_name, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and table_name in ('licenses', 'active_devices', 'free_usage')
  and grantee in ('anon', 'authenticated')
order by table_name, grantee, privilege_type;

-- RPC function existence + security mode.
select
  n.nspname as schema_name,
  p.proname as function_name,
  p.prosecdef as security_definer,
  pg_get_function_identity_arguments(p.oid) as args
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname = 'consume_free_images';


-- ==========================================================
-- 2) OPTIONAL ALIGNMENT FIXES (uncomment carefully)
-- ==========================================================

-- 2.1 Ensure timezone-aware expiry columns (recommended for cloud apps).
-- alter table public.licenses
--   alter column expires_at type timestamptz using expires_at at time zone 'UTC';
-- alter table public.licenses
--   alter column created_at type timestamptz using created_at at time zone 'UTC';
-- alter table public.licenses
--   alter column last_seen type timestamptz using last_seen at time zone 'UTC';
-- alter table public.active_devices
--   alter column added_at type timestamptz using added_at at time zone 'UTC';
-- alter table public.active_devices
--   alter column last_seen type timestamptz using last_seen at time zone 'UTC';

-- 2.2 If RLS is enabled but you intentionally need anon REST reads/updates,
-- create explicit policies. Without policies, grants alone do not allow access.
-- NOTE: This is broad access. Prefer Edge Functions for stricter security.
-- create policy licenses_anon_select
--   on public.licenses
--   for select
--   to anon
--   using (true);
--
-- create policy active_devices_anon_write
--   on public.active_devices
--   for all
--   to anon
--   using (true)
--   with check (true);


-- ==========================================================
-- 3) SIGNATURE FLOW CHECK (informational)
-- ==========================================================
-- Important: signature mismatch seen in app logs is usually NOT a SQL issue.
-- It is most often one of these:
--   A) Edge Function deployed code is outdated (legacy signer)
--   B) LICENSE_SIGNING_PRIVATE_KEY secret mismatch vs app PUBLIC_KEY_PEM
--   C) Returned signature is truncated/transformed
--
-- Expected Ed25519 Base64 signature length is typically around 88 characters.
-- If app logs show signature_len=32, that strongly indicates wrong signer/format.

-- If you happen to store a 'signature' column in licenses, inspect lengths:
-- select license_id, length(signature) as sig_len
-- from public.licenses
-- where signature is not null
-- order by sig_len asc
-- limit 20;

-- End of diagnostics.
