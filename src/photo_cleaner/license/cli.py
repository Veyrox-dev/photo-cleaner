"""CLI Commands für Lizenzverwaltung in PhotoCleaner.

Ermöglicht:
- Lizenz-Status anzeigen
- Lizenz aktivieren
- Lizenz entfernen
- Demo-Lizenzen generieren
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import click

from photo_cleaner.license import (
    get_license_manager,
    LicenseType,
)

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def license_group(ctx: click.Context) -> None:
    """🔐 Lizenzverwaltung für PhotoCleaner."""
    ctx.ensure_object(dict)


@license_group.command(name="status")
@click.pass_context
def show_status(ctx: click.Context) -> None:
    """Zeige aktuellen Lizenz-Status."""
    try:
        manager = get_license_manager()
        status = manager.get_license_status()

        click.echo("\n" + "=" * 60)
        click.echo("📋 LIZENZ-STATUS")
        click.echo("=" * 60)

        license_type = status.get("license_type", "FREE").upper()
        
        # Farb-Markierungen
        if license_type == "FREE":
            icon = "📦"
        elif license_type == "TRIAL":
            icon = "🔓"
        elif license_type == "PRO":
            icon = "⭐"
        elif license_type == "ENTERPRISE":
            icon = "🏢"
        else:
            icon = "❓"

        click.echo(f"{icon} Typ:              {license_type}")
        click.echo(f"👤 Inhaber:           {status.get('licensee', 'Nicht zugewiesen')}")
        click.echo(f"📅 Ausgestellt:      {status.get('issued_at', 'N/A')}")
        click.echo(f"⏰ Ablauf:            {status.get('expires_at', 'Unbegrenzt')}")
        click.echo(f"🖼️  Max. Bilder:      {status.get('max_images', 'Unbegrenzt')}")
        click.echo(f"📆 Tage verbleibend: {status.get('days_remaining', '∞')}")

        # Features
        enabled = status.get("enabled_features", [])
        click.echo("\n✓ Aktivierte Features:")
        if enabled:
            for feature in enabled:
                click.echo(f"  • {feature}")
        else:
            click.echo("  (Keine)")

        click.echo("=" * 60 + "\n")

    except Exception as e:
        click.echo(f"❌ Fehler beim Lesen der Lizenz: {e}", err=True)
        logger.exception("Failed to read license status")


@license_group.command(name="activate")
@click.argument("license_file", type=click.Path(exists=True))
@click.pass_context
def activate_license(ctx: click.Context, license_file: str) -> None:
    """Aktiviere eine Lizenz durch Laden der .lic-Datei."""
    try:
        manager = get_license_manager()
        
        # Importiere Lizenzdatei
        if manager.import_license_file(Path(license_file)):
            info = manager.get_license_info()
            click.echo("✓ Lizenz erfolgreich importiert!")
            click.echo(f"  Typ: {info.license_type.value}")
            click.echo(f"  Benutzer: {info.user}")
            if info.expires_at:
                click.echo(f"  Ablauf: {info.expires_at.isoformat()}")
        else:
            click.echo("❌ Lizenzdatei konnte nicht importiert werden", err=True)
            raise click.Abort()

    except click.Abort:
        raise
    except Exception as e:
        click.echo(f"❌ Fehler: {e}", err=True)
        logger.exception("Failed to activate license")
        raise click.Abort()


@license_group.command(name="remove")
@click.confirmation_option(
    prompt="Lizenz wirklich entfernen? Sie kehren zu FREE-Tier zurück."
)
@click.pass_context
def remove_license(ctx: click.Context) -> None:
    """Entferne aktuelle Lizenz (Rückfall zu FREE)."""
    try:
        manager = get_license_manager()

        if manager.remove_license():
            click.echo("✓ Lizenz erfolgreich entfernt")
            click.echo("  Sie arbeiten jetzt mit dem FREE-Tier")
        else:
            click.echo("❌ Lizenz konnte nicht entfernt werden", err=True)
            raise click.Abort()

    except Exception as e:
        click.echo(f"❌ Fehler: {e}", err=True)
        logger.exception("Failed to remove license")
        raise click.Abort()


@license_group.command(name="generate")
@click.pass_context
def generate_demo_license(ctx: click.Context) -> None:
    """Zeige Anleitung zum Generieren einer Lizenz.
    
    Lizenzen werden mit dem create_license.py Werkzeug generiert.
    """
    click.echo("\n" + "="*60)
    click.echo("📝 LIZENZGENERIERUNG")
    click.echo("="*60)
    click.echo("\nLizenzen werden mit dem create_license.py Werkzeug generiert:")
    click.echo("\n  python create_license.py \\")
    click.echo("    --user 'John Doe' \\")
    click.echo("    --license-type PRO \\")
    click.echo("    --expires 2025-12-31 \\")
    click.echo("\nDie generierte .lic-Datei kann dann mit folgendem Befehl ")
    click.echo("importiert werden:")
    click.echo("\n  photo-cleaner license activate license.lic")
    click.echo("\n" + "="*60 + "\n")


@license_group.command(name="info")
@click.pass_context
def show_license_info(ctx: click.Context) -> None:
    """Zeige Informationen zu Lizenztypen."""
    info_text = """
╔════════════════════════════════════════════════════════════╗
║                    LIZENZ-ÜBERSICHT                        ║
╚════════════════════════════════════════════════════════════╝

📦 FREE (Standard)
   • Grundlegende Bildanalyse
   • Bis zu 1000 Bilder pro Scan
   • Keine Premium-Features
   • Kostenfrei, unbegrenzte Nutzung

🔓 TRIAL (30 Tage)
   • Batch-Verarbeitung
   • HEIC/HEIF-Unterstützung
   • Bulk-Löschung
   • Bis zu 1000 Bilder
   • Ablauf nach 30 Tagen

⭐ PRO (Jährlich)
   • Alle TRIAL-Features +
   • Erweitertes Caching (ImageCache)
   • Erweiterte Qualitätsanalyse
   • Custom Export-Formate
   • Bis zu 1000 Bilder
   • 365 Tage Gültigkeit

🏢 ENTERPRISE (Unbegrenzt)
   • ALLE Features freigeschaltet
   • Unbegrenzte Bilder
   • REST API-Zugriff
   • Keine zeitlichen Beschränkungen
   • Vollständige Automatisierung

╔════════════════════════════════════════════════════════════╗
║                    FEATURE-TABELLE                         ║
╚════════════════════════════════════════════════════════════╝

Feature                    │ FREE │ TRIAL │ PRO │ ENTERPRISE
───────────────────────────┼──────┼───────┼─────┼───────────
Batch-Verarbeitung         │  ✗   │   ✓   │  ✓  │    ✓
HEIC/HEIF-Format           │  ✗   │   ✓   │  ✓  │    ✓
Erweitertes Caching        │  ✗   │   ✗   │  ✓  │    ✓
Erweiterte Qualitätsanalyse│  ✗   │   ✗   │  ✓  │    ✓
Bulk-Löschung              │  ✗   │   ✓   │  ✓  │    ✓
Custom Export-Formate      │  ✗   │   ✗   │  ✓  │    ✓
REST API-Zugriff           │  ✗   │   ✗   │  ✗  │    ✓
Unbegrenzte Bilder         │  ✗   │   ✗   │  ✗  │    ✓
"""
    click.echo(info_text)


if __name__ == "__main__":
    license_group()
