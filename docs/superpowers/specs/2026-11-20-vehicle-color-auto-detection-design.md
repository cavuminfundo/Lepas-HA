# Design Spec — Auto-rilevamento Colore Veicolo (`vmc/queryList` → `lepas-card.js`)

**Data:** 2026-11-20
**Stato:** Approvato come Approccio A in brainstorming; pronto per audit e pianificazione esecutiva
**Obiettivo:** Estrarre automaticamente il colore reale del veicolo da `POST /tsp/v1/app/vmc/queryList` (`colorCode` / `colorNameEn`), persisterlo in `entry.data` (con backfill automatico tramite marcatore `DATA_CAPS_PROBED_V6`), esporlo come attributo non-PII su `LepasSessionStatus` e usarlo come colore predefinito `"auto"` nella Lovelace card (`lepas-card.js`) sia per l'immagine hero sia per il Blueprint SVG.

---

## 1. Perimetro & Esclusioni Esplicite (YAGNI)
- **Incluso:** estrazione e normalizzazione colore da `vmc/queryList` (`colorCode`, `colorNameEn`, `colorName`), persistenza in `entry.data`, esposizione in `extra_state_attributes` su `LepasSessionStatus`, sezione diagnostica `vehicle`, selezione automatica `"auto"` in `lepas-card.js` + `LepasCardEditor`.
- **Escluso esplicitamente:**
  - `skylightType` (`0` confermato su Lepas L8 dotata di tetto apribile di serie → NON va usato per filtrare entità);
  - `dynamicPureElectricRange`, `electricRange`, `chargingCutOffSOC`, `carPicture` (URL remoto UAT), e funzionalità tagliando/service.

---

## 2. Architettura & Flusso Dati

### 2.1 Costanti e Normalizzazione (`custom_components/lepas/const.py`)
- Nuove chiavi in `entry.data`:
  - `DATA_VEHICLE_COLOR = "vehicle_color"` (`"black" | "grey" | "teal" | "violet" | "white"`)
  - `DATA_VEHICLE_COLOR_CODE = "vehicle_color_code"` (stringa grezza da `colorCode`, es. `"KME8"`)
  - `DATA_VEHICLE_COLOR_NAME = "vehicle_color_name"` (stringa grezza da `colorNameEn` / fallback `colorName`)
  - `DATA_CAPS_PROBED_V6 = "caps_probed_v6"`
- Tabella & funzione pura:
  - `VEHICLE_COLOR_CODE_MAP = {"KME8": "black"}`
  - `normalize_vehicle_color(code: object, name_en: object, name_local: object = None) -> str | None`:
    1. Se `code` ripulito/maiuscolo è in `VEHICLE_COLOR_CODE_MAP`, ritorna il colore canonico.
    2. Altrimenti tokenizza alfabeticamente (`[a-z]+`) `name_en` (poi `name_local`) per evitare falsi positivi da substring (`AB-HA-001`) e mappa:
       - `{"black", "nero", "zwart"}` → `"black"`
       - `{"white", "bianco", "wit"}` → `"white"`
       - `{"grey", "gray", "grigio", "grijs", "silver"}` → `"grey"`
       - `{"teal", "ottanio", "petrolio", "green", "verde", "zeegroen", "cyan", "emerald"}` → `"teal"`
       - `{"violet", "viola", "purple", "ametista"}` → `"violet"`
    3. Altrimenti `None` (fail-open).
- In `capabilities_from_item(item)`: estrae `colorCode` e `colorNameEn`/`colorName` (stringhe non vuote, max 64 caratteri), valorizza `DATA_VEHICLE_COLOR_CODE`, `DATA_VEHICLE_COLOR_NAME` e, se riconosciuto, `DATA_VEHICLE_COLOR`.

