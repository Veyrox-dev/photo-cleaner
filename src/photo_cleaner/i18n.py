"""Translation system for PhotoCleaner (DE/EN).

Simple i18n with language switching persisted in settings.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Translation dictionary
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "de": {
        "0_gruppen": "0 Gruppen",
        "_aktion_erforderlich_if_grpopencount_0_else_vollst": "{'⚠️ AKTION ERFORDERLICH' if grp.open_count > 0 else '✅ Vollständig entschieden'}",
        "_autoauswahl_fuer_gruppe_augengewicht_55": "⭐ Auto-Auswahl für Gruppe (Augen-Gewicht: 55%):",
        "_bempfehlung_fuer_ihr_systemb_recrecommendedpackag": "💡 <b>Empfehlung für Ihr System:</b> {rec.recommended_package}<br>",
        "_benoetigt_build_tools": "      ⚠ Benötigt Build Tools",
        "_benoetigt_joindepnames": "⚠ Benötigt: {', '.join(dep_names)}",
        "_build_tools_verfuegbar_if_selfsysteminfohasbuildt": "  Build Tools: {'✓ Verfügbar' if self.system_info.has_build_tools else '✗ Nicht erkannt'}",
        "_ctrlj_ctrlk_gruppe_wechseln": "  Ctrl+J / Ctrl+K - Gruppe wechseln",
        "_der_ordner_gueltige_bilddateien_enthaeltn": "• Der Ordner gültige Bilddateien enthält\n",
        "_fertigstellen_exportieren": "✓ Fertigstellen & Exportieren",
        "_geloescht_intfloatdeletedat": " (gelöscht: {int(float(deleted_at))})",
        "_genuegend_speicherplatz_vorhanden_ist": "• Genügend Speicherplatz vorhanden ist",
        "_gpu_verfuegbar_if_selfsysteminfohasgpu_else_nicht": "  GPU: {'✓ Verfügbar' if self.system_info.has_gpu else '✗ Nicht erkannt'}",
        "_hohe_qualitaet_if_score_07_else_mittlere_qualitae": "{'✓ Hohe Qualität' if score >= 0.7 else '~ Mittlere Qualität' if score >= 0.4 else '✗ Niedrige Qualität'}",
        "_kein_gesicht_erkannt_regel_greift_nicht": "❌ Kein Gesicht erkannt → Regel greift nicht",
        "_lendeletedids_bilder_geloescht": "✓ {len(deleted_ids)} Bild(er) gelöscht.",
        "_openfiles_benoetigen_entscheidung": "⚠️ {open_files} benötigen Entscheidung",
        "_sie_leserechte_fuer_den_ordner_habenn": "• Sie Leserechte für den Ordner haben\n",
        "_speichern": "💾 Speichern",
        "_sync_aus": "🔗 Sync: AUS",
        "_voreinstellung_geloescht": "✓ Voreinstellung gelöscht",
        "_zoom_inout": "+/-: Zoom in/out",
        "alle_bilder_disqualifiziert_geschlossene_augenqual": "Alle Bilder disqualifiziert (geschlossene Augen/Qualitätsfehler) – keine Empfehlung",
        "als_behalten_markieren": "Als Behalten markieren",
        "alte_datenbank_geloescht_selfdbpath": "Alte Datenbank gelöscht: {self.db_path}",
        "anzahl_duplikatgruppen": "Anzahl Duplikat-Gruppen",
        "auf_niedrigere_stufe_zurueckfallen_bei_fehler": "Auf niedrigere Stufe zurückfallen bei Fehler",
        "aufloesung_exifdatasize": "Auflösung: {exif_data['Size']}",
        "aufloesung_filerowresolutionscore0f": "Auflösung: {file_row.resolution_score:.0f}%",
        "augenerkennung_einstellungen": "Augenerkennung Einstellungen",
        "b1_bild_ausgewaehltb": "<b>1 Bild ausgewählt</b>",
        "b2_bilder_ausgewaehltb": "<b>2 Bilder ausgewählt</b>",
        "bcount_bilder_ausgewaehltb": "<b>{count} Bilder ausgewählt</b>",
        "behalten": "Behalten",
        "bestaetigung_loeschen": "Bestätigung: Löschen",
        "bild_konnte_nicht_geladen_werden": "Bild konnte nicht geladen werden",
        "bilder_sortieren_jmt": "Bilder sortieren (J/M/T)",
        "bitte_starten_sie_die_analyse_neu_um_die_aenderung": "Bitte starten Sie die Analyse neu, um die Änderungen zu übernehmen.",
        "bitte_ueberpruefen_sie_das_log_fuer_details_oder_i": "Bitte überprüfen Sie das Log für Details oder installieren Sie manuell.",
        "bticon_c_build_tools_verfuegbar_if_infohasbuildtoo": "{bt_icon} C++ Build Tools: {'Verfügbar' if info.has_build_tools else 'Nicht erkannt'}",
        "buisteuerung_dropdowns_hinzugefu00fcgtb": "<b>UI-Steuerung (Dropdowns hinzugef\u00fcgt):</b>",
        "cache_aelter_als_selfconfiggraceperioddays_tage_of": "Cache älter als {self.config.grace_period_days} Tage (offline zu lange)",
        "cache_fuer_andere_lizenz_cachedlicenseid": "Cache für andere Lizenz ({cached_license_id})",
        "cache_statistics_reset": "Cache statistics reset",
        "datei_waehlen": "Datei wählen…",
        "dateien_entfernen": "Dateien entfernen",
        "dateigroesse_sizemb2f_mb": "Dateigröße: {size_mb:.2f} MB",
        "depname_benoetigt_build_tools_die_nicht_erkannt_wu": "{dep.name} benötigt Build Tools, die nicht erkannt wurden.",
        "detailansicht_geoeffnet_filerowpathname": "Detailansicht geöffnet: {file_row.path.name}",
        "die_ausgewaehlten_dateien_dauerhaft_loeschen": "Die ausgewählten Dateien dauerhaft löschen?",
        "dlib_nicht_verfuegbar_falle_zurueck_auf_stufe_1": "dlib nicht verfügbar, falle zurück auf Stufe 1",
        "einstellungen_konnten_nicht_geoeffnet_werden_e": "Einstellungen konnten nicht geöffnet werden: {e}",
        "endgueltig_loeschen": "Endgültig löschen",
        "export_fehlgeschlagen": "Export Fehlgeschlagen",
        "exportiert_alle_als_keep_markierten_bilder_in_die_": "Exportiert alle als KEEP markierten Bilder in die Zielstruktur",
        "fehler": "Fehler",
        "fehler_beim_markieren_der_empfehlungen_fuer_groupi": "Fehler beim Markieren der Empfehlungen für {group_id}: {e}",
        "fehler_beim_oeffnen_der_detailansicht_fuer_filerow": "Fehler beim Öffnen der Detailansicht für {file_row.path.name}: {e}",
        "fehler_beim_zusammenfuehren_e": "Fehler beim Zusammenführen: {e}",
        "gefundene_gruppen": "Gefundene Gruppen",
        "geloescht": "Gelöscht",
        "gesamtgesaecher_erfolgsrate_": "Gesamt-Gesächer: -, Erfolgsrate: -",
        "gpuicon_gpu_verfuegbar_if_infohasgpu_else_nicht_er": "{gpu_icon} GPU: {'Verfügbar' if info.has_gpu else 'Nicht erkannt'}",
        "gruppe_groupid_keine_gueltigen_qualityergebnisse": "Gruppe {group_id}: Keine gültigen Quality-Ergebnisse",
        "gruppen": "Gruppen",
        "h4zoom_controlsh4": "<h4>Zoom Controls</h4>",
        "heicheif_uebersprungen_pillowheif_fehlt_imagepathn": "HEIC/HEIF übersprungen (pillow-heif fehlt): {image_path.name}",
        "hohe_qualitaet_empfohlen_zum_behalten": "Hohe Qualität - Empfohlen zum Behalten",
        "imittel_dlibdepsizemb_mb_benoetigt_c_build_toolsi": "<i>Mittel, {dlib_dep.size_mb} MB, benötigt C++ Build Tools</i>",
        "importvalidierung_fehlgeschlagen_fuer_key": "Import-Validierung fehlgeschlagen für {key}",
        "information": "Information",
        "inputordner": "Input-Ordner:",
        "kann_builtin_preset_nicht_loeschen_key": "Kann Built-In Preset nicht löschen: {key}",
        "kann_builtin_preset_nicht_ueberschreiben_key": "Kann Built-In Preset nicht überschreiben: {key}",
        "kann_vordefiniertes_preset_presetname_nicht_loesch": "Kann vordefiniertes Preset '{preset_name}' nicht löschen.",
        "keine_ausstehenden_aenderungen": "Keine ausstehenden Änderungen",
        "keine_dependencies_verfuegbar_ueberspringe_gesicht": "Keine Dependencies verfügbar, überspringe Gesichtserkennung",
        "konnte_alte_datenbank_nicht_loeschen_e": "Konnte alte Datenbank nicht löschen: {e}",
        "konnte_preset_nicht_loeschennerror": "Konnte Preset nicht löschen:\n{error}",
        "lendeletepaths_bilder_sind_als_loeschen_markiertnn": "{len(delete_paths)} Bild(er) sind als LÖSCHEN markiert.\n\nJetzt löschen?",
        "lizenzdialog_konnte_nicht_geoeffnet_werdenne": "Lizenz-Dialog konnte nicht geöffnet werden:\n{e}",
        "loesche_ausgewaehlte": "Lösche Ausgewählte",
        "mediapipe_nicht_verfuegbar_falle_zurueck_auf_stufe": "MediaPipe nicht verfügbar, falle zurück auf Stufe 2",
        "messagenndie_neuen_funktionen_sind_jetzt_verfuegba": "{message}\n\nDie neuen Funktionen sind jetzt verfügbar.\n\n",
        "mittlere_qualitaet": "Mittlere Qualität",
        "moechten_sie_fortfahren": "Möchten Sie fortfahren?",
        "moechten_sie_lengroupids_gruppen_zusammenfuehrennn": "Möchten Sie {len(group_ids)} Gruppen zusammenführen?\n\n",
        "mousewheel_zoom": "Mousewheel: Zoom",
        "ngefundene_gruppen_aehnlicher_bilder_numgroups": "\nGefundene Gruppen ähnlicher Bilder: {num_groups}",
        "nichts_zum_rueckgaengigmachen": "Nichts zum Rückgängigmachen",
        "nichts_zum_wiederherstellen": "Nichts zum Wiederherstellen",
        "niedrige_qualitaet_kandidat_zum_loeschen": "Niedrige Qualität - Kandidat zum Löschen",
        "nlenskippedlocked_dateien_wurden_uebersprungen_ges": "\n{len(skipped_locked)} Datei(en) wurden übersprungen (gesperrt).",
        "nn_bewertung_abgeschlossen_bilder_wurden_automatis": "\n\n✓ Bewertung abgeschlossen: Bilder wurden automatisch eingeschätzt.",
        "opencv_nicht_verfuegbar_augenerkennung_deaktiviert": "OpenCV nicht verfügbar, Augenerkennung deaktiviert",
        "ordner_waehlen": "Ordner wählen",
        "outputordner": "Output-Ordner:",
        "photo_cleaner_ordnerauswahl": "Photo Cleaner - Ordnerauswahl",
        "photocleaner_aufraeumen": "PhotoCleaner — Aufräumen",
        "preset_geloescht_key": "Preset gelöscht: {key}",
        "presets_auf_standard_zurueckgesetzt": "Presets auf Standard zurückgesetzt",
        "rueckgaengig_desc": "Rückgängig: {desc}",
        "schaerfe_filerowsharpnessscore0f": "Schärfe: {file_row.sharpness_score:.0f}%",
        "seiteanseitevergleich": "Seite-an-Seite-Vergleich",
        "setze_konfiguration_auf_defaults_zurueck": "Setze Konfiguration auf Defaults zurück",
        "soll_die_voreinstellung_presetname_wirklich_geloes": "Soll die Voreinstellung '{preset_name}' wirklich gelöscht werden?",
        "statischer_bildmodus_empfohlen_fuer_fotos": "Statischer Bildmodus (empfohlen für Fotos)",
        "status_nicht_geprueft": "Status: ✗ Nicht geprüft",
        "stufe_2_konfiguriert_aber_dlib_nicht_verfuegbar": "Stufe 2 konfiguriert, aber dlib nicht verfügbar",
        "stufe_3_konfiguriert_aber_mediapipe_nicht_verfuegb": "Stufe 3 konfiguriert, aber MediaPipe nicht verfügbar",
        "test_ausfuehren": "Test ausführen",
        "ueberpruefe_installation": "Überprüfe Installation...",
        "ueberpruefe_installierte_bibliotheken": "Überprüfe installierte Bibliotheken...",
        "ungueltiger_lizenzstatus_status": "Ungültiger Lizenz-Status: {status}",
        "ungueltiges_bildformat_magic_bytes_imagepath": "Ungültiges Bildformat (magic bytes): {image_path}",
        "validierung_fehlgeschlagen_fuer_changekey_changene": "Validierung fehlgeschlagen für {change.key}: {change.new_value}",
        "verfuegbar_fehlende_dependencies_fallback_aktivier": "verfügbar (fehlende Dependencies). Fallback aktiviert.",
        "verfuegbar_in_availablein": "Verfügbar in: {available_in}",
        "vergleichsfenster_geoeffnet_filerow1pathname_vs_fi": "Vergleichsfenster geöffnet: {file_row_1.path.name} vs {file_row_2.path.name}",
        "waehle_die_gewuenschte_genauigkeit_stufe_2_benoeti": "Wähle die gewünschte Genauigkeit. Stufe 2 benötigt die dlib Predictor-Datei. Stufe 3 benötigt mediapipe.",
        "waehle_eine_gruppe_um_details_zu_sehen": "Wähle eine Gruppe, um Details zu sehen.",
        "ziel_waehlen": "Ziel wählen",
    
    
        # Menu (ohne Icons; Icons werden im Code vorangestellt)
        "import": "Import",
        "settings": "Einstellungen",
        "license": "Lizenz",
        "help": "Hilfe",
        "language": "Sprache",
        "language_dialog_title": "Sprache waehlen",
        "language_dialog_desc": "Waehle die Sprache fuer die Benutzeroberflaeche. Aenderungen werden sofort uebernommen.",
        "apply": "Anwenden",
        "theme": "Design",
        "browse": "Durchsuchen...",
        "duplicate_groups": "Duplikat-Gruppen",
        "search_placeholder": "🔍 Suchen...",
        "select_folders_title": "PhotoCleaner - Ordner wählen",
        "select_folders_subtitle": "Wählen Sie Ordner und Top-N für die automatische Auswahl",
        "start_analysis": "Analyse starten",
        "input_hint": "Wählen Sie den Ordner mit den Fotos, die Sie sortieren möchten.",
        "output_hint": "Wählen Sie den Zielordner für exportierte Bilder.",
        "topn_hint": "Wie viele der besten Bilder pro Gruppe automatisch behalten werden sollen.",
        "output_required": "⚠ Bitte wählen Sie einen Zielordner aus",
        "work_existing": "ℹ Sie können nun mit bereits vorhandenen Daten arbeiten oder einen Foto-Ordner auswählen",
        "ready_to_start": "✓ Bereit zum Starten",
        "pick_group": "Wählen Sie eine Gruppe aus",
        "quick_actions": "Schnellaktionen",
        
        # Tips panel
        "tips": "Tipps",
        "tip_ctrl_click": "Strg+Klick: Auswahl umschalten",
        "tip_shift_click": "Shift+Klick: Bereichsauswahl",
        "tip_click_card": "Karte klicken: Detailansicht öffnen",
        "clear_selection": "☐ Auswahl löschen",
        "compare_two": "🔍 Vergleichen (2 ausgewählt)",
        "keep": "✓ Behalten (K)",
        "delete_confirm": "🗑 Löschen bestätigen",
        "select_multiple": "Mehrfachauswahl:",
        "select_all": "☑ Alle auswählen",
        
        # Dialogs & Messages
        "welcome": "Willkommen bei PhotoCleaner",
        "select_folders": "Ordner wählen",
        "input_folder": "Eingabeordner",
        "output_folder": "Ausgabeordner",
        "start": "✓ Starten",
        "cancel": "Abbrechen",
        "analyze": "▶ Analysieren",
        "analyzing": "Bilder werden analysiert...",
        "no_selection": "Keine Auswahl",
        "select_images": "Bitte wählen Sie Bilder aus",
        "keep": "✓ Behalten (K)",
        "delete": "🗑 Löschen bestätigen",
        "unsure": "? Unsicher (U)",
        "compare": "🔍 Vergleichen",
        "export": "✓ Exportieren",
        "close": "Schließen",
        "ok": "OK",
        
        # Status messages
        "ready": "Bereit",
        "analyzing_status": "Bilder werden analysiert...",
        "indexed": "Bilder indexiert",
        "processing": "Verarbeitung läuft",
        "complete": "Fertig",
        "sync_pan_on": "Sync Pan: EIN",
        "sync_pan_off": "Sync Pan: AUS",
        "page_info": "Seite {page}/{total} • {start}-{end} von {count}",
        "groups_count": "📊 {count} Gruppen",
        "select_group": "Wählen Sie eine Gruppe aus",
        "group_title": "Gruppe {id} ({count} Bilder)",
        "preview_from_input": "Vorschau aus Input-Ordner",
        "no_images_imported": "Keine Bilder importiert",
        "images_loaded": "{count} Bilder geladen",
        "select_output_folder_title": "Ausgabeordner wählen (Wo ausgewählte Fotos gespeichert werden)",
        "quality_settings": "Qualitäts-Einstellungen",
        
        # Language names
        "language_de": "Deutsch",
        "language_en": "English",
        
        # Theme names
        "theme_dark": "Dunkel",
        "theme_light": "Hell",
        
        # Tooltips
        "import_tooltip": "Ordner auswählen und Analyse startet automatisch",
        "settings_tooltip": "Qualitäts- und Erkennungseinstellungen",
        "license_tooltip": "Lizenz verwalten",
        "help_tooltip": "Hilfe & Tastaturkürzel",
        
        # Dialog titles and buttons
        "select_input_folder_title": "Eingabeordner wählen",
        "select_output_folder_title_short": "Ausgabeordner wählen",
        "analyze_started": "Analyse gestartet",
        "folderselection_dialog_title": "PhotoCleaner - Ordner wählen",
        
        # Quality settings UI
        "quality_weights": "Qualitäts-Gewichtung",
        "exposure": "Belichtung",
        "blur": "Unschärfe",
        "contrast": "Kontrast",
        "noise": "Rauschen",
        "presets": "Vorgaben (Presets)",
        "preset_quality_profiles": "Schnellauswahl von Qualitäts-Profilen:",
        "closed_eyes_detection": "Geschlossene Augen erkennen",
        "redeye_detection": "Rote-Augen Effekt erkennen",
        "eye_detection": "Augen-Erkennung:",
        "error_detection": "Fehler-Erkennung:",
        "blur_detection": "Unschärfe-Erkennung",
        "contrast_detection": "Kontrast-Erkennung",
        "noise_detection": "Rauschen-Erkennung",
        "closed_eyes_warning": "Geschlossene Augen erkannt",
        "blur_warning": "Unschärfe erkannt",
        
        # Export settings
        "export_format": "Dateiformat für Export:",
        "compression_quality": "Kompression-Qualität:",
        "similarity_threshold": "Ähnlichkeitsschwelle:",
        "keep_originals": "Originaldateien behalten (nicht verschieben)",
        "auto_backup": "Automatische Sicherung vor Löschung",
        "confirm_delete": "Bestätigung vor Löschung",
        
        # Analysis dialog
        "analysis_running": "Analyse läuft...",
        "initializing": "Initialisierung...",
        "analysis_completed": "✓ Analyse abgeschlossen",
        "analysis_failed": "✗ Analyse fehlgeschlagen",
        "analysis_wait": "Bitte warten Sie, während Ihre Bilder analysiert werden.\nDieser Vorgang kann einige Minuten dauern.",
        "cancel_analysis": "Abbrechen",
        
        # Settings dialog
        "settings_title": "⚙️ Einstellungen",
        "quality_tab": "🎨 Qualität",
        "detection_tab": "👁 Erkennung",
        "export_tab": "💾 Export",
        "behavior_settings": "⚙ Verhalten",
        "reset_settings": "↻ Zurücksetzen",
        "save_settings": "💾 Speichern",
        "maintenance_tab": "🧹 Wartung",
        "hide_completed_groups": "Abgeschlossene Gruppen ausblenden",
        "maintenance": "Wartung",
        "clear_cache": "Cache leeren",
        "reset_pipeline_db": "Pipeline zurücksetzen (DB)",
        "actions_unavailable": "Aktionen nicht verfügbar.",
        "clear_cache_title": "Cache leeren",
        "clear_cache_confirm": "Soll der Cache wirklich geleert werden?",
        "cache_cleared_title": "Cache geleert",
        "cache_cleared_msg": "Cache wurde erfolgreich geleert.",
        "cache_clear_failed": "Cache konnte nicht geleert werden.",
        "reset_pipeline_title": "Pipeline zurücksetzen",
        "reset_pipeline_confirm": "Dieser Vorgang setzt Gruppen, Entscheidungen und Caches zurück. Fortfahren?",
        "reset_pipeline_done_title": "Zurückgesetzt",
        "reset_pipeline_done_msg": "Pipeline-Status wurde zurückgesetzt.",
        "reset_pipeline_failed": "Zurücksetzen fehlgeschlagen.",
        "error": "Fehler",
        
        # Hotkeys help
        "hotkey_title": "Hotkeys & Bedienung",
        "navigation": "<b>Navigation:</b>",
        "hotkey_switch_group": "  Ctrl+J / Ctrl+K - Gruppe wechseln",
        "hotkey_navigate_image": "  Links/Rechts - Bild navigieren",
        "actions": "<b>Aktionen:</b>",
        "hotkey_keep": "  K - Keep (behalten)",
        "hotkey_delete": "  D - Delete (löschen markieren)",
        "hotkey_unsure": "  U - Unsure (unsicher)",
        "hotkey_lock": "  Space - Lock/Unlock",
        "hotkey_undo": "  Z - Undo letzte Aktion",
        "hotkey_fullscreen": "  F - Fullscreen Vorschau",
        "ui_control": "<b>UI-Steuerung (Dropdowns hinzugefügt):</b>",
        "hotkey_mode": "  Mode-Dropdown - SAFE/REVIEW/CLEANUP wählen",
        "hotkey_theme": "  Theme-Dropdown - Dark/Light/System/High-Contrast",
        "hotkey_help": "  ? - Dieses Overlay",
        "hotkey_search": "  Strg+F - Suche",
        
        # Main window
        "groups": "Gruppen",
        "details": "Details",
        "finalize_export": "✓ Fertigstellen & Exportieren",
        "finalize_export_tooltip": "Exportiert alle als KEEP markierten Bilder in die Zielstruktur",
        "no_selection_display": "Keine Auswahl",
        "preview_unavailable": "(Vorschau nicht verfügbar)",
        "action_success": "✓ Aktion erfolgreich",
        "action_error": "✗ {msg}",
        
        # Folder selection dialog
        "select_input_folder_label": "<b>1. Foto-Ordner auswählen</b>",
        "select_output_folder_label": "<b>2. Zielordner auswählen</b>",
        "select_topn_label": "<b>3. Top-N für Auto-Auswahl</b>",
        "topn_value_label": "Top-N:",
        "topn_hint_text": "Wie viele beste Bilder pro Duplikat-Gruppe automatisch behalten werden",
        "quality_settings_label": "<b>Qualitäts-Einstellungen</b>",
        "analysis_starts": "Analyse startet automatisch nach Import...",
        "quality_settings_for_analysis": "<b>Qualitäts-Einstellungen für die Analyse</b>",
        "presets_label": "Vorgaben:",
        
        # License dialog
        "license_management": "Lizenz-Verwaltung",
        "license_status_tab": "Status",
        "license_features_tab": "Features",
        "license_activate_tab": "Aktivieren",
        "license_batch_processing": "Massenverarbeitung",
        "license_heic_support": "HEIC/HEIF-Format",
        "license_extended_cache": "Erweitertes Caching",
        "license_advanced_quality": "Erweiterte Qualitätsanalyse",
        "license_bulk_delete": "Batch-Löschung",
        "license_no_watermark": "Kein Wasserzeichen",
        "license_api_access": "API-Zugriff",
        "license_confirm_activation": "Bestätigung erforderlich",
        "license_activate_success": "Lizenz erfolgreich aktiviert!",
        "license_activate_failed": "Aktivierung fehlgeschlagen",
        "license_key_label": "Schlüssel",
        "license_key_placeholder": "z.B. TEST-20260126-001",
        "license_online_licensing": "Online-Lizenzierung",
        "license_online_info_html": """<b>Online-Lizenzierung mit Supabase</b>

    • <b>FREE-Lizenz:</b> kostenlos per E-Mail-Aktivierung
    • <b>FREE-Kontingent:</b> einmalig 250 Bilder (Lebenszeit)
    • <b>PRO-Lizenz:</b> unbegrenzte Bilder + Premium-Features
    • <b>Cloud Sync:</b> Lizenzstatus wird nach Wiederherstellung der Verbindung synchronisiert

