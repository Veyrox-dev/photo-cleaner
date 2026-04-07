# Stripe + Supabase E2E Runbook

## Ziel

Dieser Runbook dokumentiert den kompletten Slice-3-Durchlauf:

Checkout -> Webhook -> Lizenz in Supabase -> Lizenzmail -> Aktivierung in der App

Er gilt fuer das aktuelle Modell:

- FREE: einmalig 250 Bilder
- PRO: Jahresabo, unbegrenzt

---

## Voraussetzungen

### Stripe
- Test Mode aktiv
- genau ein aktives PRO Product/Price
- Webhook Endpoint zeigt auf die Supabase Function
- Event `checkout.session.completed` ist abonniert

### Supabase
- Function `license-webhook` deployed
- Function `exchange-license-key` deployed
- Tabelle `licenses` erreichbar

### Environment Variablen (`license-webhook`)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_DB_URL` (Fallback bei PostgREST-Cacheproblemen)
- `STRIPE_WEBHOOK_SECRET`
- `RESEND_API_KEY` (wenn echte E-Mail geprueft werden soll)
- `RESEND_FROM`

Optional fuer manuelle Tests:
- `STRIPE_ALLOW_MISSING_SIGNATURE=true`
- `TEST_EMAIL_OVERRIDE=<test@adresse>`

Wichtig:
- Bei echten Stripe-Events mit Signatur wird `TEST_EMAIL_OVERRIDE` nicht verwendet.

---

## Produktmodell-Guardrail

Der Webhook akzeptiert nur `metadata.plan=pro`.

- Erwartung: `plan` ist `pro`
- Abweichung: Request wird mit Fehler abgelehnt

Damit ist das bezahlte Modell auf einen bezahlten Plan fest fixiert.

---

## Testpfad A: Echter Stripe-Testkauf (empfohlen)

1. Checkout Session mit PRO Price starten.
2. Testkarte verwenden (z. B. `4242 4242 4242 4242`).
3. In Stripe Events pruefen: `checkout.session.completed` erfolgreich.
4. In Supabase Function Logs pruefen:
   - Event empfangen
   - Lizenzschluessel erzeugt
   - DB-Eintrag erstellt
5. In Tabelle `licenses` pruefen:
   - `plan = pro`
   - `status = active`
   - `assigned_to = customer_email`
6. E-Mail-Eingang pruefen (wenn Resend aktiv ist).
7. Lizenz in der App aktivieren:
   - Lizenzschluessel eingeben
   - Aktivierung erfolgreich
   - PRO-Features verfuegbar

Erwartetes Ergebnis:
- End-to-End Durchlauf erfolgreich ohne manuellen Eingriff.

---

## Testpfad B: Manueller Webhook-Post (lokal/schnell)

Nur fuer technische Schnelltests ohne Stripe-Signatur.

1. `STRIPE_ALLOW_MISSING_SIGNATURE=true` setzen.
2. Testpayload posten:

```powershell
$payload = @'
{
  "type": "checkout.session.completed",
  "data": {
    "object": {
      "customer_email": "test@example.com",
      "customer_details": {
        "email": "test@example.com",
        "name": "Test User"
      },
      "metadata": {
        "plan": "pro"
      },
      "payment_intent": "pi_test_123",
      "amount_total": 3900
    }
  }
}
'@

Invoke-RestMethod \
  -Method Post \
  -Uri "https://<project-ref>.supabase.co/functions/v1/license-webhook" \
  -ContentType "application/json" \
  -Body $payload
```

3. Danach dieselben DB-/Mail-/Aktivierungschecks wie in Testpfad A durchlaufen.

---

## Negativtests (Pflicht)

1. `metadata.plan` ungueltig (`enterprise`, `trial`, leer)
   - Erwartung: Webhook bricht mit Fehler ab.

2. Signatur fehlt und `STRIPE_ALLOW_MISSING_SIGNATURE=false`
   - Erwartung: Request wird abgelehnt.

3. Resend deaktiviert
   - Erwartung: Lizenz wird erstellt, Antwort meldet `email_sent=false`.

---

## Troubleshooting

### Problem: Schema cache error
- Symptom: Insert ueber PostgREST scheitert mit Schema-Cache-Fehler
- Verhalten: Webhook versucht Retry und kann auf `SUPABASE_DB_URL`-Insert ausweichen
- Aktion: PostgREST-Schema-Fix und Logs kontrollieren

### Problem: E-Mail kommt nicht an
- `RESEND_API_KEY` und Senderdomain pruefen
- Spam-Ordner pruefen
- Function-Logs auf Mail-Fehler pruefen

### Problem: Aktivierung in App scheitert
- Lizenzschluessel in `licenses` vorhanden?
- `status=active`?
- `exchange-license-key` Logs auf Signatur- oder Device-Binding-Probleme pruefen

---

## Abnahme-Checkliste Slice 3

- [ ] Stripe Product/Price auf genau einen PRO-Plan konsolidiert
- [ ] Webhook-Guardrail `metadata.plan=pro` aktiv
- [ ] Echter Stripe-Testkauf erfolgreich
- [ ] Lizenz in `licenses` korrekt angelegt
- [ ] Lizenzmail zugestellt (oder bewusst deaktiviert)
- [ ] Aktivierung in App erfolgreich

Wenn alle Punkte gruen sind, ist Slice 3 technisch abgeschlossen.

---

## Letzte Ausfuehrung (2026-04-07)

Durchgefuehrte Validierung in der aktuellen Umgebung:

1. Deploy der aktualisierten Function `license-webhook` auf Projekt `uxkbolrinptxyullfowo`
2. Positivtest (Testpfad B) mit `metadata.plan=pro`
  - Webhook: `success=true`
  - Lizenzschluessel erzeugt
  - Exchange-Aktivierung: `ok=true`, `license_type=pro`, Signatur vorhanden
3. Negativtest mit `metadata.plan=enterprise`
  - Erwartung erfuellt: HTTP 400
  - Fehlermeldung: `Unexpected plan metadata 'enterprise'. Expected 'pro'.`

Status nach Lauf:
- Guardrail technisch wirksam
- Webhook -> Exchange-Fluss verifiziert
- Offener Restpunkt bleibt der echte Stripe-Signaturpfad aus einem realen Test-Checkout