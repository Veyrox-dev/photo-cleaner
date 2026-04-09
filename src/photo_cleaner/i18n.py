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
        "_aktion_erforderlich_if_grpopencount_0_else_vollst": "{'AKTION ERFORDERLICH' if grp.open_count > 0 else 'Vollständig entschieden'}",
        "_autoauswahl_fuer_gruppe_augengewicht_55": "Auto-Auswahl für Gruppe (Augen-Gewicht: 55%):",
        "_bempfehlung_fuer_ihr_systemb_recrecommendedpackag": "💡 <b>Empfehlung für Ihr System:</b> {rec.recommended_package}<br>",
        "_benoetigt_build_tools": "      Benötigt Build Tools",
        "_benoetigt_joindepnames": "Benötigt: {', '.join(dep_names)}",
        "_build_tools_verfuegbar_if_selfsysteminfohasbuildt": "  Build Tools: {'Verfügbar' if self.system_info.has_build_tools else 'Nicht erkannt'}",
        "_ctrlj_ctrlk_gruppe_wechseln": "  Ctrl+J / Ctrl+K - Gruppe wechseln",
        "_der_ordner_gueltige_bilddateien_enthaeltn": "• Der Ordner gültige Bilddateien enthält\n",
        "_fertigstellen_exportieren": "Fertigstellen & Exportieren",
        "_geloescht_intfloatdeletedat": " (gelöscht: {int(float(deleted_at))})",
        "_genuegend_speicherplatz_vorhanden_ist": "• Genügend Speicherplatz vorhanden ist",
        "_gpu_verfuegbar_if_selfsysteminfohasgpu_else_nicht": "  GPU: {'Verfügbar' if self.system_info.has_gpu else 'Nicht erkannt'}",
        "_hohe_qualitaet_if_score_07_else_mittlere_qualitae": "{'Hohe Qualität' if score >= 0.7 else '~ Mittlere Qualität' if score >= 0.4 else 'Niedrige Qualität'}",
        "_kein_gesicht_erkannt_regel_greift_nicht": "Kein Gesicht erkannt -> Regel greift nicht",
        "_lendeletedids_bilder_geloescht": "{len(deleted_ids)} Bild(er) gelöscht.",
        "_openfiles_benoetigen_entscheidung": "{open_files} benötigen Entscheidung",
        "_sie_leserechte_fuer_den_ordner_habenn": "• Sie Leserechte für den Ordner haben\n",
        "_speichern": "Speichern",
        "_sync_aus": "Sync: AUS",
        "_voreinstellung_geloescht": "Voreinstellung gelöscht",
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
        "nn_bewertung_abgeschlossen_bilder_wurden_automatis": "\n\nBewertung abgeschlossen: Bilder wurden automatisch eingeschätzt.",
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
        "status_nicht_geprueft": "Status: Nicht geprüft",
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
        "search_placeholder": "Suchen...",
        "select_folders_title": "PhotoCleaner - Ordner wählen",
        "select_folders_subtitle": "Wählen Sie Ordner und Top-N für die automatische Auswahl",
        "start_analysis": "Analyse starten",
        "input_hint": "Wählen Sie den Ordner mit den Fotos, die Sie sortieren möchten.",
        "output_hint": "Wählen Sie den Zielordner für exportierte Bilder.",
        "topn_hint": "Wie viele der besten Bilder pro Gruppe automatisch behalten werden sollen.",
        "output_required": "Bitte wählen Sie einen Zielordner aus",
        "work_existing": "Sie können mit vorhandenen Daten arbeiten oder einen Foto-Ordner auswählen",
        "ready_to_start": "Bereit zum Starten",
        "pick_group": "Wählen Sie eine Gruppe aus",
        "quick_actions": "Schnellaktionen",
        
        # Tips panel
        "tips": "Tipps",
        "tip_ctrl_click": "Strg+Klick: Auswahl umschalten",
        "tip_shift_click": "Shift+Klick: Bereichsauswahl",
        "tip_click_card": "Karte klicken: Detailansicht öffnen",
        "clear_selection": "Auswahl löschen",
        "compare_two": "Vergleichen (2 ausgewählt)",
        "keep": "Behalten",
        "delete_confirm": "Zum Löschen markieren",
        "select_multiple": "Mehrfachauswahl:",
        "select_all": "Alle auswählen",
        
        # Dialogs & Messages
        "welcome": "Willkommen bei PhotoCleaner",
        "select_folders": "Ordner wählen",
        "input_folder": "Eingabeordner",
        "output_folder": "Ausgabeordner",
        "start": "Starten",
        "cancel": "Abbrechen",
        "analyze": "Analysieren",
        "analyzing": "Bilder werden analysiert...",
        "no_selection": "Keine Auswahl",
        "select_images": "Bitte wählen Sie Bilder aus",
        "keep": "Behalten",
        "delete": "Zum Löschen markieren",
        "unsure": "? Unsicher (U)",
        "compare": "Vergleichen",
        "export": "Exportieren",
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
        "groups_count": "{count} Gruppen",
        "select_group": "Wählen Sie eine Gruppe aus",
        "group_title": "Gruppe {id} ({count} Bilder)",
        "group_list_single": "Einzelbild",
        "group_list_many": "Gruppe {id} • {count} Bilder",
        "group_status_open": "Offen",
        "group_status_partial": "Teilweise entschieden",
        "group_status_done": "Fertig entschieden",
        "group_counts_summary": "Offen: {open_count} | Entschieden: {decided_count} | Löschen: {delete_count}",
        "group_action_needed": "Entscheidung nötig",
        "group_action_done": "Alles entschieden",
        "review_next_step": "Nächster Schritt",
        "review_guidance_done": "Gruppe ist abgeschlossen. Weiter zur nächsten offenen Gruppe.",
        "review_guidance_low_confidence": "Erst die unsicheren Bilder prüfen, dann Keep/Delete setzen.",
        "review_guidance_large_open": "Große Gruppe: zuerst klare Treffer markieren, Rest als Unsicher lassen.",
        "review_guidance_continue": "Mit den offenen Bildern fortfahren und Entscheidungen abschließen.",
        "onboarding_title": "Willkommen bei PhotoCleaner",
        "onboarding_message": "Kurzstart:\n1) Wähle Behalten/Löschen/Unsicher pro Bild.\n2) Nutze Unsicher für schwere Fälle.\n3) Shortcuts: K=Behalten, D=Löschen, U=Unsicher, Z=Undo.",
        "onboarding_start_review": "Review starten",
        "onboarding_skip": "Später",
        "onboarding_next": "Weiter",
        "onboarding_previous": "Zurück",
        "onboarding_finish": "Fertig",
        "onboarding_interactive_mode": "Interaktiver Klickmodus",
        "onboarding_interactive_hint": "Aktiv: Klicke auf den markierten Bereich, um zum nächsten Schritt zu wechseln.",
        "onboarding_dont_show_again": "Nicht erneut anzeigen",
        "onboarding_step_welcome_title": "Willkommen im Review-Workflow",
        "onboarding_step_welcome_body": "Diese Tour zeigt dir die wichtigsten Bereiche.\n\nDu kannst mit Weiter und Zurück durch die Schritte gehen. Der Rest wird abgedunkelt, damit du den Fokus behältst.",
        "onboarding_step_import_title": "1) Bilder importieren",
        "onboarding_step_import_body": "Starte hier: Wähle deinen Bildordner. Danach beginnt die Analyse und Gruppen werden automatisch erstellt.",
        "onboarding_step_filter_title": "2) Gruppen finden",
        "onboarding_step_filter_body": "Mit Suche und Filter-Dropdown findest du schnell die richtigen Gruppen, z. B. offene oder manuell zu prüfende Gruppen.",
        "onboarding_step_groups_title": "3) Gruppenliste verstehen",
        "onboarding_step_groups_body": "Jede Zeile ist eine Gruppe.\nRot = noch offen, Grün = fertig entschieden.\nWähle eine Gruppe aus, um die Bilder rechts zu prüfen.",
        "onboarding_step_actions_title": "4) Entscheidungen treffen",
        "onboarding_step_actions_body": "Hier setzt du den Status für ausgewählte Bilder:\n• Behalten\n• Löschen\n• Unsicher\n\nTipps: K = Behalten, D = Löschen, U = Unsicher, Z = Undo.",
        "onboarding_step_finalize_title": "5) Export abschließen",
        "onboarding_step_finalize_body": "Wenn deine Entscheidungen fertig sind, exportiere hier die Behalten-Bilder in den Ausgabeordner.",
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
        "analysis_completed": "Analyse abgeschlossen",
        "analysis_failed": "Analyse fehlgeschlagen",
        "analysis_wait": "Bitte warten Sie, während Ihre Bilder analysiert werden.\nDieser Vorgang kann einige Minuten dauern.",
        "cancel_analysis": "Abbrechen",
        
        # Settings dialog
        "settings_title": "Einstellungen",
        "quality_tab": "Qualität",
        "detection_tab": "Erkennung",
        "export_tab": "Export",
        "behavior_settings": "Verhalten",
        "reset_settings": "↻ Zurücksetzen",
        "save_settings": "Speichern",
        "maintenance_tab": "Wartung",
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
        "finalize_export": "Fertigstellen & Exportieren",
        "finalize_export_tooltip": "Exportiert alle als KEEP markierten Bilder in die Zielstruktur",
        "no_selection_display": "Keine Auswahl",
        "preview_unavailable": "(Vorschau nicht verfügbar)",
        "action_success": "Aktion erfolgreich",
        "action_error": "{msg}",
        
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