<b>Pläne:</b>
    • <b>FREE</b> - Einstieg (250 Bilder gesamt)
    • <b>PRO</b> - Professionell (Cloud, 3 Geräte, unbegrenzt)

<b>Aktivierung:</b>
Geben Sie Ihren Lizenzschlüssel oben ein und klicken Sie auf "Aktivieren".
    Das Gerät wird automatisch registriert.""",
        "license_plan_comparison_html": """<style>
    table { border-collapse: collapse; width: 100%; margin: 10px 0; }
    th { background: #333; color: white; padding: 12px; text-align: center; font-weight: bold; }
    td { padding: 10px; border: 1px solid #444; text-align: center; }
    .feature-name { text-align: left; font-weight: bold; background: #2a2a2a; }
    .check { color: #4CAF50; font-size: 18px; }
    .cross { color: #666; font-size: 18px; }
    .plan-free { background: #1a1a1a; }
    .plan-pro { background: #2a2a2a; }
    .price { font-size: 20px; font-weight: bold; color: #FF9800; }
    .highlight { background: #FF9800; color: white; padding: 4px 8px; border-radius: 4px; }
</style>

<h2>📊 Plan-Vergleich</h2>

<table>
    <tr>
        <th class="feature-name">Feature / Limit</th>
        <th class="plan-free">FREE<br><span class="price">€0</span></th>
        <th class="plan-pro">PRO ⭐<br><span class="price">ab €19/Jahr</span></th>
    </tr>
    
    <!-- Basis-Features -->
    <tr>
        <td class="feature-name">🔍 Bildanalyse & Duplikatsuche</td>
        <td class="plan-free"><span class="check">✓</span></td>
        <td class="plan-pro"><span class="check">✓</span></td>
    </tr>
    <tr>
        <td class="feature-name">📊 Bildlimit</td>
        <td class="plan-free">250 Bilder gesamt</td>
        <td class="plan-pro"><span class="highlight">Unbegrenzt</span></td>
    </tr>
    <tr>
        <td class="feature-name">💻 Geräte-Limit</td>
        <td class="plan-free">1 Gerät</td>
        <td class="plan-pro">3 Geräte</td>
    </tr>
    
    <!-- PRO Features -->
    <tr>
        <td class="feature-name">🚀 Batch-Verarbeitung (Massen-Import)</td>
        <td class="plan-free"><span class="cross">✗</span></td>
        <td class="plan-pro"><span class="check">✓</span></td>
    </tr>
    <tr>
        <td class="feature-name">📷 HEIC/HEIF-Format Support</td>
        <td class="plan-free"><span class="cross">✗</span></td>
        <td class="plan-pro"><span class="check">✓</span></td>
    </tr>
    <tr>
        <td class="feature-name">⚡ Erweitertes Caching (2-8x schneller)</td>
        <td class="plan-free"><span class="cross">✗</span></td>
        <td class="plan-pro"><span class="check">✓</span></td>
    </tr>
    <tr>
        <td class="feature-name">🎯 Qualitätsanalyse (Schärfe/Belichtung/Details)</td>
        <td class="plan-free">Basis</td>
        <td class="plan-pro"><span class="highlight">Erweitert</span></td>
    </tr>
    <tr>
        <td class="feature-name">📦 Batch-Löschung</td>
        <td class="plan-free"><span class="cross">✗</span></td>
        <td class="plan-pro"><span class="check">✓</span></td>
    </tr>
    <tr>
        <td class="feature-name">📄 Export-Formate (CSV, JSON)</td>
        <td class="plan-free"><span class="cross">✗</span></td>
        <td class="plan-pro"><span class="check">✓</span></td>
    </tr>
    <tr>
        <td class="feature-name">📧 Support</td>
        <td class="plan-free"><span class="cross">✗</span></td>
        <td class="plan-pro">Email</td>
    </tr>
    <tr>
        <td class="feature-name">📱 Offline Grace Period</td>
        <td class="plan-free">-</td>
        <td class="plan-pro">7 Tage</td>
    </tr>
</table>

<br>
<p><b>💡 Empfehlung:</b></p>
<ul>
    <li><b>FREE:</b> Testen & kleine Sammlungen (bis 250 Bilder gesamt)</li>
    <li><b>PRO:</b> Regelmäßige Nutzung mit unbegrenzten Bildern</li>
</ul>""",
        "license_your_plan": "Dein Plan",
        "license_plan_standard": "Standard",
        "license_plan_active": "Aktiv",
        "license_basic_features": "Basis-Features",
        "license_invalid": "ungültig",
        "license_free_details": """Lizenz: FREE (Basis-Features)
    Limit: Einmalig 250 Bilder (Lebenszeit-Kontingent)
Status: Offline-Nutzung aktiv

💡 Für unbegrenzte Bilder und Premium-Features:
       → Upgrade auf PRO""",
        "license_label": "Lizenz",
        "license_user": "Benutzer",
        "license_not_assigned": "Nicht zugewiesen",
        "license_machine_id": "Maschinen-ID",
        "license_expires": "Ablauf",
        "license_signature": "Signatur",
        "license_valid": "Gültig",
        "license_machine": "Maschine",
        "license_correct": "Korrekt",
        "license_mismatch": "Abweichung",
        "license_no_premium_features": "Keine Premium-Features aktiviert",
        "license_configuration": "Konfiguration",
        "license_supabase_not_configured": "Supabase-Parameter nicht gesetzt (SUPABASE_PROJECT_URL, SUPABASE_ANON_KEY).",
        "license_remove_confirmation": "Lizenz entfernen? Sie kehren zu FREE-Tier zurück.",
        "license_removed_success": "Lizenz wurde entfernt.",
        "license_removed_failed": "Lizenz konnte nicht entfernt werden.",
        
        # Installation dialog
        "installation_title": "🔧 Erweiterte Augenerkennung installieren",
        "installation_log": "Installations-Log:",
        "install_button": "Installieren",
        "close_button": "Schließen",
        "previous_image": "Vorheriges Bild",
        "next_image": "Nächstes Bild",
        "merge_groups": "Gruppen zusammenführen",
        "merge_success": "Gruppen erfolgreich zusammengeführt",
        "merge_failed": "Zusammenführen fehlgeschlagen",
        
        # Selection and comparison
        "selection_none_bold": "<b>Keine Auswahl</b>",
        "compare_select_two": "🔍 Vergleichen (2 auswählen)",
        "selection_one_image": "<b>1 Bild ausgewählt</b>",
        "compare_need_two": "🔍 Vergleichen (2 benötigt)",
        "selection_two_images": "<b>2 Bilder ausgewählt</b>",
        "compare_side_by_side": "🔍 Seite-an-Seite Vergleich",
        "selection_n_images": "<b>{count} Bilder ausgewählt</b>",
        "compare_select_exactly_two": "🔍 Vergleichen (genau 2 wählen)",
        "invalid_selection": "Ungültige Auswahl",
        "select_exactly_two_images": "Bitte wählen Sie genau 2 Bilder zum Vergleichen aus.",
        "comparison_window_failed": "Vergleichsfenster konnte nicht geöffnet werden",
        "no_images_selected_error": "Keine Bilder ausgewählt",
        "no_valid_images_to_update": "Keine gültigen Bilder zum Aktualisieren",
        "images_updated_count": "{success}/{total} Bild(er) aktualisiert",
        "error_message": "Fehler: {error}",
        "lock_toggled_count": "Sperre bei {count} Bild(ern) umgeschaltet",
        
        # Error/Warning messages
        "no_output_folder_title": "Kein Output-Ordner",
        "no_output_folder_msg": "Es wurde kein Output-Ordner festgelegt. Export nicht möglich.",
        "no_images_selected": "Keine Auswahl",
        "no_images_selected_msg": "Es wurden keine Bilder zum Behalten markiert.",
        "finalize_confirmation": "Fertigstellen?",
        "finalize_confirmation_msg": "Möchten Sie die Auswahl wirklich speichern und exportieren?",
        "finalize_success": "✓ Export erfolgreich abgeschlossen",
        "finalize_partial": "⚠ Export mit Warnungen abgeschlossen",
        "finalize_failed": "✗ Export fehlgeschlagen",
        "reset_settings_confirm": "Einstellungen zurücksetzen?",
        "reset_settings_confirm_msg": "Alle Einstellungen werden auf Standardwerte zurückgesetzt.",
        
        # Status bar
        "mode_label": "Modus",
        "theme_label": "Theme",
        "progress_format": "%p% Dateien entschieden",
        
        # Folder selection dialog
        "select_input_folder_label": "<b>1. Foto-Ordner auswählen</b>",
        "select_output_folder_label": "<b>2. Zielordner für ausgewählte Fotos</b>",
        "select_topn_label": "<b>3. Top-N pro Gruppe</b>",
        "output_folder_required": "<span style='color: #F44336;'>*Erforderlich</span>",
        "help_dialog_content": "PhotoCleaner - Intelligente Fotoverwaltung\n\nWorkflow:\n1. 📁 Import: Wähle einen Ordner mit Bildern\n2. ▶ Analyse: Findet doppelte Bilder automatisch\n3. ⚙ Einstellungen: Passe Qualitäts-Parameter an\n4. Entscheide für jedes Bild: Behalten oder Löschen\n\nTastaturkürzel:\n? = Diese Hilfe\nDelete = Markiere zum Löschen\nK = Behalte Bild\nSpace = Nächstes Bild",
        "closed_eyes_detection": "Geschlossene Augen erkennen",
        "redeye_detection": "Rote-Augen Effekt erkennen",
        "blurry_detection": "Unscharfe Fotos",
        "underexposed_detection": "Unterbelichtet",
        "overexposed_detection": "Überbelichtet",
        "close_button": "Schließen",
        "reset_button": "Zurücksetzen",
        "image_analysis_async": "Bildanalyse läuft",
        "image_analysis": "Bildanalyse läuft",
        "min_eye_size": "Minimale Augengröße (Pixel):",
        "delete_button": "🗑 Löschen",
        "reset_icon": "↺ Zurücksetzen",
        "not_possible": "Nicht möglich",
        "select_group_message": "<h3>Wählen Sie eine Gruppe aus</h3>",
        "actions_on_selection": "<b>Aktionen auf Auswahl:</b>",
        "undo_button": "↶ Rückgängig (Z)",
        "no_selection_msg": "Keine Auswahl",
        "export_running": "Export läuft (Streaming)",
        "no_deletions": "Keine Löschungen",
        "delete_completed": "Löschen abgeschlossen",
        "keyboard_shortcuts": "Tastaturkürzel",
        "keyboard_shortcuts_detailed": """
        <h3>PhotoCleaner Tastaturkürzel</h3>
        <p><b>Navigation:</b></p>
        <ul>
            <li>Strg+J / Strg+K - Nächste/Vorherige Gruppe</li>
            <li>Karte klicken - Detailansicht öffnen</li>
            <li>Strg+Klick - Auswahl umschalten</li>
            <li>Umschalt+Klick - Bereichsauswahl</li>
        </ul>
        <p><b>Aktionen:</b></p>
        <ul>
            <li>D - Löschen bestätigen</li>
        </ul>
        <p><b>Mehrfachauswahl:</b></p>
        <ul>
            <li>Strg+Klick - Auswahl umschalten</li>
        </ul>
        <p><b>Zoom (in Detailansicht):</b></p>
        <ul>
            <li>Mausrad - Hinein-/Herauszoomen</li>
            <li>Strg+Mausrad - Feiner Zoom</li>
            <li>+/- - Hinein-/Herauszoomen</li>
            <li>0 - Zoom zurücksetzen</li>
            <li>Doppelklick - An Ansicht anpassen</li>
            <li>Ziehen - Bild verschieben</li>
        </ul>
        <p><b>Sonstiges:</b></p>
        <ul>
            <li>Strg+F - Suche fokussieren</li>
            <li>? - Diese Hilfe anzeigen</li>
        </ul>
        """,
        "build_tools_required": "Build Tools werden für dlib benötigt. MediaPipe ist eine einfachere Alternative.",
        "install_both_option": "<b>Beide installieren</b><br><i>Maximale Flexibilität</i>",
        "app_mode_tooltip": "Wähle App-Mode: SAFE (nur lesen), REVIEW (markieren), CLEANUP (löschen erlaubt)",
        "ui_theme_tooltip": "Wähle UI-Theme",
        "unsure_button": "? Unsicher (U)",
        "lock_unlock_button": "🔒 Sperren/Entsperren (Leer)",
        "finalize_export": "✓ Exportieren",
        "splash_loading_app": "Initialisiere PhotoCleaner",
        "splash_loading_ui": "Lade UI-Module",
        "splash_loading_image_processing": "Lade Bildverarbeitung",
        "splash_preparing_ui": "Bereite Benutzeroberfläche vor",
        "splash_starting": "Starte Anwendung",
        "splash_version": "Version",
    },
    "en": {
        # Menu (no icons; icons are added in code)
        "import": "Import",
        "settings": "Settings",
        "license": "License",
        "help": "Help",
        "language": "Language",
        "language_dialog_title": "Select language",
        "language_dialog_desc": "Choose the UI language. Changes apply immediately.",
        "apply": "Apply",
        "theme": "Theme",
        "browse": "Browse...",
        "duplicate_groups": "Duplicate Groups",
        "search_placeholder": "🔍 Search...",
        "select_folders_title": "PhotoCleaner - Select folders",
        "select_folders_subtitle": "Pick folders and Top-N for auto selection",
        "start_analysis": "Start analysis",
        "input_hint": "Choose the folder with photos you want to sort.",
        "output_hint": "Choose the target folder for exported images.",
        "topn_hint": "How many top photos per group should be kept automatically.",
        "output_required": "⚠ Please select a target folder",
        "work_existing": "ℹ You can work with existing data or pick a photos folder",
        "ready_to_start": "✓ Ready to start",
        "pick_group": "Select a group",
        "quick_actions": "Quick actions",
        
        # Tips panel
        "tips": "Tips",
        "tip_ctrl_click": "Ctrl+Click: Toggle selection",
        "tip_shift_click": "Shift+Click: Range selection",
        "tip_click_card": "Click card: Open detail view",
        "clear_selection": "☐ Clear selection",
        "compare_two": "🔍 Compare (2 selected)",
        "keep": "✓ Keep (K)",
        "delete_confirm": "🗑 Confirm delete",
        "select_multiple": "Multi-select:",
        "select_all": "☑ Select all",
        
        # Dialogs & Messages
        "welcome": "Welcome to PhotoCleaner",
        "select_folders": "Select Folders",
        "input_folder": "Input Folder",
        "output_folder": "Output Folder",
        "start": "✓ Start",
        "cancel": "Cancel",
        "analyze": "▶ Analyze",
        "analyzing": "Analyzing images...",
        "no_selection": "No Selection",
        "select_images": "Please select images",
        "keep": "✓ Keep (K)",
        "delete": "🗑 Confirm Delete",
        "unsure": "? Unsure (U)",
        "compare": "🔍 Compare",
        "export": "✓ Export",
        "close": "Close",
        "ok": "OK",
        
        # Status messages
        "ready": "Ready",
        "analyzing_status": "Analyzing images...",
        "indexed": "Images indexed",
        "processing": "Processing",
        "complete": "Complete",
        "page_info": "Page {page}/{total} • {start}-{end} of {count}",
        "groups_count": "📊 {count} Groups",
        "select_group": "Select a group",
        "group_title": "Group {id} ({count} images)",
        "preview_from_input": "Preview from input folder",
        "no_images_imported": "No images imported",
        "images_loaded": "{count} images loaded",
        "sync_pan_on": "Sync Pan: ON",
        "sync_pan_off": "Sync Pan: OFF",
        "select_output_folder_title": "Select output folder (Where selected photos will be saved)",
        "quality_settings": "Quality Settings",
        
        # Language names
        "language_de": "Deutsch",
        "language_en": "English",
        
        # Theme names
        "theme_dark": "Dark",
        "theme_light": "Light",
        
        # Tooltips
        "import_tooltip": "Select folder, analysis starts automatically",
        "settings_tooltip": "Quality and detection settings",
        "license_tooltip": "Manage license",
        "help_tooltip": "Help & Keyboard Shortcuts",
        
        # Dialog titles and buttons
        "select_input_folder_title": "Select Input Folder",
        "select_output_folder_title_short": "Select Output Folder",
        "analyze_started": "Analysis started",
        "folderselection_dialog_title": "PhotoCleaner - Select Folders",
        
        # Quality settings UI
        "quality_weights": "Quality Weighting",
        "exposure": "Exposure",
        "blur": "Blur",
        "contrast": "Contrast",
        "noise": "Noise",
        "presets": "Presets",
        "preset_quality_profiles": "Quick selection of quality profiles:",
        "closed_eyes_detection": "Detect closed eyes",
        "redeye_detection": "Red-eye detection",
        "eye_detection": "Eye Detection:",
        "error_detection": "Error Detection:",
        "blur_detection": "Blur detection",
        "contrast_detection": "Contrast detection",
        "noise_detection": "Noise detection",
        "closed_eyes_warning": "Closed eyes detected",
        "blur_warning": "Blur detected",
        
        # Export settings
        "export_format": "File format for export:",
        "compression_quality": "Compression quality:",
        "similarity_threshold": "Similarity threshold:",
        "keep_originals": "Keep original files (do not move)",
        "auto_backup": "Automatic backup before deletion",
        "confirm_delete": "Confirmation before deletion",
        
        # Analysis dialog
        "analysis_running": "Analysis running...",
        "initializing": "Initializing...",
        "analysis_completed": "✓ Analysis completed",
        "analysis_failed": "✗ Analysis failed",
        "analysis_wait": "Please wait while your images are being analyzed.\nThis may take several minutes.",
        "cancel_analysis": "Cancel",
        
        # Settings dialog
        "settings_title": "⚙️ Settings",
        "quality_tab": "🎨 Quality",
        "detection_tab": "👁 Detection",
        "export_tab": "💾 Export",
        "behavior_settings": "⚙ Behavior",
        "reset_settings": "↻ Reset",
        "save_settings": "💾 Save",
        "maintenance_tab": "🧹 Maintenance",
        "hide_completed_groups": "Hide completed groups",
        "maintenance": "Maintenance",
        "clear_cache": "Clear cache",
        "reset_pipeline_db": "Reset pipeline (DB)",
        "actions_unavailable": "Actions not available.",
        "clear_cache_title": "Clear cache",
        "clear_cache_confirm": "Do you really want to clear the cache?",
        "cache_cleared_title": "Cache cleared",
        "cache_cleared_msg": "Cache was cleared successfully.",
        "cache_clear_failed": "Cache could not be cleared.",
        "reset_pipeline_title": "Reset pipeline",
        "reset_pipeline_confirm": "This will reset groups, decisions, and caches. Continue?",
        "reset_pipeline_done_title": "Reset complete",
        "reset_pipeline_done_msg": "Pipeline state was reset.",
        "reset_pipeline_failed": "Reset failed.",
        "error": "Error",
        
        # Hotkeys help
        "hotkey_title": "Hotkeys & Controls",
        "navigation": "<b>Navigation:</b>",
        "hotkey_switch_group": "  Ctrl+J / Ctrl+K - Switch group",
        "hotkey_navigate_image": "  Left/Right - Navigate image",
        "actions": "<b>Actions:</b>",
        "hotkey_keep": "  K - Keep",
        "hotkey_delete": "  D - Delete (mark)",
        "hotkey_unsure": "  U - Unsure",
        "hotkey_lock": "  Space - Lock/Unlock",
        "hotkey_undo": "  Z - Undo last action",
        "hotkey_fullscreen": "  F - Fullscreen preview",
        "ui_control": "<b>UI Control (Dropdowns added):</b>",
        "hotkey_mode": "  Mode dropdown - Choose SAFE/REVIEW/CLEANUP",
        "hotkey_theme": "  Theme dropdown - Dark/Light/System/High-Contrast",
        "hotkey_help": "  ? - This overlay",
        "hotkey_search": "  Ctrl+F - Search",
        
        # Main window
        "groups": "Groups",
        "details": "Details",
        "finalize_export": "✓ Finalize & Export",
        "finalize_export_tooltip": "Exports all images marked as KEEP to target directory",
        "no_selection_display": "No selection",
        "preview_unavailable": "(Preview unavailable)",
        "action_success": "✓ Action successful",
        "action_error": "✗ {msg}",
        
        # Folder selection dialog
        "select_input_folder_label": "<b>1. Select photo folder</b>",
        "select_output_folder_label": "<b>2. Select target folder</b>",
        "select_topn_label": "<b>3. Top-N for auto selection</b>",
        "topn_value_label": "Top-N:",
        "topn_hint_text": "How many best images per duplicate group should be kept automatically",
        "quality_settings_label": "<b>Quality Settings</b>",
        "analysis_starts": "Analysis starts automatically after import...",
        "quality_settings_for_analysis": "<b>Quality settings for analysis</b>",
        "presets_label": "Presets:",
        
        # License dialog
        "license_management": "License Management",
        "license_status_tab": "Status",
        "license_features_tab": "Features",
        "license_activate_tab": "Activate",
        "license_batch_processing": "Batch Processing",
        "license_heic_support": "HEIC/HEIF Format",
        "license_extended_cache": "Extended Caching",
        "license_advanced_quality": "Advanced Quality Analysis",
        "license_bulk_delete": "Bulk Delete",
        "license_no_watermark": "No Watermark",
        "license_api_access": "API Access",
        "license_confirm_activation": "Confirmation required",
        "license_activate_success": "License activated successfully!",
        "license_activate_failed": "Activation failed",
        "license_key_label": "Key",
        "license_key_placeholder": "e.g. TEST-20260126-001",
        "license_online_licensing": "Online Licensing",
        "license_online_info_html": """<b>Online Licensing with Supabase</b>

    • <b>FREE license:</b> free email-based activation
    • <b>FREE quota:</b> one-time 250 images (lifetime)
    • <b>PRO license:</b> unlimited images + premium features
    • <b>Cloud Sync:</b> License status is synchronized after connection is restored

<b>Plans:</b>
    • <b>FREE</b> - Starter (250 images total)
    • <b>PRO</b> - Professional (Cloud, 3 devices, unlimited)

<b>Activation:</b>
Enter your license key above and click "Activate".
    The device will be registered automatically.""",
        "license_plan_comparison_html": """<style>
    table { border-collapse: collapse; width: 100%; margin: 10px 0; }
    th { background: #333; color: white; padding: 12px; text-align: center; font-weight: bold; }
    td { padding: 10px; border: 1px solid #444; text-align: center; }
    .feature-name { text-align: left; font-weight: bold; background: #2a2a2a; }
    .check { color: #4CAF50; font-size: 18px; }
    .cross { color: #666; font-size: 18px; }
    .plan-free { background: #1a1a1a; }
    .plan-pro { background: #2a2a2a; }
    .price { font-size: 20px; font-weight: bold; color: #FF9800; }
    .highlight { background: #FF9800; color: white; padding: 4px 8px; border-radius: 4px; }
</style>

<h2>📊 Plan Comparison</h2>

<table>
    <tr>
        <th class="feature-name">Feature / Limit</th>
        <th class="plan-free">FREE<br><span class="price">€0</span></th>
        <th class="plan-pro">PRO ⭐<br><span class="price">from €19/year</span></th>
    </tr>
    
    <!-- Basic Features -->
    <tr>
        <td class="feature-name">🔍 Image Analysis & Duplicate Detection</td>
        <td class="plan-free"><span class="check">✓</span></td>
        <td class="plan-pro"><span class="check">✓</span></td>
    </tr>
    <tr>
        <td class="feature-name">📊 Image Limit</td>
        <td class="plan-free">250 images total</td>
        <td class="plan-pro"><span class="highlight">Unlimited</span></td>
    </tr>
    <tr>
        <td class="feature-name">💻 Device Limit</td>
        <td class="plan-free">1 device</td>
        <td class="plan-pro">3 devices</td>
    </tr>
    
    <!-- PRO Features -->
    <tr>
        <td class="feature-name">🚀 Batch Processing (Mass Import)</td>
        <td class="plan-free"><span class="cross">✗</span></td>
        <td class="plan-pro"><span class="check">✓</span></td>
    </tr>
    <tr>
        <td class="feature-name">📷 HEIC/HEIF Format Support</td>
        <td class="plan-free"><span class="cross">✗</span></td>
        <td class="plan-pro"><span class="check">✓</span></td>
    </tr>
    <tr>
        <td class="feature-name">⚡ Extended Caching (2-8x faster)</td>
        <td class="plan-free"><span class="cross">✗</span></td>
        <td class="plan-pro"><span class="check">✓</span></td>
    </tr>
    <tr>
        <td class="feature-name">🎯 Quality Analysis (Sharpness/Exposure/Details)</td>
        <td class="plan-free">Basic</td>
        <td class="plan-pro"><span class="highlight">Advanced</span></td>
    </tr>
    <tr>
        <td class="feature-name">📦 Batch Deletion</td>
        <td class="plan-free"><span class="cross">✗</span></td>
        <td class="plan-pro"><span class="check">✓</span></td>
    </tr>
    <tr>
        <td class="feature-name">📄 Export Formats (CSV, JSON)</td>
        <td class="plan-free"><span class="cross">✗</span></td>
        <td class="plan-pro"><span class="check">✓</span></td>
    </tr>
    <tr>
        <td class="feature-name">📧 Support</td>
        <td class="plan-free"><span class="cross">✗</span></td>
        <td class="plan-pro">Email</td>
    </tr>
    <tr>
        <td class="feature-name">📱 Offline Grace Period</td>
        <td class="plan-free">-</td>
        <td class="plan-pro">7 days</td>
    </tr>
</table>

<br>
<p><b>💡 Recommendation:</b></p>
<ul>
    <li><b>FREE:</b> Testing & small collections (up to 250 images total)</li>
    <li><b>PRO:</b> Regular use with unlimited images</li>
</ul>""",
        "license_your_plan": "Your Plan",
        "license_plan_standard": "Standard",
        "license_plan_active": "Active",
        "license_basic_features": "Basic Features",
        "license_invalid": "invalid",
        "license_free_details": """License: FREE (Basic Features)
    Limit: One-time 250 images (lifetime quota)
Status: Offline usage active

💡 For unlimited images and premium features:
       → Upgrade to PRO""",
        "license_label": "License",
        "license_user": "User",
        "license_not_assigned": "Not assigned",
        "license_machine_id": "Machine ID",
        "license_expires": "Expires",
        "license_signature": "Signature",
        "license_valid": "Valid",
        "license_machine": "Machine",
        "license_correct": "Correct",
        "license_mismatch": "Mismatch",
        "license_no_premium_features": "No premium features enabled",
        "license_configuration": "Configuration",
        "license_supabase_not_configured": "Supabase parameters not configured (SUPABASE_PROJECT_URL, SUPABASE_ANON_KEY).",
        "license_remove_confirmation": "Remove license? You will return to FREE tier.",
        "license_removed_success": "License was removed.",
        "license_removed_failed": "License could not be removed.",
        
        # Installation dialog
        "installation_title": "🔧 Install Advanced Eye Detection",
        "installation_log": "Installation log:",
        "install_button": "Install",
        "close_button": "Close",
        "previous_image": "Previous Image",
        "next_image": "Next Image",
        "merge_groups": "Merge Groups",
        "merge_success": "Groups merged successfully",
        "merge_failed": "Merge failed",
        
        # Selection and comparison
        "selection_none_bold": "<b>No selection</b>",
        "compare_select_two": "🔍 Compare (select 2)",
        "selection_one_image": "<b>1 image selected</b>",
        "compare_need_two": "🔍 Compare (2 required)",
        "selection_two_images": "<b>2 images selected</b>",
        "compare_side_by_side": "🔍 Side-by-Side Comparison",
        "selection_n_images": "<b>{count} images selected</b>",
        "compare_select_exactly_two": "🔍 Compare (select exactly 2)",
        "invalid_selection": "Invalid Selection",
        "select_exactly_two_images": "Please select exactly 2 images to compare.",
        "comparison_window_failed": "Comparison window could not be opened",
        "no_images_selected_error": "No images selected",
        "no_valid_images_to_update": "No valid images to update",
        "images_updated_count": "{success}/{total} image(s) updated",
        "error_message": "Error: {error}",
        "lock_toggled_count": "Lock toggled for {count} image(s)",
        
        # Error/Warning messages
        "no_output_folder_title": "No Output Folder",
        "no_output_folder_msg": "No output folder has been set. Export not possible.",
        "no_images_selected": "No selection",
        "no_images_selected_msg": "No images have been marked for keeping.",
        "finalize_confirmation": "Finalize?",
        "finalize_confirmation_msg": "Do you really want to save the selection and export?",
        "finalize_success": "✓ Export completed successfully",
        "finalize_partial": "⚠ Export completed with warnings",
        "finalize_failed": "✗ Export failed",
        "reset_settings_confirm": "Reset settings?",
        "reset_settings_confirm_msg": "All settings will be reset to default values.",
        
        # Status bar
        "mode_label": "Mode",
        "theme_label": "Theme",
        "progress_format": "%p% Files decided",
        
        # Folder selection dialog
        "select_input_folder_label": "<b>1. Select photo folder</b>",
        "select_output_folder_label": "<b>2. Select target folder for photos</b>",
        "select_topn_label": "<b>3. Top-N per group</b>",
        "output_folder_required": "<span style='color: #F44336;'>*Required</span>",
        "help_dialog_content": "PhotoCleaner - Intelligent Photo Management\n\nWorkflow:\n1. 📁 Import: Choose a folder with photos\n2. ▶ Analysis: Find duplicate photos automatically\n3. ⚙ Settings: Adjust quality parameters\n4. Decide for each photo: Keep or Delete\n\nKeyboard Shortcuts:\n? = This help\nDelete = Mark for deletion\nK = Keep photo\nSpace = Next photo",
        "closed_eyes_detection": "Detect closed eyes",
        "redeye_detection": "Detect red-eye effect",
        "blurry_detection": "Blurry photos",
        "underexposed_detection": "Underexposed",
        "overexposed_detection": "Overexposed",        "close_button": "Close",
        "reset_button": "Reset",
        "image_analysis_async": "Image analysis running",
        "image_analysis": "Image analysis running",
        "min_eye_size": "Minimum eye size (pixels):",
        "delete_button": "🗑 Delete",
        "reset_icon": "↺ Reset",
        "not_possible": "Not possible",
        "select_group_message": "<h3>Select a group</h3>",
        "actions_on_selection": "<b>Actions on selection:</b>",
        "undo_button": "↶ Undo (Z)",
        "no_selection_msg": "No selection",
        "export_running": "Export running (Streaming)",
        "no_deletions": "No deletions",
        "delete_completed": "Deletion completed",
        "keyboard_shortcuts": "Keyboard shortcuts",
        "keyboard_shortcuts_detailed": """
        <h3>PhotoCleaner Keyboard Shortcuts</h3>
        <p><b>Navigation:</b></p>
        <ul>
            <li>Ctrl+J / Ctrl+K - Next/Previous group</li>
            <li>Click card - Open detail view</li>
            <li>Ctrl+Click - Toggle selection</li>
            <li>Shift+Click - Range selection</li>
        </ul>
        <p><b>Actions:</b></p>
        <ul>
            <li>D - Confirm delete</li>
        </ul>
        <p><b>Multi-selection:</b></p>
        <ul>
            <li>Ctrl+Click - Toggle selection</li>
        </ul>
        <p><b>Zoom (in detail view):</b></p>
        <ul>
            <li>Mouse wheel - Zoom in/out</li>
            <li>Ctrl+Mouse wheel - Fine zoom</li>
            <li>+/- - Zoom in/out</li>
            <li>0 - Reset zoom</li>
            <li>Double-click - Fit to view</li>
            <li>Drag - Pan image</li>
        </ul>
        <p><b>Other:</b></p>
        <ul>
            <li>Ctrl+F - Focus search</li>
            <li>? - Show this help</li>
        </ul>
        """,
        "build_tools_required": "Build tools are required for dlib. MediaPipe is a simpler alternative.",
        "install_both_option": "<b>Install both</b><br><i>Maximum flexibility</i>",
        "app_mode_tooltip": "Choose app mode: SAFE (read-only), REVIEW (mark), CLEANUP (allow delete)",
        "ui_theme_tooltip": "Choose UI theme",
        "unsure_button": "? Unsure (U)",
        "lock_unlock_button": "🔒 Lock/Unlock (Space)",
        "finalize_export": "✓ Export",
        "splash_loading_app": "Initializing PhotoCleaner",
        "splash_loading_ui": "Loading UI modules",
        "splash_loading_image_processing": "Loading image processing",
        "splash_preparing_ui": "Preparing user interface",
        "splash_starting": "Starting application",
        "splash_version": "Version",
    }
}

# Current language
_current_language: str = "de"


def set_language(lang: str) -> None:
    """Set current language (de or en)."""
    global _current_language
    if lang in TRANSLATIONS:
        _current_language = lang
        logger.info(f"Language switched to: {lang}")
    else:
        logger.warning(f"Unknown language: {lang}, using default (de)")


def get_language() -> str:
    """Get current language code."""
    return _current_language


def translate(key: str, language: Optional[str] = None) -> str:
    """Translate key to current or specified language.
    
    Args:
        key: Translation key (e.g., "import", "ready")
        language: Optional language code (defaults to current language)
    
    Returns:
        Translated string or the key itself if not found
    """
    lang = language or _current_language
    
    if lang not in TRANSLATIONS:
        lang = "de"
    
    translation_dict = TRANSLATIONS[lang]
    return translation_dict.get(key, key)


def t(key: str, language: Optional[str] = None) -> str:
    """Shorthand for translate()."""
    return translate(key, language)


def load_language_from_settings(settings_path: Path) -> str:
    """Load language preference from settings file.
    
    Returns:
        Language code (de or en), or "de" if not found
    """
    try:
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                lang = data.get("language", "de")
                if lang in TRANSLATIONS:
                    set_language(lang)
                    return lang
    except Exception as e:
        logger.warning(f"Could not load language from settings: {e}")
    
    return "de"


def save_language_to_settings(settings_path: Path, language: str) -> bool:
    """Save language preference to settings file.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read existing settings
        data = {}
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        # Update language
        data["language"] = language
        
        # Write back
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        logger.error(f"Could not save language to settings: {e}")
        return False


def get_available_languages() -> Dict[str, str]:
    """Get available languages as {code: name}."""
    return {
        "de": translate("language_de"),
        "en": translate("language_en"),
    }
