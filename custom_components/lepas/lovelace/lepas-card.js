/*
 * Lepas vehicle card — Matte Titanium OEM edition (Lepas Connect v1.19.0).
 *
 * Adaptive single-bundle Web Component:
 *   - Compact 4-tab layout below 680px (Overview, Climate, Charging, Security)
 *   - Multi-column Cockpit layout at 680px+ (2-col) and 960px+ (3-col)
 *   - Includes <lepas-card-editor> visual configuration element
 *
 * Compatibility constraints:
 *   - No optional chaining or nullish coalescing (older Android System WebView)
 *   - No top-level ES module import/export (passes CJS syntax checks and HA module loading)
 */
(function () {
  var CARD_VERSION = "1.19.0";
  var CONFIRM_MS = 4000;
  var VALID_COLORS = ["grey", "teal", "violet", "black", "white"];
  var VALID_LAYOUTS = ["auto", "compact", "cockpit"];
  var VALID_TABS = ["overview", "climate", "charging", "security"];
  var DAY_SLUGS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

  var COLOR_ALIASES = {
    grey: "grey",
    gray: "grey",
    grigio: "grey",
    teal: "teal",
    verde: "teal",
    ottanio: "teal",
    petrolio: "teal",
    green: "teal",
    violet: "violet",
    viola: "violet",
    purple: "violet",
    ametista: "violet",
    black: "black",
    nero: "black",
    white: "white",
    bianco: "white",
  };

  var COLOR_SWATCHES = {
    grey: "#6B7280",
    teal: "#1B6B6B",
    violet: "#6D4C8A",
    black: "#1A1D24",
    white: "#E5E7EB",
  };

  var HERO_IMAGES = {
    grey: "/lepas_card/lepas-hero-grey.png?v=1.19.0",
    teal: "/lepas_card/lepas-hero-teal.png?v=1.19.0",
    violet: "/lepas_card/lepas-hero-violet.png?v=1.19.0",
    black: "/lepas_card/lepas-hero-black.png?v=1.19.0",
    white: "/lepas_card/lepas-hero-white.png?v=1.19.0",
  };
  var DEFAULT_HERO = "/lepas_card/lepas-hero.png?v=1.19.0";

  var SENSITIVE_ACTIONS = {
    unlock: true,
    quick_unlock: true,
    trunk_open: true,
    quick_trunk_open: true,
    windows_open: true,
    sunroof_open: true,
    vent_windows: true,
    vent_sunroof: true,
    alarm_toggle: true,
    remote_start: true,
  };

  var I18N = {
    it: {
      tabs: { overview: "Plancia", climate: "Clima", charging: "Ricarica", security: "Sicurezza" },
      weekdays: ["L", "M", "M", "G", "V", "S", "D"],
      dayNames: { mon: "Lun", tue: "Mar", wed: "Mer", thu: "Gio", fri: "Ven", sat: "Sab", sun: "Dom" },
      colors: { grey: "Grigio", teal: "Ottanio", violet: "Viola", black: "Nero", white: "Bianco" },
      layouts: { auto: "Auto", compact: "Compatto 4-Tab", cockpit: "Cockpit Desktop" },
      online: "Online",
      offline: "Offline",
      atHome: "A casa",
      away: "Fuori",
      awake: "Sveglia",
      asleep: "A riposo",
      locked: "Bloccata",
      unlocked: "Sbloccata",
      lock: "Blocca",
      unlock: "Sblocca",
      open: "Aperto",
      closed: "Chiuso",
      openCmd: "Apri",
      closeCmd: "Chiudi",
      confirm: "Conferma?",
      climateOn: "Clima ON",
      climateOff: "Clima OFF",
      charging: "In carica",
      idle: "In attesa",
      plugged: "Cavo collegato",
      unplugged: "Scollegato",
      evRange: "Autonomia EV",
      totalRange: "Autonomia tot.",
      fuelRange: "Autonomia benz.",
      chargingLbl: "Ricarica",
      odometer: "Odometro",
      cable: "Cavo",
      quickActions: "Comandi rapidi",
      trunk: "Baule",
      windows: "Finestrini",
      sunroof: "Tetto",
      ventWindows: "Ventila finestrini",
      ventSunroof: "Ventila tetto",
      alarm: "Antifurto",
      remoteStart: "Avvio remoto",
      flashLights: "Lampeggia",
      wakeCar: "Sveglia auto",
      refreshLoc: "Aggiorna pos.",
      refreshFull: "Stato completo",
      locateGps: "Localizza GPS",
      position: "Posizione",
      updated: "Aggiornato",
      climateHub: "Climatizzazione",
      targetTemp: "Temperatura",
      leftZone: "SX",
      rightZone: "DX",
      airPurification: "Purificazione aria",
      duration: "Durata",
      macros: "Macro comfort",
      coolAll: "Raffredda tutto",
      heatAll: "Riscalda tutto",
      defrosts: "Sbrinamenti e volante",
      windshieldDefrost: "Sbrina parabrezza",
      windshieldDefog: "Disappanna vetro",
      rearDefrost: "Lunotto termico",
      steeringHeat: "Volante caldo",
      seats: "Sedili",
      driver: "Guida",
      passenger: "Passeggero",
      rearLeft: "Post. SX",
      rearRight: "Post. DX",
      rearCenter: "Post. Centrale",
      heat: "Risc.",
      vent: "Vent.",
      liveCharging: "Ricarica live",
      scheduledCharging: "Ricarica programmata",
      startTime: "Inizio",
      chargeDuration: "Durata",
      chargeDays: "Giorni",
      applySchedule: "Applica piano",
      synced: "Sincronizzato",
      pendingSync: "Da sincronizzare",
      daysFallback2131: "Ripiego tutti i giorni (permesso 2131)",
      departures: "Partenze programmate",
      nextDeparture: "Prossima partenza",
      quickDeparture: "Partenza rapida",
      syncCharge: "Allinea ricarica",
      depClimateMode: "Clima partenza",
      blueprintTitle: "Stato chiusure e TPMS",
      securityControls: "Sicurezza e aperture",
      batteryLow: "Batteria bassa",
      fuelLow: "Carburante basso",
      chargeNeeded: "Ricarica necessaria",
      ajarLocked: "Chiusure aperte a veicolo bloccato",
      commandFailed: "Comando non riuscito",
      details: "Dettagli",
      more: "Altre entita",
      editorTitle: "Titolo",
      editorColor: "Colore veicolo",
      editorImage: "URL immagine (opzionale)",
      editorLayout: "Layout",
      editorDefaultTab: "Tab iniziale",
      editorShowAll: "Mostra tutte le entita",
      on: "ON",
      off: "OFF",
      active: "Attivo",
      inactive: "Spento",
      enableDay: "Attiva giorno",
      timeLbl: "Orario",
      chargeStartHint: "Avvio carica",
      homeEnergy: "Casa",
      awayEnergy: "Fuori",
      voltage: "Tensione",
      current: "Corrente",
      remaining: "Residuo",
      fastPort: "Presa rapida",
    },
    en: {
      tabs: { overview: "Overview", climate: "Climate", charging: "Charging", security: "Security" },
      weekdays: ["M", "T", "W", "T", "F", "S", "S"],
      dayNames: { mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", fri: "Fri", sat: "Sat", sun: "Sun" },
      colors: { grey: "Grey", teal: "Teal", violet: "Violet", black: "Black", white: "White" },
      layouts: { auto: "Auto", compact: "Compact 4-Tab", cockpit: "Desktop Cockpit" },
      online: "Online",
      offline: "Offline",
      atHome: "At home",
      away: "Away",
      awake: "Awake",
      asleep: "Asleep",
      locked: "Locked",
      unlocked: "Unlocked",
      lock: "Lock",
      unlock: "Unlock",
      open: "Open",
      closed: "Closed",
      openCmd: "Open",
      closeCmd: "Close",
      confirm: "Confirm?",
      climateOn: "Climate ON",
      climateOff: "Climate OFF",
      charging: "Charging",
      idle: "Idle",
      plugged: "Plugged in",
      unplugged: "Unplugged",
      evRange: "EV Range",
      totalRange: "Total Range",
      fuelRange: "Fuel Range",
      chargingLbl: "Charging",
      odometer: "Odometer",
      cable: "Cable",
      quickActions: "Quick controls",
      trunk: "Trunk",
      windows: "Windows",
      sunroof: "Sunroof",
      ventWindows: "Vent windows",
      ventSunroof: "Vent sunroof",
      alarm: "Alarm",
      remoteStart: "Remote start",
      flashLights: "Flash lights",
      wakeCar: "Wake car",
      refreshLoc: "Refresh pos.",
      refreshFull: "Full status",
      locateGps: "Locate GPS",
      position: "Location",
      updated: "Updated",
      climateHub: "Climate control",
      targetTemp: "Target temp",
      leftZone: "Left",
      rightZone: "Right",
      airPurification: "Air purification",
      duration: "Duration",
      macros: "Comfort macros",
      coolAll: "Cool everything",
      heatAll: "Heat everything",
      defrosts: "Defrost and wheel",
      windshieldDefrost: "Windshield defrost",
      windshieldDefog: "Windshield defog",
      rearDefrost: "Rear window heat",
      steeringHeat: "Steering wheel",
      seats: "Seats",
      driver: "Driver",
      passenger: "Passenger",
      rearLeft: "Rear L",
      rearRight: "Rear R",
      rearCenter: "Rear Center",
      heat: "Heat",
      vent: "Vent",
      liveCharging: "Live charging",
      scheduledCharging: "Scheduled charging",
      startTime: "Start time",
      chargeDuration: "Duration",
      chargeDays: "Days",
      applySchedule: "Apply schedule",
      synced: "Synced",
      pendingSync: "Pending sync",
      daysFallback2131: "All-days fallback (permission 2131)",
      departures: "Departure scheduler",
      nextDeparture: "Next departure",
      quickDeparture: "Quick departure",
      syncCharge: "Sync charging",
      depClimateMode: "Departure climate",
      blueprintTitle: "Closures and TPMS",
      securityControls: "Security and closures",
      batteryLow: "Battery low",
      fuelLow: "Fuel low",
      chargeNeeded: "Charge needed",
      ajarLocked: "Open closure while locked",
      commandFailed: "Command failed",
      details: "Details",
      more: "More entities",
      editorTitle: "Title",
      editorColor: "Vehicle color",
      editorImage: "Image URL (optional)",
      editorLayout: "Layout",
      editorDefaultTab: "Default tab",
      editorShowAll: "Show all entities",
      on: "ON",
      off: "OFF",
      active: "Active",
      inactive: "Off",
      enableDay: "Enable day",
      timeLbl: "Time",
      chargeStartHint: "Charge start",
      homeEnergy: "Home",
      awayEnergy: "Away",
      voltage: "Voltage",
      current: "Current",
      remaining: "Remaining",
      fastPort: "Fast port",
    },
    nl: {
      tabs: { overview: "Overzicht", climate: "Klimaat", charging: "Laden", security: "Beveiliging" },
      weekdays: ["M", "D", "W", "D", "V", "Z", "Z"],
      dayNames: { mon: "Ma", tue: "Di", wed: "Wo", thu: "Do", fri: "Vr", sat: "Za", sun: "Zo" },
      colors: { grey: "Grijs", teal: "Zeegroen", violet: "Violet", black: "Zwart", white: "Wit" },
      layouts: { auto: "Auto", compact: "Compact 4-Tab", cockpit: "Desktop Cockpit" },
      online: "Online",
      offline: "Offline",
      atHome: "Thuis",
      away: "Weg",
      awake: "Wakker",
      asleep: "In rust",
      locked: "Vergrendeld",
      unlocked: "Ontgrendeld",
      lock: "Vergrendel",
      unlock: "Ontgrendel",
      open: "Open",
      closed: "Gesloten",
      openCmd: "Open",
      closeCmd: "Sluit",
      confirm: "Bevestig?",
      climateOn: "Klimaat AAN",
      climateOff: "Klimaat UIT",
      charging: "Opladen",
      idle: "Inactief",
      plugged: "Aangesloten",
      unplugged: "Losgekoppeld",
      evRange: "EV-bereik",
      totalRange: "Totaal bereik",
      fuelRange: "Benzinebereik",
      chargingLbl: "Laden",
      odometer: "Kilometerstand",
      cable: "Kabel",
      quickActions: "Snelle bediening",
      trunk: "Kofferbak",
      windows: "Ramen",
      sunroof: "Schuifdak",
      ventWindows: "Ramen ventileren",
      ventSunroof: "Dak ventileren",
      alarm: "Alarm",
      remoteStart: "Op afstand starten",
      flashLights: "Knipperlichten",
      wakeCar: "Auto wekken",
      refreshLoc: "Locatie vernieuwen",
      refreshFull: "Volledige status",
      locateGps: "GPS zoeken",
      position: "Locatie",
      updated: "Bijgewerkt",
      climateHub: "Klimaatregeling",
      targetTemp: "Doeltemp.",
      leftZone: "Links",
      rightZone: "Rechts",
      airPurification: "Luchtzuivering",
      duration: "Duur",
      macros: "Comfortmacro's",
      coolAll: "Alles koelen",
      heatAll: "Alles verwarmen",
      defrosts: "Ontdooiing en stuur",
      windshieldDefrost: "Voorruit ontdooien",
      windshieldDefog: "Voorruit ontwasemen",
      rearDefrost: "Achterruitverwarming",
      steeringHeat: "Stuurverwarming",
      seats: "Stoelen",
      driver: "Bestuurder",
      passenger: "Passagier",
      rearLeft: "Achter L",
      rearRight: "Achter R",
      rearCenter: "Achter midden",
      heat: "Verw.",
      vent: "Vent.",
      liveCharging: "Live laden",
      scheduledCharging: "Gepland laden",
      startTime: "Starttijd",
      chargeDuration: "Duur",
      chargeDays: "Dagen",
      applySchedule: "Schema toepassen",
      synced: "Gesynchroniseerd",
      pendingSync: "Wacht op sync",
      daysFallback2131: "Alle dagen (permissie 2131)",
      departures: "Vertrekschema",
      nextDeparture: "Volgend vertrek",
      quickDeparture: "Snel vertrek",
      syncCharge: "Laden synchroniseren",
      depClimateMode: "Vertrekklimaat",
      blueprintTitle: "Sluitingen en TPMS",
      securityControls: "Beveiliging en sluitingen",
      batteryLow: "Accu laag",
      fuelLow: "Brandstof laag",
      chargeNeeded: "Laden nodig",
      ajarLocked: "Opening open tijdens vergrendeling",
      commandFailed: "Opdracht mislukt",
      details: "Details",
      more: "Meer entiteiten",
      editorTitle: "Titel",
      editorColor: "Voertuigkleur",
      editorImage: "Afbeeldings-URL (optioneel)",
      editorLayout: "Indeling",
      editorDefaultTab: "Begintab",
      editorShowAll: "Alle entiteiten tonen",
      on: "AAN",
      off: "UIT",
      active: "Actief",
      inactive: "Uit",
      enableDay: "Dag inschakelen",
      timeLbl: "Tijd",
      chargeStartHint: "Start laden",
      homeEnergy: "Thuis",
      awayEnergy: "Onderweg",
      voltage: "Spanning",
      current: "Stroom",
      remaining: "Resterend",
      fastPort: "Snellaadpoort",
    },
  };

  function getLang(hass) {
    var raw = "en";
    if (hass && hass.locale && hass.locale.language) {
      raw = hass.locale.language;
    } else if (hass && hass.language) {
      raw = hass.language;
    }
    var code = String(raw || "en").slice(0, 2).toLowerCase();
    return I18N[code] ? code : "en";
  }

  function getTexts(lang) {
    return I18N[lang] || I18N.en;
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function sanitizeUrl(url) {
    if (url == null) return "";
    var s = String(url).trim();
    if (!s) return "";
    if (/^data:image\/(?:png|jpe?g|webp|gif|avif);base64,[A-Za-z0-9+/=]+$/i.test(s)) {
      return s;
    }
    if (/^(?:https?:\/\/|\/(?!\/))/i.test(s)) {
      if (/[\x00-\x1f\x7f]/.test(s)) return "";
      return s.replace(/["'()\\<>\s]/g, encodeURIComponent);
    }
    return "";
  }

  function resolveColor(raw) {
    var norm = String(raw == null ? "" : raw).trim().toLowerCase();
    if (!norm) return "grey";
    return COLOR_ALIASES[norm] || "grey";
  }

  function resolveHeroImage(config, items) {
    var cfg = config || {};
    if (cfg.image) {
      var safeCfg = sanitizeUrl(cfg.image);
      if (safeCfg) return safeCfg;
    }
    if (Array.isArray(items)) {
      for (var i = 0; i < items.length; i += 1) {
        var r = items[i];
        var attrImg = r && r.s && r.s.attributes && r.s.attributes.vehicle_image;
        if (attrImg) {
          var safeAttr = sanitizeUrl(attrImg);
          if (safeAttr) return safeAttr;
        }
      }
    }
    var color = resolveColor(cfg.color);
    return HERO_IMAGES[color] || DEFAULT_HERO;
  }

  function isSensitiveAction(actionId) {
    return Boolean(SENSITIVE_ACTIONS[String(actionId || "")]);
  }

  function hhmmToMinutes(hhmm) {
    if (!hhmm || typeof hhmm !== "string") return null;
    var parts = hhmm.split(":");
    if (parts.length < 2) return null;
    var hh = parseInt(parts[0], 10);
    var mm = parseInt(parts[1], 10);
    if (isNaN(hh) || isNaN(mm)) return null;
    return ((hh * 60 + mm) % 1440 + 1440) % 1440;
  }

  function formatTimestamp(raw, lang) {
    if (!raw || raw === "unknown" || raw === "unavailable") return "—";
    var dt = new Date(raw);
    if (isNaN(dt.getTime())) return String(raw);
    try {
      return dt.toLocaleTimeString(lang || "en", { hour: "2-digit", minute: "2-digit" });
    } catch (e) {
      var hh = String(dt.getHours()).padStart(2, "0");
      var mm = String(dt.getMinutes()).padStart(2, "0");
      return hh + ":" + mm;
    }
  }

  function buildStyles() {
    return [
      ":host {",
      "  display: block;",
      "  container-type: inline-size;",
      "  font-family: var(--ha-card-font-family, inherit);",
      "  --lp-canvas: #111317;",
      "  --lp-surface: #181B20;",
      "  --lp-elevated: #21252C;",
      "  --lp-elevated-hover: #262B34;",
      "  --lp-border: rgba(255, 255, 255, 0.08);",
      "  --lp-border-strong: rgba(255, 255, 255, 0.16);",
      "  --lp-text: #F3F4F6;",
      "  --lp-text-secondary: #9CA3AF;",
      "  --lp-text-muted: #6B7280;",
      "  --lp-emerald: #34D399;",
      "  --lp-glacier: #60A5FA;",
      "  --lp-amber: #F59E0B;",
      "  --lp-coral: #EF4444;",
      "}",
      "*, *::before, *::after { box-sizing: border-box; }",
      "button, input, select { font: inherit; color: inherit; }",
      ".sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }",
      ".hidden { display: none !important; }",
      ".num { font-variant-numeric: tabular-nums; }",
      "ha-card { display: block; width: 100%; background: var(--lp-canvas); border: 1px solid var(--lp-border); border-radius: 16px; overflow: hidden; color: var(--lp-text); box-shadow: none; }",
      ".cockpit-grid { display: flex; flex-direction: column; gap: 10px; padding: 10px; }",
      ".hero-region { display: flex; flex-direction: column; gap: 8px; }",
      ".hero-card { position: relative; min-height: 196px; border-radius: 12px; overflow: hidden; background: var(--lp-surface); border: 1px solid var(--lp-border); display: flex; flex-direction: column; justify-content: space-between; }",
      ".hero-img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: center 56%; pointer-events: none; }",
      ".hero-scrim { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(17, 19, 23, 0.62) 0%, rgba(17, 19, 23, 0.12) 45%, rgba(24, 27, 32, 0.88) 84%, #181B20 100%); pointer-events: none; }",
      ".hero-inner { position: relative; z-index: 1; padding: 14px; display: flex; flex-direction: column; justify-content: space-between; min-height: 196px; gap: 12px; }",
      ".hero-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }",
      ".status-pill { display: inline-flex; align-items: center; gap: 7px; padding: 5px 10px; min-height: 30px; border-radius: 999px; background: rgba(17, 19, 23, 0.78); border: 1px solid var(--lp-border); -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px); font-size: 0.74rem; font-weight: 600; color: var(--lp-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 72%; }",
      ".status-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; background: var(--lp-text-muted); }",
      ".status-dot.is-online { background: var(--lp-emerald); }",
      ".status-dot.is-offline { background: var(--lp-coral); }",
      ".soc-btn { position: relative; width: 54px; height: 54px; padding: 0; border-radius: 999px; border: 1px solid var(--lp-border); background: rgba(17, 19, 23, 0.82); -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px); display: inline-flex; align-items: center; justify-content: center; cursor: pointer; flex-shrink: 0; }",
      ".soc-btn svg { position: absolute; inset: 2px; width: 48px; height: 48px; transform: rotate(-90deg); }",
      ".soc-ring-bg { fill: none; stroke: rgba(255, 255, 255, 0.12); stroke-width: 3.2; }",
      ".soc-ring-fg { fill: none; stroke: var(--lp-emerald); stroke-width: 3.2; stroke-linecap: round; }",
      ".soc-ring-fg.is-warn { stroke: var(--lp-amber); }",
      ".soc-ring-fg.is-low { stroke: var(--lp-coral); }",
      ".soc-val { position: relative; font-size: 0.78rem; font-weight: 700; color: var(--lp-text); line-height: 1; }",
      ".hero-bottom { margin-top: auto; cursor: pointer; border-radius: 8px; padding: 2px 0; }",
      ".hero-title { font-size: 1.28rem; font-weight: 700; letter-spacing: -0.015em; line-height: 1.2; color: var(--lp-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }",
      ".hero-sub { font-size: 0.8rem; color: var(--lp-text-secondary); margin-top: 3px; min-height: 1.2em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }",
      ".warns-row { display: flex; flex-wrap: wrap; gap: 6px; }",
      ".warn-chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; min-height: 34px; border-radius: 8px; background: rgba(239, 68, 68, 0.14); border: 1px solid rgba(239, 68, 68, 0.32); color: #FCA5A5; font-size: 0.78rem; font-weight: 600; cursor: pointer; }",
      ".warn-chip.is-amber { background: rgba(245, 158, 11, 0.14); border-color: rgba(245, 158, 11, 0.32); color: #FCD34D; }",
      ".error-banner { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 8px 12px; border-radius: 10px; background: rgba(239, 68, 68, 0.16); border: 1px solid rgba(239, 68, 68, 0.4); color: #FECACA; font-size: 0.82rem; }",
      ".error-dismiss { background: transparent; border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 6px; min-width: 32px; min-height: 32px; padding: 2px 8px; cursor: pointer; }",
      ".tabs-bar { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 4px; padding: 4px; background: var(--lp-surface); border: 1px solid var(--lp-border); border-radius: 12px; }",
      ".tab-btn { min-height: 44px; min-width: 44px; border: 1px solid transparent; border-radius: 9px; background: transparent; color: var(--lp-text-secondary); font-size: 0.78rem; font-weight: 600; cursor: pointer; padding: 6px 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }",
      ".tab-btn:hover { color: var(--lp-text); background: rgba(255, 255, 255, 0.04); }",
      ".tab-btn.is-active { background: var(--lp-text); color: var(--lp-canvas); font-weight: 700; }",
      ".panel { display: none; flex-direction: column; gap: 10px; }",
      ".panel.is-active { display: flex; }",
      ".surface { background: var(--lp-surface); border: 1px solid var(--lp-border); border-radius: 12px; padding: 12px; display: flex; flex-direction: column; gap: 10px; }",
      ".sec-hdr { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: 0.76rem; font-weight: 600; color: var(--lp-text-muted); letter-spacing: 0.02em; }",
      ".metrics-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }",
      ".metric-card { background: var(--lp-surface); border: 1px solid var(--lp-border); border-radius: 12px; padding: 11px 12px; cursor: pointer; display: flex; flex-direction: column; gap: 4px; min-height: 70px; }",
      ".metric-card:hover { background: var(--lp-elevated); border-color: var(--lp-border-strong); }",
      ".metric-lbl { font-size: 0.74rem; color: var(--lp-text-secondary); }",
      ".metric-val { font-size: 1.08rem; font-weight: 700; color: var(--lp-text); line-height: 1.25; }",
      ".metric-bar { height: 3px; border-radius: 999px; background: rgba(255, 255, 255, 0.08); overflow: hidden; margin-top: 2px; }",
      ".metric-bar-fill { height: 100%; background: var(--lp-emerald); border-radius: 999px; }",
      ".btn-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }",
      ".btn-row { display: flex; flex-wrap: wrap; gap: 8px; }",
      ".ctrl-btn { position: relative; overflow: hidden; min-height: 44px; min-width: 44px; padding: 8px 12px; border-radius: 10px; background: var(--lp-elevated); border: 1px solid var(--lp-border); color: var(--lp-text); font-size: 0.82rem; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 6px; text-align: center; }",
      ".ctrl-btn:hover { background: var(--lp-elevated-hover); border-color: var(--lp-border-strong); }",
      ".ctrl-btn:disabled, .ctrl-btn.is-pending { opacity: 0.58; cursor: wait; }",
      ".ctrl-btn.is-primary { background: var(--lp-text); color: var(--lp-canvas); border-color: var(--lp-text); }",
      ".ctrl-btn.is-emerald { border-color: rgba(52, 211, 153, 0.45); color: var(--lp-emerald); background: rgba(52, 211, 153, 0.12); }",
      ".ctrl-btn.is-glacier { border-color: rgba(96, 165, 250, 0.45); color: var(--lp-glacier); background: rgba(96, 165, 250, 0.12); }",
      ".ctrl-btn.is-amber { border-color: rgba(245, 158, 11, 0.45); color: var(--lp-amber); background: rgba(245, 158, 11, 0.12); }",
      ".ctrl-btn.is-confirming { border-color: rgba(239, 68, 68, 0.72); color: #FECACA; background: rgba(239, 68, 68, 0.24); }",
      ".confirm-bar { position: absolute; left: 0; bottom: 0; height: 3px; width: 100%; background: var(--lp-coral); transform-origin: left center; pointer-events: none; }",
      ".stepper { display: flex; align-items: center; justify-content: space-between; gap: 8px; background: var(--lp-elevated); border: 1px solid var(--lp-border); border-radius: 10px; padding: 4px; }",
      ".step-val { font-size: 1.15rem; font-weight: 700; color: var(--lp-text); }",
      ".chip-row { display: flex; flex-wrap: wrap; gap: 6px; }",
      ".chip-btn { min-height: 44px; min-width: 44px; padding: 6px 11px; border-radius: 9px; background: var(--lp-elevated); border: 1px solid var(--lp-border); font-size: 0.8rem; font-weight: 600; color: var(--lp-text-secondary); cursor: pointer; }",
      ".chip-btn.is-active { background: var(--lp-text); color: var(--lp-canvas); border-color: var(--lp-text); }",
      ".seat-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }",
      ".seat-card { background: var(--lp-elevated); border: 1px solid var(--lp-border); border-radius: 10px; padding: 8px; display: flex; flex-direction: column; gap: 6px; }",
      ".seat-name { font-size: 0.76rem; font-weight: 600; color: var(--lp-text-secondary); }",
      ".seat-btns { display: flex; gap: 6px; }",
      ".seat-btns .ctrl-btn { flex: 1; padding: 6px; font-size: 0.76rem; }",
      ".seat-readonly { background: var(--lp-elevated); border: 1px solid var(--lp-border); border-radius: 10px; padding: 8px 10px; display: flex; align-items: center; justify-content: space-between; font-size: 0.78rem; color: var(--lp-text-secondary); }",
      ".timeline-track { position: relative; height: 14px; border-radius: 7px; background: var(--lp-elevated); border: 1px solid var(--lp-border); overflow: hidden; }",
      ".timeline-seg { position: absolute; top: 0; bottom: 0; background: var(--lp-emerald); opacity: 0.85; border-radius: 4px; }",
      ".timeline-axis { display: flex; justify-content: space-between; font-size: 0.68rem; color: var(--lp-text-muted); margin-top: 3px; }",
      ".field-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; min-height: 44px; }",
      ".field-lbl { font-size: 0.82rem; color: var(--lp-text-secondary); }",
      ".ctrl-input, .ctrl-select { min-height: 44px; padding: 6px 10px; border-radius: 9px; background: var(--lp-elevated); border: 1px solid var(--lp-border); color: var(--lp-text); font-size: 0.84rem; }",
      ".days-strip { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; }",
      ".day-chip { min-height: 44px; min-width: 36px; border-radius: 9px; border: 1px solid var(--lp-border); background: var(--lp-elevated); color: var(--lp-text-secondary); font-size: 0.78rem; font-weight: 700; cursor: pointer; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px; padding: 4px 2px; }",
      ".day-chip.is-enabled { border-color: rgba(52, 211, 153, 0.48); color: var(--lp-text); }",
      ".day-chip.is-expanded { background: var(--lp-text); color: var(--lp-canvas); border-color: var(--lp-text); }",
      ".day-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--lp-text-muted); }",
      ".day-chip.is-enabled .day-dot { background: var(--lp-emerald); }",
      ".day-editor { background: var(--lp-elevated); border: 1px solid var(--lp-border-strong); border-radius: 10px; padding: 10px; display: flex; flex-direction: column; gap: 8px; }",
      ".bp-stage { display: grid; grid-template-columns: minmax(82px, 1fr) minmax(112px, 130px) minmax(82px, 1fr); gap: 8px; align-items: center; }",
      ".tpms-col { display: flex; flex-direction: column; justify-content: space-between; gap: 28px; }",
      ".tpms-box { background: var(--lp-elevated); border: 1px solid var(--lp-border); border-radius: 9px; padding: 7px 8px; cursor: pointer; display: flex; flex-direction: column; gap: 2px; min-height: 48px; }",
      ".tpms-box.is-ok { border-color: rgba(52, 211, 153, 0.35); }",
      ".tpms-box.is-alert { border-color: rgba(239, 68, 68, 0.72); background: rgba(239, 68, 68, 0.14); color: #FECACA; }",
      ".tpms-press { font-size: 0.82rem; font-weight: 700; color: var(--lp-text); }",
      ".tpms-temp { font-size: 0.72rem; color: var(--lp-text-secondary); }",
      ".bp-svg { width: 100%; max-width: 130px; height: auto; display: block; margin: 0 auto; }",
      ".bp-body { fill: var(--lp-elevated); stroke: rgba(255, 255, 255, 0.24); stroke-width: 1.5; }",
      ".bp-glass { fill: rgba(17, 19, 23, 0.75); stroke: rgba(255, 255, 255, 0.2); stroke-width: 1; }",
      ".bp-part { fill: rgba(255, 255, 255, 0.08); stroke: rgba(255, 255, 255, 0.34); stroke-width: 1.4; }",
      ".bp-part.is-open { fill: rgba(245, 158, 11, 0.35); stroke: var(--lp-amber); }",
      ".bp-part.is-window-open { fill: rgba(96, 165, 250, 0.35); stroke: var(--lp-glacier); }",
      ".bp-part.is-moving { fill: rgba(96, 165, 250, 0.45); stroke: var(--lp-glacier); }",
      ".bp-door-fl.is-open { transform: translate(-6px, 0) rotate(-18deg); transform-origin: 48px 98px; }",
      ".bp-door-fr.is-open { transform: translate(6px, 0) rotate(18deg); transform-origin: 112px 98px; }",
      ".bp-door-rl.is-open { transform: translate(-6px, 0) rotate(-18deg); transform-origin: 48px 148px; }",
      ".bp-door-rr.is-open { transform: translate(6px, 0) rotate(18deg); transform-origin: 112px 148px; }",
      ".footer-bar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; font-size: 0.76rem; color: var(--lp-text-secondary); }",
      ".badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 600; background: var(--lp-elevated); border: 1px solid var(--lp-border); color: var(--lp-text-secondary); }",
      ".badge.is-emerald { border-color: rgba(52, 211, 153, 0.4); color: var(--lp-emerald); background: rgba(52, 211, 153, 0.1); }",
      ".badge.is-glacier { border-color: rgba(96, 165, 250, 0.4); color: var(--lp-glacier); background: rgba(96, 165, 250, 0.1); }",
      ".badge.is-amber { border-color: rgba(245, 158, 11, 0.4); color: var(--lp-amber); background: rgba(245, 158, 11, 0.1); }",
      ".info-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 9px 10px; min-height: 44px; border-radius: 9px; background: var(--lp-elevated); border: 1px solid var(--lp-border); cursor: pointer; font-size: 0.84rem; }",
      ".info-row:hover { border-color: var(--lp-border-strong); }",
      ".info-val { font-weight: 600; color: var(--lp-text); }",
      "ha-card[data-layout=\"cockpit\"] .tabs-bar { display: none; }",
      "ha-card[data-layout=\"cockpit\"] .panel { display: flex; }",
      "@container (min-width: 680px) {",
      "  ha-card[data-layout=\"auto\"] .tabs-bar { display: none; }",
      "  ha-card[data-layout=\"auto\"] .panel { display: flex; }",
      "  ha-card[data-layout=\"auto\"] .cockpit-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); align-items: stretch; }",
      "  ha-card[data-layout=\"auto\"] .hero-region { grid-column: 1 / -1; }",
      "}",
      "@container (min-width: 560px) {",
      "  ha-card[data-layout=\"cockpit\"] .cockpit-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); align-items: stretch; }",
      "  ha-card[data-layout=\"cockpit\"] .hero-region { grid-column: 1 / -1; }",
      "}",
      "@container (min-width: 960px) {",
      "  ha-card[data-layout=\"auto\"] .cockpit-grid, ha-card[data-layout=\"cockpit\"] .cockpit-grid { grid-template-columns: minmax(250px, 1fr) minmax(290px, 1.15fr) minmax(250px, 1fr); }",
      "  ha-card[data-layout=\"auto\"] .hero-region, ha-card[data-layout=\"cockpit\"] .hero-region { grid-column: 1; grid-row: 1; }",
      "  ha-card[data-layout=\"auto\"] .panel[data-panel=\"security\"], ha-card[data-layout=\"cockpit\"] .panel[data-panel=\"security\"] { grid-column: 1; grid-row: 2; }",
      "  ha-card[data-layout=\"auto\"] .panel[data-panel=\"overview\"], ha-card[data-layout=\"cockpit\"] .panel[data-panel=\"overview\"] { grid-column: 2; grid-row: 1; }",
      "  ha-card[data-layout=\"auto\"] .panel[data-panel=\"charging\"], ha-card[data-layout=\"cockpit\"] .panel[data-panel=\"charging\"] { grid-column: 2; grid-row: 2; }",
      "  ha-card[data-layout=\"auto\"] .panel[data-panel=\"climate\"], ha-card[data-layout=\"cockpit\"] .panel[data-panel=\"climate\"] { grid-column: 3; grid-row: 1 / span 2; }",
      "}",
      "@supports not (container-type: inline-size) {",
      "  @media (min-width: 680px) {",
      "    ha-card[data-layout=\"auto\"] .tabs-bar { display: none; }",
      "    ha-card[data-layout=\"auto\"] .panel { display: flex; }",
      "    ha-card[data-layout=\"auto\"] .cockpit-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); align-items: stretch; }",
      "    ha-card[data-layout=\"auto\"] .hero-region { grid-column: 1 / -1; }",
      "  }",
      "  @media (min-width: 960px) {",
      "    ha-card[data-layout=\"auto\"] .cockpit-grid { grid-template-columns: minmax(250px, 1fr) minmax(290px, 1.15fr) minmax(250px, 1fr); }",
      "    ha-card[data-layout=\"auto\"] .hero-region { grid-column: 1; grid-row: 1; }",
      "    ha-card[data-layout=\"auto\"] .panel[data-panel=\"security\"] { grid-column: 1; grid-row: 2; }",
      "    ha-card[data-layout=\"auto\"] .panel[data-panel=\"overview\"] { grid-column: 2; grid-row: 1; }",
      "    ha-card[data-layout=\"auto\"] .panel[data-panel=\"charging\"] { grid-column: 2; grid-row: 2; }",
      "    ha-card[data-layout=\"auto\"] .panel[data-panel=\"climate\"] { grid-column: 3; grid-row: 1 / span 2; }",
      "  }",
      "}",
      "@media (prefers-reduced-motion: no-preference) {",
      "  .soc-ring-fg { transition: stroke-dashoffset 0.35s ease-out, stroke 0.2s ease; }",
      "  .bp-part { transition: opacity 0.2s ease, transform 0.25s ease-out, stroke 0.2s ease, fill 0.2s ease; }",
      "  .panel.is-active { animation: lp-fade 0.18s ease-out; }",
      "  .confirm-bar { animation: lp-drain 4s linear forwards; }",
      "  .bp-part.is-moving { animation: lp-pulse-soft 1.2s ease-in-out infinite alternate; }",
      "}",
      "@media (prefers-reduced-motion: reduce) {",
      "  *, *::before, *::after { animation: none !important; transition: none !important; }",
      "}",
      "button:focus-visible, input:focus-visible, select:focus-visible, [role=\"button\"]:focus-visible { outline: 2px solid #F3F4F6; outline-offset: 2px; }",
      "@keyframes lp-fade { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; transform: translateY(0); } }",
      "@keyframes lp-drain { from { transform: scaleX(1); } to { transform: scaleX(0); } }",
      "@keyframes lp-pulse-soft { from { opacity: 0.45; } to { opacity: 0.95; } }",
    ].join("\n");
  }

  function buildEditorStyles() {
    return [
      ":host { display: block; font-family: var(--ha-card-font-family, inherit); color: #F3F4F6; }",
      "*, *::before, *::after { box-sizing: border-box; }",
      "button, input, select { font: inherit; color: inherit; }",
      ".ed-wrap { display: flex; flex-direction: column; gap: 14px; padding: 12px; background: #181B20; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; }",
      ".ed-field { display: flex; flex-direction: column; gap: 6px; }",
      ".ed-lbl { font-size: 0.8rem; font-weight: 600; color: #9CA3AF; }",
      ".ed-input, .ed-select { min-height: 44px; padding: 8px 10px; border-radius: 9px; background: #21252C; border: 1px solid rgba(255, 255, 255, 0.12); color: #F3F4F6; width: 100%; }",
      ".ed-swatches { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 6px; }",
      ".ed-swatch { min-height: 44px; padding: 6px 4px; border-radius: 9px; background: #21252C; border: 1px solid rgba(255, 255, 255, 0.1); cursor: pointer; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; font-size: 0.72rem; color: #9CA3AF; }",
      ".ed-swatch.is-selected { border-color: #F3F4F6; background: #262B34; color: #F3F4F6; font-weight: 700; }",
      ".ed-dot { width: 16px; height: 16px; border-radius: 50%; border: 1px solid rgba(255, 255, 255, 0.28); }",
      ".ed-check-row { display: flex; align-items: center; justify-content: space-between; min-height: 44px; padding: 6px 10px; border-radius: 9px; background: #21252C; border: 1px solid rgba(255, 255, 255, 0.08); cursor: pointer; }",
      "button:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid #F3F4F6; outline-offset: 2px; }",
    ].join("\n");
  }

  class LepasCardEditor extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._config = {};
      this._hass = null;
      this._rendered = false;
      this._onEvent = this._handleFieldChange.bind(this);
    }

    setConfig(config) {
      this._config = Object.assign({}, config || {});
      this._render();
    }

    set hass(hass) {
      var prevLang = this._lang;
      this._hass = hass;
      var nextLang = getLang(hass);
      if (prevLang !== nextLang) {
        this._lang = nextLang;
        this._rendered = false;
        this._render();
      }
    }

    _emitConfig(patch) {
      var next = Object.assign({}, this._config, patch);
      if (next.title === "") delete next.title;
      if (next.image === "") delete next.image;
      this._config = next;
      this.dispatchEvent(new CustomEvent("config-changed", {
        detail: { config: next },
        bubbles: true,
        composed: true,
      }));
    }

    _handleFieldChange(ev) {
      var target = ev.target;
      if (!target) return;
      var colorBtn = target.closest ? target.closest("[data-color]") : null;
      if (ev.type === "click" && colorBtn) {
        this._emitConfig({ color: colorBtn.getAttribute("data-color") });
        this._syncValues();
        return;
      }
      if (ev.type === "change" || ev.type === "input") {
        var field = target.getAttribute("data-field");
        if (!field) return;
        if (ev.type === "input" && field !== "title" && field !== "image") return;
        if (field === "show_all") {
          this._emitConfig({ show_all: Boolean(target.checked) });
        } else {
          var patch = {};
          patch[field] = String(target.value || "").trim();
          this._emitConfig(patch);
        }
      }
    }

    _syncValues() {
      if (!this.shadowRoot) return;
      var cfg = this._config || {};
      var color = resolveColor(cfg.color);
      var swatches = this.shadowRoot.querySelectorAll("[data-color]");
      for (var i = 0; i < swatches.length; i += 1) {
        swatches[i].classList.toggle("is-selected", swatches[i].getAttribute("data-color") === color);
      }
      var titleEl = this.shadowRoot.querySelector('[data-field="title"]');
      if (titleEl && this.shadowRoot.activeElement !== titleEl) titleEl.value = cfg.title || "";
      var imgEl = this.shadowRoot.querySelector('[data-field="image"]');
      if (imgEl && this.shadowRoot.activeElement !== imgEl) imgEl.value = cfg.image || "";
      var layEl = this.shadowRoot.querySelector('[data-field="layout"]');
      if (layEl) layEl.value = VALID_LAYOUTS.indexOf(cfg.layout) >= 0 ? cfg.layout : "auto";
      var tabEl = this.shadowRoot.querySelector('[data-field="default_tab"]');
      if (tabEl) tabEl.value = VALID_TABS.indexOf(cfg.default_tab) >= 0 ? cfg.default_tab : "overview";
      var showEl = this.shadowRoot.querySelector('[data-field="show_all"]');
      if (showEl) showEl.checked = Boolean(cfg.show_all);
    }

    _render() {
      if (!this.shadowRoot) return;
      var lang = getLang(this._hass);
      this._lang = lang;
      var t = getTexts(lang);
      if (!this._rendered) {
        var swatchesHtml = VALID_COLORS.map(function (c) {
          return '<button type="button" class="ed-swatch" data-color="' + c + '">' +
            '<span class="ed-dot" style="background:' + COLOR_SWATCHES[c] + '"></span>' +
            '<span>' + escapeHtml(t.colors[c] || c) + "</span></button>";
        }).join("");

        var layoutOpts = VALID_LAYOUTS.map(function (l) {
          return '<option value="' + l + '">' + escapeHtml(t.layouts[l] || l) + "</option>";
        }).join("");

        var tabOpts = VALID_TABS.map(function (tb) {
          return '<option value="' + tb + '">' + escapeHtml(t.tabs[tb] || tb) + "</option>";
        }).join("");

        this.shadowRoot.innerHTML =
          "<style>" + buildEditorStyles() + "</style>" +
          '<div class="ed-wrap">' +
            '<div class="ed-field">' +
              '<span class="ed-lbl">' + escapeHtml(t.editorColor) + "</span>" +
              '<div class="ed-swatches">' + swatchesHtml + "</div>" +
            "</div>" +
            '<div class="ed-field">' +
              '<label class="ed-lbl">' + escapeHtml(t.editorLayout) + "</label>" +
              '<select class="ed-select" data-field="layout">' + layoutOpts + "</select>" +
            "</div>" +
            '<div class="ed-field">' +
              '<label class="ed-lbl">' + escapeHtml(t.editorDefaultTab) + "</label>" +
              '<select class="ed-select" data-field="default_tab">' + tabOpts + "</select>" +
            "</div>" +
            '<div class="ed-field">' +
              '<label class="ed-lbl">' + escapeHtml(t.editorTitle) + "</label>" +
              '<input type="text" class="ed-input" data-field="title" placeholder="Lepas">' +
            "</div>" +
            '<div class="ed-field">' +
              '<label class="ed-lbl">' + escapeHtml(t.editorImage) + "</label>" +
              '<input type="text" class="ed-input" data-field="image" placeholder="/lepas_card/lepas-hero-grey.png?v=1.19.0">' +
            "</div>" +
            '<label class="ed-check-row">' +
              '<span class="ed-lbl">' + escapeHtml(t.editorShowAll) + "</span>" +
              '<input type="checkbox" data-field="show_all">' +
            "</label>" +
          "</div>";

        this.shadowRoot.addEventListener("click", this._onEvent);
        this.shadowRoot.addEventListener("change", this._onEvent);
        this.shadowRoot.addEventListener("input", this._onEvent);
        this._rendered = true;
      }
      this._syncValues();
    }
  }

  class LepasCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this.config = {
        integration: "lepas",
        prefix: "lepas_",
        show_all: false,
        color: "grey",
        layout: "auto",
        default_tab: "overview",
      };
      this._hass = null;
      this._activeTab = "overview";
      this._expandedDay = null;
      this._confirmState = null;
      this._confirmTimer = null;
      this._pendingKeys = new Set();
      this._errorMsg = null;
      this._lastStructKey = "";
      this._lastDefaultTab = "overview";
      this._listenersBound = false;
      this._latestActions = Object.create(null);
      this._onClick = this._handleClick.bind(this);
      this._onChange = this._handleChange.bind(this);
      this._onKeyDown = this._handleKeyDown.bind(this);
    }

    static getStubConfig() {
      return { type: "custom:lepas-card" };
    }

    static getGridOptions() {
      return { columns: 12, min_columns: 4, rows: "auto" };
    }

    static getConfigElement() {
      return document.createElement("lepas-card-editor");
    }

    getCardSize() {
      return 4;
    }

    setConfig(config) {
      var merged = Object.assign(
        {
          integration: "lepas",
          prefix: "lepas_",
          show_all: false,
          color: "grey",
          layout: "auto",
          default_tab: "overview",
        },
        config || {}
      );
      if (VALID_LAYOUTS.indexOf(merged.layout) < 0) merged.layout = "auto";
      if (VALID_TABS.indexOf(merged.default_tab) < 0) merged.default_tab = "overview";
      var prevDefault = this._lastDefaultTab;
      this.config = merged;
      if (!this._lastStructKey || merged.default_tab !== prevDefault) {
        this._activeTab = merged.default_tab;
      }
      this._lastDefaultTab = merged.default_tab;
      if (this._hass) this._render(this._hass);
    }

    disconnectedCallback() {
      if (this._confirmTimer) {
        clearTimeout(this._confirmTimer);
        this._confirmTimer = null;
      }
      this._confirmState = null;
    }

    _dead(s) {
      return !s || s.state === "unavailable" || s.state === "unknown" || s.state === "";
    }

    _num(s) {
      var n = s ? parseFloat(s.state) : NaN;
      return isNaN(n) ? null : n;
    }

    _disp(s) {
      if (!s) return "—";
      var h = this._hass;
      if (h && typeof h.formatEntityState === "function") {
        try { return h.formatEntityState(s); } catch (e) { /* fall through */ }
      }
      var n = parseFloat(s.state);
      var u = s.attributes && s.attributes.unit_of_measurement;
      if (isNaN(n)) return u ? s.state + " " + u : s.state;
      var dp = s.attributes && s.attributes.suggested_display_precision;
      var v;
      if (typeof dp === "number") {
        v = n.toFixed(dp);
      } else if (Number.isInteger(n)) {
        v = String(n);
      } else if (u === "bar") {
        v = n.toFixed(2);
      } else {
        v = String(Math.round(n * 100) / 100);
      }
      return u ? v + " " + u : v;
    }

    _h(s) {
      return escapeHtml(s);
    }

    _esc(s) {
      return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }

    _imgUrl(s) {
      return sanitizeUrl(s);
    }

    _collect(hass) {
      var c = this.config;
      var out = [];
      if (!hass || !hass.states) return out;
      var strip = function (o) {
        return o.indexOf(c.prefix) === 0 ? o.slice(c.prefix.length) : o;
      };
      var reg = hass.entities;
      if (reg) {
        for (var id in reg) {
          if (!Object.prototype.hasOwnProperty.call(reg, id)) continue;
          if (!reg[id] || reg[id].platform !== c.integration) continue;
          var s = hass.states[id];
          if (s) {
            var dot = id.indexOf(".");
            out.push({ id: id, domain: dot >= 0 ? id.slice(0, dot) : "", key: strip(id.slice(dot + 1)), s: s });
          }
        }
      }
      if (!out.length) {
        for (var sid in hass.states) {
          if (!Object.prototype.hasOwnProperty.call(hass.states, sid)) continue;
          var sdot = sid.indexOf(".");
          if (sdot < 0) continue;
          var obj = sid.slice(sdot + 1);
          if (obj.indexOf(c.prefix) === 0) {
            out.push({ id: sid, domain: sid.slice(0, sdot), key: strip(obj), s: hass.states[sid] });
          }
        }
      }
      return out;
    }

    _find(items) {
      for (var i = 1; i < arguments.length; i += 1) {
        var k = arguments[i];
        for (var j = 0; j < items.length; j += 1) {
          if (items[j].key === k) return items[j];
        }
      }
      return null;
    }

    _findDomain(items, domain) {
      for (var i = 2; i < arguments.length; i += 1) {
        var k = arguments[i];
        for (var j = 0; j < items.length; j += 1) {
          if (items[j].domain === domain && items[j].key === k) return items[j];
        }
      }
      return null;
    }

    _deviceId(hass, items) {
      var reg = hass && hass.entities;
      if (!reg) return null;
      for (var i = 0; i < items.length; i += 1) {
        var entry = reg[items[i].id];
        if (entry && entry.device_id) return entry.device_id;
      }
      return null;
    }

    _moreInfo(id) {
      if (!id) return;
      this.dispatchEvent(new CustomEvent("hass-more-info", {
        bubbles: true,
        composed: true,
        detail: { entityId: id },
      }));
    }

    _navigate(path) {
      if (typeof history !== "undefined" && typeof history.pushState === "function") {
        history.pushState(null, "", path);
      }
      this.dispatchEvent(new Event("location-changed", { bubbles: true, composed: true }));
    }

    _ensureShellListeners() {
      if (this._listenersBound || !this.shadowRoot) return;
      this.shadowRoot.addEventListener("click", this._onClick);
      this.shadowRoot.addEventListener("change", this._onChange);
      this.shadowRoot.addEventListener("keydown", this._onKeyDown);
      this._listenersBound = true;
    }

    _handleClick(ev) {
      var target = ev.target;
      if (!target || !target.closest) return;

      var dismiss = target.closest("[data-dismiss-error]");
      if (dismiss) {
        this._errorMsg = null;
        if (this._hass) this._render(this._hass);
        return;
      }

      var tabEl = target.closest("[data-tab]");
      if (tabEl) {
        var nextTab = tabEl.getAttribute("data-tab");
        if (VALID_TABS.indexOf(nextTab) >= 0 && nextTab !== this._activeTab) {
          this._activeTab = nextTab;
          if (this._hass) this._render(this._hass);
        }
        return;
      }

      var dayChip = target.closest("[data-day-chip]");
      if (dayChip) {
        var slug = dayChip.getAttribute("data-day-chip");
        this._expandedDay = this._expandedDay === slug ? null : slug;
        if (this._hass) this._render(this._hass);
        return;
      }

      var actionEl = target.closest("[data-action-id]");
      if (actionEl) {
        ev.stopPropagation();
        this._triggerAction(actionEl.getAttribute("data-action-id"), actionEl);
        return;
      }

      if (target.closest("input, select, button")) return;

      var entEl = target.closest("[data-e]");
      if (entEl) {
        this._moreInfo(entEl.getAttribute("data-e"));
        return;
      }

      var devEl = target.closest("[data-device]");
      if (devEl && devEl.getAttribute("data-device")) {
        this._navigate("/config/devices/device/" + devEl.getAttribute("data-device"));
      }
    }

    _handleKeyDown(ev) {
      if (ev.key !== "Enter" && ev.key !== " ") return;
      var target = ev.target;
      if (!target || !target.closest) return;
      if (target.tagName === "BUTTON" || target.tagName === "INPUT" || target.tagName === "SELECT") return;
      var actionable = target.closest("[data-e], [data-device]");
      if (!actionable) return;
      ev.preventDefault();
      if (actionable.hasAttribute("data-e")) {
        this._moreInfo(actionable.getAttribute("data-e"));
      } else if (actionable.getAttribute("data-device")) {
        this._navigate("/config/devices/device/" + actionable.getAttribute("data-device"));
      }
    }

    _handleChange(ev) {
      var target = ev.target;
      if (!target || !target.getAttribute) return;
      var entId = target.getAttribute("data-entity-input");
      if (!entId || !this._hass) return;
      var domain = entId.slice(0, entId.indexOf("."));
      var rawVal = String(target.value || "").trim();
      if (!rawVal) return;

      if (domain === "time") {
        var formatted = rawVal.length === 5 ? rawVal + ":00" : rawVal;
        this._callService("time", "set_value", { entity_id: entId, time: formatted }, "input:" + entId);
      } else if (domain === "select") {
        this._callService("select", "select_option", { entity_id: entId, option: rawVal }, "input:" + entId);
      }
    }

    _clearConfirm() {
      if (this._confirmTimer) {
        clearTimeout(this._confirmTimer);
        this._confirmTimer = null;
      }
      this._confirmState = null;
    }

    _triggerAction(actionId, actionEl) {
      var lookupKey = actionId;
      if (actionEl && actionEl.hasAttribute && actionEl.hasAttribute("data-value")) {
        lookupKey = actionId + "_" + actionEl.getAttribute("data-value");
      }
      var spec = this._latestActions && (this._latestActions[lookupKey] || this._latestActions[actionId]);
      if (!spec || !this._hass) return;

      var confirmKey = spec.confirmKey || actionId;
      if (spec.sensitive) {
        if (this._confirmState && this._confirmState.key === confirmKey) {
          this._clearConfirm();
          this._callService(spec.domain, spec.service, spec.data, confirmKey);
          return;
        }
        this._clearConfirm();
        var self = this;
        this._confirmState = {
          key: confirmKey,
          expiresAt: Date.now() + CONFIRM_MS,
        };
        this._confirmTimer = setTimeout(function () {
          self._confirmTimer = null;
          self._confirmState = null;
          if (self._hass) self._render(self._hass);
        }, CONFIRM_MS);
        this._render(this._hass);
        return;
      }

      this._callService(spec.domain, spec.service, spec.data, confirmKey);
    }

    _callService(domain, service, data, pendingKey) {
      if (!this._hass || typeof this._hass.callService !== "function") return;
      var self = this;
      var lang = getLang(this._hass);
      var t = getTexts(lang);
      this._errorMsg = null;
      this._pendingKeys.add(pendingKey);
      this._render(this._hass);

      try {
        Promise.resolve(this._hass.callService(domain, service, data)).then(
          function () {
            self._pendingKeys.delete(pendingKey);
            if (self._hass) self._render(self._hass);
          },
          function (err) {
            self._pendingKeys.delete(pendingKey);
            self._errorMsg = (err && err.message) ? String(err.message) : t.commandFailed;
            if (self._hass) self._render(self._hass);
          }
        );
      } catch (syncErr) {
        this._pendingKeys.delete(pendingKey);
        this._errorMsg = (syncErr && syncErr.message) ? String(syncErr.message) : t.commandFailed;
        this._render(this._hass);
      }
    }

    set hass(hass) {
      this._hass = hass;
      this._ensureShellListeners();
      try {
        this._render(hass);
      } catch (e) {
        if (this.shadowRoot) {
          this.shadowRoot.innerHTML =
            "<style>" + buildStyles() + "</style>" +
            `<ha-card><div class="error-banner" role="alert">Lepas card error: ${this._h(e && e.message ? e.message : e)}</div></ha-card>`;
          this._lastStructKey = "";
        }
      }
    }

    _isOn(ent) {
      return Boolean(ent && ent.s && ent.s.state === "on");
    }

    _render(hass) {
      if (!this.shadowRoot) return;
      var cfg = this.config;
      var lang = getLang(hass);
      var t = getTexts(lang);
      var items = this._collect(hass);
      var self = this;

      var nameHolder = items.find(function (r) { return r.s && r.s.attributes && r.s.attributes.friendly_name; });
      var nameSrc = nameHolder ? nameHolder.s.attributes.friendly_name : null;
      var device = nameSrc ? nameSrc.split(" ").slice(0, 2).join(" ") : "Lepas";
      var deviceRe = new RegExp("^" + this._esc(device) + "\\s*", "i");
      var title = cfg.title || device;
      var deviceId = this._deviceId(hass, items);

      // Core entities (domain-disambiguated)
      var conn = this._findDomain(items, "binary_sensor", "connection");
      var atHome = this._findDomain(items, "binary_sensor", "at_home");
      var awake = this._findDomain(items, "binary_sensor", "car_awake");
      var bat = this._findDomain(items, "sensor", "battery") || items.find(function (r) {
        return r.domain === "sensor" && r.s && r.s.attributes &&
          r.s.attributes.device_class === "battery" && r.s.attributes.unit_of_measurement === "%";
      });
      var evRange = this._findDomain(items, "sensor", "electric_range");
      var wltpRange = this._findDomain(items, "sensor", "wltp_range");
      var totalRange = this._findDomain(items, "sensor", "total_range");
      var fuelRange = this._findDomain(items, "sensor", "fuel_range", "petrol_range_miles", "fuel_remaining");
      var chgPower = this._findDomain(items, "sensor", "charging_power");
      var chgStatus = this._findDomain(items, "sensor", "charging_status");
      var remTime = this._findDomain(items, "sensor", "remaining_charge_time");
      var chgSwitch = this._findDomain(items, "switch", "charging");
      var plug = this._findDomain(items, "binary_sensor", "charging_cable");
      var odo = this._findDomain(items, "sensor", "odometer");
      var lock = this._findDomain(items, "lock", "lock");
      var climate = this._findDomain(items, "climate", "climate");
      var trunk = this._findDomain(items, "cover", "trunk");
      var windowsCov = this._findDomain(items, "cover", "windows");
      var sunroofCov = this._findDomain(items, "cover", "sunroof");
      var cmdResult = this._findDomain(items, "sensor", "command_result");
      var carUpdated = this._findDomain(items, "sensor", "car_data_updated", "last_seen");
      var flashBtn = this._findDomain(items, "button", "find_car_flash_lights");
      var wakeBtn = this._findDomain(items, "button", "wake_car");
      var refreshLocBtn = this._findDomain(items, "button", "refresh_location");
      var refreshFullBtn = this._findDomain(items, "button", "refresh_full_status");
      var locateBtn = this._findDomain(items, "button", "locate_car_gps");
      var tracker = this._findDomain(items, "device_tracker", "location");

      // Climate entities
      var cliDur = this._findDomain(items, "number", "climate_duration");
      var setTempL = this._findDomain(items, "sensor", "set_temperature_left");
      var setTempR = this._findDomain(items, "sensor", "set_temperature_right");
      var airPurif = this._findDomain(items, "binary_sensor", "air_purification");
      var coolSwitch = this._findDomain(items, "switch", "cool_everything") || this._findDomain(items, "button", "cool_everything");
      var heatSwitch = this._findDomain(items, "switch", "heat_everything") || this._findDomain(items, "button", "heat_everything");
      var defrostEntities = [
        { key: "windshield_defrost", ent: this._findDomain(items, "switch", "windshield_defrost"), label: t.windshieldDefrost },
        { key: "windshield_defog", ent: this._findDomain(items, "switch", "windshield_defog"), label: t.windshieldDefog },
        { key: "rear_window_heating", ent: this._findDomain(items, "switch", "rear_window_heating"), label: t.rearDefrost },
        { key: "steering_wheel_heating", ent: this._findDomain(items, "switch", "steering_wheel_heating"), label: t.steeringHeat },
      ].filter(function (d) { return Boolean(d.ent); });

      var seatDefs = [
        { slug: "driver", label: t.driver, heat: this._findDomain(items, "switch", "driver_seat_heating"), vent: this._findDomain(items, "switch", "driver_seat_ventilation") },
        { slug: "passenger", label: t.passenger, heat: this._findDomain(items, "switch", "passenger_seat_heating"), vent: this._findDomain(items, "switch", "passenger_seat_ventilation") },
        { slug: "rear_left", label: t.rearLeft, heat: this._findDomain(items, "switch", "rear_left_seat_heating"), vent: this._findDomain(items, "switch", "rear_left_seat_ventilation") },
        { slug: "rear_right", label: t.rearRight, heat: this._findDomain(items, "switch", "rear_right_seat_heating"), vent: this._findDomain(items, "switch", "rear_right_seat_ventilation") },
      ].filter(function (s) { return Boolean(s.heat || s.vent); });
      var rearCenterHeat = this._findDomain(items, "sensor", "rear_center_seat_heating");
      var rearCenterVent = this._findDomain(items, "sensor", "rear_center_seat_ventilation");

      // Charging & departure entities
      var hvVolt = this._findDomain(items, "sensor", "hv_battery_voltage");
      var hvCurr = this._findDomain(items, "sensor", "hv_battery_current");
      var homeEnergy = this._findDomain(items, "sensor", "home_charging_energy");
      var awayEnergy = this._findDomain(items, "sensor", "away_charging_energy");
      var fastPort = this._findDomain(items, "sensor", "fast_charging_port");
      var schedSwitch = this._findDomain(items, "switch", "scheduled_charging");
      var schedWindow = this._findDomain(items, "sensor", "scheduled_charging_window");
      var chgStartTime = this._findDomain(items, "time", "charge_start_time");
      var chgDur = this._findDomain(items, "number", "charge_duration");
      var chgDays = this._findDomain(items, "select", "charge_days");
      var applySchedBtn = this._findDomain(items, "button", "apply_charging_schedule");

      var nextDep = this._findDomain(items, "sensor", "next_departure");
      var quickDep = this._findDomain(items, "switch", "quick_departure");
      var quickDepTime = this._findDomain(items, "time", "quick_departure_time");
      var syncCharge = this._findDomain(items, "switch", "sync_charge_to_departure");
      var depCliMode = this._findDomain(items, "select", "departure_climate_mode");
      var weekDays = DAY_SLUGS.map(function (slug, idx) {
        return {
          slug: slug,
          letter: t.weekdays[idx],
          name: t.dayNames[slug],
          sw: self._findDomain(items, "switch", "departure_" + slug + "_enabled"),
          tm: self._findDomain(items, "time", "departure_" + slug + "_time"),
        };
      });

      // Security & blueprint entities
      var doorFL = this._findDomain(items, "binary_sensor", "front_left_door");
      var doorFR = this._findDomain(items, "binary_sensor", "front_right_door");
      var doorRL = this._findDomain(items, "binary_sensor", "rear_left_door");
      var doorRR = this._findDomain(items, "binary_sensor", "rear_right_door");
      var hood = this._findDomain(items, "binary_sensor", "hood");
      var tailMoving = this._findDomain(items, "binary_sensor", "tailgate_moving");
      var winFL = this._findDomain(items, "binary_sensor", "front_left_window");
      var winFR = this._findDomain(items, "binary_sensor", "front_right_window");
      var winRL = this._findDomain(items, "binary_sensor", "rear_left_window");
      var winRR = this._findDomain(items, "binary_sensor", "rear_right_window");
      var sunroofMove = this._findDomain(items, "sensor", "sunroof_movement_state");
      var sunroofBlind = this._findDomain(items, "binary_sensor", "sunroof_blind");
      var ventWinBtn = this._findDomain(items, "button", "vent_windows");
      var ventSunBtn = this._findDomain(items, "button", "vent_sunroof");
      var alarmSw = this._findDomain(items, "switch", "alarm");
      var remoteStartBtn = this._findDomain(items, "button", "remote_start");

      var tpmsCorners = [
        { pos: "front_left", label: "FL", p: this._findDomain(items, "sensor", "tire_pressure_front_left"), temp: this._findDomain(items, "sensor", "tire_temperature_front_left"), w: this._findDomain(items, "binary_sensor", "tire_warning_front_left") },
        { pos: "front_right", label: "FR", p: this._findDomain(items, "sensor", "tire_pressure_front_right"), temp: this._findDomain(items, "sensor", "tire_temperature_front_right"), w: this._findDomain(items, "binary_sensor", "tire_warning_front_right") },
        { pos: "rear_left", label: "RL", p: this._findDomain(items, "sensor", "tire_pressure_rear_left"), temp: this._findDomain(items, "sensor", "tire_temperature_rear_left"), w: this._findDomain(items, "binary_sensor", "tire_warning_rear_left") },
        { pos: "rear_right", label: "RR", p: this._findDomain(items, "sensor", "tire_pressure_rear_right"), temp: this._findDomain(items, "sensor", "tire_temperature_rear_right"), w: this._findDomain(items, "binary_sensor", "tire_warning_rear_right") },
      ];

      // Warnings
      var warns = [];
      items.filter(function (r) {
        return r.domain === "binary_sensor" && /tire.*warning|tyre.*warning/.test(r.key) && r.s && r.s.state === "on";
      }).forEach(function (r) {
        var nm = (r.s.attributes && r.s.attributes.friendly_name ? r.s.attributes.friendly_name : r.key)
          .replace(deviceRe, "").replace(/warning/i, "").trim();
        warns.push({ id: r.id, text: nm || r.key, amber: false });
      });
      var lowBat = this._findDomain(items, "binary_sensor", "low_battery");
      if (this._isOn(lowBat)) warns.push({ id: lowBat.id, text: t.batteryLow, amber: false });
      var lowFuel = this._findDomain(items, "binary_sensor", "low_fuel_warning");
      if (this._isOn(lowFuel)) warns.push({ id: lowFuel.id, text: t.fuelLow, amber: true });
      var chgNeed = this._findDomain(items, "binary_sensor", "charge_needed_warning");
      if (this._isOn(chgNeed)) warns.push({ id: chgNeed.id, text: t.chargeNeeded, amber: true });
      if (conn && conn.s && conn.s.state === "off") warns.push({ id: conn.id, text: t.offline, amber: false });

      var lockIsLocked = lock && lock.s && lock.s.state === "locked";
      var anyDoorOpen = this._isOn(doorFL) || this._isOn(doorFR) || this._isOn(doorRL) || this._isOn(doorRR) || this._isOn(hood);
      var anyWinOpen = this._isOn(winFL) || this._isOn(winFR) || this._isOn(winRL) || this._isOn(winRR) || (windowsCov && windowsCov.s && windowsCov.s.state === "open");
      if (lockIsLocked && (anyDoorOpen || anyWinOpen)) {
        warns.push({ id: lock.id, text: t.ajarLocked, amber: true });
      }

      // Build action map for the current render
      var actions = Object.create(null);
      var regAction = function (actionId, domain, service, data, sensitive, confirmKey) {
        actions[actionId] = {
          domain: domain,
          service: service,
          data: data,
          sensitive: Boolean(sensitive),
          confirmKey: confirmKey || actionId,
        };
      };

      if (lock) {
        if (lockIsLocked) {
          regAction("unlock", "lock", "unlock", { entity_id: lock.id }, true, "unlock");
          regAction("quick_unlock", "lock", "unlock", { entity_id: lock.id }, true, "unlock");
        } else {
          regAction("lock_now", "lock", "lock", { entity_id: lock.id }, false, "lock_now");
          regAction("quick_lock_now", "lock", "lock", { entity_id: lock.id }, false, "lock_now");
        }
      }
      if (climate) {
        var cliOn = !this._dead(climate.s) && climate.s.state !== "off";
        var nextMode = cliOn ? "off" : "heat_cool";
        regAction("climate_toggle", "climate", "set_hvac_mode", { entity_id: climate.id, hvac_mode: nextMode }, false, "climate_toggle");
        regAction("climate_quick", "climate", "set_hvac_mode", { entity_id: climate.id, hvac_mode: nextMode }, false, "climate_toggle");
        var attrs = climate.s.attributes || {};
        var minT = typeof attrs.min_temp === "number" ? attrs.min_temp : 16;
        var maxT = typeof attrs.max_temp === "number" ? attrs.max_temp : 30;
        var stepT = typeof attrs.target_temperature_step === "number" ? attrs.target_temperature_step : 0.5;
        var curT = typeof attrs.temperature === "number" ? attrs.temperature : 21;
        var downT = Math.max(minT, Math.round((curT - stepT) * 10) / 10);
        var upT = Math.min(maxT, Math.round((curT + stepT) * 10) / 10);
        regAction("temp_down", "climate", "set_temperature", { entity_id: climate.id, temperature: downT }, false, "temp_step");
        regAction("temp_up", "climate", "set_temperature", { entity_id: climate.id, temperature: upT }, false, "temp_step");
      }
      if (cliDur) {
        var cdAttrs = cliDur.s.attributes || {};
        var cdMin = typeof cdAttrs.min === "number" ? cdAttrs.min : 5;
        var cdMax = typeof cdAttrs.max === "number" ? cdAttrs.max : 30;
        var cdVals = [5, 10, 15, 20, 30].filter(function (v) { return v >= cdMin && v <= cdMax; });
        if (!cdVals.length) cdVals = [cdMin, cdMax];
        cdVals.forEach(function (v) {
          regAction("climate_duration_" + v, "number", "set_value", { entity_id: cliDur.id, value: v }, false, "climate_duration");
        });
      }
      if (trunk) {
        var trunkClosed = trunk.s && trunk.s.state === "closed";
        if (trunkClosed) {
          regAction("trunk_open", "cover", "open_cover", { entity_id: trunk.id }, true, "trunk_open");
          regAction("quick_trunk_open", "cover", "open_cover", { entity_id: trunk.id }, true, "trunk_open");
        } else {
          regAction("trunk_close", "cover", "close_cover", { entity_id: trunk.id }, false, "trunk_close");
          regAction("quick_trunk_close", "cover", "close_cover", { entity_id: trunk.id }, false, "trunk_close");
        }
      }
      if (windowsCov) {
        if (windowsCov.s && windowsCov.s.state === "closed") {
          regAction("windows_open", "cover", "open_cover", { entity_id: windowsCov.id }, true, "windows_open");
        } else {
          regAction("windows_close", "cover", "close_cover", { entity_id: windowsCov.id }, false, "windows_close");
        }
      }
      if (sunroofCov) {
        if (sunroofCov.s && sunroofCov.s.state === "closed") {
          regAction("sunroof_open", "cover", "open_cover", { entity_id: sunroofCov.id }, true, "sunroof_open");
        } else {
          regAction("sunroof_close", "cover", "close_cover", { entity_id: sunroofCov.id }, false, "sunroof_close");
        }
      }
      if (ventWinBtn) regAction("vent_windows", "button", "press", { entity_id: ventWinBtn.id }, true, "vent_windows");
      if (ventSunBtn) regAction("vent_sunroof", "button", "press", { entity_id: ventSunBtn.id }, true, "vent_sunroof");
      if (alarmSw) {
        var alarmSvc = this._isOn(alarmSw) ? "turn_off" : "turn_on";
        regAction("alarm_toggle", "switch", alarmSvc, { entity_id: alarmSw.id }, true, "alarm_toggle");
      }
      if (remoteStartBtn) regAction("remote_start", "button", "press", { entity_id: remoteStartBtn.id }, true, "remote_start");
      if (flashBtn) {
        regAction("flash_lights", "button", "press", { entity_id: flashBtn.id }, false, "flash_lights");
        regAction("sec_flash_lights", "button", "press", { entity_id: flashBtn.id }, false, "flash_lights");
      }
      if (wakeBtn) regAction("wake_car", "button", "press", { entity_id: wakeBtn.id }, false, "wake_car");
      if (refreshLocBtn) regAction("refresh_location", "button", "press", { entity_id: refreshLocBtn.id }, false, "refresh_location");
      if (refreshFullBtn) regAction("refresh_full", "button", "press", { entity_id: refreshFullBtn.id }, false, "refresh_full");
      if (locateBtn) regAction("locate_gps", "button", "press", { entity_id: locateBtn.id }, false, "locate_gps");
      if (applySchedBtn) regAction("apply_charging_schedule", "button", "press", { entity_id: applySchedBtn.id }, false, "apply_charging_schedule");

      var regSwitchToggle = function (actionId, ent) {
        if (!ent) return;
        if (ent.domain === "button") {
          regAction(actionId, "button", "press", { entity_id: ent.id }, false, actionId);
        } else {
          regAction(actionId, "switch", self._isOn(ent) ? "turn_off" : "turn_on", { entity_id: ent.id }, false, actionId);
        }
      };
      regSwitchToggle("cool_everything", coolSwitch);
      regSwitchToggle("heat_everything", heatSwitch);
      defrostEntities.forEach(function (d) { regSwitchToggle(d.key, d.ent); });
      seatDefs.forEach(function (sd) {
        if (sd.heat) regSwitchToggle("seat_" + sd.slug + "_heat", sd.heat);
        if (sd.vent) regSwitchToggle("seat_" + sd.slug + "_vent", sd.vent);
      });
      regSwitchToggle("charging_toggle", chgSwitch);
      regSwitchToggle("scheduled_charging_toggle", schedSwitch);
      regSwitchToggle("quick_departure_toggle", quickDep);
      regSwitchToggle("sync_charge_toggle", syncCharge);

      if (chgDur) {
        var chAttrs = chgDur.s.attributes || {};
        var chMin = typeof chAttrs.min === "number" ? chAttrs.min : 1;
        var chMax = typeof chAttrs.max === "number" ? chAttrs.max : 12;
        var chStep = typeof chAttrs.step === "number" ? chAttrs.step : 1;
        var chCur = this._num(chgDur.s);
        if (chCur === null) chCur = 6;
        regAction("charge_dur_down", "number", "set_value", { entity_id: chgDur.id, value: Math.max(chMin, chCur - chStep) }, false, "charge_dur");
        regAction("charge_dur_up", "number", "set_value", { entity_id: chgDur.id, value: Math.min(chMax, chCur + chStep) }, false, "charge_dur");
      }
      weekDays.forEach(function (wd) {
        if (wd.sw) regSwitchToggle("day_toggle_" + wd.slug, wd.sw);
      });

      this._latestActions = actions;

      // Structural signature: rebuild DOM only when structure/entities/warnings/expandedDay/lang change
      var entityIdsSig = items.map(function (r) { return r.id; }).sort().join(",");
      var extraSig = Array.isArray(cfg.entities)
        ? cfg.entities.map(function (e) { return typeof e === "string" ? e : (e && e.entity ? e.entity : ""); }).join(",")
        : "";
      var warnSig = warns.map(function (w) { return w.id + ":" + w.text; }).join("|");
      var structKey = [
        lang,
        cfg.layout,
        cfg.show_all ? "1" : "0",
        extraSig,
        this._expandedDay || "",
        warnSig,
        entityIdsSig,
      ].join("#");

      if (structKey !== this._lastStructKey) {
        var activeEl = this.shadowRoot.activeElement;
        var activeUid = activeEl && activeEl.getAttribute ? activeEl.getAttribute("data-uid") : null;
        var activeVal = (activeEl && activeEl.tagName === "INPUT") ? activeEl.value : null;

        this.shadowRoot.innerHTML = this._buildSkeletonHtml({
          lang: lang,
          t: t,
          cfg: cfg,
          items: items,
          deviceId: deviceId,
          deviceRe: deviceRe,
          warns: warns,
          bat: bat,
          evRange: evRange,
          totalRange: totalRange,
          fuelRange: fuelRange,
          chgPower: chgPower,
          chgStatus: chgStatus,
          chgSwitch: chgSwitch,
          plug: plug,
          odo: odo,
          lock: lock,
          climate: climate,
          trunk: trunk,
          flashBtn: flashBtn,
          wakeBtn: wakeBtn,
          refreshLocBtn: refreshLocBtn,
          refreshFullBtn: refreshFullBtn,
          carUpdated: carUpdated,
          cmdResult: cmdResult,
          cliDur: cliDur,
          setTempL: setTempL,
          setTempR: setTempR,
          airPurif: airPurif,
          coolSwitch: coolSwitch,
          heatSwitch: heatSwitch,
          defrostEntities: defrostEntities,
          seatDefs: seatDefs,
          rearCenterHeat: rearCenterHeat,
          rearCenterVent: rearCenterVent,
          remTime: remTime,
          hvVolt: hvVolt,
          hvCurr: hvCurr,
          homeEnergy: homeEnergy,
          awayEnergy: awayEnergy,
          fastPort: fastPort,
          schedSwitch: schedSwitch,
          schedWindow: schedWindow,
          chgStartTime: chgStartTime,
          chgDur: chgDur,
          chgDays: chgDays,
          applySchedBtn: applySchedBtn,
          nextDep: nextDep,
          quickDep: quickDep,
          quickDepTime: quickDepTime,
          syncCharge: syncCharge,
          depCliMode: depCliMode,
          weekDays: weekDays,
          tpmsCorners: tpmsCorners,
          windowsCov: windowsCov,
          sunroofCov: sunroofCov,
          ventWinBtn: ventWinBtn,
          ventSunBtn: ventSunBtn,
          alarmSw: alarmSw,
          remoteStartBtn: remoteStartBtn,
          locateBtn: locateBtn,
          tracker: tracker,
        });
        this._lastStructKey = structKey;

        if (activeUid) {
          var restored = this.shadowRoot.querySelector('[data-uid="' + activeUid + '"]');
          if (restored) {
            if (typeof restored.focus === "function") restored.focus();
            if (activeVal !== null && restored.tagName === "INPUT") restored.value = activeVal;
          }
        }
      }

      // Always patch live values, classes, SVG offsets, confirm states, and non-focused inputs
      this._applyBindings(hass, {
        lang: lang,
        t: t,
        cfg: cfg,
        items: items,
        title: title,
        deviceRe: deviceRe,
        conn: conn,
        atHome: atHome,
        awake: awake,
        bat: bat,
        evRange: evRange,
        wltpRange: wltpRange,
        totalRange: totalRange,
        fuelRange: fuelRange,
        chgPower: chgPower,
        chgStatus: chgStatus,
        remTime: remTime,
        chgSwitch: chgSwitch,
        plug: plug,
        odo: odo,
        lock: lock,
        climate: climate,
        trunk: trunk,
        windowsCov: windowsCov,
        sunroofCov: sunroofCov,
        carUpdated: carUpdated,
        cmdResult: cmdResult,
        cliDur: cliDur,
        setTempL: setTempL,
        setTempR: setTempR,
        airPurif: airPurif,
        coolSwitch: coolSwitch,
        heatSwitch: heatSwitch,
        defrostEntities: defrostEntities,
        seatDefs: seatDefs,
        rearCenterHeat: rearCenterHeat,
        rearCenterVent: rearCenterVent,
        hvVolt: hvVolt,
        hvCurr: hvCurr,
        homeEnergy: homeEnergy,
        awayEnergy: awayEnergy,
        fastPort: fastPort,
        schedSwitch: schedSwitch,
        schedWindow: schedWindow,
        chgStartTime: chgStartTime,
        chgDur: chgDur,
        chgDays: chgDays,
        nextDep: nextDep,
        quickDep: quickDep,
        quickDepTime: quickDepTime,
        syncCharge: syncCharge,
        depCliMode: depCliMode,
        weekDays: weekDays,
        doorFL: doorFL,
        doorFR: doorFR,
        doorRL: doorRL,
        doorRR: doorRR,
        hood: hood,
        tailMoving: tailMoving,
        winFL: winFL,
        winFR: winFR,
        winRL: winRL,
        winRR: winRR,
        sunroofMove: sunroofMove,
        sunroofBlind: sunroofBlind,
        alarmSw: alarmSw,
        tpmsCorners: tpmsCorners,
        tracker: tracker,
      });
    }

    _buildSkeletonHtml(ctx) {
      var t = ctx.t;
      var cfg = ctx.cfg;
      var self = this;

      var warnsHtml = ctx.warns.length
        ? '<div class="warns-row">' + ctx.warns.map(function (w) {
            return '<div class="warn-chip' + (w.amber ? " is-amber" : "") + '" role="button" tabindex="0" data-e="' +
              self._h(w.id) + '">' + self._h(w.text) + "</div>";
          }).join("") + "</div>"
        : "";

      var tabsHtml = '<div class="tabs-bar" role="tablist">' + VALID_TABS.map(function (tb) {
        return '<button type="button" class="tab-btn" role="tab" data-tab="' + tb + '" data-uid="tab:' + tb + '">' +
          self._h(t.tabs[tb]) + "</button>";
      }).join("") + "</div>";

      // Hero region
      var socRingHtml = ctx.bat ? (
        '<div class="soc-btn" role="button" tabindex="0" data-e="' + self._h(ctx.bat.id) + '">' +
          '<svg viewBox="0 0 52 52" aria-hidden="true">' +
            '<circle class="soc-ring-bg" cx="26" cy="26" r="21"/>' +
            '<circle class="soc-ring-fg" data-soc-ring cx="26" cy="26" r="21" stroke-dasharray="131.95" stroke-dashoffset="131.95"/>' +
          "</svg>" +
          '<span class="soc-val num" data-bind="socText">—</span>' +
          '<progress class="sr-only" data-bind="socProgress" max="100" value="0"></progress>' +
        "</div>"
      ) : "";

      var heroHtml =
        '<div class="hero-region">' +
          '<div class="hero-card">' +
            '<img class="hero-img" data-bind="heroImg" alt="" decoding="async" fetchpriority="high">' +
            '<div class="hero-scrim"></div>' +
            '<div class="hero-inner">' +
              '<div class="hero-top">' +
                '<div class="status-pill">' +
                  '<span class="status-dot" data-bind="connDot"></span>' +
                  '<span data-bind="statusText"></span>' +
                "</div>" +
                socRingHtml +
              "</div>" +
              '<div class="hero-bottom" ' + (ctx.deviceId ? 'role="button" tabindex="0" data-device="' + self._h(ctx.deviceId) + '"' : "") + ">" +
                '<div class="hero-title" data-bind="heroTitle"></div>' +
                '<div class="hero-sub" data-bind="heroSub"></div>' +
              "</div>" +
            "</div>" +
          "</div>" +
          warnsHtml +
          '<div class="error-banner hidden" role="alert" data-bind="errorBanner">' +
            '<span data-bind="errorText"></span>' +
            '<button type="button" class="error-dismiss" data-dismiss-error aria-label="Dismiss">×</button>' +
          "</div>" +
        "</div>";

      // Panel 1: Overview
      var quickDockBtns = [];
      if (ctx.lock) quickDockBtns.push('<button type="button" class="ctrl-btn" data-bind="quickLockBtn" data-action-id="quick_unlock"></button>');
      if (ctx.climate) quickDockBtns.push('<button type="button" class="ctrl-btn" data-bind="quickClimateBtn" data-action-id="climate_quick"></button>');
      if (ctx.trunk) quickDockBtns.push('<button type="button" class="ctrl-btn" data-bind="quickTrunkBtn" data-action-id="quick_trunk_open"></button>');
      if (ctx.flashBtn) quickDockBtns.push('<button type="button" class="ctrl-btn" data-action-id="flash_lights" data-confirm-key="flash_lights">' + self._h(t.flashLights) + "</button>");
      if (ctx.wakeBtn) quickDockBtns.push('<button type="button" class="ctrl-btn" data-action-id="wake_car" data-confirm-key="wake_car">' + self._h(t.wakeCar) + "</button>");

      var extraRowsHtml = "";
      if (Array.isArray(cfg.entities) && cfg.entities.length) {
        extraRowsHtml = '<div class="surface"><div class="sec-hdr"><span>' + self._h(t.details) + "</span></div>" +
          cfg.entities.map(function (e) {
            var eid = typeof e === "string" ? e : (e && e.entity);
            if (!eid) return "";
            return '<div class="info-row" role="button" tabindex="0" data-e="' + self._h(eid) + '" data-extra-entity="' + self._h(eid) + '">' +
              '<span data-extra-name="' + self._h(eid) + '"></span><span class="info-val num" data-extra-val="' + self._h(eid) + '"></span></div>';
          }).join("") + "</div>";
      } else if (cfg.show_all) {
        var usedIds = new Set(
          [ctx.bat, ctx.evRange, ctx.totalRange, ctx.fuelRange, ctx.chgPower, ctx.chgStatus, ctx.chgSwitch, ctx.plug, ctx.odo]
            .filter(Boolean).map(function (r) { return r.id; })
        );
        var rest = ctx.items.filter(function (r) {
          return !usedIds.has(r.id) && !self._dead(r.s) && (!r.s.attributes || r.s.attributes.entity_category !== "diagnostic");
        }).sort(function (a, b) { return a.key.localeCompare(b.key); });
        if (rest.length) {
          extraRowsHtml = '<div class="surface"><div class="sec-hdr"><span>' + self._h(t.more) + "</span></div>" +
            rest.map(function (r) {
              return '<div class="info-row" role="button" tabindex="0" data-e="' + self._h(r.id) + '" data-extra-entity="' + self._h(r.id) + '">' +
                '<span data-extra-name="' + self._h(r.id) + '"></span><span class="info-val num" data-extra-val="' + self._h(r.id) + '"></span></div>';
            }).join("") + "</div>";
        }
      }

      var overviewHtml =
        '<section class="panel" data-panel="overview">' +
          '<div class="metrics-grid">' +
            '<div class="metric-card" data-bind="mEvCard">' +
              '<span class="metric-lbl">' + self._h(t.evRange) + "</span>" +
              '<span class="metric-val num" data-bind="mEvVal">—</span>' +
              '<div class="metric-bar hidden" data-bind="mEvBarWrap"><div class="metric-bar-fill" data-bind="mEvBar"></div></div>' +
            "</div>" +
            '<div class="metric-card" data-bind="mFuelCard">' +
              '<span class="metric-lbl" data-bind="mFuelLbl">' + self._h(t.totalRange) + "</span>" +
              '<span class="metric-val num" data-bind="mFuelVal">—</span>' +
            "</div>" +
            '<div class="metric-card" data-bind="mChgCard">' +
              '<span class="metric-lbl">' + self._h(t.chargingLbl) + "</span>" +
              '<span class="metric-val num" data-bind="mChgVal">—</span>' +
            "</div>" +
            '<div class="metric-card" data-bind="mOdoCard">' +
              '<span class="metric-lbl" data-bind="mOdoLbl">' + self._h(t.odometer) + "</span>" +
              '<span class="metric-val num" data-bind="mOdoVal">—</span>' +
            "</div>" +
          "</div>" +
          (quickDockBtns.length ? '<div class="surface"><div class="sec-hdr"><span>' + self._h(t.quickActions) + '</span></div><div class="btn-grid">' + quickDockBtns.join("") + "</div></div>" : "") +
          '<div class="surface">' +
            '<div class="footer-bar">' +
              '<span data-bind="freshnessText"></span>' +
              '<span class="badge hidden" data-bind="cmdResultBadge"></span>' +
            "</div>" +
            ((ctx.refreshLocBtn || ctx.refreshFullBtn)
              ? '<div class="btn-row">' +
                  (ctx.refreshLocBtn ? '<button type="button" class="ctrl-btn" data-action-id="refresh_location" data-confirm-key="refresh_location">' + self._h(t.refreshLoc) + "</button>" : "") +
                  (ctx.refreshFullBtn ? '<button type="button" class="ctrl-btn" data-action-id="refresh_full" data-confirm-key="refresh_full">' + self._h(t.refreshFull) + "</button>" : "") +
                "</div>"
              : "") +
          "</div>" +
          extraRowsHtml +
        "</section>";

      // Panel 2: Climate
      var durHtml = "";
      if (ctx.cliDur) {
        var cdAttrs = ctx.cliDur.s.attributes || {};
        var cdMin = typeof cdAttrs.min === "number" ? cdAttrs.min : 5;
        var cdMax = typeof cdAttrs.max === "number" ? cdAttrs.max : 30;
        var cdVals = [5, 10, 15, 20, 30].filter(function (v) { return v >= cdMin && v <= cdMax; });
        if (!cdVals.length) cdVals = [cdMin, cdMax];
        durHtml = '<div class="sec-hdr"><span>' + self._h(t.duration) + '</span><span class="num" data-bind="cliDurText"></span></div>' +
          '<div class="chip-row">' + cdVals.map(function (v) {
            return '<button type="button" class="chip-btn num" data-action-id="climate_duration" data-value="' + v + '">' + v + "m</button>";
          }).join("") + "</div>";
      }

      var climateHubHtml = ctx.climate ? (
        '<div class="surface">' +
          '<div class="sec-hdr"><span>' + self._h(t.climateHub) + '</span><span class="badge hidden" data-bind="airPurifBadge">' + self._h(t.airPurification) + "</span></div>" +
          '<div class="btn-row">' +
            '<button type="button" class="ctrl-btn" style="flex:1" data-action-id="climate_toggle" data-confirm-key="climate_toggle" data-bind="climateToggleBtn"></button>' +
          "</div>" +
          '<div class="stepper">' +
            '<button type="button" class="ctrl-btn" data-action-id="temp_down" aria-label="-">−</button>' +
            '<span class="step-val num" data-bind="targetTempText">—</span>' +
            '<button type="button" class="ctrl-btn" data-action-id="temp_up" aria-label="+">+</button>' +
          "</div>" +
          ((ctx.setTempL || ctx.setTempR)
            ? '<div class="footer-bar">' +
                (ctx.setTempL ? '<span class="num" data-bind="setTempLText"></span>' : "") +
                (ctx.setTempR ? '<span class="num" data-bind="setTempRText"></span>' : "") +
              "</div>"
            : "") +
          durHtml +
        "</div>"
      ) : "";

      var macrosHtml = (ctx.coolSwitch || ctx.heatSwitch) ? (
        '<div class="surface"><div class="sec-hdr"><span>' + self._h(t.macros) + '</span></div><div class="btn-grid">' +
          (ctx.coolSwitch ? '<button type="button" class="ctrl-btn" data-action-id="cool_everything" data-confirm-key="cool_everything" data-bind="coolAllBtn">' + self._h(t.coolAll) + "</button>" : "") +
          (ctx.heatSwitch ? '<button type="button" class="ctrl-btn" data-action-id="heat_everything" data-confirm-key="heat_everything" data-bind="heatAllBtn">' + self._h(t.heatAll) + "</button>" : "") +
        "</div></div>"
      ) : "";

      var defrostHtml = ctx.defrostEntities.length ? (
        '<div class="surface"><div class="sec-hdr"><span>' + self._h(t.defrosts) + '</span></div><div class="btn-grid">' +
          ctx.defrostEntities.map(function (d) {
            return '<button type="button" class="ctrl-btn" data-action-id="' + d.key + '" data-confirm-key="' + d.key + '" data-defrost-btn="' + d.key + '">' +
              self._h(d.label) + "</button>";
          }).join("") +
        "</div></div>"
      ) : "";

      var rearCenterHtml = (ctx.rearCenterHeat || ctx.rearCenterVent) ? (
        '<div class="seat-readonly" data-seat-readonly="rear_center">' +
          "<span>" + self._h(t.rearCenter) + "</span>" +
          '<span class="num" data-bind="rearCenterText"></span>' +
        "</div>"
      ) : "";

      var seatsHtml = (ctx.seatDefs.length || rearCenterHtml) ? (
        '<div class="surface"><div class="sec-hdr"><span>' + self._h(t.seats) + '</span></div>' +
          '<div class="seat-grid">' +
            ctx.seatDefs.map(function (sd) {
              return '<div class="seat-card">' +
                '<div class="seat-name">' + self._h(sd.label) + "</div>" +
                '<div class="seat-btns">' +
                  (sd.heat ? '<button type="button" class="ctrl-btn" data-action-id="seat_' + sd.slug + '_heat" data-seat-btn="' + sd.slug + '_heat">' + self._h(t.heat) + "</button>" : "") +
                  (sd.vent ? '<button type="button" class="ctrl-btn" data-action-id="seat_' + sd.slug + '_vent" data-seat-btn="' + sd.slug + '_vent">' + self._h(t.vent) + "</button>" : "") +
                "</div>" +
              "</div>";
            }).join("") +
          "</div>" +
          rearCenterHtml +
        "</div>"
      ) : "";

      var climateHtml = '<section class="panel" data-panel="climate">' + climateHubHtml + macrosHtml + defrostHtml + seatsHtml + "</section>";

      // Panel 3: Charging & Departures
      var liveChgHtml = (ctx.chgSwitch || ctx.plug || ctx.chgPower || ctx.remTime || ctx.hvVolt || ctx.hvCurr) ? (
        '<div class="surface">' +
          '<div class="sec-hdr"><span>' + self._h(t.liveCharging) + '</span><span class="badge" data-bind="cableBadge"></span></div>' +
          (ctx.chgSwitch ? '<button type="button" class="ctrl-btn" data-action-id="charging_toggle" data-confirm-key="charging_toggle" data-bind="chgToggleBtn"></button>' : "") +
          '<div class="chip-row" data-bind="chgStatsRow">' +
            (ctx.chgPower ? '<span class="badge num" data-bind="chgPowerBadge"></span>' : "") +
            (ctx.remTime ? '<span class="badge num" data-bind="remTimeBadge"></span>' : "") +
            (ctx.hvVolt ? '<span class="badge num" data-bind="hvVoltBadge"></span>' : "") +
            (ctx.hvCurr ? '<span class="badge num" data-bind="hvCurrBadge"></span>' : "") +
            (ctx.homeEnergy ? '<span class="badge num" data-bind="homeEnergyBadge"></span>' : "") +
            (ctx.awayEnergy ? '<span class="badge num" data-bind="awayEnergyBadge"></span>' : "") +
            (ctx.fastPort ? '<span class="badge" data-bind="fastPortBadge"></span>' : "") +
          "</div>" +
        "</div>"
      ) : "";

      var timelineHtml = ctx.schedWindow ? (
        '<div>' +
          '<div class="timeline-track" data-bind="timelineTrack"></div>' +
          '<div class="timeline-axis num"><span>00:00</span><span data-bind="schedWindowText"></span><span>24:00</span></div>' +
        "</div>"
      ) : "";

      var chgDaysOptsHtml = "";
      if (ctx.chgDays) {
        var opts = (ctx.chgDays.s && ctx.chgDays.s.attributes && Array.isArray(ctx.chgDays.s.attributes.options))
          ? ctx.chgDays.s.attributes.options
          : ["all_days", "weekdays", "weekend", "mon_wed_fri", "tue_thu_sat", "custom"];
        chgDaysOptsHtml = opts.map(function (o) {
          return '<option value="' + self._h(o) + '">' + self._h(o) + "</option>";
        }).join("");
      }

      var schedChgHtml = (ctx.schedSwitch || ctx.schedWindow || ctx.chgStartTime || ctx.chgDur || ctx.chgDays || ctx.applySchedBtn) ? (
        '<div class="surface">' +
          '<div class="sec-hdr"><span>' + self._h(t.scheduledCharging) + '</span><span class="badge hidden" data-bind="schedSyncBadge"></span></div>' +
          (ctx.schedSwitch ? '<button type="button" class="ctrl-btn" data-action-id="scheduled_charging_toggle" data-confirm-key="scheduled_charging_toggle" data-bind="schedToggleBtn"></button>' : "") +
          timelineHtml +
          (ctx.chgStartTime ? '<div class="field-row"><label class="field-lbl">' + self._h(t.startTime) + '</label><input type="time" class="ctrl-input num" data-entity-input="' + self._h(ctx.chgStartTime.id) + '" data-uid="input:' + self._h(ctx.chgStartTime.id) + '"></div>' : "") +
          (ctx.chgDur ? '<div class="field-row"><span class="field-lbl">' + self._h(t.chargeDuration) + '</span><div class="stepper" style="min-width:150px"><button type="button" class="ctrl-btn" data-action-id="charge_dur_down">−</button><span class="num" data-bind="chgDurText">—</span><button type="button" class="ctrl-btn" data-action-id="charge_dur_up">+</button></div></div>' : "") +
          (ctx.chgDays ? '<div class="field-row"><label class="field-lbl">' + self._h(t.chargeDays) + '</label><select class="ctrl-select" data-entity-input="' + self._h(ctx.chgDays.id) + '" data-uid="input:' + self._h(ctx.chgDays.id) + '">' + chgDaysOptsHtml + "</select></div>" : "") +
          '<span class="badge is-amber hidden" data-bind="fallback2131Badge">' + self._h(t.daysFallback2131) + "</span>" +
          (ctx.applySchedBtn ? '<button type="button" class="ctrl-btn is-primary" data-action-id="apply_charging_schedule" data-confirm-key="apply_charging_schedule">' + self._h(t.applySchedule) + "</button>" : "") +
        "</div>"
      ) : "";

      var depModeOptsHtml = "";
      if (ctx.depCliMode) {
        var dOpts = (ctx.depCliMode.s && ctx.depCliMode.s.attributes && Array.isArray(ctx.depCliMode.s.attributes.options))
          ? ctx.depCliMode.s.attributes.options : ["at_home", "anywhere", "off"];
        depModeOptsHtml = dOpts.map(function (o) {
          return '<option value="' + self._h(o) + '">' + self._h(o) + "</option>";
        }).join("");
      }

      var hasWeekDays = ctx.weekDays.some(function (w) { return Boolean(w.sw || w.tm); });
      var expandedDayObj = this._expandedDay
        ? ctx.weekDays.find(function (w) { return w.slug === self._expandedDay; })
        : null;
      var dayEditorHtml = (expandedDayObj && (expandedDayObj.sw || expandedDayObj.tm)) ? (
        '<div class="day-editor" data-day-editor="' + expandedDayObj.slug + '">' +
          '<div class="sec-hdr"><span>' + self._h(expandedDayObj.name) + "</span></div>" +
          (expandedDayObj.sw ? '<button type="button" class="ctrl-btn" data-action-id="day_toggle_' + expandedDayObj.slug + '" data-bind="expandedDayToggle"></button>' : "") +
          (expandedDayObj.tm ? '<div class="field-row"><label class="field-lbl">' + self._h(t.timeLbl) + '</label><input type="time" class="ctrl-input num" data-entity-input="' + self._h(expandedDayObj.tm.id) + '" data-uid="input:' + self._h(expandedDayObj.tm.id) + '"></div>' : "") +
        "</div>"
      ) : "";

      var depHtml = (ctx.nextDep || ctx.quickDep || hasWeekDays) ? (
        '<div class="surface">' +
          '<div class="sec-hdr"><span>' + self._h(t.departures) + '</span><span class="badge hidden num" data-bind="depChargeHint"></span></div>' +
          (ctx.nextDep ? '<div class="info-row" role="button" tabindex="0" data-e="' + self._h(ctx.nextDep.id) + '"><span>' + self._h(t.nextDeparture) + '</span><span class="info-val num" data-bind="nextDepText"></span></div>' : "") +
          ((ctx.quickDep || ctx.quickDepTime)
            ? '<div class="btn-row">' +
                (ctx.quickDep ? '<button type="button" class="ctrl-btn" style="flex:1" data-action-id="quick_departure_toggle" data-confirm-key="quick_departure_toggle" data-bind="quickDepBtn"></button>' : "") +
                (ctx.quickDepTime ? '<input type="time" class="ctrl-input num" data-entity-input="' + self._h(ctx.quickDepTime.id) + '" data-uid="input:' + self._h(ctx.quickDepTime.id) + '">' : "") +
              "</div>"
            : "") +
          (ctx.syncCharge ? '<button type="button" class="ctrl-btn" data-action-id="sync_charge_toggle" data-confirm-key="sync_charge_toggle" data-bind="syncChargeBtn"></button>' : "") +
          (ctx.depCliMode ? '<div class="field-row"><label class="field-lbl">' + self._h(t.depClimateMode) + '</label><select class="ctrl-select" data-entity-input="' + self._h(ctx.depCliMode.id) + '" data-uid="input:' + self._h(ctx.depCliMode.id) + '">' + depModeOptsHtml + "</select></div>" : "") +
          (hasWeekDays
            ? '<div class="days-strip">' + ctx.weekDays.map(function (wd) {
                return '<button type="button" class="day-chip" data-day-chip="' + wd.slug + '" data-uid="day:' + wd.slug + '">' +
                  "<span>" + self._h(wd.letter) + '</span><span class="day-dot"></span></button>';
              }).join("") + "</div>" + dayEditorHtml
            : "") +
        "</div>"
      ) : "";

      var chargingHtml = '<section class="panel" data-panel="charging">' + liveChgHtml + schedChgHtml + depHtml + "</section>";

      // Panel 4: Security & Blueprint
      var tpmsCard = function (c) {
        if (!c.p && !c.temp && !c.w) return '<div class="tpms-box" data-tpms="' + c.pos + '"><span class="tpms-press num">—</span></div>';
        var entRef = c.p ? c.p.id : (c.w ? c.w.id : c.temp.id);
        return '<div class="tpms-box" role="button" tabindex="0" data-e="' + self._h(entRef) + '" data-tpms="' + c.pos + '">' +
          '<span class="tpms-press num" data-tpms-press="' + c.pos + '">—</span>' +
          '<span class="tpms-temp num" data-tpms-temp="' + c.pos + '"></span>' +
        "</div>";
      };

      var blueprintSvg =
        '<svg class="bp-svg" viewBox="0 0 160 250" aria-label="Vehicle blueprint">' +
          '<rect class="bp-body" x="42" y="16" width="76" height="218" rx="22"/>' +
          '<path class="bp-part" data-bp-part="hood" d="M 48 26 Q 80 18 112 26 L 108 68 L 52 68 Z"/>' +
          '<path class="bp-glass" d="M 52 72 L 108 72 L 104 94 L 56 94 Z"/>' +
          '<rect class="bp-part" data-bp-part="sunroof" x="56" y="102" width="48" height="44" rx="4"/>' +
          '<line class="bp-part" data-bp-part="sunroof_blind" x1="58" y1="124" x2="102" y2="124"/>' +
          '<path class="bp-part" data-bp-part="windows" d="M 46 84 L 50 84 L 50 182 L 46 182 Z M 110 84 L 114 84 L 114 182 L 110 182 Z"/>' +
          '<rect class="bp-part bp-door-fl" data-bp-part="front_left_door" x="41" y="96" width="8" height="42" rx="2"/>' +
          '<rect class="bp-part bp-door-fr" data-bp-part="front_right_door" x="111" y="96" width="8" height="42" rx="2"/>' +
          '<rect class="bp-part bp-door-rl" data-bp-part="rear_left_door" x="41" y="144" width="8" height="40" rx="2"/>' +
          '<rect class="bp-part bp-door-rr" data-bp-part="rear_right_door" x="111" y="144" width="8" height="40" rx="2"/>' +
          '<path class="bp-glass" d="M 56 184 L 104 184 L 108 202 L 52 202 Z"/>' +
          '<path class="bp-part" data-bp-part="trunk" d="M 52 206 L 108 206 L 112 226 Q 80 234 48 226 Z"/>' +
          '<rect class="bp-part" data-bp-part="tailgate_moving" x="62" y="226" width="36" height="5" rx="2"/>' +
        "</svg>";

      var blueprintHtml =
        '<div class="surface">' +
          '<div class="sec-hdr"><span>' + self._h(t.blueprintTitle) + "</span></div>" +
          '<div class="bp-stage">' +
            '<div class="tpms-col">' + tpmsCard(ctx.tpmsCorners[0]) + tpmsCard(ctx.tpmsCorners[2]) + "</div>" +
            blueprintSvg +
            '<div class="tpms-col">' + tpmsCard(ctx.tpmsCorners[1]) + tpmsCard(ctx.tpmsCorners[3]) + "</div>" +
          "</div>" +
        "</div>";

      var secBtns = [];
      if (ctx.lock) secBtns.push('<button type="button" class="ctrl-btn" data-bind="secLockBtn" data-action-id="unlock"></button>');
      if (ctx.trunk) secBtns.push('<button type="button" class="ctrl-btn" data-bind="secTrunkBtn" data-action-id="trunk_open"></button>');
      if (ctx.windowsCov) secBtns.push('<button type="button" class="ctrl-btn" data-bind="secWindowsBtn" data-action-id="windows_open"></button>');
      if (ctx.ventWinBtn) secBtns.push('<button type="button" class="ctrl-btn" data-action-id="vent_windows" data-confirm-key="vent_windows" data-bind="ventWinBtn">' + self._h(t.ventWindows) + "</button>");
      if (ctx.sunroofCov) secBtns.push('<button type="button" class="ctrl-btn" data-bind="secSunroofBtn" data-action-id="sunroof_open"></button>');
      if (ctx.ventSunBtn) secBtns.push('<button type="button" class="ctrl-btn" data-action-id="vent_sunroof" data-confirm-key="vent_sunroof" data-bind="ventSunBtn">' + self._h(t.ventSunroof) + "</button>");
      if (ctx.alarmSw) secBtns.push('<button type="button" class="ctrl-btn" data-action-id="alarm_toggle" data-confirm-key="alarm_toggle" data-bind="alarmBtn"></button>');
      if (ctx.remoteStartBtn) secBtns.push('<button type="button" class="ctrl-btn" data-action-id="remote_start" data-confirm-key="remote_start" data-bind="remoteStartBtn">' + self._h(t.remoteStart) + "</button>");
      if (ctx.locateBtn) secBtns.push('<button type="button" class="ctrl-btn" data-action-id="locate_gps" data-confirm-key="locate_gps">' + self._h(t.locateGps) + "</button>");
      if (ctx.flashBtn) secBtns.push('<button type="button" class="ctrl-btn" data-action-id="sec_flash_lights" data-confirm-key="flash_lights">' + self._h(t.flashLights) + "</button>");

      var secCtrlHtml = (secBtns.length || ctx.tracker) ? (
        '<div class="surface">' +
          '<div class="sec-hdr"><span>' + self._h(t.securityControls) + "</span></div>" +
          (secBtns.length ? '<div class="btn-grid">' + secBtns.join("") + "</div>" : "") +
          (ctx.tracker ? '<div class="info-row" role="button" tabindex="0" data-e="' + self._h(ctx.tracker.id) + '"><span>' + self._h(t.position) + '</span><span class="info-val" data-bind="trackerText"></span></div>' : "") +
        "</div>"
      ) : "";

      var securityHtml = '<section class="panel" data-panel="security">' + blueprintHtml + secCtrlHtml + "</section>";

      return "<style>" + buildStyles() + "</style>" +
        '<ha-card data-layout="' + self._h(cfg.layout) + '">' +
          '<div class="cockpit-grid">' +
            heroHtml +
            tabsHtml +
            overviewHtml +
            climateHtml +
            chargingHtml +
            securityHtml +
          "</div>" +
        "</ha-card>";
    }

    _applyBtnState(btn, label, actionId, confirmKey, variantClass, t) {
      if (!btn) return;
      btn.setAttribute("data-action-id", actionId);
      btn.setAttribute("data-confirm-key", confirmKey);
      var isConfirming = Boolean(this._confirmState && this._confirmState.key === confirmKey);
      var isPending = this._pendingKeys.has(confirmKey);

      btn.classList.remove("is-primary", "is-emerald", "is-glacier", "is-amber", "is-confirming", "is-pending");
      if (variantClass) btn.classList.add(variantClass);
      if (isPending) btn.classList.add("is-pending");
      btn.disabled = isPending;

      if (isConfirming) {
        btn.setAttribute("data-confirming", "true");
        btn.classList.add("is-confirming");
        btn.innerHTML = this._h(t.confirm) + '<span class="confirm-bar"></span>';
      } else {
        btn.removeAttribute("data-confirming");
        btn.textContent = label;
      }
    }

    _applyBindings(hass, vm) {
      var root = this.shadowRoot;
      if (!root) return;
      var t = vm.t;
      var self = this;

      var haCard = root.querySelector("ha-card");
      if (haCard) haCard.setAttribute("data-layout", vm.cfg.layout);

      // Tabs & Panels
      for (var i = 0; i < VALID_TABS.length; i += 1) {
        var tb = VALID_TABS[i];
        var tabBtn = root.querySelector('[data-tab="' + tb + '"]');
        var panelEl = root.querySelector('[data-panel="' + tb + '"]');
        var active = tb === this._activeTab;
        if (tabBtn) tabBtn.classList.toggle("is-active", active);
        if (panelEl) panelEl.classList.toggle("is-active", active);
      }

      // Hero
      var heroImg = root.querySelector('[data-bind="heroImg"]');
      if (heroImg) {
        var imgUrl = resolveHeroImage(vm.cfg, vm.items);
        if (heroImg.getAttribute("src") !== imgUrl) heroImg.setAttribute("src", imgUrl);
      }
      var heroTitle = root.querySelector('[data-bind="heroTitle"]');
      if (heroTitle) heroTitle.textContent = vm.title;

      var isCharging = this._isOn(vm.chgSwitch) ||
        (vm.chgStatus && vm.chgStatus.s && /charg/i.test(vm.chgStatus.s.state) && !/not/i.test(vm.chgStatus.s.state));
      var online = !vm.conn || (vm.conn.s && vm.conn.s.state === "on");
      var connDot = root.querySelector('[data-bind="connDot"]');
      if (connDot) {
        connDot.classList.toggle("is-online", online);
        connDot.classList.toggle("is-offline", Boolean(vm.conn && vm.conn.s && vm.conn.s.state === "off"));
      }
      var statusParts = [online ? t.online : t.offline];
      if (vm.atHome && !this._dead(vm.atHome.s)) {
        statusParts.push(this._isOn(vm.atHome) ? t.atHome : t.away);
      }
      if (vm.awake && !this._dead(vm.awake.s) && this._isOn(vm.awake)) {
        statusParts.push(t.awake);
      }
      var statusText = root.querySelector('[data-bind="statusText"]');
      if (statusText) statusText.textContent = statusParts.join(" · ");

      // SoC ring & accessible <progress>
      if (vm.bat) {
        var batNum = this._num(vm.bat.s);
        var pct = batNum === null ? 0 : Math.max(0, Math.min(100, batNum));
        var socText = root.querySelector('[data-bind="socText"]');
        if (socText) socText.textContent = batNum === null ? "—" : Math.round(pct) + "%";
        var socProg = root.querySelector('[data-bind="socProgress"]');
        if (socProg) {
          socProg.setAttribute("value", String(Math.round(pct)));
          socProg.setAttribute("aria-label", Math.round(pct) + "%");
        }
        var socRing = root.querySelector("[data-soc-ring]");
        if (socRing) {
          var circ = 131.95;
          var offset = circ * (1 - pct / 100);
          socRing.setAttribute("stroke-dashoffset", offset.toFixed(2));
          socRing.classList.toggle("is-low", !isCharging && pct <= 15);
          socRing.classList.toggle("is-warn", !isCharging && pct > 15 && pct <= 30);
        }
      }

      // Hero subtitle (never VIN or GPS)
      var subParts = [];
      if (vm.lock && !this._dead(vm.lock.s)) {
        subParts.push(vm.lock.s.state === "locked" ? t.locked : t.unlocked);
      }
      if (vm.climate && !this._dead(vm.climate.s)) {
        var cliOn = vm.climate.s.state !== "off";
        var cTemp = vm.climate.s.attributes && vm.climate.s.attributes.temperature;
        subParts.push(cliOn ? (t.climateOn + (cTemp ? " " + cTemp + "°C" : "")) : t.climateOff);
      }
      if (vm.odo && !this._dead(vm.odo.s)) {
        subParts.push(this._disp(vm.odo.s));
      } else if (vm.plug && !this._dead(vm.plug.s)) {
        subParts.push(this._isOn(vm.plug) ? t.plugged : t.unplugged);
      }
      var heroSub = root.querySelector('[data-bind="heroSub"]');
      if (heroSub) heroSub.textContent = subParts.join(" · ");

      // Error banner
      var errBanner = root.querySelector('[data-bind="errorBanner"]');
      var errText = root.querySelector('[data-bind="errorText"]');
      if (errBanner && errText) {
        errBanner.classList.toggle("hidden", !this._errorMsg);
        errText.textContent = this._errorMsg || "";
      }

      // Overview 2x2 Metrics
      var evCard = root.querySelector('[data-bind="mEvCard"]');
      var evVal = root.querySelector('[data-bind="mEvVal"]');
      if (evCard && vm.evRange) evCard.setAttribute("data-e", vm.evRange.id);
      if (evVal) evVal.textContent = (vm.evRange && !this._dead(vm.evRange.s)) ? this._disp(vm.evRange.s) : "—";
      var evBarWrap = root.querySelector('[data-bind="mEvBarWrap"]');
      var evBar = root.querySelector('[data-bind="mEvBar"]');
      if (evBarWrap && evBar) {
        var evNum = vm.evRange ? this._num(vm.evRange.s) : null;
        var wltpNum = vm.wltpRange ? this._num(vm.wltpRange.s) : null;
        if (evNum !== null && wltpNum !== null && wltpNum > 0) {
          evBarWrap.classList.remove("hidden");
          evBar.style.setProperty("width", Math.min(100, Math.max(0, (evNum / wltpNum) * 100)).toFixed(0) + "%");
        } else {
          evBarWrap.classList.add("hidden");
        }
      }

      var rangeTarget = vm.totalRange || vm.fuelRange;
      var fuelCard = root.querySelector('[data-bind="mFuelCard"]');
      var fuelLbl = root.querySelector('[data-bind="mFuelLbl"]');
      var fuelVal = root.querySelector('[data-bind="mFuelVal"]');
      if (fuelCard && rangeTarget) fuelCard.setAttribute("data-e", rangeTarget.id);
      if (fuelLbl) fuelLbl.textContent = (rangeTarget && rangeTarget.key === "total_range") ? t.totalRange : t.fuelRange;
      if (fuelVal) fuelVal.textContent = (rangeTarget && !this._dead(rangeTarget.s)) ? this._disp(rangeTarget.s) : "—";

      var chgCard = root.querySelector('[data-bind="mChgCard"]');
      var chgVal = root.querySelector('[data-bind="mChgVal"]');
      var chgOut = t.idle;
      var chgEntId = null;
      if (isCharging) {
        if (vm.chgPower && !this._dead(vm.chgPower.s) && this._num(vm.chgPower.s) > 0) {
          chgOut = this._disp(vm.chgPower.s);
          chgEntId = vm.chgPower.id;
        } else {
          chgOut = t.charging;
          chgEntId = vm.chgSwitch ? vm.chgSwitch.id : (vm.chgStatus ? vm.chgStatus.id : null);
        }
      } else if (vm.chgStatus && !this._dead(vm.chgStatus.s)) {
        chgOut = vm.chgStatus.s.state;
        chgEntId = vm.chgStatus.id;
      } else if (vm.plug && !this._dead(vm.plug.s)) {
        chgOut = this._isOn(vm.plug) ? t.plugged : t.unplugged;
        chgEntId = vm.plug.id;
      }
      if (chgCard && chgEntId) chgCard.setAttribute("data-e", chgEntId);
      if (chgVal) chgVal.textContent = chgOut;

      var odoCard = root.querySelector('[data-bind="mOdoCard"]');
      var odoLbl = root.querySelector('[data-bind="mOdoLbl"]');
      var odoVal = root.querySelector('[data-bind="mOdoVal"]');
      if (vm.odo && !this._dead(vm.odo.s)) {
        if (odoCard) odoCard.setAttribute("data-e", vm.odo.id);
        if (odoLbl) odoLbl.textContent = t.odometer;
        if (odoVal) odoVal.textContent = this._disp(vm.odo.s);
      } else if (vm.nextDep && !this._dead(vm.nextDep.s)) {
        if (odoCard) odoCard.setAttribute("data-e", vm.nextDep.id);
        if (odoLbl) odoLbl.textContent = t.nextDeparture;
        if (odoVal) odoVal.textContent = vm.nextDep.s.state;
      } else if (vm.plug && !this._dead(vm.plug.s)) {
        if (odoCard) odoCard.setAttribute("data-e", vm.plug.id);
        if (odoLbl) odoLbl.textContent = t.cable;
        if (odoVal) odoVal.textContent = this._isOn(vm.plug) ? t.plugged : t.unplugged;
      }

      // Overview Quick Dock + Security Action Buttons (synchronized confirmation keys!)
      if (vm.lock) {
        var isLocked = vm.lock.s && vm.lock.s.state === "locked";
        this._applyBtnState(
          root.querySelector('[data-bind="quickLockBtn"]'),
          isLocked ? t.unlock : t.lock,
          isLocked ? "quick_unlock" : "quick_lock_now",
          isLocked ? "unlock" : "lock_now",
          isLocked ? "" : "is-emerald",
          t
        );
        this._applyBtnState(
          root.querySelector('[data-bind="secLockBtn"]'),
          isLocked ? t.unlock : t.lock,
          isLocked ? "unlock" : "lock_now",
          isLocked ? "unlock" : "lock_now",
          isLocked ? "" : "is-emerald",
          t
        );
      }
      if (vm.climate) {
        var cliActive = !this._dead(vm.climate.s) && vm.climate.s.state !== "off";
        this._applyBtnState(
          root.querySelector('[data-bind="quickClimateBtn"]'),
          cliActive ? t.climateOn : t.climateOff,
          "climate_quick",
          "climate_toggle",
          cliActive ? "is-glacier" : "",
          t
        );
        this._applyBtnState(
          root.querySelector('[data-bind="climateToggleBtn"]'),
          cliActive ? t.climateOn : t.climateOff,
          "climate_toggle",
          "climate_toggle",
          cliActive ? "is-glacier" : "",
          t
        );
      }
      if (vm.trunk) {
        var trunkClosed = vm.trunk.s && vm.trunk.s.state === "closed";
        this._applyBtnState(
          root.querySelector('[data-bind="quickTrunkBtn"]'),
          t.trunk + ": " + (trunkClosed ? t.openCmd : t.closeCmd),
          trunkClosed ? "quick_trunk_open" : "quick_trunk_close",
          trunkClosed ? "trunk_open" : "trunk_close",
          trunkClosed ? "" : "is-amber",
          t
        );
        this._applyBtnState(
          root.querySelector('[data-bind="secTrunkBtn"]'),
          t.trunk + ": " + (trunkClosed ? t.openCmd : t.closeCmd),
          trunkClosed ? "trunk_open" : "trunk_close",
          trunkClosed ? "trunk_open" : "trunk_close",
          trunkClosed ? "" : "is-amber",
          t
        );
      }
      if (vm.windowsCov) {
        var winClosed = vm.windowsCov.s && vm.windowsCov.s.state === "closed";
        this._applyBtnState(
          root.querySelector('[data-bind="secWindowsBtn"]'),
          t.windows + ": " + (winClosed ? t.openCmd : t.closeCmd),
          winClosed ? "windows_open" : "windows_close",
          winClosed ? "windows_open" : "windows_close",
          winClosed ? "" : "is-glacier",
          t
        );
      }
      if (vm.sunroofCov) {
        var sunClosed = vm.sunroofCov.s && vm.sunroofCov.s.state === "closed";
        this._applyBtnState(
          root.querySelector('[data-bind="secSunroofBtn"]'),
          t.sunroof + ": " + (sunClosed ? t.openCmd : t.closeCmd),
          sunClosed ? "sunroof_open" : "sunroof_close",
          sunClosed ? "sunroof_open" : "sunroof_close",
          sunClosed ? "" : "is-glacier",
          t
        );
      }
      this._applyBtnState(root.querySelector('[data-bind="ventWinBtn"]'), t.ventWindows, "vent_windows", "vent_windows", "", t);
      this._applyBtnState(root.querySelector('[data-bind="ventSunBtn"]'), t.ventSunroof, "vent_sunroof", "vent_sunroof", "", t);
      this._applyBtnState(root.querySelector('[data-bind="remoteStartBtn"]'), t.remoteStart, "remote_start", "remote_start", "", t);
      if (vm.alarmSw) {
        var alarmOn = this._isOn(vm.alarmSw);
        this._applyBtnState(
          root.querySelector('[data-bind="alarmBtn"]'),
          t.alarm + ": " + (alarmOn ? t.on : t.off),
          "alarm_toggle",
          "alarm_toggle",
          alarmOn ? "is-emerald" : "",
          t
        );
      }

      // Overview Footer & Extra rows
      var freshEl = root.querySelector('[data-bind="freshnessText"]');
      if (freshEl) {
        freshEl.textContent = vm.carUpdated && !this._dead(vm.carUpdated.s)
          ? t.updated + ": " + formatTimestamp(vm.carUpdated.s.state, vm.lang)
          : t.updated + ": —";
      }
      var cmdBadge = root.querySelector('[data-bind="cmdResultBadge"]');
      if (cmdBadge) {
        if (vm.cmdResult && !this._dead(vm.cmdResult.s)) {
          cmdBadge.classList.remove("hidden");
          cmdBadge.textContent = vm.cmdResult.s.state;
        } else {
          cmdBadge.classList.add("hidden");
        }
      }
      var extraValEls = root.querySelectorAll("[data-extra-entity]");
      for (var ex = 0; ex < extraValEls.length; ex += 1) {
        var rowEl = extraValEls[ex];
        var eid = rowEl.getAttribute("data-extra-entity");
        var es = hass.states[eid];
        var nmEl = rowEl.querySelector("[data-extra-name]");
        var vlEl = rowEl.querySelector("[data-extra-val]");
        if (nmEl && es) {
          var rawNm = (es.attributes && es.attributes.friendly_name) ? es.attributes.friendly_name : eid;
          nmEl.textContent = rawNm.replace(vm.deviceRe, "").trim() || eid;
        }
        if (vlEl) vlEl.textContent = es ? this._disp(es) : "—";
      }

      // Climate details
      if (vm.climate) {
        var tt = vm.climate.s.attributes && vm.climate.s.attributes.temperature;
        var ttEl = root.querySelector('[data-bind="targetTempText"]');
        if (ttEl) ttEl.textContent = (typeof tt === "number") ? tt.toFixed(1) + " °C" : "—";
      }
      var stl = root.querySelector('[data-bind="setTempLText"]');
      if (stl && vm.setTempL) stl.textContent = t.leftZone + ": " + (this._dead(vm.setTempL.s) ? "—" : this._disp(vm.setTempL.s));
      var str = root.querySelector('[data-bind="setTempRText"]');
      if (str && vm.setTempR) str.textContent = t.rightZone + ": " + (this._dead(vm.setTempR.s) ? "—" : this._disp(vm.setTempR.s));
      var apBadge = root.querySelector('[data-bind="airPurifBadge"]');
      if (apBadge) apBadge.classList.toggle("hidden", !this._isOn(vm.airPurif));

      if (vm.cliDur) {
        var curDur = this._num(vm.cliDur.s);
        var cdTxt = root.querySelector('[data-bind="cliDurText"]');
        if (cdTxt) cdTxt.textContent = curDur === null ? "—" : Math.round(curDur) + " min";
        var allChips = root.querySelectorAll('[data-action-id="climate_duration"]');
        for (var ci = 0; ci < allChips.length; ci += 1) {
          var vNum = parseFloat(allChips[ci].getAttribute("data-value"));
          allChips[ci].classList.toggle("is-active", curDur !== null && Math.round(curDur) === Math.round(vNum));
        }
      }

      var coolBtn = root.querySelector('[data-bind="coolAllBtn"]');
      if (coolBtn) coolBtn.classList.toggle("is-glacier", this._isOn(vm.coolSwitch));
      var heatBtn = root.querySelector('[data-bind="heatAllBtn"]');
      if (heatBtn) heatBtn.classList.toggle("is-amber", this._isOn(vm.heatSwitch));

      for (var di = 0; di < vm.defrostEntities.length; di += 1) {
        var df = vm.defrostEntities[di];
        var dBtn = root.querySelector('[data-defrost-btn="' + df.key + '"]');
        if (dBtn) dBtn.classList.toggle("is-amber", this._isOn(df.ent));
      }

      for (var si = 0; si < vm.seatDefs.length; si += 1) {
        var sd = vm.seatDefs[si];
        var hBtn = root.querySelector('[data-seat-btn="' + sd.slug + '_heat"]');
        if (hBtn) hBtn.classList.toggle("is-amber", this._isOn(sd.heat));
        var vBtn = root.querySelector('[data-seat-btn="' + sd.slug + '_vent"]');
        if (vBtn) vBtn.classList.toggle("is-glacier", this._isOn(sd.vent));
      }

      var rcTxt = root.querySelector('[data-bind="rearCenterText"]');
      if (rcTxt) {
        var rcParts = [];
        if (vm.rearCenterHeat && !this._dead(vm.rearCenterHeat.s)) rcParts.push(t.heat + " " + vm.rearCenterHeat.s.state);
        if (vm.rearCenterVent && !this._dead(vm.rearCenterVent.s)) rcParts.push(t.vent + " " + vm.rearCenterVent.s.state);
        rcTxt.textContent = rcParts.length ? rcParts.join(" · ") : "0";
      }

      // Charging & Departures
      var cableBadge = root.querySelector('[data-bind="cableBadge"]');
      if (cableBadge) {
        var plugged = this._isOn(vm.plug);
        cableBadge.textContent = vm.plug ? (plugged ? t.plugged : t.unplugged) : "";
        cableBadge.classList.toggle("is-emerald", plugged);
      }
      var chgToggleBtn = root.querySelector('[data-bind="chgToggleBtn"]');
      if (chgToggleBtn && vm.chgSwitch) {
        var chgSwOn = this._isOn(vm.chgSwitch);
        this._applyBtnState(chgToggleBtn, t.chargingLbl + ": " + (chgSwOn ? t.on : t.off), "charging_toggle", "charging_toggle", chgSwOn ? "is-emerald" : "", t);
      }

      var setBadge = function (bind, label, ent) {
        var el = root.querySelector('[data-bind="' + bind + '"]');
        if (!el) return;
        if (ent && !self._dead(ent.s)) {
          el.classList.remove("hidden");
          el.textContent = label + ": " + self._disp(ent.s);
        } else {
          el.classList.add("hidden");
        }
      };
      setBadge("chgPowerBadge", t.chargingLbl, vm.chgPower);
      setBadge("remTimeBadge", t.remaining, vm.remTime);
      setBadge("hvVoltBadge", t.voltage, vm.hvVolt);
      setBadge("hvCurrBadge", t.current, vm.hvCurr);
      setBadge("homeEnergyBadge", t.homeEnergy, vm.homeEnergy);
      setBadge("awayEnergyBadge", t.awayEnergy, vm.awayEnergy);
      setBadge("fastPortBadge", t.fastPort, vm.fastPort);

      var schedToggleBtn = root.querySelector('[data-bind="schedToggleBtn"]');
      if (schedToggleBtn && vm.schedSwitch) {
        var scOn = this._isOn(vm.schedSwitch);
        this._applyBtnState(schedToggleBtn, t.scheduledCharging + ": " + (scOn ? t.on : t.off), "scheduled_charging_toggle", "scheduled_charging_toggle", scOn ? "is-emerald" : "", t);
      }

      if (vm.schedWindow && vm.schedWindow.s) {
        var swAttrs = vm.schedWindow.s.attributes || {};
        var trackEl = root.querySelector('[data-bind="timelineTrack"]');
        if (trackEl) {
          var segKey = (swAttrs.start_time || "") + "|" + (swAttrs.end_time || "") + "|" + (swAttrs.next_day ? "1" : "0");
          if (trackEl.getAttribute("data-seg-key") !== segKey) {
            trackEl.setAttribute("data-seg-key", segKey);
            var sMin = hhmmToMinutes(swAttrs.start_time || "23:00");
            var eMin = hhmmToMinutes(swAttrs.end_time || "05:00");
            var segs = [];
            if (sMin !== null && eMin !== null) {
              var sPct = (sMin / 1440) * 100;
              var ePct = (eMin / 1440) * 100;
              if (swAttrs.next_day || eMin <= sMin) {
                segs.push({ left: sPct.toFixed(2), width: (100 - sPct).toFixed(2) });
                segs.push({ left: "0", width: ePct.toFixed(2) });
              } else {
                segs.push({ left: sPct.toFixed(2), width: Math.max(2, ePct - sPct).toFixed(2) });
              }
            }
            trackEl.innerHTML = segs.map(function (sg) {
              return '<div class="timeline-seg" data-timeline-seg style="left:' + sg.left + "%;width:" + sg.width + '%"></div>';
            }).join("");
          }
        }
        var swTxt = root.querySelector('[data-bind="schedWindowText"]');
        if (swTxt) {
          swTxt.textContent = (swAttrs.start_time && swAttrs.end_time)
            ? swAttrs.start_time + " → " + swAttrs.end_time
            : vm.schedWindow.s.state;
        }
        var syncBadge = root.querySelector('[data-bind="schedSyncBadge"]');
        if (syncBadge) {
          if (swAttrs.synced_with_car === true || swAttrs.synced_with_car === false) {
            syncBadge.classList.remove("hidden");
            syncBadge.classList.toggle("is-emerald", swAttrs.synced_with_car === true);
            syncBadge.classList.toggle("is-amber", swAttrs.synced_with_car === false);
            syncBadge.textContent = swAttrs.synced_with_car ? t.synced : t.pendingSync;
          } else {
            syncBadge.classList.add("hidden");
          }
        }
        var fb2131 = root.querySelector('[data-bind="fallback2131Badge"]');
        if (fb2131) {
          var isAllSeven = Array.isArray(swAttrs.days) && swAttrs.days.length === 7;
          var selectedNotAll = vm.chgDays && vm.chgDays.s && vm.chgDays.s.state !== "all_days";
          fb2131.classList.toggle("hidden", !(isAllSeven && selectedNotAll));
        }
      }

      var syncInputVal = function (ent, slice5) {
        if (!ent || !ent.s) return;
        var el = root.querySelector('[data-entity-input="' + ent.id + '"]');
        if (!el || root.activeElement === el) return;
        var nextV = slice5 ? String(ent.s.state || "").slice(0, 5) : String(ent.s.state || "");
        if (!self._dead(ent.s)) el.value = nextV;
      };
      syncInputVal(vm.chgStartTime, true);
      syncInputVal(vm.chgDays, false);
      syncInputVal(vm.quickDepTime, true);
      syncInputVal(vm.depCliMode, false);

      var chgDurEl = root.querySelector('[data-bind="chgDurText"]');
      if (chgDurEl && vm.chgDur) chgDurEl.textContent = this._dead(vm.chgDur.s) ? "—" : this._disp(vm.chgDur.s);

      // Departures
      var nextDepEl = root.querySelector('[data-bind="nextDepText"]');
      if (nextDepEl && vm.nextDep) nextDepEl.textContent = this._dead(vm.nextDep.s) ? "—" : vm.nextDep.s.state;
      var depHintEl = root.querySelector('[data-bind="depChargeHint"]');
      if (depHintEl) {
        var pStart = vm.nextDep && vm.nextDep.s && vm.nextDep.s.attributes && vm.nextDep.s.attributes.planned_charge_start;
        if (pStart) {
          depHintEl.classList.remove("hidden");
          depHintEl.textContent = t.chargeStartHint + ": " + pStart;
        } else {
          depHintEl.classList.add("hidden");
        }
      }

      var qDepBtn = root.querySelector('[data-bind="quickDepBtn"]');
      if (qDepBtn && vm.quickDep) {
        var qOn = this._isOn(vm.quickDep);
        this._applyBtnState(qDepBtn, t.quickDeparture + ": " + (qOn ? t.on : t.off), "quick_departure_toggle", "quick_departure_toggle", qOn ? "is-emerald" : "", t);
      }
      var syncBtn = root.querySelector('[data-bind="syncChargeBtn"]');
      if (syncBtn && vm.syncCharge) {
        var sOn = this._isOn(vm.syncCharge);
        this._applyBtnState(syncBtn, t.syncCharge + ": " + (sOn ? t.on : t.off), "sync_charge_toggle", "sync_charge_toggle", sOn ? "is-emerald" : "", t);
      }
      for (var wi = 0; wi < vm.weekDays.length; wi += 1) {
        var wd = vm.weekDays[wi];
        var dChip = root.querySelector('[data-day-chip="' + wd.slug + '"]');
        if (dChip) {
          dChip.classList.toggle("is-enabled", this._isOn(wd.sw));
          dChip.classList.toggle("is-expanded", this._expandedDay === wd.slug);
        }
        if (this._expandedDay === wd.slug) {
          var expBtn = root.querySelector('[data-bind="expandedDayToggle"]');
          if (expBtn && wd.sw) {
            var dOn = this._isOn(wd.sw);
            this._applyBtnState(expBtn, t.enableDay + ": " + (dOn ? t.on : t.off), "day_toggle_" + wd.slug, "day_toggle_" + wd.slug, dOn ? "is-emerald" : "", t);
          }
          syncInputVal(wd.tm, true);
        }
      }

      // Blueprint SVG & TPMS
      var setBp = function (part, cls, active) {
        var el = root.querySelector('[data-bp-part="' + part + '"]');
        if (el) el.classList.toggle(cls, Boolean(active));
      };
      setBp("front_left_door", "is-open", this._isOn(vm.doorFL));
      setBp("front_right_door", "is-open", this._isOn(vm.doorFR));
      setBp("rear_left_door", "is-open", this._isOn(vm.doorRL));
      setBp("rear_right_door", "is-open", this._isOn(vm.doorRR));
      setBp("hood", "is-open", this._isOn(vm.hood));
      setBp("trunk", "is-open", vm.trunk && vm.trunk.s && vm.trunk.s.state === "open");
      setBp("tailgate_moving", "is-moving", this._isOn(vm.tailMoving));
      setBp("sunroof_blind", "is-open", this._isOn(vm.sunroofBlind));

      var winOpen = this._isOn(vm.winFL) || this._isOn(vm.winFR) || this._isOn(vm.winRL) || this._isOn(vm.winRR) ||
        (vm.windowsCov && vm.windowsCov.s && vm.windowsCov.s.state === "open");
      setBp("windows", "is-open", winOpen);
      setBp("windows", "is-window-open", winOpen);

      var sunOpen = (vm.sunroofCov && vm.sunroofCov.s && vm.sunroofCov.s.state === "open") ||
        (vm.sunroofMove && vm.sunroofMove.s && /open|mov|tilt/i.test(vm.sunroofMove.s.state));
      setBp("sunroof", "is-open", sunOpen);
      setBp("sunroof", "is-window-open", sunOpen);

      for (var ti = 0; ti < vm.tpmsCorners.length; ti += 1) {
        var tp = vm.tpmsCorners[ti];
        var box = root.querySelector('[data-tpms="' + tp.pos + '"]');
        var pEl = root.querySelector('[data-tpms-press="' + tp.pos + '"]');
        var tEl = root.querySelector('[data-tpms-temp="' + tp.pos + '"]');
        var isAlert = this._isOn(tp.w);
        if (box) {
          box.classList.toggle("is-alert", isAlert);
          box.classList.toggle("is-ok", !isAlert && Boolean(tp.p && !this._dead(tp.p.s)));
        }
        if (pEl) pEl.textContent = (tp.p && !this._dead(tp.p.s)) ? this._disp(tp.p.s) : "—";
        if (tEl) tEl.textContent = (tp.temp && !this._dead(tp.temp.s)) ? this._disp(tp.temp.s) : "";
      }

      // Device tracker (zone label only — NEVER raw lat/lon)
      var trkEl = root.querySelector('[data-bind="trackerText"]');
      if (trkEl && vm.tracker) {
        var st = vm.tracker.s ? vm.tracker.s.state : "unknown";
        if (st === "home") trkEl.textContent = t.atHome;
        else if (st === "not_home") trkEl.textContent = t.away;
        else trkEl.textContent = this._dead(vm.tracker.s) ? "—" : st;
      }
    }
  }

  LepasCard._helpers = {
    CARD_VERSION: CARD_VERSION,
    COLORS: VALID_COLORS.slice(),
    COLOR_ALIASES: Object.assign({}, COLOR_ALIASES),
    VALID_TABS: VALID_TABS.slice(),
    VALID_LAYOUTS: VALID_LAYOUTS.slice(),
    resolveColor: resolveColor,
    resolveHeroImage: resolveHeroImage,
    sanitizeUrl: sanitizeUrl,
    escapeHtml: escapeHtml,
    isSensitiveAction: isSensitiveAction,
    getTexts: getTexts,
  };

  if (!customElements.get("lepas-card-editor")) {
    customElements.define("lepas-card-editor", LepasCardEditor);
  }
  if (!customElements.get("lepas-card")) {
    customElements.define("lepas-card", LepasCard);
  }
  window.customCards = window.customCards || [];
  if (!window.customCards.some(function (c) { return c.type === "custom:lepas-card"; })) {
    window.customCards.push({
      type: "custom:lepas-card",
      name: "Lepas Card",
      preview: true,
      description: "Matte Titanium OEM dashboard card for Lepas Connect (responsive 4-tab / cockpit, blueprint SVG, TPMS, climate, charging, departures).",
    });
  }
})();