<h2>Plan-Vergleich</h2>

<table>
    <tr>
        <th class="feature-name">Feature / Limit</th>
        <th class="plan-free">FREE<br><span class="price">€0</span></th>
        <th class="plan-pro">PRO<br><span class="price">ab €19/Jahr</span></th>
    </tr>
    
    <!-- Basis-Features -->
    <tr>
        <td class="feature-name">Bildanalyse & Duplikatsuche</td>
        <td class="plan-free">Ja</td>
        <td class="plan-pro">Ja</td>
    </tr>
    <tr>
        <td class="feature-name">Bildlimit</td>
        <td class="plan-free">250 Bilder gesamt</td>
        <td class="plan-pro"><span class="highlight">Unbegrenzt</span></td>
    </tr>
    <tr>
        <td class="feature-name">Geräte-Limit</td>
        <td class="plan-free">1 Gerät</td>
        <td class="plan-pro">3 Geräte</td>
    </tr>
    
    <!-- PRO Features -->
    <tr>
        <td class="feature-name">Batch-Verarbeitung (Massen-Import)</td>
        <td class="plan-free">Nein</td>
        <td class="plan-pro">Ja</td>
    </tr>
    <tr>
        <td class="feature-name">HEIC/HEIF-Format Support</td>
        <td class="plan-free">Nein</td>
        <td class="plan-pro">Ja</td>
    </tr>
    <tr>
        <td class="feature-name">Erweitertes Caching (2-8x schneller)</td>
        <td class="plan-free">Nein</td>
        <td class="plan-pro">Ja</td>
    </tr>
    <tr>
        <td class="feature-name">Qualitätsanalyse (Schärfe/Belichtung/Details)</td>
        <td class="plan-free">Basis</td>
        <td class="plan-pro"><span class="highlight">Erweitert</span></td>
    </tr>
    <tr>
        <td class="feature-name">Batch-Löschung</td>
        <td class="plan-free">Nein</td>
        <td class="plan-pro">Ja</td>
    </tr>
    <tr>
        <td class="feature-name">Export-Formate (CSV, JSON)</td>
        <td class="plan-free">Nein</td>
        <td class="plan-pro">Ja</td>
    </tr>
    <tr>
        <td class="feature-name">Support</td>
        <td class="plan-free">Nein</td>
        <td class="plan-pro">Email</td>
    </tr>
    <tr>
        <td class="feature-name">Offline Grace Period</td>
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
        "split_group": "Auswahl abspalten",
        "split_success": "Auswahl erfolgreich abgespalten",
        "split_failed": "Abspalten fehlgeschlagen",
        "needs_review_only": "Manuell prüfen",
        "group_filters_title": "Filter",
        "group_filter_all": "Alle Gruppen",
        "needs_review_only_tooltip": "Zeige nur Gruppen, die manuell geprüft werden sollten",
        "open_only": "Nur offene",
        "open_only_tooltip": "Zeige nur Gruppen mit offenen Entscheidungen",
        "low_confidence_only": "Nur niedrige Confidence",
        "low_confidence_only_tooltip": "Zeige nur Gruppen mit niedriger oder unvollständiger Confidence",
        "high_impact_only": "Nur große Gruppen",
        "high_impact_only_tooltip": "Zeige nur Gruppen mit mindestens {count} Bildern",
        "smart_filter_counter": "Filter: {visible}/{total} sichtbar | Aktiv: {active}",
        "smart_filter_none": "Keine",
        "needs_review_counter": "Manuell prüfen: {visible} / {total}",
        "manual_review_hint": " | Manuell prüfen: {count}",
        "quota_limit_title": "FREE-Limit erreicht",
        "quota_limit_default_reason": "Das FREE-Limit wurde erreicht.",
        "quota_limit_action": "Öffne Lizenz-Verwaltung und upgrade auf PRO, um unbegrenzt fortzufahren.",
        "quota_limit_message": "{reason}\n\nAktueller Vorgang: {requested} Bild(er).\n{action}",
        
        # Selection and comparison
        "selection_none_bold": "<b>Keine Auswahl</b>",
        "compare_select_two": "Vergleichen (2 auswählen)",
        "selection_one_image": "<b>1 Bild ausgewählt</b>",
        "compare_need_two": "Vergleichen (2 benötigt)",
        "selection_two_images": "<b>2 Bilder ausgewählt</b>",
        "compare_side_by_side": "Seite-an-Seite Vergleich",
        "selection_n_images": "<b>{count} Bilder ausgewählt</b>",
        "compare_select_exactly_two": "Vergleichen (genau 2 wählen)",
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
        "finalize_success": "Export erfolgreich abgeschlossen",
        "finalize_partial": "Export mit Warnungen abgeschlossen",
        "finalize_failed": "Export fehlgeschlagen",
        "reset_settings_confirm": "Einstellungen zurücksetzen?",
        "reset_settings_confirm_msg": "Alle Einstellungen werden auf Standardwerte zurückgesetzt.",
        "load_image_failed": "Bild konnte nicht geladen werden: {error}",
        "language_change_failed": "Sprache konnte nicht geändert werden: {error}",
        "theme_change_failed": "Design konnte nicht geändert werden: {error}",
        "settings_open_failed": "Einstellungen konnten nicht geöffnet werden: {error}",
        "scan_failed": "Fehler beim Scannen:\n{error}",
        "duplicate_search_failed": "Fehler beim Duplikate-Suchen:\n{error}",
        "predictor_set_title": "Predictor gesetzt",
        "predictor_set_message": "dlib Predictor konfiguriert:\n{path}",
        "predictor_set_failed": "Konnte Predictor nicht setzen: {error}",
        "preset_save_failed": "Konnte Preset nicht speichern:\n{error}",
        "preset_delete_failed": "Konnte Preset nicht löschen:\n{error}",
        "export_failed_title": "Export fehlgeschlagen",
        "export_failed_message": "Fehler: {error}",
        "undo_title": "Rückgängig",
        "redo_title": "Wiederholen",
        "nothing_to_undo": "Keine Aktion zum Rückgängigmachen",
        "nothing_to_redo": "Keine Aktion zum Wiederholen",
        "recent_actions": "Letzte Aktionen",
        "no_recent_actions": "Noch keine Aktionen in dieser Sitzung",
        "action_summary_status_change": "{count} Bild(er) auf {status} gesetzt",
        "action_summary_group_merge": "{count} Bild(er) zusammengeführt",
        "action_summary_group_split": "{count} Bild(er) abgespalten",
        "action_summary_group_reassign": "{count} Bild(er) neu gruppiert",
        "action_summary_lock_toggle": "Sperrstatus für {count} Bild(er) geändert",
        "action_undone": "Rückgängig: {action}",
        "action_undone_generic": "Letzte Aktion rückgängig gemacht",
        "split_single_not_allowed": "Einzelbilder können nicht weiter abgespalten werden.",
        "split_not_all": "Bitte nicht alle Bilder aus der Gruppe abspalten.",
        "split_confirm": "{count} Bild(er) in eine neue Gruppe verschieben?",
        "split_error": "Fehler beim Abspalten: {error}",
        "startup_error_title": "Startfehler",
        
        # Status bar
        "mode_label": "Modus",
        "theme_label": "Theme",
        "progress_format": "%p% Dateien entschieden",
        
        # Folder selection dialog
        "select_input_folder_label": "<b>1. Foto-Ordner auswählen</b>",
        "select_output_folder_label": "<b>2. Zielordner für ausgewählte Fotos</b>",
        "select_topn_label": "<b>3. Top-N pro Gruppe</b>",
        "import_dialog_title": "Fotos auswählen",
        "import_dialog_subtitle": "Wähle die Bilder und den Zielordner. Danach startet die Analyse automatisch und zeigt jeden Schritt klar an.",
        "import_input_card_hint": "Hier liegen die Fotos, die du prüfen möchtest.",
        "import_output_card_hint": "Dorthin werden die ausgewählten Bilder später kopiert oder verschoben.",
        "import_topn_card_hint": "So viele Bilder pro ähnlicher Gruppe werden automatisch vorgeschlagen.",
        "output_folder_required": "<span style='color: #F44336;'>*Erforderlich</span>",
        "not_selected": "Noch nicht ausgewählt",
        "validation_select_output": "Bitte wähle zuerst einen Zielordner aus.",
        "validation_optional_input": "Du kannst mit vorhandenen Daten starten oder zusätzlich einen Foto-Ordner wählen.",
        "validation_ready": "Alles bereit. Die Analyse kann starten.",
        "help_dialog_content": "PhotoCleaner - Intelligente Fotoverwaltung\n\nWorkflow:\n1. Import: Wähle einen Ordner mit Bildern\n2. Analyse: Findet doppelte Bilder automatisch\n3. Einstellungen: Passe Qualitäts-Parameter an\n4. Entscheide für jedes Bild: Behalten oder Löschen\n\nTastaturkürzel:\n? = Diese Hilfe\nDelete = Markiere zum Löschen\nK = Behalte Bild\nSpace = Nächstes Bild",
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
        "delete_button": "Löschen",
        "reset_icon": "Zurücksetzen",
        "not_possible": "Nicht möglich",
        "select_group_message": "<h3>Wählen Sie eine Gruppe aus</h3>",
        "actions_on_selection": "<b>Aktionen auf Auswahl:</b>",
        "undo_button": "Rückgängig (Z)",
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
        "lock_unlock_button": "Sperren/Entsperren (Leer)",
        "finalize_export": "Exportieren",
        "splash_loading_app": "Initialisiere PhotoCleaner",
        "splash_loading_ui": "Lade UI-Module",
        "splash_loading_image_processing": "Lade Bildverarbeitung",
        "splash_preparing_ui": "Bereite Benutzeroberfläche vor",
        "splash_starting": "Starte Anwendung",
        "splash_version": "Version",
        
        # Phase C: Confidence & Quality Labels (verständliche Begriffe)
        "confidence_very_reliable": "Sehr zuverlässig",
        "confidence_review_recommended": "Überprüfung empfohlen",
        "confidence_review_needed": "Überprüfung nötig",
        "confidence_data_incomplete": "Daten unvollständig",
        "confidence_no_data": "Keine Daten",
        
        # Quality Ratings (Bewertungen statt Score)
        "quality_rating_very_good": "Sehr gut",
        "quality_rating_good": "Gut",
        "quality_rating_fair": "Befriedigend",
        "quality_rating_poor": "Schlecht",
        
        # Metric Labels (Unit tested & clear)
        "metric_sharpness": "Schärfe",
        "metric_lighting": "Belichtung",
        "metric_resolution": "Auflösung",
        "metric_face_quality": "Gesichtsqualität",
        
        # Phase D: Progress & Finalization
        "progress_step_1_scanning": "Bilder scannen...",
        "progress_step_2_grouping": "Gruppen bilden...",
        "progress_step_3_rating": "Bilder bewerten...",
        "progress_step_4_finalization": "Fertigstellung...",
        "progress_step_current": "Schritt {step}/{total}",
        "progress_eta": "Restzeit: {eta}",
        "progress_eta_calculating": "Restzeit wird berechnet...",
        
        "finalization_dialog_title": "Analyse abgeschlossen",
        "finalization_success_summary": "{total} Bilder verarbeitet, {groups} Gruppen gefunden",
        "finalization_processing_info": "Davon: {new} neu, {cached} aus Cache",
        "finalization_errors_header": "Fehler und Warnungen",
        "finalization_error_loading": "{count} Dateien konnten nicht geladen werden",
        "finalization_affected_files": "Betroffene Dateien",
        "finalization_button_report_error": "Fehler melden",
        "finalization_button_ok": "OK",
        "error_report_dialog_title": "Fehler berichten",
        "error_report_email_label": "E-Mail (optional):",
        "error_report_message_label": "Nachricht (optional):",
        "error_report_button_send": "Senden",
        "error_report_button_cancel": "Abbrechen",
        "error_report_sent": "Fehler berichten erfolgreich gesendet.",
        "error_report_failed": "Fehler berichten fehlgeschlagen: {error}",
        
        # Phase E: Review Productivity
        "phase_e_keyboard_shortcuts": "Tastaturkürzel",
        "phase_e_shortcut_keep": "<b>K</b> Behalten",
        "phase_e_shortcut_delete": "<b>D</b> Löschen",
        "phase_e_shortcut_unsure": "<b>U</b> Unsicher",
        "phase_e_shortcut_merge": "<b>M</b> Zusammenführen",
        "phase_e_shortcut_split": "<b>S</b> Abspalten",
        "phase_e_shortcut_undo": "<b>Z</b> Rückgängig",
        "phase_e_shortcut_next_group": "<b>→</b> Nächste Gruppe",
        "phase_e_shortcut_prev_group": "<b>←</b> Vorherige Gruppe",
        "phase_e_batch_select": "Mehrfachauswahl: Shift+Klick, Strg+A",
        "phase_e_unsure_prominent": "? Unsicher – Standard für schwierige Fälle",
        "phase_e_unsure_recommendation": "Diese Bilder benötigen weitere Überprüfung",
        "phase_e_action_visibility": "Aktionen (Merge/Split/Undo):",
        "phase_e_merge_available": "Zusammenführen verfügbar",
        "phase_e_split_available": "Abspalten verfügbar",
        "phase_e_undo_available": "{count} Aktion(en) zum Rückgängigmachen",
        "phase_e_decisions_quick": "Schnelle Entscheidungen: K, D oder U drücken",
        
        # Phase F: Validation & KPI Tracking
        "phase_f_kpi_title": "Produktivitäts-KPIs",
        "phase_f_kpi_decision_time": "Ø Zeit pro Entscheidung",
        "phase_f_kpi_error_rate": "Fehlerquote",
        "phase_f_kpi_accuracy": "Genauigkeit vs. Auto-Empfehlung",
        "phase_f_kpi_total_decisions": "Gesamtentscheidungen",
        "phase_f_kpi_export_title": "KPI-Daten exportieren",
        "phase_f_kpi_export_button": "KPI-Bericht exportieren",
        "phase_f_user_test_mode": "Testmodus (KPI-Tracking aktiv)",
        "phase_f_mode_indicator": "🧪 Im Testmodus (Entscheidungen werden aufgezeichnet)",
        "phase_f_export_success": "KPI-Bericht erfolgreich exportiert: {path}",
        "phase_f_export_failed": "KPI-Export fehlgeschlagen: {error}",
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
        "search_placeholder": "Search...",
        "select_folders_title": "PhotoCleaner - Select folders",
        "select_folders_subtitle": "Pick folders and Top-N for auto selection",
        "start_analysis": "Start analysis",
        "input_hint": "Choose the folder with photos you want to sort.",
        "output_hint": "Choose the target folder for exported images.",
        "topn_hint": "How many top photos per group should be kept automatically.",
        "output_required": "Please select a target folder",
        "work_existing": "You can work with existing data or pick a photos folder",
        "ready_to_start": "Ready to start",
        "pick_group": "Select a group",
        "quick_actions": "Quick actions",
        
        # Tips panel
        "tips": "Tips",
        "tip_ctrl_click": "Ctrl+Click: Toggle selection",
        "tip_shift_click": "Shift+Click: Range selection",
        "tip_click_card": "Click card: Open detail view",
        "clear_selection": "Clear selection",
        "compare_two": "Compare (2 selected)",
        "keep": "Keep",
        "delete_confirm": "Mark for deletion",
        "select_multiple": "Multi-select:",
        "select_all": "Select all",
        
        # Dialogs & Messages
        "welcome": "Welcome to PhotoCleaner",
        "select_folders": "Select Folders",
        "input_folder": "Input Folder",
        "output_folder": "Output Folder",
        "start": "Start",
        "cancel": "Cancel",
        "analyze": "Analyze",
        "analyzing": "Analyzing images...",
        "no_selection": "No Selection",
        "select_images": "Please select images",
        "keep": "Keep",
        "delete": "Mark for deletion",
        "unsure": "? Unsure (U)",
        "compare": "Compare",
        "export": "Export",
        "close": "Close",
        "ok": "OK",
        
        # Status messages
        "ready": "Ready",
        "analyzing_status": "Analyzing images...",
        "indexed": "Images indexed",
        "processing": "Processing",
        "complete": "Complete",
        "page_info": "Page {page}/{total} • {start}-{end} of {count}",
        "groups_count": "{count} Groups",
        "select_group": "Select a group",
        "group_title": "Group {id} ({count} images)",
        "group_list_single": "Single image",
        "group_list_many": "Group {id} • {count} images",
        "group_status_open": "Open",
        "group_status_partial": "Partly decided",
        "group_status_done": "Fully decided",
        "group_counts_summary": "Open: {open_count} | Decided: {decided_count} | Delete: {delete_count}",
        "group_action_needed": "Decision needed",
        "group_action_done": "All decided",
        "review_next_step": "Next step",
        "review_guidance_done": "Group is complete. Continue with the next open group.",
        "review_guidance_low_confidence": "Review uncertain images first, then set Keep/Delete.",
        "review_guidance_large_open": "Large group: mark clear winners first, keep uncertain ones as Unsure.",
        "review_guidance_continue": "Continue with open images and complete decisions.",
        "onboarding_title": "Welcome to PhotoCleaner",
        "onboarding_message": "Quick start:\n1) Mark each image as Keep/Delete/Unsure.\n2) Use Unsure for difficult cases.\n3) Shortcuts: K=Keep, D=Delete, U=Unsure, Z=Undo.",
        "onboarding_start_review": "Start review",
        "onboarding_skip": "Later",
        "onboarding_next": "Next",
        "onboarding_previous": "Back",
        "onboarding_finish": "Finish",
        "onboarding_interactive_mode": "Interactive click mode",
        "onboarding_interactive_hint": "Enabled: click the highlighted area to move to the next step.",
        "onboarding_dont_show_again": "Do not show again",
        "onboarding_step_welcome_title": "Welcome to the review workflow",
        "onboarding_step_welcome_body": "This tour shows the key areas.\n\nUse Next and Back to move through the steps. The rest of the UI is dimmed so you can focus.",
        "onboarding_step_import_title": "1) Import images",
        "onboarding_step_import_body": "Start here: choose your image folder. Analysis starts afterward and groups are built automatically.",
        "onboarding_step_filter_title": "2) Find groups quickly",
        "onboarding_step_filter_body": "Use search and the filter dropdown to focus on the right groups, for example open groups or groups needing manual review.",
        "onboarding_step_groups_title": "3) Understand the group list",
        "onboarding_step_groups_body": "Each row is one group.\nRed = still open, Green = fully decided.\nSelect a group to review images on the right.",
        "onboarding_step_actions_title": "4) Make decisions",
        "onboarding_step_actions_body": "Set status for selected images here:\n• Keep\n• Delete\n• Unsure\n\nTips: K = Keep, D = Delete, U = Unsure, Z = Undo.",
        "onboarding_step_finalize_title": "5) Finalize export",
        "onboarding_step_finalize_body": "When decisions are done, export the Keep images to the output folder here.",
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
        "analysis_completed": "Analysis completed",
        "analysis_failed": "Analysis failed",
        "analysis_wait": "Please wait while your images are being analyzed.\nThis may take several minutes.",
        "cancel_analysis": "Cancel",
        
        # Settings dialog
        "settings_title": "Settings",
        "quality_tab": "Quality",
        "detection_tab": "Detection",
        "export_tab": "Export",
        "behavior_settings": "Behavior",
        "reset_settings": "↻ Reset",
        "save_settings": "Save",
        "maintenance_tab": "Maintenance",
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
        "finalize_export": "Finalize & Export",
        "finalize_export_tooltip": "Exports all images marked as KEEP to target directory",
        "no_selection_display": "No selection",
        "preview_unavailable": "(Preview unavailable)",
        "action_success": "Action successful",
        "action_error": "{msg}",
        
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