### 2.2 Coordinator & Backfill (`custom_components/lepas/coordinator.py`, `diagnostics.py`)
- `LepasCoordinator.__init__`: legge `self.vehicle_color`, `self.vehicle_color_code`, `self.vehicle_color_name` da `cfg`.
- `async_ensure_vehicle_identity`:
  - Verifica `caps_da_leggere = not self.entry.data.get(DATA_CAPS_PROBED_V6)` (backfill una-tantum sulle installazioni `V5` esistenti).
  - `_fetch_vehicle_identity` scrive `DATA_CAPS_PROBED_V6: True` insieme a `DATA_CAPS_PROBED..V5` e `**capabilities_from_item(item)`.
  - Aggiorna subito `self.vehicle_color`, `self.vehicle_color_code`, `self.vehicle_color_name` in memoria se presenti in `info`, poi persiste `entry.data` e chiama `self.async_update_listeners()` se il colore è stato aggiornato (senza forzare reload extra quando `vehicle_features` non ha `False`).
- `diagnostics.py`: aggiunge `color`, `color_code`, `color_name` (non-PII) dentro `diag["vehicle"]`.

### 2.3 Esposizione Attributi (`custom_components/lepas/sensor.py`)
- Su `LepasSessionStatus` (`sensor.lepas_session_status`, sempre presente su ogni veicolo):
  - Aggiunge `extra_state_attributes` con le sole chiavi valorizzate tra `vehicle_color`, `vehicle_color_code`, `vehicle_color_name` (ritorna `None` se nessuna è valorizzata).
  - Zero nuove entità create nel registro di Home Assistant.

### 2.4 Card Lovelace & Editor (`custom_components/lepas/lovelace/lepas-card.js`)
- Precedenza risoluzione colore (`resolveCardColor(config, items)`):
  1. Se `config.color` è valorizzato e diverso da `"auto"` (case-insensitive): ritorna `resolveColor(config.color)` (override manuale o fallback `"grey"` per valori sconosciuti — retrocompatibile al 100%).
  2. Altrimenti (quando `config.color` è vuoto/`undefined`/`"auto"`): cerca in `items` `attributes.vehicle_color`, poi `attributes.vehicle_color_name` (token match / `COLOR_ALIASES`), poi `attributes.vehicle_color_code` (`KME8` → `"black"`).
  3. Fallback finale: `"grey"`.
- Precedenza immagine hero (`resolveHeroImage(config, items)`): `config.image` → `attributes.vehicle_image` → `HERO_IMAGES[resolveCardColor(config, items)]` → `DEFAULT_HERO`.
- Blueprint SVG: sia il render iniziale (`.bp-stage[data-car-color]`) sia l'aggiornamento reattivo in `_applyBindingsInner` usano `resolveCardColor(cfg, items)`.
- Editor (`LepasCardEditor`): aggiunge lo swatch `"auto"` (localizzato `"Auto"` in IT/EN/NL) prima dei 5 colori in `VALID_COLORS`. Cliccando `"auto"` emette `{ color: "" }`, evidenziato come selezionato quando `!cfg.color || cfg.color === "auto"`. `LepasCard._helpers.COLORS` resta invariato (`["grey", "teal", "violet", "black", "white"]`).

---

## 3. Vincoli, Sicurezza & Test Falsificabili
- **Zero PII/segreti:** nessun VIN, token o coordinata negli attributi né nel DOM (`tests/lepas_card.test.mjs`).
- **Compatibilità WebView:** niente optional chaining (`?.`) né nullish coalescing (`??`) in `lepas-card.js`.
- **Test falsificabili:**
  - Python (`tests/test_vehicle_color.py` o `tests/test_native_departure_battery.py` + `tests/test_sensors.py`): `normalize_vehicle_color()` su `KME8`, `"New Carbon Black"`, stringhe ambigue/vuote; `capabilities_from_item()` estrazione colore; backfill `V5 → V6` che popola `coordinator.vehicle_color` e `LepasSessionStatus.extra_state_attributes` e non ripete `queryList` al secondo giro;
  - JS (`tests/lepas_card.test.mjs`): `resolveCardColor` / `resolveHeroImage` / `.bp-stage[data-car-color]` con `cfg.color` assente o `"auto"` + entità con `vehicle_color: "black"` (e solo `vehicle_color_name: "New Carbon Black"` / `vehicle_color_code: "KME8"`), precedenza override manuale `cfg.color: "teal"` su `vehicle_color: "black"`, precedenza `vehicle_image`, selezione `"auto"` in `LepasCardEditor`.
