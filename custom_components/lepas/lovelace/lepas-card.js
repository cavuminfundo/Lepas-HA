/*
 * Lepas vehicle card — Matte Titanium OEM edition (Lepas Connect v1.22.1).
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
  var CARD_VERSION = "1.22.1";
  var VALID_COLORS = ["grey", "teal", "violet", "black", "white"];
  var VALID_LAYOUTS = ["auto", "compact", "cockpit"];
  var VALID_TABS = ["overview", "climate", "charging", "security"];
  var DAY_SLUGS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
  var CHARGE_DAY_PRESETS = {
    all_days: [1, 2, 3, 4, 5, 6, 7],
    weekdays: [1, 2, 3, 4, 5],
    weekend: [6, 7],
    mon_wed_fri: [1, 3, 5],
    tue_thu_sat: [2, 4, 6],
  };

  var ALLOWED_CLIMATE_EXTRAS = [
    "driver_seat_heating",
    "driver_seat_ventilation",
    "passenger_seat_heating",
    "passenger_seat_ventilation",
    "rear_left_seat_heating",
    "rear_left_seat_ventilation",
    "rear_right_seat_heating",
    "rear_right_seat_ventilation",
    "rear_window_heating",
    "windshield_defrost",
    "windshield_defog",
    "steering_wheel_heating",
  ];

  var CLIMATE_EXTRA_META = {
    driver_seat_heating: { icon: "flame", opposite: "driver_seat_ventilation" },
    driver_seat_ventilation: { icon: "fan", opposite: "driver_seat_heating" },
    passenger_seat_heating: { icon: "flame", opposite: "passenger_seat_ventilation" },
    passenger_seat_ventilation: { icon: "fan", opposite: "passenger_seat_heating" },
    rear_left_seat_heating: { icon: "flame", opposite: "rear_left_seat_ventilation" },
    rear_left_seat_ventilation: { icon: "fan", opposite: "rear_left_seat_heating" },
    rear_right_seat_heating: { icon: "flame", opposite: "rear_right_seat_ventilation" },
    rear_right_seat_ventilation: { icon: "fan", opposite: "rear_right_seat_heating" },
    rear_window_heating: { icon: "rear_defrost", opposite: null },
    windshield_defrost: { icon: "windshield", opposite: null },
    windshield_defog: { icon: "windshield", opposite: null },
    steering_wheel_heating: { icon: "steering", opposite: null },
  };

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
    grey: "/lepas_card/lepas-hero-grey.png?v=1.22.1",
    teal: "/lepas_card/lepas-hero-teal.png?v=1.22.1",
    violet: "/lepas_card/lepas-hero-violet.png?v=1.22.1",
    black: "/lepas_card/lepas-hero-black.png?v=1.22.1",
    white: "/lepas_card/lepas-hero-white.png?v=1.22.1",
  };
  var DEFAULT_HERO = "/lepas_card/lepas-hero.png?v=1.22.1";

  var CONFIRM_ACTIONS = Object.freeze({
    wake_car: true,
    refresh_location: true,
    refresh_full: true,
    locate_gps: true,
    flash_lights: true,
    sec_flash_lights: true,
    vent_windows: true,
    vent_sunroof: true,
    remote_start: true,
    apply_charging_schedule: true,
    apply_departure_schedule: true,
    unlock: true,
    quick_unlock: true,
    trunk_open: true,
    quick_trunk_open: true,
    windows_open: true,
    sunroof_open: true,
    alarm_toggle: true,
  });

  var CMD_ERROR_PATTERNS = [
    "❌",
    "⚠",
    "rifiut",
    "errore",
    "error",
    "fallit",
    "failed",
    "non riuscit",
    "scadut",
    "bloccat",
    "eseguito solo in parte",
  ];

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
      confirmModalTitle: "Confermare comando?",
      confirmModalHint: "Il comando verrà inviato al veicolo.",
      confirmCancel: "Annulla",
      confirmSend: "Invia",
      lastCommand: "Ultimo comando",
      commandSendError: "Errore invio comando",
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
      departureActive: "Attiva",
      today: "Oggi",
      tomorrow: "Domani",
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
      startCharging: "Avvia ricarica",
      stopCharging: "Ferma ricarica",
      chargeModeManual: "Orario manuale",
      chargeModeDeparture: "Segui partenza",
      presetAll: "Tutti",
      presetWeekdays: "Lun–Ven",
      presetWeekend: "Weekend",
      followDepartureTitle: "Avvio automatico per partenza",
      noDeparturePlanned: "Nessuna partenza attiva: abilita un giorno sotto.",
      closuresGroup: "Aperture e accessi",
      securityGroup: "Sicurezza e posizione",
      applyDeparture: "Applica su auto",
      disableOnCar: "Disattiva su auto",
      carDeparturePlan: "Prossima partenza pianificata",
      noScheduledDeparture: "Nessuna partenza programmata",
      depClimateExtras: "Extra clima alla partenza",
      batteryPreheat: "Preriscaldamento batteria",
      batteryPreheatTime: "Orario preriscaldamento batteria",
      syncBatteryHeat: "Allinea alla partenza",
      batteryHeatHint: "Avvio batteria",
      climateExtraLabels: {
        driver_seat_heating: "Sedile guida caldo",
        driver_seat_ventilation: "Sedile guida aria",
        passenger_seat_heating: "Sedile pass. caldo",
        passenger_seat_ventilation: "Sedile pass. aria",
        rear_left_seat_heating: "Sed. post. SX caldo",
        rear_left_seat_ventilation: "Sed. post. SX aria",
        rear_right_seat_heating: "Sed. post. DX caldo",
        rear_right_seat_ventilation: "Sed. post. DX aria",
        rear_window_heating: "Lunotto termico",
        windshield_defrost: "Sbrina parabrezza",
        windshield_defog: "Disappanna vetro",
        steering_wheel_heating: "Volante caldo",
      },
      tpmsLabels: { front_left: "ANT SX", front_right: "ANT DX", rear_left: "POST SX", rear_right: "POST DX" },
      options: {
        departure_climate_mode: { at_home: "Solo a casa", anywhere: "Ovunque", off: "Disattivato" },
        charge_days: {
          all_days: "Tutti i giorni",
          weekdays: "Lun–Ven",
          weekend: "Weekend",
          mon_wed_fri: "Lun / Mer / Ven",
          tue_thu_sat: "Mar / Gio / Sab",
          custom: "Personalizzato",
        },
      },
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
      confirmModalTitle: "Confirm command?",
      confirmModalHint: "This command will be sent to the vehicle.",
      confirmCancel: "Cancel",
      confirmSend: "Send",
      lastCommand: "Last command",
      commandSendError: "Command failed",
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
      departureActive: "Active",
      today: "Today",
      tomorrow: "Tomorrow",
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
      startCharging: "Start charging",
      stopCharging: "Stop charging",
      chargeModeManual: "Manual time",
      chargeModeDeparture: "Follow departure",
      presetAll: "All",
      presetWeekdays: "Mon–Fri",
      presetWeekend: "Weekend",
      followDepartureTitle: "Auto-start before departure",
      noDeparturePlanned: "No active departure: enable a day below.",
      closuresGroup: "Closures and access",
      securityGroup: "Security and location",
      applyDeparture: "Apply to car",
      disableOnCar: "Disable on car",
      carDeparturePlan: "Next scheduled departure",
      noScheduledDeparture: "No scheduled departure",
      depClimateExtras: "Departure climate extras",
      batteryPreheat: "Battery preheating",
      batteryPreheatTime: "Battery preheat time",
      syncBatteryHeat: "Align to departure",
      batteryHeatHint: "Battery heat",
      climateExtraLabels: {
        driver_seat_heating: "Driver seat heat",
        driver_seat_ventilation: "Driver seat vent",
        passenger_seat_heating: "Pass. seat heat",
        passenger_seat_ventilation: "Pass. seat vent",
        rear_left_seat_heating: "Rear L seat heat",
        rear_left_seat_ventilation: "Rear L seat vent",
        rear_right_seat_heating: "Rear R seat heat",
        rear_right_seat_ventilation: "Rear R seat vent",
        rear_window_heating: "Rear defrost",
        windshield_defrost: "Windshield defrost",
        windshield_defog: "Windshield defog",
        steering_wheel_heating: "Steering wheel",
      },
      tpmsLabels: { front_left: "FL", front_right: "FR", rear_left: "RL", rear_right: "RR" },
      options: {
        departure_climate_mode: { at_home: "Home only", anywhere: "Anywhere", off: "Off" },
        charge_days: {
          all_days: "Every day",
          weekdays: "Mon–Fri",
          weekend: "Weekend",
          mon_wed_fri: "Mon / Wed / Fri",
          tue_thu_sat: "Tue / Thu / Sat",
          custom: "Custom",
        },
      },
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
      confirmModalTitle: "Opdracht bevestigen?",
      confirmModalHint: "De opdracht wordt naar het voertuig gestuurd.",
      confirmCancel: "Annuleren",
      confirmSend: "Verzenden",
      lastCommand: "Laatste opdracht",
      commandSendError: "Opdracht mislukt",
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
      departureActive: "Actief",
      today: "Vandaag",
      tomorrow: "Morgen",
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
      startCharging: "Laden starten",
      stopCharging: "Laden stoppen",
      chargeModeManual: "Handmatige tijd",
      chargeModeDeparture: "Volg vertrek",
      presetAll: "Alle",
      presetWeekdays: "Ma–Vr",
      presetWeekend: "Weekend",
      followDepartureTitle: "Automatische start voor vertrek",
      noDeparturePlanned: "Geen actief vertrek: schakel hieronder een dag in.",
      closuresGroup: "Sluitingen en toegang",
      securityGroup: "Beveiliging en locatie",
      applyDeparture: "Toepassen op auto",
      disableOnCar: "Uitschakelen op auto",
      carDeparturePlan: "Volgend gepland vertrek",
      noScheduledDeparture: "Geen gepland vertrek",
      depClimateExtras: "Extra vertrekklimaat",
      batteryPreheat: "Batterij voorverwarming",
      batteryPreheatTime: "Tijd batterij voorverwarming",
      syncBatteryHeat: "Afstemmen op vertrek",
      batteryHeatHint: "Accu start",
      climateExtraLabels: {
        driver_seat_heating: "Stoel best. verw.",
        driver_seat_ventilation: "Stoel best. vent.",
        passenger_seat_heating: "Stoel pass. verw.",
        passenger_seat_ventilation: "Stoel pass. vent.",
        rear_left_seat_heating: "Stoel A-L verw.",
        rear_left_seat_ventilation: "Stoel A-L vent.",
        rear_right_seat_heating: "Stoel A-R verw.",
        rear_right_seat_ventilation: "Stoel A-R vent.",
        rear_window_heating: "Achterruit",
        windshield_defrost: "Voorruit ontdooien",
        windshield_defog: "Voorruit ontwasemen",
        steering_wheel_heating: "Stuurverwarming",
      },
      tpmsLabels: { front_left: "LV", front_right: "RV", rear_left: "LA", rear_right: "RA" },
      options: {
        departure_climate_mode: { at_home: "Alleen thuis", anywhere: "Overal", off: "Uitgeschakeld" },
        charge_days: {
          all_days: "Elke dag",
          weekdays: "Ma–Vr",
          weekend: "Weekend",
          mon_wed_fri: "Ma / Wo / Vr",
          tue_thu_sat: "Di / Do / Za",
          custom: "Aangepast",
        },
      },
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

  function requiresConfirmation(actionId) {
    return Boolean(CONFIRM_ACTIONS[String(actionId || "")]);
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

  function parseOutcomeTsMs(raw) {
    if (raw == null || raw === "") return NaN;
    if (typeof raw === "number") return isFinite(raw) ? raw : NaN;
    var parsed = Date.parse(String(raw));
    return isNaN(parsed) ? NaN : parsed;
  }

  function isDeadStateObj(s) {
    if (!s || s.state == null) return true;
    var st = String(s.state).trim();
    return !st || st === "unavailable" || st === "unknown";
  }

  function formatCommandOutcome(cmdStateObj, localFeedback, lang) {
    var code = String(lang || "en").slice(0, 2).toLowerCase();
    var resolvedLang = I18N[code] ? code : "en";
    var t = getTexts(resolvedLang);
    var cmdAlive = !isDeadStateObj(cmdStateObj);
    var hasLocal = Boolean(localFeedback && typeof localFeedback === "object" && typeof localFeedback.ok === "boolean");
    if (!cmdAlive && !hasLocal) return null;

    var cmdRawTs = cmdAlive ? (cmdStateObj.last_changed || cmdStateObj.last_updated || null) : null;
    var cmdMs = parseOutcomeTsMs(cmdRawTs);
    var fbRawTs = hasLocal && localFeedback.ts != null ? localFeedback.ts : null;
    var fbMs = parseOutcomeTsMs(fbRawTs);

    var useLocal = false;
    if (hasLocal) {
      if (!cmdAlive) {
        useLocal = true;
      } else if (!isNaN(fbMs)) {
        useLocal = isNaN(cmdMs) || fbMs >= cmdMs;
      }
    }

    var ok;
    var chosenTs;
    if (useLocal) {
      ok = Boolean(localFeedback.ok);
      chosenTs = fbRawTs;
    } else {
      var rawState = String(cmdStateObj.state || "");
      var lowerState = rawState.toLowerCase();
      var isErr = false;
      for (var i = 0; i < CMD_ERROR_PATTERNS.length; i += 1) {
        if (lowerState.indexOf(CMD_ERROR_PATTERNS[i]) >= 0) {
          isErr = true;
          break;
        }
      }
      ok = !isErr;
      chosenTs = cmdRawTs;
    }

    var prefix = ok ? t.lastCommand : t.commandSendError;
    var glyph = ok ? "✓" : "✕";
    var timeStr = chosenTs != null ? formatTimestamp(chosenTs, resolvedLang) : "—";
    var text = (timeStr && timeStr !== "—")
      ? prefix + " · " + timeStr + " " + glyph
      : prefix + " " + glyph;
    return { text: text, ok: ok };
  }

  var SVG_PATHS = {
    overview: '<rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="8" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/>',
    climate: '<path d="M12 12c0-3 2.5-5 5-5 1.8 0 3 1.2 3 3 0 2.2-2 3.5-5 3.5"/><path d="M12 12c3 0 5 2.5 5 5 0 1.8-1.2 3-3 3-2.2 0-3.5-2-3.5-5"/><path d="M12 12c0 3-2.5 5-5 5-1.8 0-3-1.2-3-3 0-2.2 2-3.5 5-3.5"/><path d="M12 12c-3 0-5-2.5-5-5 0-1.8 1.2-3 3-3 2.2 0 3.5 2 3.5 5"/><circle cx="12" cy="12" r="1.5"/>',
    charging: '<polygon points="13 2 4 14 11 14 10 22 20 10 13 10 13 2"/>',
    security: '<path d="M12 21s7-3.6 7-9.5V5.5L12 3 5 5.5v6C5 17.4 12 21 12 21z"/><path d="M9.5 12l1.8 1.8L15 10"/>',
    battery: '<rect x="2" y="7" width="17" height="10" rx="2"/><line x1="22" y1="10" x2="22" y2="14"/><polygon points="11 9.5 8 12.5 10.5 12.5 9.5 15 13 11.5 10.5 11.5 11 9.5"/>',
    bolt: '<polygon points="13 2 4 14 11 14 10 22 20 10 13 10 13 2"/>',
    route: '<circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="6" r="2.5"/><path d="M8.5 18H14a3 3 0 0 0 0-6H10a3 3 0 0 1 0-6h5.5"/>',
    gauge: '<path d="M4.5 17.5A9 9 0 1 1 19.5 17.5"/><line x1="12" y1="13" x2="16" y2="9"/><circle cx="12" cy="13" r="1.5"/>',
    plug: '<path d="M9 3v4"/><path d="M15 3v4"/><path d="M7 7h10v4a5 5 0 0 1-10 0V7z"/><path d="M12 16v5"/>',
    clock: '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 14"/>',
    volt: '<path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z"/>',
    current: '<polyline points="3 12 7 12 10 5 14 19 17 12 21 12"/>',
    home: '<path d="M3 10.5L12 3l9 7.5"/><path d="M5 9.5V20h14V9.5"/><path d="M9.5 20v-5.5h5V20"/>',
    pin: '<path d="M12 21s-6-5.2-6-10.5a6 6 0 1 1 12 0C18 15.8 12 21 12 21z"/><circle cx="12" cy="10.5" r="2"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    unlock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 7.6-1.7"/>',
    fan: '<path d="M12 12c0-3 2.5-5 5-5 1.8 0 3 1.2 3 3 0 2.2-2 3.5-5 3.5"/><path d="M12 12c3 0 5 2.5 5 5 0 1.8-1.2 3-3 3-2.2 0-3.5-2-3.5-5"/><path d="M12 12c0 3-2.5 5-5 5-1.8 0-3-1.2-3-3 0-2.2 2-3.5 5-3.5"/><path d="M12 12c-3 0-5-2.5-5-5 0-1.8 1.2-3 3-3 2.2 0 3.5 2 3.5 5"/><circle cx="12" cy="12" r="1.5"/>',
    snow: '<line x1="12" y1="3" x2="12" y2="21"/><line x1="4.2" y1="7.5" x2="19.8" y2="16.5"/><line x1="19.8" y1="7.5" x2="4.2" y2="16.5"/>',
    flame: '<path d="M12 3c2.5 3 5 5.8 5 9.5a5 5 0 1 1-10 0c0-2.4 1.3-4.6 3-6.5.2 1.8 1.2 2.8 2 3.2.2-2.2 0-4.2 0-6.2z"/>',
    trunk: '<path d="M3 16h14l2-4.5L15 8H6L3 12v4z"/><circle cx="7" cy="17.5" r="2"/><circle cx="16.5" cy="17.5" r="2"/><path d="M17 9.5L21 6"/>',
    lights: '<path d="M9 7h4a5 5 0 0 1 0 10H9V7z"/><line x1="3" y1="9" x2="6" y2="9"/><line x1="3" y1="12" x2="6" y2="12"/><line x1="3" y1="15" x2="6" y2="15"/>',
    wake: '<path d="M12 3v7"/><path d="M7.1 5.6a8 8 0 1 0 9.8 0"/>',
    refresh: '<polyline points="20 5 20 10 15 10"/><path d="M19.5 14a7.5 7.5 0 1 1-1.8-6.4L20 10"/>',
    gps: '<circle cx="12" cy="12" r="6"/><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/>',
    shield: '<path d="M12 21s7-3.6 7-9.5V5.5L12 3 5 5.5v6C5 17.4 12 21 12 21z"/>',
    seat: '<path d="M7 4l2 10h8l2 5"/><path d="M6 17h9"/><circle cx="7" cy="4" r="1"/>',
    windshield: '<path d="M4 16L7 7h10l3 9H4z"/><path d="M9 19c.8-.9.8-2.1 0-3"/><path d="M15 19c.8-.9.8-2.1 0-3"/>',
    rear_defrost: '<rect x="4" y="6" width="16" height="10" rx="2"/><path d="M8.5 19c.8-.9.8-2.1 0-3"/><path d="M12 19c.8-.9.8-2.1 0-3"/><path d="M15.5 19c.8-.9.8-2.1 0-3"/>',
    steering: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="2"/><line x1="4.5" y1="10" x2="10" y2="11.5"/><line x1="19.5" y1="10" x2="14" y2="11.5"/><line x1="12" y1="14" x2="12" y2="20"/>',
    window: '<rect x="4" y="5" width="16" height="14" rx="2"/><line x1="4" y1="12" x2="20" y2="12"/>',
    sunroof: '<path d="M4 15h16"/><path d="M6 15l3-6h8l1 3"/>',
    tire: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3.2"/><line x1="12" y1="3.5" x2="12" y2="8.8"/><line x1="12" y1="15.2" x2="12" y2="20.5"/><line x1="3.5" y1="12" x2="8.8" y2="12"/><line x1="15.2" y1="12" x2="20.5" y2="12"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="8" y1="3" x2="8" y2="7"/><line x1="16" y1="3" x2="16" y2="7"/>',
    check: '<polyline points="4 12.5 9.5 18 20 6"/>',
    alert: '<path d="M12 3L2.5 19.5h19L12 3z"/><line x1="12" y1="10" x2="12" y2="14"/><circle cx="12" cy="17" r="0.8"/>',
    thermometer: '<path d="M14 14.8V5a2 2 0 1 0-4 0v9.8a3.5 3.5 0 1 0 4 0z"/>',
    minus: '<line x1="5" y1="12" x2="19" y2="12"/>',
    plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  };

  function svgIcon(name, cls) {
    var body = SVG_PATHS[String(name || "")] || '<circle cx="12" cy="12" r="4"/>';
    var clsAttr = "lp-ico" + (cls ? " " + escapeHtml(cls) : "");
    return '<svg class="' + clsAttr + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + body + "</svg>";
  }

  function formatMetric(s, lang) {
    if (!s || s.state == null) return "—";
    var rawStr = String(s.state).trim();
    if (!rawStr || rawStr === "unavailable" || rawStr === "unknown") return "—";
    var u = (s.attributes && s.attributes.unit_of_measurement) ? String(s.attributes.unit_of_measurement) : "";
    var n = Number(rawStr);
    if (isNaN(n) || !isFinite(n)) return u ? rawStr + " " + u : rawStr;

    var dp = (s.attributes && typeof s.attributes.suggested_display_precision === "number")
      ? s.attributes.suggested_display_precision
      : null;
    var v;
    if (dp !== null && dp >= 0 && !(dp === 0 && (u === "km" || u === "mi" || u === "min" || u === "%" || u === "W"))) {
      v = n.toFixed(dp);
    } else if (u === "km" || u === "mi" || u === "min" || u === "%" || u === "W") {
      v = String(Math.round(n));
    } else if (u === "bar") {
      v = n.toFixed(2);
    } else if (u === "kWh" || u === "Wh" || u === "MWh") {
      v = String(Math.round(n * 100) / 100);
    } else if (u === "°C" || u === "°F" || u === "A" || u === "kW") {
      v = String(Math.round(n * 10) / 10);
    } else if (Number.isInteger(n)) {
      v = String(n);
    } else {
      v = String(Math.round(n * 100) / 100);
    }
    return u ? v + " " + u : v;
  }

  function translateOption(kind, val, lang) {
    var code = String(lang || "en").slice(0, 2).toLowerCase();
    var dict = I18N[code] || I18N.en;
    var key = String(val == null ? "" : val);
    if (dict && dict.options && dict.options[kind] && Object.prototype.hasOwnProperty.call(dict.options[kind], key)) {
      return dict.options[kind][key];
    }
    if (I18N.en && I18N.en.options && I18N.en.options[kind] && Object.prototype.hasOwnProperty.call(I18N.en.options[kind], key)) {
      return I18N.en.options[kind][key];
    }
    return key;
  }

  function normalizeDaysList(raw) {
    if (!Array.isArray(raw)) return null;
    var seen = Object.create(null);
    var out = [];
    for (var i = 0; i < raw.length; i += 1) {
      var n = parseInt(raw[i], 10);
      if (n >= 1 && n <= 7 && !seen[n]) {
        seen[n] = true;
        out.push(n);
      }
    }
    out.sort(function (a, b) { return a - b; });
    return out.length ? out : null;
  }

  function presetDaysForKey(key) {
    var k = String(key || "");
    if (!Object.prototype.hasOwnProperty.call(CHARGE_DAY_PRESETS, k)) return null;
    return CHARGE_DAY_PRESETS[k].slice();
  }

  function presetForDays(days) {
    var norm = normalizeDaysList(days);
    if (!norm) return "custom";
    var keys = Object.keys(CHARGE_DAY_PRESETS);
    for (var i = 0; i < keys.length; i += 1) {
      var preset = CHARGE_DAY_PRESETS[keys[i]];
      if (preset.length === norm.length && preset.join(",") === norm.join(",")) {
        return keys[i];
      }
    }
    return "custom";
  }

  function computeToggleDays(days, dayNum) {
    var cur = normalizeDaysList(days) || [];
    var d = parseInt(dayNum, 10);
    if (!(d >= 1 && d <= 7)) {
      return cur.length ? cur : [1, 2, 3, 4, 5, 6, 7];
    }
    var idx = cur.indexOf(d);
    if (idx >= 0) {
      if (cur.length <= 1) return cur.slice();
      return cur.filter(function (x) { return x !== d; });
    }
    return cur.concat([d]).sort(function (a, b) { return a - b; });
  }

  function formatCarNextDeparture(orario, giorni, now, t) {
    var m = /^(\d{1,2}):(\d{2})$/.exec(String(orario || "").trim());
    if (!m) return orario ? String(orario) : "";
    var hh = parseInt(m[1], 10);
    var mm = parseInt(m[2], 10);
    if (hh < 0 || hh > 23 || mm < 0 || mm > 59) return String(orario);
    var hhmm = ("0" + hh).slice(-2) + ":" + m[2];
    var normDays = normalizeDaysList(giorni);
    if (!normDays) return hhmm;
    var ref = now instanceof Date && !isNaN(now.getTime()) ? now : new Date();
    var isoToday = ref.getDay() === 0 ? 7 : ref.getDay();
    var nowMin = ref.getHours() * 60 + ref.getMinutes();
    var depMin = hh * 60 + mm;
    for (var delta = 0; delta <= 7; delta += 1) {
      var wd = ((isoToday - 1 + delta) % 7) + 1;
      if (normDays.indexOf(wd) < 0) continue;
      if (delta === 0 && depMin <= nowMin) continue;
      if (delta === 0) return t.today + " " + hhmm;
      if (delta === 1) return t.tomorrow + " " + hhmm;
      var dLbl = (t.dayNames && t.dayNames[DAY_SLUGS[wd - 1]]) ? t.dayNames[DAY_SLUGS[wd - 1]] : DAY_SLUGS[wd - 1];
      return dLbl + " " + hhmm;
    }
    return hhmm;
  }

  // Filter strictly against the 12-key allowlist so untrusted attributes cannot reach the DOM.
  function filterAllowedClimateExtras(raw) {
    if (!Array.isArray(raw)) return [];
    var seen = Object.create(null);
    var out = [];
    for (var i = 0; i < raw.length; i += 1) {
      if (typeof raw[i] !== "string") continue;
      var key = raw[i].trim();
      if (!Object.prototype.hasOwnProperty.call(CLIMATE_EXTRA_META, key) || seen[key]) continue;
      seen[key] = true;
      out.push(key);
    }
    return out;
  }

  function computeToggleClimateExtras(currentExtras, toggleKey) {
    var cur = filterAllowedClimateExtras(currentExtras);
    if (!Object.prototype.hasOwnProperty.call(CLIMATE_EXTRA_META, toggleKey)) {
      return cur;
    }
    if (cur.indexOf(toggleKey) >= 0) {
      return cur.filter(function (k) { return k !== toggleKey; });
    }
    var opposite = CLIMATE_EXTRA_META[toggleKey].opposite;
    var next = opposite ? cur.filter(function (k) { return k !== opposite; }) : cur.slice();
    next.push(toggleKey);
    return next;
  }

  function buildStyles() {
    return [
      ":host {",
      "  display: block;",
      "  container-type: inline-size;",
      "  overflow-anchor: none;",
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
      ".lp-ico { width: 16px; height: 16px; flex-shrink: 0; display: block; }",
      ".tab-ico { width: 18px; height: 18px; }",
      ".kpi-ico, .sec-ico, .stat-ico, .meta-ico, .tpms-ico { width: 14px; height: 14px; color: var(--lp-text-secondary); }",
      ".btn-ico { width: 16px; height: 16px; }",
      "ha-card { display: block; width: 100%; background: var(--lp-canvas); border: 1px solid var(--lp-border); border-radius: 16px; overflow: hidden; overflow-anchor: none; color: var(--lp-text); box-shadow: none; }",
      ".cockpit-grid { display: flex; flex-direction: column; gap: 10px; padding: 10px; }",
      ".hero-region { display: flex; flex-direction: column; gap: 8px; }",
      ".hero-card { border-radius: 12px; overflow: hidden; background: var(--lp-surface); border: 1px solid var(--lp-border); display: flex; flex-direction: column; }",
      ".hero-stage { position: relative; aspect-ratio: 2 / 1; width: 100%; background: #14171D; overflow: hidden; }",
      ".hero-img { width: 100%; height: 100%; object-fit: contain; display: block; pointer-events: none; }",
      ".hero-overlay-top { position: absolute; top: 10px; left: 10px; right: 10px; display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; pointer-events: none; z-index: 1; }",
      ".hero-overlay-top .status-pill, .hero-overlay-top .soc-btn { pointer-events: auto; }",
      ".status-pill { display: inline-flex; align-items: center; gap: 7px; padding: 5px 10px; min-height: 30px; border-radius: 999px; background: rgba(17, 19, 23, 0.82); border: 1px solid var(--lp-border); -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px); font-size: 0.74rem; font-weight: 600; color: var(--lp-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 72%; }",
      ".status-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; background: var(--lp-text-muted); }",
      ".status-dot.is-online { background: var(--lp-emerald); }",
      ".status-dot.is-offline { background: var(--lp-coral); }",
      ".soc-btn { position: relative; width: 54px; height: 54px; padding: 0; border-radius: 999px; border: 1px solid var(--lp-border); background: rgba(17, 19, 23, 0.84); -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px); display: inline-flex; align-items: center; justify-content: center; cursor: pointer; flex-shrink: 0; }",
      ".soc-btn.is-charging { border-color: rgba(52, 211, 153, 0.48); }",
      ".soc-btn svg.soc-svg { position: absolute; inset: 2px; width: 48px; height: 48px; transform: rotate(-90deg); }",
      ".soc-ring-bg { fill: none; stroke: rgba(255, 255, 255, 0.12); stroke-width: 3.2; }",
      ".soc-ring-fg { fill: none; stroke: var(--lp-emerald); stroke-width: 3.2; stroke-linecap: round; }",
      ".soc-ring-fg.is-warn { stroke: var(--lp-amber); }",
      ".soc-ring-fg.is-low { stroke: var(--lp-coral); }",
      ".soc-val { position: relative; font-size: 0.78rem; font-weight: 700; color: var(--lp-text); line-height: 1; }",
      ".soc-chg-ico { position: absolute; bottom: 4px; display: inline-flex; color: var(--lp-emerald); pointer-events: none; }",
      ".soc-chg-ico .lp-ico { width: 10px; height: 10px; }",
      ".hero-meta { padding: 12px 14px; border-top: 1px solid var(--lp-border); background: var(--lp-surface); display: flex; flex-direction: column; gap: 3px; }",
      ".hero-meta[data-device] { cursor: pointer; }",
      ".hero-meta-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-width: 0; }",
      ".hero-title { font-size: 1.24rem; font-weight: 700; letter-spacing: -0.015em; line-height: 1.2; color: var(--lp-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }",
      ".hero-sub { font-size: 0.8rem; color: var(--lp-text-secondary); min-height: 1.2em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }",
      ".warns-row { display: flex; flex-wrap: wrap; gap: 6px; }",
      ".warn-chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; min-height: 34px; border-radius: 8px; background: rgba(239, 68, 68, 0.14); border: 1px solid rgba(239, 68, 68, 0.32); color: #FCA5A5; font-size: 0.78rem; font-weight: 600; cursor: pointer; }",
      ".warn-chip.is-amber { background: rgba(245, 158, 11, 0.14); border-color: rgba(245, 158, 11, 0.32); color: #FCD34D; }",
      ".error-banner { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 8px 12px; border-radius: 10px; background: rgba(239, 68, 68, 0.16); border: 1px solid rgba(239, 68, 68, 0.4); color: #FECACA; font-size: 0.82rem; }",
      ".error-dismiss { background: transparent; border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 6px; min-width: 32px; min-height: 32px; padding: 2px 8px; cursor: pointer; }",
      ".tabs-bar { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 4px; padding: 4px; background: var(--lp-surface); border: 1px solid var(--lp-border); border-radius: 12px; }",
      ".tab-btn { position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px; min-height: 50px; min-width: 44px; border: 1px solid transparent; border-radius: 9px; background: transparent; color: var(--lp-text-secondary); font-size: 0.74rem; font-weight: 600; cursor: pointer; padding: 6px 4px 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }",
      ".tab-btn:hover { color: var(--lp-text); background: rgba(255, 255, 255, 0.04); }",
      ".tab-btn.is-active, .tab-btn[aria-selected=\"true\"] { background: #262B34; color: var(--lp-text); border-color: rgba(255, 255, 255, 0.16); font-weight: 700; }",
      ".tab-btn.is-active::after, .tab-btn[aria-selected=\"true\"]::after { content: \"\"; position: absolute; left: 22%; right: 22%; bottom: 3px; height: 2.5px; border-radius: 999px; background: #E5E7EB; }",
      ".tab-lbl { max-width: 100%; overflow: hidden; text-overflow: ellipsis; line-height: 1.1; }",
      ".panel { display: none; flex-direction: column; gap: 10px; }",
      ".panel.is-active { display: flex; }",
      ".surface { background: var(--lp-surface); border: 1px solid var(--lp-border); border-radius: 12px; padding: 12px; display: flex; flex-direction: column; gap: 10px; }",
      ".sec-hdr { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-size: 0.76rem; font-weight: 600; color: var(--lp-text-muted); letter-spacing: 0.02em; }",
      ".sec-hdr-title { display: inline-flex; align-items: center; gap: 6px; min-width: 0; }",
      ".sec-subhdr { font-size: 0.72rem; font-weight: 600; color: var(--lp-text-secondary); display: flex; align-items: center; gap: 6px; padding-top: 2px; }",
      ".metrics-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }",
      ".metric-card { background: var(--lp-surface); border: 1px solid var(--lp-border); border-radius: 12px; padding: 11px 12px; cursor: pointer; display: flex; flex-direction: column; gap: 4px; min-height: 72px; }",
      ".metric-card:hover { background: var(--lp-elevated); border-color: var(--lp-border-strong); }",
      ".metric-hdr { display: inline-flex; align-items: center; gap: 6px; min-width: 0; }",
      ".metric-lbl { font-size: 0.74rem; color: var(--lp-text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }",
      ".metric-val { font-size: 1.08rem; font-weight: 700; color: var(--lp-text); line-height: 1.25; }",
      ".metric-bar { height: 3px; border-radius: 999px; background: rgba(255, 255, 255, 0.08); overflow: hidden; margin-top: 2px; }",
      ".metric-bar-fill { height: 100%; background: var(--lp-emerald); border-radius: 999px; }",
      ".btn-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }",
      ".btn-triple { display: grid; grid-template-columns: repeat(auto-fit, minmax(92px, 1fr)); gap: 8px; }",
      ".btn-row { display: flex; flex-wrap: wrap; gap: 8px; }",
      ".ctrl-btn { position: relative; overflow: hidden; min-height: 44px; min-width: 44px; padding: 8px 12px; border-radius: 10px; background: var(--lp-elevated); border: 1px solid var(--lp-border); color: var(--lp-text); font-size: 0.82rem; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 6px; text-align: center; }",
      ".ctrl-btn:hover { background: var(--lp-elevated-hover); border-color: var(--lp-border-strong); }",
      ".ctrl-btn:disabled, .ctrl-btn.is-pending { opacity: 0.58; cursor: wait; }",
      ".ctrl-btn.is-primary { background: #262B34; color: var(--lp-text); border-color: rgba(52, 211, 153, 0.55); }",
      ".ctrl-btn.is-primary:hover { background: #2A313D; border-color: var(--lp-emerald); }",
      ".ctrl-btn.is-emerald { border-color: rgba(52, 211, 153, 0.45); color: var(--lp-emerald); background: rgba(52, 211, 153, 0.12); }",
      ".ctrl-btn.is-glacier { border-color: rgba(96, 165, 250, 0.45); color: var(--lp-glacier); background: rgba(96, 165, 250, 0.12); }",
      ".ctrl-btn.is-amber { border-color: rgba(245, 158, 11, 0.45); color: var(--lp-amber); background: rgba(245, 158, 11, 0.12); }",
      ".btn-compact { min-height: 40px; padding: 7px 8px; font-size: 0.76rem; }",
      ".stepper { display: flex; align-items: center; justify-content: space-between; gap: 8px; background: var(--lp-elevated); border: 1px solid var(--lp-border); border-radius: 10px; padding: 4px; }",
      ".step-val { font-size: 1.15rem; font-weight: 700; color: var(--lp-text); }",
      ".chip-row { display: flex; flex-wrap: wrap; gap: 6px; }",
      ".chip-btn { min-height: 44px; min-width: 44px; padding: 6px 11px; border-radius: 9px; background: var(--lp-elevated); border: 1px solid var(--lp-border); font-size: 0.8rem; font-weight: 600; color: var(--lp-text-secondary); cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 4px; }",
      ".chip-btn:hover { background: var(--lp-elevated-hover); color: var(--lp-text); }",
      ".chip-btn.is-active { background: #2A313D; color: var(--lp-text); border-color: rgba(243, 244, 246, 0.55); }",
      ".seat-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }",
      ".seat-card { background: var(--lp-elevated); border: 1px solid var(--lp-border); border-radius: 10px; padding: 8px; display: flex; flex-direction: column; gap: 6px; }",
      ".seat-name { font-size: 0.76rem; font-weight: 600; color: var(--lp-text-secondary); }",
      ".seat-btns { display: flex; gap: 6px; }",
      ".seat-btns .ctrl-btn { flex: 1; padding: 6px; font-size: 0.76rem; }",
      ".seat-readonly { background: var(--lp-elevated); border: 1px solid var(--lp-border); border-radius: 10px; padding: 8px 10px; display: flex; align-items: center; justify-content: space-between; font-size: 0.78rem; color: var(--lp-text-secondary); }",
      ".flow-track { position: relative; height: 4px; border-radius: 999px; background: rgba(52, 211, 153, 0.14); overflow: hidden; }",
      ".flow-bar { position: absolute; top: 0; bottom: 0; width: 42%; border-radius: 999px; background: linear-gradient(90deg, transparent, var(--lp-emerald), transparent); }",
      ".chg-stats-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }",
      ".chg-stat { background: var(--lp-elevated); border: 1px solid var(--lp-border); border-radius: 9px; padding: 8px 10px; display: flex; flex-direction: column; gap: 2px; min-height: 54px; }",
      ".chg-stat-lbl { display: inline-flex; align-items: center; gap: 5px; font-size: 0.7rem; color: var(--lp-text-secondary); }",
      ".chg-stat-val { font-size: 0.88rem; font-weight: 700; color: var(--lp-text); }",
      ".seg-switch { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px; padding: 4px; border-radius: 10px; background: var(--lp-canvas); border: 1px solid var(--lp-border); }",
      ".seg-btn { min-height: 40px; border: 1px solid transparent; border-radius: 7px; background: transparent; color: var(--lp-text-secondary); font-size: 0.78rem; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 6px 8px; }",
      ".seg-btn:hover { color: var(--lp-text); }",
      ".seg-btn.is-active { background: #262B34; color: var(--lp-text); border-color: rgba(255, 255, 255, 0.16); font-weight: 700; }",
      ".manual-charge-box { display: flex; flex-direction: column; gap: 10px; }",
      ".departure-charge-box { background: var(--lp-elevated); border: 1px solid rgba(52, 211, 153, 0.34); border-radius: 10px; padding: 10px 12px; display: flex; flex-direction: column; gap: 4px; }",
      ".dep-charge-title { display: inline-flex; align-items: center; gap: 6px; font-size: 0.78rem; font-weight: 700; color: var(--lp-emerald); }",
      ".dep-charge-val { font-size: 0.84rem; color: var(--lp-text); font-weight: 600; }",
      ".timeline-track { position: relative; height: 14px; border-radius: 7px; background: var(--lp-elevated); border: 1px solid var(--lp-border); overflow: hidden; }",
      ".timeline-seg { position: absolute; top: 0; bottom: 0; background: var(--lp-emerald); opacity: 0.85; border-radius: 4px; }",
      ".timeline-axis { display: flex; justify-content: space-between; font-size: 0.68rem; color: var(--lp-text-muted); margin-top: 3px; }",
      ".field-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; min-height: 44px; }",
      ".field-lbl { font-size: 0.82rem; color: var(--lp-text-secondary); }",
      ".ctrl-input, .ctrl-select { min-height: 44px; padding: 6px 10px; border-radius: 9px; background: var(--lp-elevated); border: 1px solid var(--lp-border); color: var(--lp-text); font-size: 0.84rem; }",
      '.ctrl-input[type="time"] { caret-color: transparent; user-select: none; cursor: pointer; }',
      ".charge-days-strip { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; }",
      ".charge-day-chip { min-height: 44px; min-width: 0; padding: 4px 2px; border-radius: 9px; font-size: 0.78rem; font-weight: 700; }",
      ".charge-day-chip.is-active { background: #2A313D; color: var(--lp-emerald); border-color: rgba(52, 211, 153, 0.55); }",
      ".preset-row { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }",
      ".preset-btn { min-height: 38px; padding: 4px 8px; font-size: 0.76rem; }",
      ".preset-btn.is-active { background: #262B34; color: var(--lp-text); border-color: rgba(255, 255, 255, 0.24); }",
      ".days-strip { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; }",
      ".day-chip { min-height: 52px; min-width: 36px; border-radius: 9px; border: 1px solid var(--lp-border); background: var(--lp-elevated); color: var(--lp-text-secondary); font-size: 0.78rem; font-weight: 700; cursor: pointer; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; padding: 4px 2px; }",
      ".day-chip.is-enabled { border-color: rgba(52, 211, 153, 0.48); color: var(--lp-text); }",
      ".day-chip.is-expanded { background: #2A313D; color: var(--lp-text); border-color: rgba(243, 244, 246, 0.65); }",
      ".day-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--lp-text-muted); }",
      ".day-chip.is-enabled .day-dot { background: var(--lp-emerald); }",
      ".day-time { font-size: 0.62rem; font-weight: 600; color: var(--lp-text-secondary); line-height: 1; min-height: 0.75em; }",
      ".day-chip.is-enabled .day-time { color: var(--lp-emerald); }",
      ".day-editor { background: var(--lp-elevated); border: 1px solid var(--lp-border-strong); border-radius: 10px; padding: 10px; display: flex; flex-direction: column; gap: 8px; }",
      ".dep-hdr-badges { display: inline-flex; align-items: center; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }",
      ".dep-summary { background: var(--lp-elevated); border: 1px solid var(--lp-border); border-radius: 9px; overflow: hidden; }",
      ".dep-summary-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 7px 10px; min-height: 36px; cursor: pointer; font-size: 0.81rem; }",
      ".dep-summary-row + .dep-summary-row { border-top: 1px solid var(--lp-border); }",
      ".dep-summary-row:hover { background: var(--lp-elevated-hover); }",
      ".dep-subbox { border-top: 1px solid var(--lp-border); padding-top: 8px; display: flex; flex-direction: column; gap: 6px; }",
      ".climate-extras-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }",
      ".climate-extra-chip { width: 100%; justify-content: flex-start; text-align: left; font-size: 0.75rem; line-height: 1.2; padding: 6px 8px; }",
      ".chip-btn.is-pending { opacity: 0.58; cursor: wait; }",
      ".climate-extra-chip.is-active { background: #2A313D; color: var(--lp-emerald); border-color: rgba(52, 211, 153, 0.55); }",
      ".bp-stage { display: grid; grid-template-columns: minmax(88px, 1fr) minmax(108px, 124px) minmax(88px, 1fr); gap: 8px; align-items: center; }",
      ".tpms-col { display: flex; flex-direction: column; justify-content: space-between; gap: 24px; }",
      ".tpms-box { background: var(--lp-elevated); border: 1px solid var(--lp-border); border-radius: 9px; padding: 7px 8px; cursor: pointer; display: flex; flex-direction: column; gap: 2px; min-height: 54px; }",
      ".tpms-box.is-ok { border-color: rgba(52, 211, 153, 0.35); }",
      ".tpms-box.is-alert { border-color: rgba(239, 68, 68, 0.72); background: rgba(239, 68, 68, 0.14); color: #FECACA; }",
      ".tpms-hdr { display: inline-flex; align-items: center; gap: 4px; font-size: 0.65rem; font-weight: 700; letter-spacing: 0.03em; white-space: nowrap; color: var(--lp-text-secondary); }",
      ".tpms-box.is-alert .tpms-hdr { color: #FECACA; }",
      ".tpms-press { font-size: 0.82rem; font-weight: 700; color: var(--lp-text); }",
      ".tpms-temp { font-size: 0.72rem; color: var(--lp-text-secondary); }",
      ".bp-svg { width: 100%; max-width: 130px; height: auto; display: block; margin: 0 auto; }",
      ".bp-body { fill: var(--lp-elevated); stroke: rgba(255, 255, 255, 0.24); stroke-width: 1.5; }",
      ".bp-glass { fill: rgba(17, 19, 23, 0.75); stroke: rgba(255, 255, 255, 0.2); stroke-width: 1; }",
      ".bp-part { fill: rgba(255, 255, 255, 0.08); stroke: rgba(255, 255, 255, 0.34); stroke-width: 1.4; }",
      ".bp-part.is-open { fill: rgba(245, 158, 11, 0.35); stroke: var(--lp-amber); }",
      ".bp-part.is-window-open { fill: rgba(96, 165, 250, 0.35); stroke: var(--lp-glacier); }",
      ".bp-part.is-moving { fill: rgba(96, 165, 250, 0.45); stroke: var(--lp-glacier); }",
      ".bp-headlights { fill: rgba(243, 244, 246, 0.14); stroke: rgba(243, 244, 246, 0.35); stroke-width: 1; }",
      ".bp-headlights.is-on { fill: rgba(245, 158, 11, 0.65); stroke: var(--lp-amber); }",
      ".bp-lock-badge { fill: rgba(17, 19, 23, 0.9); stroke: var(--lp-emerald); stroke-width: 1.3; }",
      ".bp-lock-badge.is-unlocked { stroke: var(--lp-amber); }",
      ".bp-door-fl.is-open { transform: translate(-6px, 0) rotate(-18deg); transform-origin: 48px 98px; }",
      ".bp-door-fr.is-open { transform: translate(6px, 0) rotate(18deg); transform-origin: 112px 98px; }",
      ".bp-door-rl.is-open { transform: translate(-6px, 0) rotate(-18deg); transform-origin: 48px 148px; }",
      ".bp-door-rr.is-open { transform: translate(6px, 0) rotate(18deg); transform-origin: 112px 148px; }",
      ".footer-bar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; font-size: 0.76rem; color: var(--lp-text-secondary); }",
      ".meta-inline { display: inline-flex; align-items: center; gap: 6px; }",
      ".badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 600; background: var(--lp-elevated); border: 1px solid var(--lp-border); color: var(--lp-text-secondary); }",
      ".badge.is-emerald { border-color: rgba(52, 211, 153, 0.4); color: var(--lp-emerald); background: rgba(52, 211, 153, 0.1); }",
      ".badge.is-glacier { border-color: rgba(96, 165, 250, 0.4); color: var(--lp-glacier); background: rgba(96, 165, 250, 0.1); }",
      ".badge.is-amber { border-color: rgba(245, 158, 11, 0.4); color: var(--lp-amber); background: rgba(245, 158, 11, 0.1); }",
      ".badge.is-coral { border-color: rgba(239, 68, 68, 0.45); color: #FCA5A5; background: rgba(239, 68, 68, 0.14); }",
      ".confirm-dialog { padding: 0; border: 1px solid var(--lp-border-strong); border-radius: 14px; background: var(--lp-surface); color: var(--lp-text); width: min(360px, calc(100vw - 32px)); max-width: 100%; margin: auto; box-shadow: 0 20px 48px rgba(0, 0, 0, 0.56); }",
      ".confirm-dialog[open] { display: flex; flex-direction: column; position: fixed; inset: 0; margin: auto; z-index: 999; }",
      "dialog:modal { overscroll-behavior: contain; }",
      "dialog::backdrop { overflow: hidden; overscroll-behavior: contain; background: rgba(10, 12, 16, 0.72); -webkit-backdrop-filter: blur(4px); backdrop-filter: blur(4px); }",
      ".confirm-dialog-body { padding: 16px; display: flex; flex-direction: column; gap: 8px; }",
      ".confirm-dialog-title { margin: 0; font-size: 1rem; font-weight: 700; color: var(--lp-text); }",
      ".confirm-dialog-action { margin: 0; font-size: 0.92rem; font-weight: 600; color: var(--lp-emerald); }",
      ".confirm-dialog-hint { margin: 0; font-size: 0.8rem; color: var(--lp-text-secondary); line-height: 1.35; }",
      ".confirm-dialog-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }",
      ".confirm-dialog-actions .ctrl-btn { flex: 1; }",
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
      "  .bp-part.is-moving { animation: lp-pulse-soft 1.2s ease-in-out infinite alternate; }",
      "  .soc-btn.is-charging .soc-ring-fg { animation: lp-pulse-soft 1.8s ease-in-out infinite alternate; }",
      "  .ctrl-btn.is-spinning .lp-ico { animation: lp-spin 2.4s linear infinite; }",
      "  .flow-bar { animation: lp-flow 1.4s linear infinite; }",
      "}",
      "@media (prefers-reduced-motion: reduce) {",
      "  *, *::before, *::after { animation: none !important; transition: none !important; }",
      "}",
      "button:focus-visible, input:focus-visible, select:focus-visible, [role=\"button\"]:focus-visible { outline: 2px solid rgba(243, 244, 246, 0.72); outline-offset: -2px; }",
      "@keyframes lp-fade { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; transform: translateY(0); } }",
      "@keyframes lp-pulse-soft { from { opacity: 0.45; } to { opacity: 0.95; } }",
      "@keyframes lp-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }",
      "@keyframes lp-flow { from { transform: translateX(-100%); } to { transform: translateX(250%); } }",
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
              '<input type="text" class="ed-input" data-field="image" placeholder="/lepas_card/lepas-hero-grey.png?v=1.22.1">' +
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
      this._pendingDialogAction = null;
      this._dialogOutsidePress = false;
      this._lastCmdFeedback = null;
      this._boundDialogEl = null;
      this._pendingKeys = new Set();
      this._errorMsg = null;
      this._lastStructKey = "";
      this._lastDefaultTab = "overview";
      this._listenersBound = false;
      this._latestActions = Object.create(null);
      this._optimisticChargeDays = null;
      this._currentChargeDays = [1, 2, 3, 4, 5, 6, 7];
      this._currentChargeDaysBaseSig = "";
      this._chargeDaysEntityId = null;
      this._syncChargeState = null;
      this._optimisticClimateExtras = null;
      this._currentClimateExtras = [];
      this._currentClimateExtrasBaseSig = "";
      this._allowedClimateExtras = [];
      this._currentEntryId = null;
      this._climateExtrasReqSeq = 0;
      this._onClick = this._handleClick.bind(this);
      this._onChange = this._handleChange.bind(this);
      this._onKeyDown = this._handleKeyDown.bind(this);
      this._onDialogClose = this._handleDialogClose.bind(this);
      this._onDialogCancel = this._handleDialogCancel.bind(this);
      this._onDialogPointerDown = this._handleDialogPointerDown.bind(this);
      this._onDialogPointerUp = this._handleDialogPointerUp.bind(this);
      var isTimeInput = function (el) {
        return Boolean(el && el.tagName === "INPUT" && (el.type === "time" || (el.getAttribute && el.getAttribute("type") === "time")));
      };
      this._isTimeInput = isTimeInput;
      this._onBlockTimeEdit = function (ev) {
        if (ev && isTimeInput(ev.target)) ev.preventDefault();
      };
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

    connectedCallback() {
      this._ensureShellListeners();
      this._bindDialogListeners();
    }

    disconnectedCallback() {
      this._closeConfirmDialog();
      this._unbindDialogListeners();
      this._pendingDialogAction = null;
      this._dialogOutsidePress = false;
    }

    _dead(s) {
      return !s || s.state === "unavailable" || s.state === "unknown" || s.state === "";
    }

    _num(s) {
      var n = s ? parseFloat(s.state) : NaN;
      return isNaN(n) ? null : n;
    }

    _disp(s) {
      if (!s || s.state == null) return "—";
      var rawStr = String(s.state).trim();
      if (!rawStr || rawStr === "unavailable" || rawStr === "unknown") return "—";
      var lang = getLang(this._hass);
      var n = Number(rawStr);
      if (!isNaN(n) && isFinite(n)) {
        return formatMetric(s, lang);
      }
      var h = this._hass;
      if (h && typeof h.formatEntityState === "function" && !(s.attributes && s.attributes.unit_of_measurement)) {
        try { return h.formatEntityState(s); } catch (e) { /* fall through */ }
      }
      return formatMetric(s, lang);
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

    _entryId(hass, items, preferredEnt) {
      var reg = hass && hass.entities;
      if (!reg) return null;
      if (preferredEnt && reg[preferredEnt.id]) {
        var pref = reg[preferredEnt.id];
        if (pref.config_entry_id) return String(pref.config_entry_id);
        if (pref.entry_id) return String(pref.entry_id);
      }
      for (var i = 0; i < items.length; i += 1) {
        var entry = reg[items[i].id];
        if (entry && entry.config_entry_id) return String(entry.config_entry_id);
        if (entry && entry.entry_id) return String(entry.entry_id);
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
      this.shadowRoot.addEventListener("beforeinput", this._onBlockTimeEdit);
      this.shadowRoot.addEventListener("paste", this._onBlockTimeEdit);
      this._listenersBound = true;
    }

    _handleClick(ev) {
      var target = ev.target;
      if (!target || !target.closest) return;

      var dialogActEl = target.closest("[data-dialog-action]");
      if (dialogActEl) {
        ev.stopPropagation();
        var dAction = dialogActEl.getAttribute("data-dialog-action");
        if (dAction === "confirm") {
          this._confirmPendingDialogAction();
        } else {
          this._closeConfirmDialog("cancel");
        }
        return;
      }

      var dismiss = target.closest("[data-dismiss-error]");
      if (dismiss) {
        ev.stopPropagation();
        this._errorMsg = null;
        if (this._hass) this._render(this._hass);
        return;
      }

      var tabEl = target.closest("[data-tab]");
      if (tabEl) {
        ev.stopPropagation();
        var nextTab = tabEl.getAttribute("data-tab");
        if (VALID_TABS.indexOf(nextTab) >= 0 && nextTab !== this._activeTab) {
          this._activeTab = nextTab;
          if (this._hass) this._render(this._hass);
        }
        return;
      }

      var dayChip = target.closest("[data-day-chip]");
      if (dayChip) {
        ev.stopPropagation();
        var slug = dayChip.getAttribute("data-day-chip");
        this._expandedDay = this._expandedDay === slug ? null : slug;
        if (this._hass) this._render(this._hass);
        return;
      }

      var chgDayEl = target.closest("[data-charge-day]");
      if (chgDayEl) {
        ev.stopPropagation();
        var dayNum = parseInt(chgDayEl.getAttribute("data-charge-day"), 10);
        var nextDays = computeToggleDays(this._currentChargeDays || [1, 2, 3, 4, 5, 6, 7], dayNum);
        this._handleChargeDaysSelect(nextDays);
        return;
      }

      var chgPresetEl = target.closest("[data-charge-preset]");
      if (chgPresetEl) {
        ev.stopPropagation();
        var presetKey = chgPresetEl.getAttribute("data-charge-preset");
        var presetDays = presetDaysForKey(presetKey);
        if (presetDays) this._handleChargeDaysSelect(presetDays);
        return;
      }

      var chgModeEl = target.closest("[data-charge-mode]");
      if (chgModeEl) {
        ev.stopPropagation();
        var mode = chgModeEl.getAttribute("data-charge-mode");
        var sc = this._syncChargeState;
        if (sc && sc.id) {
          if (mode === "departure" && !sc.on) {
            this._callService("switch", "turn_on", { entity_id: sc.id }, "sync_charge_toggle");
          } else if (mode === "manual" && sc.on) {
            this._callService("switch", "turn_off", { entity_id: sc.id }, "sync_charge_toggle");
          }
        }
        return;
      }

      var cliExtraEl = target.closest("[data-climate-extra]");
      if (cliExtraEl) {
        ev.stopPropagation();
        this._handleClimateExtraToggle(cliExtraEl.getAttribute("data-climate-extra"));
        return;
      }

      var actionEl = target.closest("[data-action-id]");
      if (actionEl) {
        ev.stopPropagation();
        this._triggerAction(actionEl.getAttribute("data-action-id"), actionEl);
        return;
      }

      if (this._isTimeInput(target)) {
        if (typeof target.showPicker === "function") {
          try { target.showPicker(); } catch (e) { /* ignore */ }
        }
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
      var target = ev.target;
      if (!target || !target.closest) return;
      if (this._isTimeInput(target)) {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          if (typeof target.showPicker === "function") {
            try { target.showPicker(); } catch (e) { /* ignore */ }
          }
          return;
        }
        if (ev.key !== "Tab" && ev.key !== "Escape" && !ev.ctrlKey && !ev.metaKey) {
          ev.preventDefault();
        }
        return;
      }
      if (ev.key !== "Enter" && ev.key !== " ") return;
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

    _bindDialogListeners() {
      var dlg = this.shadowRoot ? this.shadowRoot.querySelector('[data-bind="confirmDialog"]') : null;
      if (!dlg || dlg === this._boundDialogEl) return;
      this._unbindDialogListeners();
      dlg.addEventListener("close", this._onDialogClose);
      dlg.addEventListener("cancel", this._onDialogCancel);
      dlg.addEventListener("pointerdown", this._onDialogPointerDown);
      dlg.addEventListener("pointerup", this._onDialogPointerUp);
      this._boundDialogEl = dlg;
    }

    _unbindDialogListeners() {
      if (!this._boundDialogEl) return;
      this._boundDialogEl.removeEventListener("close", this._onDialogClose);
      this._boundDialogEl.removeEventListener("cancel", this._onDialogCancel);
      this._boundDialogEl.removeEventListener("pointerdown", this._onDialogPointerDown);
      this._boundDialogEl.removeEventListener("pointerup", this._onDialogPointerUp);
      this._boundDialogEl = null;
    }

    _isPointerOutsideDialog(ev, dlg) {
      if (!ev || !dlg || typeof dlg.getBoundingClientRect !== "function") return false;
      var r = dlg.getBoundingClientRect();
      if (!r) return false;
      var x = ev.clientX;
      var y = ev.clientY;
      if (typeof x !== "number" || typeof y !== "number") return false;
      return x < r.left || x > r.right || y < r.top || y > r.bottom;
    }

    _handleDialogClose() {
      var dlg = this._boundDialogEl || (this.shadowRoot ? this.shadowRoot.querySelector('[data-bind="confirmDialog"]') : null);
      if (dlg && (dlg.open || (dlg.hasAttribute && dlg.hasAttribute("open")))) return;
      if (dlg && "returnValue" in dlg) dlg.returnValue = "";
      this._pendingDialogAction = null;
      this._dialogOutsidePress = false;
    }

    _handleDialogCancel(ev) {
      if (ev && typeof ev.preventDefault === "function") ev.preventDefault();
      this._closeConfirmDialog("cancel");
    }

    _handleDialogPointerDown(ev) {
      var dlg = this._boundDialogEl || (this.shadowRoot ? this.shadowRoot.querySelector('[data-bind="confirmDialog"]') : null);
      var isOpen = Boolean(dlg && (dlg.open || (dlg.hasAttribute && dlg.hasAttribute("open"))));
      this._dialogOutsidePress = isOpen ? this._isPointerOutsideDialog(ev, dlg) : false;
    }

    _handleDialogPointerUp(ev) {
      var wasOutside = this._dialogOutsidePress;
      this._dialogOutsidePress = false;
      if (!wasOutside) return;
      var dlg = this._boundDialogEl || (this.shadowRoot ? this.shadowRoot.querySelector('[data-bind="confirmDialog"]') : null);
      if (dlg && this._isPointerOutsideDialog(ev, dlg)) {
        this._closeConfirmDialog("cancel");
      }
    }

    _syncConfirmDialogTexts(t, actionLabel) {
      if (!this.shadowRoot) return;
      var dlg = this.shadowRoot.querySelector('[data-bind="confirmDialog"]');
      if (!dlg) return;
      var titleEl = dlg.querySelector('[data-bind="confirmDialogTitle"]');
      var actEl = dlg.querySelector('[data-bind="confirmDialogAction"]');
      var hintEl = dlg.querySelector('[data-bind="confirmDialogHint"]');
      var cancelBtn = dlg.querySelector('[data-dialog-action="cancel"]');
      var confirmBtn = dlg.querySelector('[data-dialog-action="confirm"]');
      if (titleEl && titleEl.textContent !== t.confirmModalTitle) titleEl.textContent = t.confirmModalTitle;
      if (actEl && typeof actionLabel === "string" && actEl.textContent !== actionLabel) actEl.textContent = actionLabel;
      if (hintEl && hintEl.textContent !== t.confirmModalHint) hintEl.textContent = t.confirmModalHint;
      if (cancelBtn && cancelBtn.textContent !== t.confirmCancel) cancelBtn.textContent = t.confirmCancel;
      if (confirmBtn && confirmBtn.textContent !== t.confirmSend) confirmBtn.textContent = t.confirmSend;
    }

    _openConfirmDialog(spec, confirmKey, actionEl) {
      if (!this.shadowRoot) return;
      var dlg = this.shadowRoot.querySelector('[data-bind="confirmDialog"]');
      if (!dlg) return;
      this._bindDialogListeners();
      var lang = getLang(this._hass);
      var t = getTexts(lang);
      var actionLabel = (spec && spec.confirmLabel)
        ? String(spec.confirmLabel)
        : ((actionEl && actionEl.textContent) ? actionEl.textContent.trim() : confirmKey);

      this._pendingDialogAction = {
        domain: spec.domain,
        service: spec.service,
        data: spec.data,
        pendingKey: confirmKey,
        confirmLabel: actionLabel,
      };
      this._dialogOutsidePress = false;
      this._syncConfirmDialogTexts(t, actionLabel);

      var isAlreadyOpen = Boolean(dlg.open || (dlg.hasAttribute && dlg.hasAttribute("open")));
      if (!isAlreadyOpen) {
        if (typeof dlg.showModal === "function") {
          try {
            dlg.showModal();
          } catch (e) {
            dlg.setAttribute("open", "");
          }
        } else {
          dlg.setAttribute("open", "");
        }
      }
    }

    _closeConfirmDialog(returnVal) {
      this._pendingDialogAction = null;
      this._dialogOutsidePress = false;
      var dlg = this.shadowRoot ? this.shadowRoot.querySelector('[data-bind="confirmDialog"]') : null;
      if (!dlg) return;
      var isOpen = Boolean(dlg.open || (dlg.hasAttribute && dlg.hasAttribute("open")));
      if (isOpen) {
        if (typeof dlg.close === "function") {
          try {
            dlg.close(returnVal || "");
          } catch (e) {
            dlg.removeAttribute("open");
          }
        } else {
          dlg.removeAttribute("open");
        }
      }
      if ("returnValue" in dlg) dlg.returnValue = "";
    }

    _confirmPendingDialogAction() {
      var pending = this._pendingDialogAction;
      this._closeConfirmDialog("confirm");
      if (pending && this._hass) {
        this._callService(pending.domain, pending.service, pending.data, pending.pendingKey);
      }
    }

    _triggerAction(actionId, actionEl) {
      var lookupKey = actionId;
      if (actionEl && actionEl.hasAttribute && actionEl.hasAttribute("data-value")) {
        lookupKey = actionId + "_" + actionEl.getAttribute("data-value");
      }
      var spec = this._latestActions && (this._latestActions[lookupKey] || this._latestActions[actionId]);
      if (!spec || !this._hass) return;

      var confirmKey = spec.confirmKey || actionId;
      if (spec.needsConfirm) {
        this._openConfirmDialog(spec, confirmKey, actionEl);
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
            self._lastCmdFeedback = { ok: true, ts: Date.now() };
            if (self._hass) self._render(self._hass);
          },
          function (err) {
            self._pendingKeys.delete(pendingKey);
            self._errorMsg = (err && err.message) ? String(err.message) : t.commandFailed;
            self._lastCmdFeedback = { ok: false, ts: Date.now() };
            if (self._hass) self._render(self._hass);
          }
        );
      } catch (syncErr) {
        this._pendingKeys.delete(pendingKey);
        this._errorMsg = (syncErr && syncErr.message) ? String(syncErr.message) : t.commandFailed;
        this._lastCmdFeedback = { ok: false, ts: Date.now() };
        this._render(this._hass);
      }
    }

    _handleChargeDaysSelect(nextDays) {
      if (!this._hass || !Array.isArray(nextDays) || !nextDays.length) return;
      var curDays = this._currentChargeDays || [1, 2, 3, 4, 5, 6, 7];
      if (nextDays.join(",") === curDays.join(",")) return;
      var baseSig = this._currentChargeDaysBaseSig || curDays.join(",");
      var pendingKey = "charge_days_select";
      var self = this;
      var lang = getLang(this._hass);
      var t = getTexts(lang);

      this._errorMsg = null;
      this._optimisticChargeDays = { days: nextDays.slice(), baseSig: baseSig };
      this._pendingKeys.add(pendingKey);
      this._render(this._hass);

      var finishFail = function (err) {
        self._pendingKeys.delete(pendingKey);
        var msg = (err && err.message) ? String(err.message) : t.commandFailed;
        var isServiceMissing = ((/service|action/i.test(msg) && /not\s*found|unknown/i.test(msg)) || /not_found/i.test(msg));
        var fallbackPreset = presetForDays(nextDays);
        var selectId = self._chargeDaysEntityId;
        if (isServiceMissing && selectId && fallbackPreset && fallbackPreset !== "custom") {
          self._optimisticChargeDays = { days: nextDays.slice(), baseSig: baseSig };
          self._callService("select", "select_option", { entity_id: selectId, option: fallbackPreset }, pendingKey);
          return;
        }
        self._optimisticChargeDays = null;
        self._errorMsg = msg;
        if (self._hass) self._render(self._hass);
      };

      try {
        Promise.resolve(this._hass.callService("lepas", "set_charging_schedule", {
          days: nextDays.slice(),
          apply: false,
        })).then(
          function () {
            self._pendingKeys.delete(pendingKey);
            if (self._hass) self._render(self._hass);
          },
          finishFail
        );
      } catch (syncErr) {
        finishFail(syncErr);
      }
    }

    _handleClimateExtraToggle(extraKey) {
      if (!this._hass || !Object.prototype.hasOwnProperty.call(CLIMATE_EXTRA_META, extraKey)) return;
      if (!Array.isArray(this._allowedClimateExtras) || this._allowedClimateExtras.indexOf(extraKey) < 0) return;
      var pendingKey = "climate_extra:" + extraKey;
      if (this._pendingKeys.has(pendingKey)) return;

      var curExtras = this._currentClimateExtras || [];
      var nextExtras = computeToggleClimateExtras(curExtras, extraKey);
      var baseSig = this._currentClimateExtrasBaseSig || "";
      var self = this;
      var lang = getLang(this._hass);
      var t = getTexts(lang);

      // Sequence token prevents stale async failures from clearing newer selections.
      this._climateExtrasReqSeq = (this._climateExtrasReqSeq || 0) + 1;
      var reqSeq = this._climateExtrasReqSeq;

      this._errorMsg = null;
      this._optimisticClimateExtras = { extras: nextExtras.slice(), baseSig: baseSig };
      this._pendingKeys.add(pendingKey);
      this._render(this._hass);

      var svcData = { extras: nextExtras.slice() };
      if (this._currentEntryId) svcData.entry_id = this._currentEntryId;

      var onFail = function (err) {
        self._pendingKeys.delete(pendingKey);
        if (reqSeq === self._climateExtrasReqSeq) {
          self._optimisticClimateExtras = null;
          self._errorMsg = (err && err.message) ? String(err.message) : t.commandFailed;
        }
        if (self._hass) self._render(self._hass);
      };

      try {
        Promise.resolve(this._hass.callService("lepas", "set_departure_climate_extras", svcData)).then(
          function () {
            self._pendingKeys.delete(pendingKey);
            if (self._hass) self._render(self._hass);
          },
          onFail
        );
      } catch (syncErr) {
        onFail(syncErr);
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

    _findScrollParent() {
      var node = this;
      while (node) {
        if (node.nodeType === 1 && node !== this && node.scrollHeight > node.clientHeight + 1) {
          var style = typeof getComputedStyle === "function" ? getComputedStyle(node) : null;
          var ovY = style
            ? style.overflowY
            : (node.style && node.style.getPropertyValue ? node.style.getPropertyValue("overflow-y") : "");
          if (ovY === "auto" || ovY === "scroll" || ovY === "overlay" || (!style && !ovY)) {
            return node;
          }
        }
        if (node.parentNode) {
          node = node.parentNode;
        } else {
          var root = node.getRootNode ? node.getRootNode() : null;
          node = (root && root.host) ? root.host : (node.host || null);
        }
      }
      if (typeof document !== "undefined" && document.scrollingElement) {
        return document.scrollingElement;
      }
      return null;
    }

    _captureScroll() {
      var scroller = this._findScrollParent();
      return scroller ? { el: scroller, top: scroller.scrollTop } : null;
    }

    _restoreScroll(snap) {
      if (snap && snap.el && snap.el.scrollTop !== snap.top) {
        snap.el.scrollTop = snap.top;
      }
    }

    _render(hass) {
      var scrollSnap = this._captureScroll();
      try {
        this._renderInner(hass);
      } finally {
        this._restoreScroll(scrollSnap);
      }
    }

    _renderInner(hass) {
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
      var schedDep = this._findDomain(items, "sensor", "scheduled_departure", "partenza_programmata");
      var quickDep = this._findDomain(items, "switch", "quick_departure");
      var quickDepTime = this._findDomain(items, "time", "quick_departure_time");
      var syncCharge = this._findDomain(items, "switch", "sync_charge_to_departure");
      var depCliMode = this._findDomain(items, "select", "departure_climate_mode");
      var applyDepBtn = this._findDomain(items, "button", "apply_departure_schedule");
      var batteryHeat = this._findDomain(items, "switch", "battery_pack_heat");
      var batteryHeatTime = this._findDomain(items, "time", "battery_pack_heat_time");
      var syncBatteryHeat = this._findDomain(items, "switch", "sync_battery_heat_to_departure");
      var rawAllowedExtras = (nextDep && nextDep.s && nextDep.s.attributes)
        ? nextDep.s.attributes.allowed_climate_extras
        : null;
      var allowedClimateExtras = filterAllowedClimateExtras(rawAllowedExtras);
      this._allowedClimateExtras = allowedClimateExtras.slice();
      this._currentEntryId = this._entryId(hass, items, nextDep);
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

      var carActive = false;
      if (schedDep && schedDep.s && !this._dead(schedDep.s)) {
        var sdRawAttrs = schedDep.s.attributes || {};
        if (typeof sdRawAttrs.attiva === "boolean") {
          carActive = sdRawAttrs.attiva;
        } else {
          var sdStateStr = String(schedDep.s.state || "").trim();
          carActive = Boolean(sdStateStr && sdStateStr !== "Disattivata");
        }
      }
      var hasDaySwitches = Boolean(quickDep) || weekDays.some(function (wd) { return Boolean(wd.sw); });
      var haHasActiveDep = hasDaySwitches
        ? (this._isOn(quickDep) || weekDays.some(function (wd) { return self._isOn(wd.sw); }))
        : Boolean(nextDep && nextDep.s && nextDep.s.attributes && nextDep.s.attributes.departure_at);

      // Build action map for the current render
      var actions = Object.create(null);
      var regAction = function (actionId, domain, service, data, needsConfirm, confirmKey, confirmLabel) {
        actions[actionId] = {
          domain: domain,
          service: service,
          data: data,
          needsConfirm: Boolean(needsConfirm),
          confirmKey: confirmKey || actionId,
          confirmLabel: confirmLabel || "",
        };
      };

      if (lock) {
        if (lockIsLocked) {
          regAction("unlock", "lock", "unlock", { entity_id: lock.id }, true, "unlock", t.unlock);
          regAction("quick_unlock", "lock", "unlock", { entity_id: lock.id }, true, "unlock", t.unlock);
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
          regAction("trunk_open", "cover", "open_cover", { entity_id: trunk.id }, true, "trunk_open", t.trunk + ": " + t.openCmd);
          regAction("quick_trunk_open", "cover", "open_cover", { entity_id: trunk.id }, true, "trunk_open", t.trunk + ": " + t.openCmd);
        } else {
          regAction("trunk_close", "cover", "close_cover", { entity_id: trunk.id }, false, "trunk_close");
          regAction("quick_trunk_close", "cover", "close_cover", { entity_id: trunk.id }, false, "trunk_close");
        }
      }
      if (windowsCov) {
        if (windowsCov.s && windowsCov.s.state === "closed") {
          regAction("windows_open", "cover", "open_cover", { entity_id: windowsCov.id }, true, "windows_open", t.windows + ": " + t.openCmd);
        } else {
          regAction("windows_close", "cover", "close_cover", { entity_id: windowsCov.id }, false, "windows_close");
        }
      }
      if (sunroofCov) {
        if (sunroofCov.s && sunroofCov.s.state === "closed") {
          regAction("sunroof_open", "cover", "open_cover", { entity_id: sunroofCov.id }, true, "sunroof_open", t.sunroof + ": " + t.openCmd);
        } else {
          regAction("sunroof_close", "cover", "close_cover", { entity_id: sunroofCov.id }, false, "sunroof_close");
        }
      }
      if (ventWinBtn) regAction("vent_windows", "button", "press", { entity_id: ventWinBtn.id }, true, "vent_windows", t.ventWindows);
      if (ventSunBtn) regAction("vent_sunroof", "button", "press", { entity_id: ventSunBtn.id }, true, "vent_sunroof", t.ventSunroof);
      if (alarmSw) {
        var alarmOnNow = this._isOn(alarmSw);
        var alarmSvc = alarmOnNow ? "turn_off" : "turn_on";
        regAction("alarm_toggle", "switch", alarmSvc, { entity_id: alarmSw.id }, true, "alarm_toggle", t.alarm + ": " + (alarmOnNow ? t.off : t.on));
      }
      if (remoteStartBtn) regAction("remote_start", "button", "press", { entity_id: remoteStartBtn.id }, true, "remote_start", t.remoteStart);
      if (flashBtn) {
        regAction("flash_lights", "button", "press", { entity_id: flashBtn.id }, true, "flash_lights", t.flashLights);
        regAction("sec_flash_lights", "button", "press", { entity_id: flashBtn.id }, true, "flash_lights", t.flashLights);
      }
      if (wakeBtn) regAction("wake_car", "button", "press", { entity_id: wakeBtn.id }, true, "wake_car", t.wakeCar);
      if (refreshLocBtn) regAction("refresh_location", "button", "press", { entity_id: refreshLocBtn.id }, true, "refresh_location", t.refreshLoc);
      if (refreshFullBtn) regAction("refresh_full", "button", "press", { entity_id: refreshFullBtn.id }, true, "refresh_full", t.refreshFull);
      if (locateBtn) regAction("locate_gps", "button", "press", { entity_id: locateBtn.id }, true, "locate_gps", t.locateGps);
      if (applySchedBtn) regAction("apply_charging_schedule", "button", "press", { entity_id: applySchedBtn.id }, true, "apply_charging_schedule", t.applySchedule);
      if (applyDepBtn) {
        regAction(
          "apply_departure_schedule",
          "button",
          "press",
          { entity_id: applyDepBtn.id },
          true,
          "apply_departure_schedule",
          haHasActiveDep ? t.applyDeparture : t.disableOnCar
        );
      }

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
      regSwitchToggle("battery_pack_heat_toggle", batteryHeat);
      regSwitchToggle("sync_battery_heat_toggle", syncBatteryHeat);

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

      // Structural signature: rebuild DOM only when structure/entities/warnings/lang change
      var entityIdsSig = items.map(function (r) { return r.id; }).sort().join(",");
      var extraSig = Array.isArray(cfg.entities)
        ? cfg.entities.map(function (e) { return typeof e === "string" ? e : (e && e.entity ? e.entity : ""); }).join(",")
        : "";
      var warnSig = warns.map(function (w) { return w.id + ":" + w.text; }).join("|");
      var allowedExtrasSig = allowedClimateExtras.join(",");
      var structKey = [
        lang,
        cfg.layout,
        cfg.show_all ? "1" : "0",
        extraSig,
        warnSig,
        allowedExtrasSig,
        entityIdsSig,
      ].join("#");

      if (structKey !== this._lastStructKey) {
        var activeEl = this.shadowRoot.activeElement;
        var activeUid = activeEl && activeEl.getAttribute ? activeEl.getAttribute("data-uid") : null;
        var activeVal = (activeEl && activeEl.tagName === "INPUT") ? activeEl.value : null;

        this._closeConfirmDialog();
        this._unbindDialogListeners();
        this._pendingDialogAction = null;
        this._dialogOutsidePress = false;

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
          schedDep: schedDep,
          quickDep: quickDep,
          quickDepTime: quickDepTime,
          syncCharge: syncCharge,
          depCliMode: depCliMode,
          applyDepBtn: applyDepBtn,
          allowedClimateExtras: allowedClimateExtras,
          batteryHeat: batteryHeat,
          batteryHeatTime: batteryHeatTime,
          syncBatteryHeat: syncBatteryHeat,
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
            if (typeof restored.focus === "function") {
              try { restored.focus({ preventScroll: true }); } catch (e) { restored.focus(); }
            }
            if (activeVal !== null && restored.tagName === "INPUT") restored.value = activeVal;
          }
        }
      }
      this._bindDialogListeners();

      // Always patch live values, classes, SVG offsets, pending states, and non-focused inputs
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
        schedDep: schedDep,
        quickDep: quickDep,
        quickDepTime: quickDepTime,
        syncCharge: syncCharge,
        depCliMode: depCliMode,
        applyDepBtn: applyDepBtn,
        carActive: carActive,
        haHasActiveDep: haHasActiveDep,
        allowedClimateExtras: allowedClimateExtras,
        batteryHeat: batteryHeat,
        batteryHeatTime: batteryHeatTime,
        syncBatteryHeat: syncBatteryHeat,
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
        return '<button type="button" class="tab-btn" role="tab" aria-selected="false" data-tab="' + tb + '" data-uid="tab:' + tb + '">' +
          svgIcon(tb, "tab-ico") +
          '<span class="tab-lbl">' + self._h(t.tabs[tb]) + "</span></button>";
      }).join("") + "</div>";

      // Hero region (2:1 full-car stage + dedicated meta bar below)
      var socRingHtml = ctx.bat ? (
        '<div class="soc-btn" data-bind="socBtn" role="button" tabindex="0" data-e="' + self._h(ctx.bat.id) + '">' +
          '<svg class="soc-svg" viewBox="0 0 52 52" aria-hidden="true">' +
            '<circle class="soc-ring-bg" cx="26" cy="26" r="21"/>' +
            '<circle class="soc-ring-fg" data-soc-ring cx="26" cy="26" r="21" stroke-dasharray="131.95" stroke-dashoffset="131.95"/>' +
          "</svg>" +
          '<span class="soc-val num" data-bind="socText">—</span>' +
          '<span class="soc-chg-ico hidden" data-bind="socChgIco">' + svgIcon("bolt", "soc-bolt") + "</span>" +
          '<progress class="sr-only" data-bind="socProgress" max="100" value="0"></progress>' +
        "</div>"
      ) : "";

      var heroHtml =
        '<div class="hero-region">' +
          '<div class="hero-card">' +
            '<div class="hero-stage">' +
              '<img class="hero-img" data-bind="heroImg" alt="" decoding="async" fetchpriority="high">' +
              '<div class="hero-overlay-top">' +
                '<div class="status-pill">' +
                  '<span class="status-dot" data-bind="connDot"></span>' +
                  '<span data-bind="statusText"></span>' +
                "</div>" +
                socRingHtml +
              "</div>" +
            "</div>" +
            '<div class="hero-meta" ' + (ctx.deviceId ? 'role="button" tabindex="0" data-device="' + self._h(ctx.deviceId) + '"' : "") + ">" +
              '<div class="hero-meta-row">' +
                '<div class="hero-title" data-bind="heroTitle"></div>' +
                '<span class="badge hidden" data-bind="heroStateBadge"></span>' +
              "</div>" +
              '<div class="hero-sub" data-bind="heroSub"></div>' +
            "</div>" +
          "</div>" +
          warnsHtml +
          '<div class="error-banner hidden" role="alert" data-bind="errorBanner">' +
            '<span data-bind="errorText"></span>' +
            '<button type="button" class="error-dismiss" data-dismiss-error aria-label="Dismiss">×</button>' +
          "</div>" +
        "</div>";

      // Panel 1: Overview
      var quickPrimaryBtns = [];
      if (ctx.lock) quickPrimaryBtns.push('<button type="button" class="ctrl-btn" data-bind="quickLockBtn" data-action-id="quick_unlock"></button>');
      if (ctx.climate) quickPrimaryBtns.push('<button type="button" class="ctrl-btn" data-bind="quickClimateBtn" data-action-id="climate_quick"></button>');
      var quickSecondaryBtns = [];
      if (ctx.trunk) quickSecondaryBtns.push('<button type="button" class="ctrl-btn btn-compact" data-bind="quickTrunkBtn" data-action-id="quick_trunk_open"></button>');
      if (ctx.flashBtn) quickSecondaryBtns.push('<button type="button" class="ctrl-btn btn-compact" data-action-id="flash_lights" data-confirm-key="flash_lights">' + svgIcon("lights", "btn-ico") + "<span>" + self._h(t.flashLights) + "</span></button>");
      if (ctx.wakeBtn) quickSecondaryBtns.push('<button type="button" class="ctrl-btn btn-compact" data-action-id="wake_car" data-confirm-key="wake_car">' + svgIcon("wake", "btn-ico") + "<span>" + self._h(t.wakeCar) + "</span></button>");

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
              '<span class="metric-hdr">' + svgIcon("battery", "kpi-ico") + '<span class="metric-lbl">' + self._h(t.evRange) + "</span></span>" +
              '<span class="metric-val num" data-bind="mEvVal">—</span>' +
              '<div class="metric-bar hidden" data-bind="mEvBarWrap"><div class="metric-bar-fill" data-bind="mEvBar"></div></div>' +
            "</div>" +
            '<div class="metric-card" data-bind="mFuelCard">' +
              '<span class="metric-hdr">' + svgIcon("route", "kpi-ico") + '<span class="metric-lbl" data-bind="mFuelLbl">' + self._h(t.totalRange) + "</span></span>" +
              '<span class="metric-val num" data-bind="mFuelVal">—</span>' +
            "</div>" +
            '<div class="metric-card" data-bind="mChgCard">' +
              '<span class="metric-hdr">' + svgIcon("bolt", "kpi-ico") + '<span class="metric-lbl">' + self._h(t.chargingLbl) + "</span></span>" +
              '<span class="metric-val num" data-bind="mChgVal">—</span>' +
            "</div>" +
            '<div class="metric-card" data-bind="mOdoCard">' +
              '<span class="metric-hdr">' + svgIcon("gauge", "kpi-ico") + '<span class="metric-lbl" data-bind="mOdoLbl">' + self._h(t.odometer) + "</span></span>" +
              '<span class="metric-val num" data-bind="mOdoVal">—</span>' +
            "</div>" +
          "</div>" +
          ((quickPrimaryBtns.length || quickSecondaryBtns.length)
            ? '<div class="surface"><div class="sec-hdr"><span>' + self._h(t.quickActions) + "</span></div>" +
                (quickPrimaryBtns.length ? '<div class="btn-grid">' + quickPrimaryBtns.join("") + "</div>" : "") +
                (quickSecondaryBtns.length ? '<div class="btn-triple">' + quickSecondaryBtns.join("") + "</div>" : "") +
              "</div>"
            : "") +
          '<div class="surface">' +
            '<div class="footer-bar">' +
              '<span class="meta-inline">' + svgIcon("clock", "meta-ico") + '<span data-bind="freshnessText"></span></span>' +
              '<span class="badge hidden" data-bind="cmdResultBadge"></span>' +
            "</div>" +
            ((ctx.refreshLocBtn || ctx.refreshFullBtn)
              ? '<div class="btn-row">' +
                  (ctx.refreshLocBtn ? '<button type="button" class="ctrl-btn" data-action-id="refresh_location" data-confirm-key="refresh_location">' + svgIcon("refresh", "btn-ico") + "<span>" + self._h(t.refreshLoc) + "</span></button>" : "") +
                  (ctx.refreshFullBtn ? '<button type="button" class="ctrl-btn" data-action-id="refresh_full" data-confirm-key="refresh_full">' + svgIcon("refresh", "btn-ico") + "<span>" + self._h(t.refreshFull) + "</span></button>" : "") +
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
          '<div class="sec-hdr"><span class="sec-hdr-title">' + svgIcon("fan", "sec-ico") + "<span>" + self._h(t.climateHub) + '</span></span><span class="badge hidden" data-bind="airPurifBadge">' + self._h(t.airPurification) + "</span></div>" +
          '<div class="btn-row">' +
            '<button type="button" class="ctrl-btn" style="flex:1" data-action-id="climate_toggle" data-confirm-key="climate_toggle" data-bind="climateToggleBtn"></button>' +
          "</div>" +
          '<div class="stepper">' +
            '<button type="button" class="ctrl-btn" data-action-id="temp_down" aria-label="-">' + svgIcon("minus", "btn-ico") + "</button>" +
            '<span class="step-val num" data-bind="targetTempText">—</span>' +
            '<button type="button" class="ctrl-btn" data-action-id="temp_up" aria-label="+">' + svgIcon("plus", "btn-ico") + "</button>" +
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
          (ctx.coolSwitch ? '<button type="button" class="ctrl-btn" data-action-id="cool_everything" data-confirm-key="cool_everything" data-bind="coolAllBtn">' + svgIcon("snow", "btn-ico") + "<span>" + self._h(t.coolAll) + "</span></button>" : "") +
          (ctx.heatSwitch ? '<button type="button" class="ctrl-btn" data-action-id="heat_everything" data-confirm-key="heat_everything" data-bind="heatAllBtn">' + svgIcon("flame", "btn-ico") + "<span>" + self._h(t.heatAll) + "</span></button>" : "") +
        "</div></div>"
      ) : "";

      var defrostIconMap = {
        windshield_defrost: "windshield",
        windshield_defog: "windshield",
        rear_window_heating: "rear_defrost",
        steering_wheel_heating: "steering",
      };
      var defrostHtml = ctx.defrostEntities.length ? (
        '<div class="surface"><div class="sec-hdr"><span>' + self._h(t.defrosts) + '</span></div><div class="btn-grid">' +
          ctx.defrostEntities.map(function (d) {
            return '<button type="button" class="ctrl-btn" data-action-id="' + d.key + '" data-confirm-key="' + d.key + '" data-defrost-btn="' + d.key + '">' +
              svgIcon(defrostIconMap[d.key] || "windshield", "btn-ico") +
              "<span>" + self._h(d.label) + "</span></button>";
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
        '<div class="surface"><div class="sec-hdr"><span class="sec-hdr-title">' + svgIcon("seat", "sec-ico") + "<span>" + self._h(t.seats) + "</span></span></div>" +
          '<div class="seat-grid">' +
            ctx.seatDefs.map(function (sd) {
              return '<div class="seat-card">' +
                '<div class="seat-name">' + self._h(sd.label) + "</div>" +
                '<div class="seat-btns">' +
                  (sd.heat ? '<button type="button" class="ctrl-btn" data-action-id="seat_' + sd.slug + '_heat" data-seat-btn="' + sd.slug + '_heat">' + svgIcon("flame", "btn-ico") + "<span>" + self._h(t.heat) + "</span></button>" : "") +
                  (sd.vent ? '<button type="button" class="ctrl-btn" data-action-id="seat_' + sd.slug + '_vent" data-seat-btn="' + sd.slug + '_vent">' + svgIcon("fan", "btn-ico") + "<span>" + self._h(t.vent) + "</span></button>" : "") +
                "</div>" +
              "</div>";
            }).join("") +
          "</div>" +
          rearCenterHtml +
        "</div>"
      ) : "";

      var climateHtml = '<section class="panel" data-panel="climate">' + climateHubHtml + macrosHtml + defrostHtml + seatsHtml + "</section>";

      // Panel 3: Charging & Departures
      var chgStatHtml = function (bind, iconName, label) {
        return '<div class="chg-stat hidden" data-bind="' + bind + '">' +
          '<span class="chg-stat-lbl">' + svgIcon(iconName, "stat-ico") + "<span>" + self._h(label) + "</span></span>" +
          '<span class="chg-stat-val num" data-stat-val="' + bind + '">—</span>' +
        "</div>";
      };
      var liveChgHtml = (ctx.chgSwitch || ctx.plug || ctx.chgPower || ctx.remTime || ctx.hvVolt || ctx.hvCurr) ? (
        '<div class="surface">' +
          '<div class="sec-hdr"><span class="sec-hdr-title">' + svgIcon("bolt", "sec-ico") + "<span>" + self._h(t.liveCharging) + '</span></span><span class="badge" data-bind="cableBadge"></span></div>' +
          (ctx.chgSwitch ? '<button type="button" class="ctrl-btn" data-action-id="charging_toggle" data-confirm-key="charging_toggle" data-bind="chgToggleBtn"></button>' : "") +
          '<div class="flow-track hidden" data-bind="chgFlowTrack"><div class="flow-bar"></div></div>' +
          '<div class="chg-stats-grid" data-bind="chgStatsRow">' +
            (ctx.chgPower ? chgStatHtml("chgPowerBadge", "bolt", t.chargingLbl) : "") +
            (ctx.remTime ? chgStatHtml("remTimeBadge", "clock", t.remaining) : "") +
            (ctx.hvVolt ? chgStatHtml("hvVoltBadge", "volt", t.voltage) : "") +
            (ctx.hvCurr ? chgStatHtml("hvCurrBadge", "current", t.current) : "") +
            (ctx.homeEnergy ? chgStatHtml("homeEnergyBadge", "home", t.homeEnergy) : "") +
            (ctx.awayEnergy ? chgStatHtml("awayEnergyBadge", "pin", t.awayEnergy) : "") +
            (ctx.fastPort ? chgStatHtml("fastPortBadge", "plug", t.fastPort) : "") +
          "</div>" +
        "</div>"
      ) : "";

      var timelineHtml = ctx.schedWindow ? (
        '<div>' +
          '<div class="timeline-track" data-bind="timelineTrack"></div>' +
          '<div class="timeline-axis num"><span>00:00</span><span data-bind="schedWindowText"></span><span>24:00</span></div>' +
        "</div>"
      ) : "";

      var chargeDaysStripHtml = (ctx.chgDays || ctx.schedWindow) ? (
        '<div class="field-row"><span class="field-lbl">' + self._h(t.chargeDays) + '</span><span class="badge" data-bind="chgDaysPresetLbl"></span></div>' +
        '<div class="charge-days-strip" role="group">' + t.weekdays.map(function (letter, idx) {
          var dayNum = idx + 1;
          return '<button type="button" class="chip-btn charge-day-chip" data-charge-day="' + dayNum + '" data-uid="chgday:' + dayNum + '">' +
            "<span>" + self._h(letter) + "</span></button>";
        }).join("") + "</div>" +
        '<div class="preset-row" role="group">' +
          '<button type="button" class="chip-btn preset-btn" data-charge-preset="all_days" data-uid="chgpreset:all_days">' + self._h(t.presetAll) + "</button>" +
          '<button type="button" class="chip-btn preset-btn" data-charge-preset="weekdays" data-uid="chgpreset:weekdays">' + self._h(t.presetWeekdays) + "</button>" +
          '<button type="button" class="chip-btn preset-btn" data-charge-preset="weekend" data-uid="chgpreset:weekend">' + self._h(t.presetWeekend) + "</button>" +
        "</div>"
      ) : "";

      var chargeModeSwitchHtml = ctx.syncCharge ? (
        '<div class="seg-switch" role="group">' +
          '<button type="button" class="seg-btn" data-charge-mode="manual" data-uid="chgmode:manual" aria-pressed="true">' + svgIcon("clock", "btn-ico") + "<span>" + self._h(t.chargeModeManual) + "</span></button>" +
          '<button type="button" class="seg-btn" data-charge-mode="departure" data-uid="chgmode:departure" aria-pressed="false">' + svgIcon("calendar", "btn-ico") + "<span>" + self._h(t.chargeModeDeparture) + "</span></button>" +
        "</div>"
      ) : "";

      var schedChgHtml = (ctx.schedSwitch || ctx.schedWindow || ctx.chgStartTime || ctx.chgDur || ctx.chgDays || ctx.applySchedBtn) ? (
        '<div class="surface">' +
          '<div class="sec-hdr"><span class="sec-hdr-title">' + svgIcon("calendar", "sec-ico") + "<span>" + self._h(t.scheduledCharging) + '</span></span><span class="badge hidden" data-bind="schedSyncBadge"></span></div>' +
          (ctx.schedSwitch ? '<button type="button" class="ctrl-btn" data-action-id="scheduled_charging_toggle" data-confirm-key="scheduled_charging_toggle" data-bind="schedToggleBtn"></button>' : "") +
          chargeModeSwitchHtml +
          timelineHtml +
          '<div class="manual-charge-box" data-bind="manualChargeBox">' +
            (ctx.chgStartTime ? '<div class="field-row"><label class="field-lbl">' + self._h(t.startTime) + '</label><input type="time" inputmode="none" class="ctrl-input num" data-entity-input="' + self._h(ctx.chgStartTime.id) + '" data-uid="input:' + self._h(ctx.chgStartTime.id) + '"></div>' : "") +
            (ctx.chgDur ? '<div class="field-row"><span class="field-lbl">' + self._h(t.chargeDuration) + '</span><div class="stepper" style="min-width:150px"><button type="button" class="ctrl-btn" data-action-id="charge_dur_down" aria-label="-">' + svgIcon("minus", "btn-ico") + '</button><span class="num" data-bind="chgDurText">—</span><button type="button" class="ctrl-btn" data-action-id="charge_dur_up" aria-label="+">' + svgIcon("plus", "btn-ico") + "</button></div></div>" : "") +
            chargeDaysStripHtml +
          "</div>" +
          '<div class="departure-charge-box hidden" data-bind="departureChargeBox">' +
            '<div class="dep-charge-title">' + svgIcon("clock", "stat-ico") + "<span>" + self._h(t.followDepartureTitle) + "</span></div>" +
            '<div class="dep-charge-val num" data-bind="depChargeStartText"></div>' +
          "</div>" +
          '<span class="badge is-amber hidden" data-bind="fallback2131Badge">' + self._h(t.daysFallback2131) + "</span>" +
          (ctx.applySchedBtn ? '<button type="button" class="ctrl-btn is-primary" data-action-id="apply_charging_schedule" data-confirm-key="apply_charging_schedule">' + svgIcon("check", "btn-ico") + "<span>" + self._h(t.applySchedule) + "</span></button>" : "") +
        "</div>"
      ) : "";

      var depModeOptsHtml = "";
      if (ctx.depCliMode) {
        var dOpts = (ctx.depCliMode.s && ctx.depCliMode.s.attributes && Array.isArray(ctx.depCliMode.s.attributes.options))
          ? ctx.depCliMode.s.attributes.options : ["at_home", "anywhere", "off"];
        depModeOptsHtml = dOpts.map(function (o) {
          return '<option value="' + self._h(o) + '">' + self._h(translateOption("departure_climate_mode", o, ctx.lang)) + "</option>";
        }).join("");
      }

      var hasWeekDays = ctx.weekDays.some(function (w) { return Boolean(w.sw || w.tm); });
      var dayEditorHtml = ctx.weekDays.map(function (wd) {
        if (!wd.sw && !wd.tm) return "";
        return (
          '<div class="day-editor hidden" data-day-editor="' + wd.slug + '" hidden>' +
            '<div class="sec-hdr"><span>' + self._h(wd.name) + "</span></div>" +
            (wd.sw ? '<button type="button" class="ctrl-btn" data-action-id="day_toggle_' + wd.slug + '" data-bind="expandedDayToggle"></button>' : "") +
            (wd.tm ? '<div class="field-row"><label class="field-lbl">' + self._h(t.timeLbl) + '</label><input type="time" inputmode="none" class="ctrl-input num" data-entity-input="' + self._h(wd.tm.id) + '" data-uid="input:' + self._h(wd.tm.id) + '"></div>' : "") +
          "</div>"
        );
      }).join("");

      var depSummaryHtml = (ctx.nextDep || ctx.schedDep) ? (
        '<div class="dep-summary">' +
          (ctx.nextDep ? '<div class="dep-summary-row" role="button" tabindex="0" data-e="' + self._h(ctx.nextDep.id) + '"><span class="meta-inline">' + svgIcon("clock", "meta-ico") + "<span>" + self._h(t.nextDeparture) + '</span></span><span class="info-val num" data-bind="nextDepText"></span></div>' : "") +
          (ctx.schedDep ? '<div class="dep-summary-row" role="button" tabindex="0" data-e="' + self._h(ctx.schedDep.id) + '"><span class="meta-inline">' + svgIcon("calendar", "meta-ico") + "<span>" + self._h(t.carDeparturePlan) + '</span></span><span class="info-val num" data-bind="schedDepText"></span></div>' : "") +
        "</div>"
      ) : "";

      var depSyncBtnsHtml = ctx.applyDepBtn
        ? '<button type="button" class="ctrl-btn is-primary" data-action-id="apply_departure_schedule" data-confirm-key="apply_departure_schedule" data-bind="applyDepBtn"></button>'
        : "";

      var sortedClimateExtras = (ctx.allowedClimateExtras && ctx.allowedClimateExtras.length)
        ? ctx.allowedClimateExtras.slice().sort(function (a, b) {
            return ALLOWED_CLIMATE_EXTRAS.indexOf(a) - ALLOWED_CLIMATE_EXTRAS.indexOf(b);
          })
        : [];
      var depExtrasHtml = sortedClimateExtras.length ? (
        '<div class="dep-subbox" data-bind="depExtrasBox">' +
          '<div class="sec-hdr"><span>' + self._h(t.depClimateExtras) + "</span></div>" +
          '<div class="climate-extras-grid" role="group" aria-label="' + self._h(t.depClimateExtras) + '">' +
            sortedClimateExtras.map(function (extraKey) {
              var meta = CLIMATE_EXTRA_META[extraKey];
              var extraLbl = (t.climateExtraLabels && t.climateExtraLabels[extraKey])
                ? t.climateExtraLabels[extraKey]
                : (I18N.en.climateExtraLabels[extraKey] || extraKey);
              return '<button type="button" class="chip-btn climate-extra-chip" data-climate-extra="' + self._h(extraKey) + '" data-uid="cliextra:' + self._h(extraKey) + '" aria-pressed="false">' +
                svgIcon(meta ? meta.icon : "fan", "btn-ico") +
                "<span>" + self._h(extraLbl) + "</span></button>";
            }).join("") +
          "</div>" +
        "</div>"
      ) : "";

      var batteryHeatHtml = (ctx.batteryHeat || ctx.batteryHeatTime || ctx.syncBatteryHeat) ? (
        '<div class="dep-subbox" data-bind="batteryHeatBox">' +
          '<div class="sec-hdr"><span class="sec-hdr-title">' + svgIcon("thermometer", "sec-ico") + "<span>" + self._h(t.batteryPreheat) + '</span></span><span class="badge hidden num" data-bind="batteryHeatSyncHint"></span></div>' +
          ((ctx.batteryHeat || ctx.batteryHeatTime)
            ? '<div class="btn-row">' +
                (ctx.batteryHeat ? '<button type="button" class="ctrl-btn" style="flex:1" data-action-id="battery_pack_heat_toggle" data-confirm-key="battery_pack_heat_toggle" data-bind="batteryHeatBtn"></button>' : "") +
                (ctx.batteryHeatTime ? '<label class="sr-only" for="lp-bat-heat-time">' + self._h(t.batteryPreheatTime) + '</label><input type="time" id="lp-bat-heat-time" inputmode="none" class="ctrl-input num" data-entity-input="' + self._h(ctx.batteryHeatTime.id) + '" data-uid="input:' + self._h(ctx.batteryHeatTime.id) + '">' : "") +
              "</div>"
            : "") +
          (ctx.syncBatteryHeat
            ? '<div class="btn-row"><button type="button" class="ctrl-btn" style="flex:1" data-action-id="sync_battery_heat_toggle" data-confirm-key="sync_battery_heat_toggle" data-bind="syncBatteryHeatBtn"></button></div>'
            : "") +
        "</div>"
      ) : "";

      var hasDepSection = Boolean(
        ctx.nextDep || ctx.quickDep || hasWeekDays ||
        ctx.applyDepBtn || ctx.schedDep ||
        (ctx.allowedClimateExtras && ctx.allowedClimateExtras.length) ||
        ctx.batteryHeat || ctx.batteryHeatTime || ctx.syncBatteryHeat
      );

      var depHtml = hasDepSection ? (
        '<div class="surface" data-bind="depSurface">' +
          '<div class="sec-hdr">' +
            '<span class="sec-hdr-title">' + svgIcon("calendar", "sec-ico") + "<span>" + self._h(t.departures) + "</span></span>" +
            '<span class="dep-hdr-badges">' +
              '<span class="badge hidden num" data-bind="depChargeHint"></span>' +
            "</span>" +
          "</div>" +
          depSummaryHtml +
          ((ctx.quickDep || ctx.quickDepTime)
            ? '<div class="btn-row">' +
                (ctx.quickDep ? '<button type="button" class="ctrl-btn" style="flex:1" data-action-id="quick_departure_toggle" data-confirm-key="quick_departure_toggle" data-bind="quickDepBtn"></button>' : "") +
                (ctx.quickDepTime ? '<input type="time" inputmode="none" class="ctrl-input num" data-entity-input="' + self._h(ctx.quickDepTime.id) + '" data-uid="input:' + self._h(ctx.quickDepTime.id) + '">' : "") +
              "</div>"
            : "") +
          (ctx.depCliMode ? '<div class="field-row"><label class="field-lbl">' + self._h(t.depClimateMode) + '</label><select class="ctrl-select" data-entity-input="' + self._h(ctx.depCliMode.id) + '" data-uid="input:' + self._h(ctx.depCliMode.id) + '">' + depModeOptsHtml + "</select></div>" : "") +
          (hasWeekDays
            ? '<div class="days-strip">' + ctx.weekDays.map(function (wd) {
                return '<button type="button" class="day-chip" data-day-chip="' + wd.slug + '" data-uid="day:' + wd.slug + '">' +
                  "<span>" + self._h(wd.letter) + '</span><span class="day-dot"></span><span class="day-time num" data-day-time="' + wd.slug + '"></span></button>';
              }).join("") + "</div>" + dayEditorHtml
            : "") +
          depSyncBtnsHtml +
          depExtrasHtml +
          batteryHeatHtml +
        "</div>"
      ) : "";

      var chargingHtml = '<section class="panel" data-panel="charging">' + liveChgHtml + schedChgHtml + depHtml + "</section>";

      // Panel 4: Security & Blueprint
      var tpmsCard = function (c) {
        var tpLabel = (t.tpmsLabels && t.tpmsLabels[c.pos]) ? t.tpmsLabels[c.pos] : c.label;
        var hdrHtml = '<span class="tpms-hdr">' + svgIcon("tire", "tpms-ico") + "<span>" + self._h(tpLabel) + "</span></span>";
        if (!c.p && !c.temp && !c.w) return '<div class="tpms-box" data-tpms="' + c.pos + '">' + hdrHtml + '<span class="tpms-press num">—</span></div>';
        var entRef = c.p ? c.p.id : (c.w ? c.w.id : c.temp.id);
        return '<div class="tpms-box" role="button" tabindex="0" data-e="' + self._h(entRef) + '" data-tpms="' + c.pos + '">' +
          hdrHtml +
          '<span class="tpms-press num" data-tpms-press="' + c.pos + '">—</span>' +
          '<span class="tpms-temp num" data-tpms-temp="' + c.pos + '"></span>' +
        "</div>";
      };

      var blueprintSvg =
        '<svg class="bp-svg" viewBox="0 0 160 250" aria-label="Vehicle blueprint">' +
          '<path class="bp-headlights" data-bp-part="headlights" d="M 46 21 Q 54 14 63 18 L 60 24 L 47 26 Z M 114 21 Q 106 14 97 18 L 100 24 L 113 26 Z"/>' +
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
          '<circle class="bp-lock-badge" data-bp-lock cx="80" cy="124" r="6"/>' +
        "</svg>";

      var blueprintHtml =
        '<div class="surface">' +
          '<div class="sec-hdr"><span class="sec-hdr-title">' + svgIcon("tire", "sec-ico") + "<span>" + self._h(t.blueprintTitle) + "</span></span></div>" +
          '<div class="bp-stage">' +
            '<div class="tpms-col">' + tpmsCard(ctx.tpmsCorners[0]) + tpmsCard(ctx.tpmsCorners[2]) + "</div>" +
            blueprintSvg +
            '<div class="tpms-col">' + tpmsCard(ctx.tpmsCorners[1]) + tpmsCard(ctx.tpmsCorners[3]) + "</div>" +
          "</div>" +
        "</div>";

      var closureBtns = [];
      if (ctx.lock) closureBtns.push('<button type="button" class="ctrl-btn" data-bind="secLockBtn" data-action-id="unlock"></button>');
      if (ctx.trunk) closureBtns.push('<button type="button" class="ctrl-btn" data-bind="secTrunkBtn" data-action-id="trunk_open"></button>');
      if (ctx.windowsCov) closureBtns.push('<button type="button" class="ctrl-btn" data-bind="secWindowsBtn" data-action-id="windows_open"></button>');
      if (ctx.ventWinBtn) closureBtns.push('<button type="button" class="ctrl-btn" data-action-id="vent_windows" data-confirm-key="vent_windows" data-bind="ventWinBtn"></button>');
      if (ctx.sunroofCov) closureBtns.push('<button type="button" class="ctrl-btn" data-bind="secSunroofBtn" data-action-id="sunroof_open"></button>');
      if (ctx.ventSunBtn) closureBtns.push('<button type="button" class="ctrl-btn" data-action-id="vent_sunroof" data-confirm-key="vent_sunroof" data-bind="ventSunBtn"></button>');

      var secActionBtns = [];
      if (ctx.alarmSw) secActionBtns.push('<button type="button" class="ctrl-btn" data-action-id="alarm_toggle" data-confirm-key="alarm_toggle" data-bind="alarmBtn"></button>');
      if (ctx.remoteStartBtn) secActionBtns.push('<button type="button" class="ctrl-btn" data-action-id="remote_start" data-confirm-key="remote_start" data-bind="remoteStartBtn"></button>');
      if (ctx.locateBtn) secActionBtns.push('<button type="button" class="ctrl-btn" data-action-id="locate_gps" data-confirm-key="locate_gps">' + svgIcon("gps", "btn-ico") + "<span>" + self._h(t.locateGps) + "</span></button>");
      if (ctx.flashBtn) secActionBtns.push('<button type="button" class="ctrl-btn" data-action-id="sec_flash_lights" data-confirm-key="flash_lights">' + svgIcon("lights", "btn-ico") + "<span>" + self._h(t.flashLights) + "</span></button>");

      var secCtrlHtml = (closureBtns.length || secActionBtns.length || ctx.tracker) ? (
        '<div class="surface">' +
          '<div class="sec-hdr"><span>' + self._h(t.securityControls) + "</span></div>" +
          (closureBtns.length
            ? '<div class="sec-group" data-security-group="closures">' +
                '<div class="sec-subhdr">' + svgIcon("lock", "sec-ico") + "<span>" + self._h(t.closuresGroup) + "</span></div>" +
                '<div class="btn-grid" style="margin-top:6px">' + closureBtns.join("") + "</div>" +
              "</div>"
            : "") +
          ((secActionBtns.length || ctx.tracker)
            ? '<div class="sec-group" data-security-group="security">' +
                '<div class="sec-subhdr">' + svgIcon("shield", "sec-ico") + "<span>" + self._h(t.securityGroup) + "</span></div>" +
                (secActionBtns.length ? '<div class="btn-grid" style="margin-top:6px">' + secActionBtns.join("") + "</div>" : "") +
                (ctx.tracker ? '<div class="info-row" style="margin-top:8px" role="button" tabindex="0" data-e="' + self._h(ctx.tracker.id) + '"><span class="meta-inline">' + svgIcon("pin", "meta-ico") + "<span>" + self._h(t.position) + '</span></span><span class="info-val" data-bind="trackerText"></span></div>' : "") +
              "</div>"
            : "") +
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
          '<dialog class="confirm-dialog" data-bind="confirmDialog" aria-labelledby="lp-confirm-title">' +
            '<div class="confirm-dialog-body">' +
              '<h2 id="lp-confirm-title" class="confirm-dialog-title" data-bind="confirmDialogTitle">' + self._h(t.confirmModalTitle) + "</h2>" +
              '<p class="confirm-dialog-action" data-bind="confirmDialogAction"></p>' +
              '<p class="confirm-dialog-hint" data-bind="confirmDialogHint">' + self._h(t.confirmModalHint) + "</p>" +
              '<div class="confirm-dialog-actions">' +
                '<button type="button" class="ctrl-btn" data-dialog-action="cancel" data-bind="confirmDialogCancel" autofocus>' + self._h(t.confirmCancel) + "</button>" +
                '<button type="button" class="ctrl-btn is-primary" data-dialog-action="confirm" data-bind="confirmDialogConfirm">' + self._h(t.confirmSend) + "</button>" +
              "</div>" +
            "</div>" +
          "</dialog>" +
        "</ha-card>";
    }

    _applyBtnState(btn, label, actionId, confirmKey, variantClass, t, iconName) {
      if (!btn) return;
      btn.setAttribute("data-action-id", actionId);
      btn.setAttribute("data-confirm-key", confirmKey);
      var ico = iconName || (btn.getAttribute ? btn.getAttribute("data-icon") : "") || "";
      if (iconName) btn.setAttribute("data-icon", iconName);
      var isPending = this._pendingKeys.has(confirmKey);

      btn.classList.remove("is-primary", "is-emerald", "is-glacier", "is-amber", "is-pending");
      if (variantClass) btn.classList.add(variantClass);
      if (isPending) btn.classList.add("is-pending");
      btn.disabled = isPending;

      var sig = ico + "|" + label;
      if (btn.getAttribute("data-btn-sig") !== sig) {
        btn.setAttribute("data-btn-sig", sig);
        btn.innerHTML = (ico ? svgIcon(ico, "btn-ico") : "") + "<span>" + this._h(label) + "</span>";
      }
    }

    _applyBindings(hass, vm) {
      var scrollSnap = this._captureScroll();
      try {
        this._applyBindingsInner(hass, vm);
      } finally {
        this._restoreScroll(scrollSnap);
      }
    }

    _applyBindingsInner(hass, vm) {
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
        if (tabBtn) {
          tabBtn.classList.toggle("is-active", active);
          tabBtn.setAttribute("aria-selected", active ? "true" : "false");
        }
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
      var cliActive = Boolean(vm.climate && !this._dead(vm.climate.s) && vm.climate.s.state !== "off");
      var heroBadge = root.querySelector('[data-bind="heroStateBadge"]');
      if (heroBadge) {
        if (isCharging) {
          heroBadge.classList.remove("hidden", "is-glacier");
          heroBadge.classList.add("is-emerald");
          heroBadge.textContent = (vm.chgPower && !this._dead(vm.chgPower.s) && this._num(vm.chgPower.s) > 0)
            ? t.charging + " · " + this._disp(vm.chgPower.s)
            : t.charging;
        } else if (cliActive) {
          heroBadge.classList.remove("hidden", "is-emerald");
          heroBadge.classList.add("is-glacier");
          heroBadge.textContent = t.climateOn;
        } else {
          heroBadge.classList.add("hidden");
          heroBadge.classList.remove("is-emerald", "is-glacier");
          heroBadge.textContent = "";
        }
      }

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
      var socBtn = root.querySelector('[data-bind="socBtn"]');
      if (socBtn) socBtn.classList.toggle("is-charging", Boolean(isCharging));
      var socChgIco = root.querySelector('[data-bind="socChgIco"]');
      if (socChgIco) socChgIco.classList.toggle("hidden", !isCharging);
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
          t,
          isLocked ? "unlock" : "lock"
        );
        this._applyBtnState(
          root.querySelector('[data-bind="secLockBtn"]'),
          isLocked ? t.unlock : t.lock,
          isLocked ? "unlock" : "lock_now",
          isLocked ? "unlock" : "lock_now",
          isLocked ? "" : "is-emerald",
          t,
          isLocked ? "unlock" : "lock"
        );
      }
      if (vm.climate) {
        var qCliBtn = root.querySelector('[data-bind="quickClimateBtn"]');
        var cTogBtn = root.querySelector('[data-bind="climateToggleBtn"]');
        this._applyBtnState(
          qCliBtn,
          cliActive ? t.climateOn : t.climateOff,
          "climate_quick",
          "climate_toggle",
          cliActive ? "is-glacier" : "",
          t,
          "fan"
        );
        this._applyBtnState(
          cTogBtn,
          cliActive ? t.climateOn : t.climateOff,
          "climate_toggle",
          "climate_toggle",
          cliActive ? "is-glacier" : "",
          t,
          "fan"
        );
        if (qCliBtn) qCliBtn.classList.toggle("is-spinning", cliActive);
        if (cTogBtn) cTogBtn.classList.toggle("is-spinning", cliActive);
      }
      if (vm.trunk) {
        var trunkClosed = vm.trunk.s && vm.trunk.s.state === "closed";
        this._applyBtnState(
          root.querySelector('[data-bind="quickTrunkBtn"]'),
          t.trunk + ": " + (trunkClosed ? t.openCmd : t.closeCmd),
          trunkClosed ? "quick_trunk_open" : "quick_trunk_close",
          trunkClosed ? "trunk_open" : "trunk_close",
          trunkClosed ? "" : "is-amber",
          t,
          "trunk"
        );
        this._applyBtnState(
          root.querySelector('[data-bind="secTrunkBtn"]'),
          t.trunk + ": " + (trunkClosed ? t.openCmd : t.closeCmd),
          trunkClosed ? "trunk_open" : "trunk_close",
          trunkClosed ? "trunk_open" : "trunk_close",
          trunkClosed ? "" : "is-amber",
          t,
          "trunk"
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
          t,
          "window"
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
          t,
          "sunroof"
        );
      }
      this._applyBtnState(root.querySelector('[data-bind="ventWinBtn"]'), t.ventWindows, "vent_windows", "vent_windows", "", t, "window");
      this._applyBtnState(root.querySelector('[data-bind="ventSunBtn"]'), t.ventSunroof, "vent_sunroof", "vent_sunroof", "", t, "sunroof");
      this._applyBtnState(root.querySelector('[data-bind="remoteStartBtn"]'), t.remoteStart, "remote_start", "remote_start", "", t, "bolt");
      if (vm.alarmSw) {
        var alarmOn = this._isOn(vm.alarmSw);
        this._applyBtnState(
          root.querySelector('[data-bind="alarmBtn"]'),
          t.alarm + ": " + (alarmOn ? t.on : t.off),
          "alarm_toggle",
          "alarm_toggle",
          alarmOn ? "is-emerald" : "",
          t,
          "shield"
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
        var cmdStateAlive = (vm.cmdResult && !this._dead(vm.cmdResult.s)) ? vm.cmdResult.s : null;
        var outcome = formatCommandOutcome(cmdStateAlive, this._lastCmdFeedback, vm.lang);
        if (outcome) {
          cmdBadge.classList.remove("hidden");
          cmdBadge.classList.toggle("is-emerald", Boolean(outcome.ok));
          cmdBadge.classList.toggle("is-coral", !outcome.ok);
          cmdBadge.textContent = outcome.text;
        } else {
          cmdBadge.classList.add("hidden");
          cmdBadge.classList.remove("is-emerald", "is-coral");
          cmdBadge.textContent = "";
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
        this._applyBtnState(chgToggleBtn, chgSwOn ? t.stopCharging : t.startCharging, "charging_toggle", "charging_toggle", chgSwOn ? "is-emerald" : "", t, "bolt");
      }
      var flowTrack = root.querySelector('[data-bind="chgFlowTrack"]');
      if (flowTrack) flowTrack.classList.toggle("hidden", !isCharging);

      var setStat = function (bind, ent) {
        var el = root.querySelector('[data-bind="' + bind + '"]');
        if (!el) return;
        var valEl = el.querySelector('[data-stat-val="' + bind + '"]');
        if (ent && !self._dead(ent.s)) {
          el.classList.remove("hidden");
          if (valEl) valEl.textContent = self._disp(ent.s);
        } else {
          el.classList.add("hidden");
          if (valEl) valEl.textContent = "—";
        }
      };
      setStat("chgPowerBadge", vm.chgPower);
      setStat("remTimeBadge", vm.remTime);
      setStat("hvVoltBadge", vm.hvVolt);
      setStat("hvCurrBadge", vm.hvCurr);
      setStat("homeEnergyBadge", vm.homeEnergy);
      setStat("awayEnergyBadge", vm.awayEnergy);
      setStat("fastPortBadge", vm.fastPort);

      var schedToggleBtn = root.querySelector('[data-bind="schedToggleBtn"]');
      if (schedToggleBtn && vm.schedSwitch) {
        var scOn = this._isOn(vm.schedSwitch);
        this._applyBtnState(schedToggleBtn, t.scheduledCharging + ": " + (scOn ? t.on : t.off), "scheduled_charging_toggle", "scheduled_charging_toggle", scOn ? "is-emerald" : "", t, "calendar");
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

      // Segmented mode: Orario manuale vs Segui partenza
      this._syncChargeState = vm.syncCharge ? { id: vm.syncCharge.id, on: this._isOn(vm.syncCharge) } : null;
      var isDepMode = Boolean(this._syncChargeState && this._syncChargeState.on);
      var modeManualBtn = root.querySelector('[data-charge-mode="manual"]');
      var modeDepBtn = root.querySelector('[data-charge-mode="departure"]');
      if (modeManualBtn) {
        modeManualBtn.classList.toggle("is-active", !isDepMode);
        modeManualBtn.setAttribute("aria-pressed", !isDepMode ? "true" : "false");
      }
      if (modeDepBtn) {
        modeDepBtn.classList.toggle("is-active", isDepMode);
        modeDepBtn.setAttribute("aria-pressed", isDepMode ? "true" : "false");
      }
      var manualBox = root.querySelector('[data-bind="manualChargeBox"]');
      var depBox = root.querySelector('[data-bind="departureChargeBox"]');
      if (manualBox) manualBox.classList.toggle("hidden", isDepMode);
      if (depBox) depBox.classList.toggle("hidden", !isDepMode);
      var depChargeStartEl = root.querySelector('[data-bind="depChargeStartText"]');
      if (depChargeStartEl) {
        var pStartChg = vm.nextDep && vm.nextDep.s && vm.nextDep.s.attributes && vm.nextDep.s.attributes.planned_charge_start;
        if (pStartChg) {
          var nextDepState = (vm.nextDep && !this._dead(vm.nextDep.s)) ? (" · " + vm.nextDep.s.state) : "";
          depChargeStartEl.textContent = t.chargeStartHint + ": " + pStartChg + nextDepState;
        } else {
          depChargeStartEl.textContent = t.noDeparturePlanned;
        }
      }

      // L-D charge days + quick presets + optimistic reconciliation
      this._chargeDaysEntityId = vm.chgDays ? vm.chgDays.id : null;
      var entityDays = (vm.chgDays && vm.chgDays.s && vm.chgDays.s.attributes && normalizeDaysList(vm.chgDays.s.attributes.days)) ||
        (vm.chgDays && vm.chgDays.s && presetDaysForKey(vm.chgDays.s.state)) ||
        (vm.schedWindow && vm.schedWindow.s && vm.schedWindow.s.attributes && normalizeDaysList(vm.schedWindow.s.attributes.days)) ||
        [1, 2, 3, 4, 5, 6, 7];
      var entityDaysSig = entityDays.join(",");
      var activeChargeDays = entityDays;
      if (this._optimisticChargeDays) {
        if (this._optimisticChargeDays.baseSig === entityDaysSig) {
          activeChargeDays = this._optimisticChargeDays.days;
        } else {
          this._optimisticChargeDays = null;
        }
      }
      this._currentChargeDays = activeChargeDays.slice();
      this._currentChargeDaysBaseSig = entityDaysSig;

      var activeDaySet = Object.create(null);
      for (var adi = 0; adi < activeChargeDays.length; adi += 1) {
        activeDaySet[activeChargeDays[adi]] = true;
      }
      var isDaysPending = this._pendingKeys.has("charge_days_select");
      var chgDayChips = root.querySelectorAll("[data-charge-day]");
      for (var cdi = 0; cdi < chgDayChips.length; cdi += 1) {
        var chipDay = parseInt(chgDayChips[cdi].getAttribute("data-charge-day"), 10);
        var dayOn = Boolean(activeDaySet[chipDay]);
        chgDayChips[cdi].classList.toggle("is-active", dayOn);
        chgDayChips[cdi].classList.toggle("is-pending", isDaysPending);
        chgDayChips[cdi].setAttribute("aria-pressed", dayOn ? "true" : "false");
      }
      var matchedPreset = presetForDays(activeChargeDays);
      var chgPresets = root.querySelectorAll("[data-charge-preset]");
      for (var cpi = 0; cpi < chgPresets.length; cpi += 1) {
        var pKey = chgPresets[cpi].getAttribute("data-charge-preset");
        var pOn = pKey === matchedPreset;
        chgPresets[cpi].classList.toggle("is-active", pOn);
        chgPresets[cpi].setAttribute("aria-pressed", pOn ? "true" : "false");
      }
      var presetLblEl = root.querySelector('[data-bind="chgDaysPresetLbl"]');
      if (presetLblEl) {
        presetLblEl.textContent = translateOption("charge_days", matchedPreset, vm.lang);
      }

      var syncInputVal = function (ent, slice5) {
        if (!ent || !ent.s) return;
        var el = root.querySelector('[data-entity-input="' + ent.id + '"]');
        if (!el || root.activeElement === el) return;
        var nextV = slice5 ? String(ent.s.state || "").slice(0, 5) : String(ent.s.state || "");
        if (!self._dead(ent.s)) el.value = nextV;
      };
      syncInputVal(vm.chgStartTime, true);
      syncInputVal(vm.quickDepTime, true);
      syncInputVal(vm.depCliMode, false);

      var chgDurEl = root.querySelector('[data-bind="chgDurText"]');
      if (chgDurEl && vm.chgDur) chgDurEl.textContent = this._dead(vm.chgDur.s) ? "—" : this._disp(vm.chgDur.s);

      // Departures
      var carActive = Boolean(vm.carActive);
      var haHasActiveDep = Boolean(vm.haHasActiveDep);

      var nextDepEl = root.querySelector('[data-bind="nextDepText"]');
      if (nextDepEl && vm.nextDep) {
        if (this._dead(vm.nextDep.s)) {
          nextDepEl.textContent = "—";
        } else if (!haHasActiveDep && carActive) {
          nextDepEl.textContent = t.departureActive;
        } else {
          nextDepEl.textContent = vm.nextDep.s.state;
        }
      }
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
        this._applyBtnState(qDepBtn, t.quickDeparture + ": " + (qOn ? t.on : t.off), "quick_departure_toggle", "quick_departure_toggle", qOn ? "is-emerald" : "", t, "clock");
      }
      for (var wi = 0; wi < vm.weekDays.length; wi += 1) {
        var wd = vm.weekDays[wi];
        var isExp = this._expandedDay === wd.slug;
        var dChip = root.querySelector('[data-day-chip="' + wd.slug + '"]');
        var dEnabled = this._isOn(wd.sw);
        if (dChip) {
          dChip.classList.toggle("is-enabled", dEnabled);
          dChip.classList.toggle("is-expanded", isExp);
        }
        var dTimeEl = root.querySelector('[data-day-time="' + wd.slug + '"]');
        if (dTimeEl) {
          var rawTm = (dEnabled && wd.tm && !this._dead(wd.tm.s)) ? String(wd.tm.s.state || "").slice(0, 5) : "";
          dTimeEl.textContent = rawTm;
        }
        var dEditor = root.querySelector('[data-day-editor="' + wd.slug + '"]');
        if (dEditor) {
          dEditor.classList.toggle("hidden", !isExp);
          dEditor.hidden = !isExp;
          if (isExp) {
            var expBtn = dEditor.querySelector('[data-bind="expandedDayToggle"]');
            if (expBtn && wd.sw) {
              var dOn = this._isOn(wd.sw);
              this._applyBtnState(expBtn, t.enableDay + ": " + (dOn ? t.on : t.off), "day_toggle_" + wd.slug, "day_toggle_" + wd.slug, dOn ? "is-emerald" : "", t, "calendar");
            }
            syncInputVal(wd.tm, true);
          }
        }
      }

      // Car scheduled departure readout & adaptive Apply/Disable on car button
      var schedDepTxt = root.querySelector('[data-bind="schedDepText"]');
      if (schedDepTxt && vm.schedDep) {
        if (this._dead(vm.schedDep.s)) {
          schedDepTxt.textContent = "—";
        } else if (carActive) {
          var sdAttrsActive = vm.schedDep.s.attributes || {};
          var rawOrario = sdAttrsActive.orario
            ? String(sdAttrsActive.orario)
            : (typeof vm.schedDep.s.state === "string" && /^\d{1,2}:\d{2}$/.test(vm.schedDep.s.state.trim())
              ? vm.schedDep.s.state.trim()
              : "");
          schedDepTxt.textContent = rawOrario
            ? formatCarNextDeparture(rawOrario, sdAttrsActive.giorni, new Date(), t)
            : (sdAttrsActive.riepilogo ? String(sdAttrsActive.riepilogo) : String(vm.schedDep.s.state));
        } else {
          schedDepTxt.textContent = t.noScheduledDeparture;
        }
      }
      var applyDepBtnEl = root.querySelector('[data-bind="applyDepBtn"]');
      if (applyDepBtnEl && vm.applyDepBtn) {
        if (haHasActiveDep) {
          applyDepBtnEl.classList.remove("hidden");
          this._applyBtnState(
            applyDepBtnEl,
            t.applyDeparture,
            "apply_departure_schedule",
            "apply_departure_schedule",
            "is-primary",
            t,
            "check"
          );
        } else if (carActive) {
          applyDepBtnEl.classList.remove("hidden");
          this._applyBtnState(
            applyDepBtnEl,
            t.disableOnCar,
            "apply_departure_schedule",
            "apply_departure_schedule",
            "",
            t,
            "wake"
          );
        } else {
          applyDepBtnEl.classList.add("hidden");
        }
      }

      // Dynamic departure climate extras (allowlisted + optimistic reconciliation)
      var rawEntityExtras = (vm.nextDep && vm.nextDep.s && vm.nextDep.s.attributes)
        ? vm.nextDep.s.attributes.climate_extras
        : null;
      var entityExtras = filterAllowedClimateExtras(rawEntityExtras);
      var entityExtrasSig = entityExtras.join(",");
      var activeClimateExtras = entityExtras;
      if (this._optimisticClimateExtras) {
        if (this._optimisticClimateExtras.baseSig === entityExtrasSig) {
          activeClimateExtras = this._optimisticClimateExtras.extras;
        } else {
          this._optimisticClimateExtras = null;
        }
      }
      this._currentClimateExtras = activeClimateExtras.slice();
      this._currentClimateExtrasBaseSig = entityExtrasSig;

      var activeExtraSet = Object.create(null);
      for (var aei = 0; aei < activeClimateExtras.length; aei += 1) {
        activeExtraSet[activeClimateExtras[aei]] = true;
      }
      var extraChips = root.querySelectorAll("[data-climate-extra]");
      for (var eci = 0; eci < extraChips.length; eci += 1) {
        var eKey = extraChips[eci].getAttribute("data-climate-extra");
        var eOn = Boolean(activeExtraSet[eKey]);
        var ePending = this._pendingKeys.has("climate_extra:" + eKey);
        extraChips[eci].classList.toggle("is-active", eOn);
        extraChips[eci].classList.toggle("is-pending", ePending);
        extraChips[eci].setAttribute("aria-pressed", eOn ? "true" : "false");
      }

      // Battery pack preheating (cat. 216)
      var batHeatBtn = root.querySelector('[data-bind="batteryHeatBtn"]');
      if (batHeatBtn && vm.batteryHeat) {
        var bhOn = this._isOn(vm.batteryHeat);
        this._applyBtnState(
          batHeatBtn,
          t.batteryPreheat + ": " + (bhOn ? t.on : t.off),
          "battery_pack_heat_toggle",
          "battery_pack_heat_toggle",
          bhOn ? "is-amber" : "",
          t,
          "flame"
        );
      }
      syncInputVal(vm.batteryHeatTime, true);
      var syncBatBtn = root.querySelector('[data-bind="syncBatteryHeatBtn"]');
      if (syncBatBtn && vm.syncBatteryHeat) {
        var sbhOn = this._isOn(vm.syncBatteryHeat);
        this._applyBtnState(
          syncBatBtn,
          t.syncBatteryHeat + ": " + (sbhOn ? t.on : t.off),
          "sync_battery_heat_toggle",
          "sync_battery_heat_toggle",
          sbhOn ? "is-emerald" : "",
          t,
          "clock"
        );
      }
      var batHintEl = root.querySelector('[data-bind="batteryHeatSyncHint"]');
      if (batHintEl) {
        var bStart = vm.nextDep && vm.nextDep.s && vm.nextDep.s.attributes && vm.nextDep.s.attributes.battery_heat_start;
        if (bStart) {
          batHintEl.classList.remove("hidden");
          batHintEl.textContent = t.batteryHeatHint + ": " + bStart;
        } else {
          batHintEl.classList.add("hidden");
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
      setBp("headlights", "is-on", Boolean(this._pendingKeys.has("flash_lights")));

      var bpLock = root.querySelector("[data-bp-lock]");
      if (bpLock) {
        bpLock.classList.toggle("is-unlocked", Boolean(vm.lock && vm.lock.s && vm.lock.s.state !== "locked"));
      }

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
      if (this._pendingDialogAction) {
        this._syncConfirmDialogTexts(t, this._pendingDialogAction.confirmLabel);
      }
    }
  }

  LepasCard._helpers = {
    CARD_VERSION: CARD_VERSION,
    COLORS: VALID_COLORS.slice(),
    COLOR_ALIASES: Object.assign({}, COLOR_ALIASES),
    VALID_TABS: VALID_TABS.slice(),
    VALID_LAYOUTS: VALID_LAYOUTS.slice(),
    CONFIRM_ACTIONS: CONFIRM_ACTIONS,
    resolveColor: resolveColor,
    resolveHeroImage: resolveHeroImage,
    sanitizeUrl: sanitizeUrl,
    escapeHtml: escapeHtml,
    requiresConfirmation: requiresConfirmation,
    formatCommandOutcome: formatCommandOutcome,
    getTexts: getTexts,
    formatMetric: formatMetric,
    translateOption: translateOption,
    computeToggleDays: computeToggleDays,
    presetForDays: presetForDays,
    presetDaysForKey: presetDaysForKey,
    ALLOWED_CLIMATE_EXTRAS: ALLOWED_CLIMATE_EXTRAS.slice(),
    filterAllowedClimateExtras: filterAllowedClimateExtras,
    computeToggleClimateExtras: computeToggleClimateExtras,
    formatCarNextDeparture: formatCarNextDeparture,
    svgIcon: svgIcon,
  };

  if (!customElements.get("lepas-card-editor")) {
    customElements.define("lepas-card-editor", LepasCardEditor);
  }
  if (!customElements.get("lepas-card")) {
    customElements.define("lepas-card", LepasCard);
  }
  window.customCards = window.customCards || [];
  if (!window.customCards.some(function (c) { return c.type === "lepas-card"; })) {
    window.customCards.push({
      type: "lepas-card",
      name: "Lepas Card",
      preview: true,
      description: "Matte Titanium OEM dashboard card for Lepas Connect (responsive 4-tab / cockpit, blueprint SVG, TPMS, climate, charging, departures).",
    });
  }
})();