<h2>Plan Comparison</h2>

<table>
    <tr>
        <th class="feature-name">Feature / Limit</th>
        <th class="plan-free">FREE<br><span class="price">€0</span></th>
        <th class="plan-pro">PRO<br><span class="price">from €19/year</span></th>
    </tr>
    
    <!-- Basic Features -->
    <tr>
        <td class="feature-name">Image Analysis & Duplicate Detection</td>
        <td class="plan-free">Yes</td>
        <td class="plan-pro">Yes</td>
    </tr>
    <tr>
        <td class="feature-name">Image Limit</td>
        <td class="plan-free">250 images total</td>
        <td class="plan-pro"><span class="highlight">Unlimited</span></td>
    </tr>
    <tr>
        <td class="feature-name">Device Limit</td>
        <td class="plan-free">1 device</td>
        <td class="plan-pro">3 devices</td>
    </tr>
    
    <!-- PRO Features -->
    <tr>
        <td class="feature-name">Batch Processing (Mass Import)</td>
        <td class="plan-free">No</td>
        <td class="plan-pro">Yes</td>
    </tr>
    <tr>
        <td class="feature-name">HEIC/HEIF Format Support</td>
        <td class="plan-free">No</td>
        <td class="plan-pro">Yes</td>
    </tr>
    <tr>
        <td class="feature-name">Extended Caching (2-8x faster)</td>
        <td class="plan-free">No</td>
        <td class="plan-pro">Yes</td>
    </tr>
    <tr>
        <td class="feature-name">Quality Analysis (Sharpness/Exposure/Details)</td>
        <td class="plan-free">Basic</td>
        <td class="plan-pro"><span class="highlight">Advanced</span></td>
    </tr>
    <tr>
        <td class="feature-name">Batch Deletion</td>
        <td class="plan-free">No</td>
        <td class="plan-pro">Yes</td>
    </tr>
    <tr>
        <td class="feature-name">Export Formats (CSV, JSON)</td>
        <td class="plan-free">No</td>
        <td class="plan-pro">Yes</td>
    </tr>
    <tr>
        <td class="feature-name">Support</td>
        <td class="plan-free">No</td>
        <td class="plan-pro">Email</td>
    </tr>
    <tr>
        <td class="feature-name">Offline Grace Period</td>
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
        "split_group": "Split Selection",
        "split_success": "Selection split successfully",
        "split_failed": "Split failed",
        "needs_review_only": "Manual review",
        "group_filters_title": "Filters",
        "group_filter_all": "All groups",
        "needs_review_only_tooltip": "Show only groups that should be reviewed manually",
        "open_only": "Open only",
        "open_only_tooltip": "Show only groups with open decisions",
        "low_confidence_only": "Low confidence only",
        "low_confidence_only_tooltip": "Show only groups with low or incomplete confidence",
        "high_impact_only": "Large groups only",
        "high_impact_only_tooltip": "Show only groups with at least {count} images",
        "smart_filter_counter": "Filter: {visible}/{total} visible | Active: {active}",
        "smart_filter_none": "None",
        "needs_review_counter": "Manual review: {visible} / {total}",
        "manual_review_hint": " | Manual review: {count}",
        "quota_limit_title": "FREE limit reached",
        "quota_limit_default_reason": "The FREE limit has been reached.",
        "quota_limit_action": "Open License Management and upgrade to PRO to continue without limits.",
        "quota_limit_message": "{reason}\n\nCurrent run: {requested} image(s).\n{action}",
        
        # Selection and comparison
        "selection_none_bold": "<b>No selection</b>",
        "compare_select_two": "Compare (select 2)",
        "selection_one_image": "<b>1 image selected</b>",
        "compare_need_two": "Compare (2 required)",
        "selection_two_images": "<b>2 images selected</b>",
        "compare_side_by_side": "Side-by-Side Comparison",
        "selection_n_images": "<b>{count} images selected</b>",
        "compare_select_exactly_two": "Compare (select exactly 2)",
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
        "finalize_success": "Export completed successfully",
        "finalize_partial": "Export completed with warnings",
        "finalize_failed": "Export failed",
        "reset_settings_confirm": "Reset settings?",
        "reset_settings_confirm_msg": "All settings will be reset to default values.",
        "load_image_failed": "Could not load image: {error}",
        "language_change_failed": "Could not change language: {error}",
        "theme_change_failed": "Could not change theme: {error}",
        "settings_open_failed": "Could not open settings: {error}",
        "scan_failed": "Scan failed:\n{error}",
        "duplicate_search_failed": "Duplicate search failed:\n{error}",
        "predictor_set_title": "Predictor set",
        "predictor_set_message": "dlib predictor configured:\n{path}",
        "predictor_set_failed": "Could not set predictor: {error}",
        "preset_save_failed": "Could not save preset:\n{error}",
        "preset_delete_failed": "Could not delete preset:\n{error}",
        "export_failed_title": "Export failed",
        "export_failed_message": "Error: {error}",
        "undo_title": "Undo",
        "redo_title": "Redo",
        "nothing_to_undo": "Nothing to undo",
        "nothing_to_redo": "Nothing to redo",
        "recent_actions": "Recent actions",
        "no_recent_actions": "No actions yet in this session",
        "action_summary_status_change": "Set {count} image(s) to {status}",
        "action_summary_group_merge": "Merged {count} image(s)",
        "action_summary_group_split": "Split out {count} image(s)",
        "action_summary_group_reassign": "Re-grouped {count} image(s)",
        "action_summary_lock_toggle": "Changed lock state for {count} image(s)",
        "action_undone": "Undid: {action}",
        "action_undone_generic": "Undid last action",
        "split_single_not_allowed": "Single images cannot be split further.",
        "split_not_all": "Please do not split all images out of the group.",
        "split_confirm": "Move {count} image(s) to a new group?",
        "split_error": "Error while splitting: {error}",
        "startup_error_title": "Startup error",
        
        # Status bar
        "mode_label": "Mode",
        "theme_label": "Theme",
        "progress_format": "%p% Files decided",
        
        # Folder selection dialog
        "select_input_folder_label": "<b>1. Select photo folder</b>",
        "select_output_folder_label": "<b>2. Select target folder for photos</b>",
        "select_topn_label": "<b>3. Top-N per group</b>",
        "import_dialog_title": "Choose photos",
        "import_dialog_subtitle": "Select the photo folder and target folder. The analysis starts automatically and shows each step clearly.",
        "import_input_card_hint": "This is where the photos you want to review are located.",
        "import_output_card_hint": "Selected photos will later be copied or moved there.",
        "import_topn_card_hint": "This many images per similar group will be suggested automatically.",
        "output_folder_required": "<span style='color: #F44336;'>*Required</span>",
        "not_selected": "Not selected yet",
        "validation_select_output": "Please choose a target folder first.",
        "validation_optional_input": "You can start with existing data or choose an additional photo folder.",
        "validation_ready": "Everything is ready. The analysis can start.",
        "help_dialog_content": "PhotoCleaner - Intelligent Photo Management\n\nWorkflow:\n1. Import: Choose a folder with photos\n2. Analysis: Find duplicate photos automatically\n3. Settings: Adjust quality parameters\n4. Decide for each photo: Keep or Delete\n\nKeyboard Shortcuts:\n? = This help\nDelete = Mark for deletion\nK = Keep photo\nSpace = Next photo",
        "closed_eyes_detection": "Detect closed eyes",
        "redeye_detection": "Detect red-eye effect",
        "blurry_detection": "Blurry photos",
        "underexposed_detection": "Underexposed",
        "overexposed_detection": "Overexposed",        "close_button": "Close",
        "reset_button": "Reset",
        "image_analysis_async": "Image analysis running",
        "image_analysis": "Image analysis running",
        "min_eye_size": "Minimum eye size (pixels):",
        "delete_button": "Delete",
        "reset_icon": "Reset",
        "not_possible": "Not possible",
        "select_group_message": "<h3>Select a group</h3>",
        "actions_on_selection": "<b>Actions on selection:</b>",
        "undo_button": "Undo (Z)",
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
        "lock_unlock_button": "Lock/Unlock (Space)",
        "finalize_export": "Export",
        "splash_loading_app": "Initializing PhotoCleaner",
        "splash_loading_ui": "Loading UI modules",
        "splash_loading_image_processing": "Loading image processing",
        "splash_preparing_ui": "Preparing user interface",
        "splash_starting": "Starting application",
        "splash_version": "Version",
        
        # Phase C: Confidence & Quality Labels (clear language)
        "confidence_very_reliable": "Very reliable",
        "confidence_review_recommended": "Review recommended",
        "confidence_review_needed": "Review needed",
        "confidence_data_incomplete": "Data incomplete",
        "confidence_no_data": "No data",
        
        # Quality Ratings (Ratings instead of Score)
        "quality_rating_very_good": "Very good",
        "quality_rating_good": "Good",
        "quality_rating_fair": "Fair",
        "quality_rating_poor": "Poor",
        
        # Metric Labels (unit tested & clear)
        "metric_sharpness": "Sharpness",
        "metric_lighting": "Lighting",
        "metric_resolution": "Resolution",
        "metric_face_quality": "Face quality",
        
        # Phase D: Progress & Finalization
        "progress_step_1_scanning": "Scanning images...",
        "progress_step_2_grouping": "Creating groups...",
        "progress_step_3_rating": "Rating images...",
        "progress_step_4_finalization": "Finishing up...",
        "progress_step_current": "Step {step}/{total}",
            "progress_eta": "Remaining time: {eta}",
        "progress_eta_calculating": "Calculating remaining time...",
        
        "finalization_dialog_title": "Analysis complete",
        "finalization_success_summary": "{total} images processed, {groups} groups found",
        "finalization_processing_info": "Of which: {new} new, {cached} from cache",
        "finalization_errors_header": "Errors and warnings",
        "finalization_error_loading": "{count} files could not be loaded",
        "finalization_affected_files": "Affected files",
        "finalization_button_report_error": "Report error",
        "finalization_button_ok": "OK",
        "error_report_dialog_title": "Report error",
        "error_report_email_label": "Email (optional):",
        "error_report_message_label": "Message (optional):",
        "error_report_button_send": "Send",
        "error_report_button_cancel": "Cancel",
        "error_report_sent": "Error report sent successfully.",
        "error_report_failed": "Error report failed: {error}",
        
        # Phase E: Review Productivity
        "phase_e_keyboard_shortcuts": "Keyboard Shortcuts",
        "phase_e_shortcut_keep": "<b>K</b> Keep",
        "phase_e_shortcut_delete": "<b>D</b> Delete",
        "phase_e_shortcut_unsure": "<b>U</b> Unsure",
        "phase_e_shortcut_merge": "<b>M</b> Merge",
        "phase_e_shortcut_split": "<b>S</b> Split",
        "phase_e_shortcut_undo": "<b>Z</b> Undo",
        "phase_e_shortcut_next_group": "<b>→</b> Next Group",
        "phase_e_shortcut_prev_group": "<b>←</b> Previous Group",
        "phase_e_batch_select": "Multi-select: Shift+Click, Ctrl+A",
        "phase_e_unsure_prominent": "? Unsure – Standard for difficult cases",
        "phase_e_unsure_recommendation": "These images require further review",
        "phase_e_action_visibility": "Actions (Merge/Split/Undo):",
        "phase_e_merge_available": "Merge available",
        "phase_e_split_available": "Split available",
        "phase_e_undo_available": "{count} action(s) to undo",
        "phase_e_decisions_quick": "Quick decisions: Press K, D, or U",
        
        # Phase F: Validation & KPI Tracking
        "phase_f_kpi_title": "Productivity KPIs",
        "phase_f_kpi_decision_time": "Average time per decision",
        "phase_f_kpi_error_rate": "Error rate",
        "phase_f_kpi_accuracy": "Accuracy vs. auto-recommendation",
        "phase_f_kpi_total_decisions": "Total decisions",
        "phase_f_kpi_export_title": "Export KPI data",
        "phase_f_kpi_export_button": "Export KPI Report",
        "phase_f_user_test_mode": "Test mode (KPI tracking active)",
        "phase_f_mode_indicator": "🧪 In test mode (decisions are recorded)",
        "phase_f_export_success": "KPI report exported successfully: {path}",
        "phase_f_export_failed": "KPI export failed: {error}",
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
