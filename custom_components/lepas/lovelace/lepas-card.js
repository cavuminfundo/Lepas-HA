/*
 * Lepas vehicle card — Dark Tech Automotive edition (Lepas Connect integration).
 *
 * At-a-glance: vehicle photo, name, battery %, estimated ranges, charging state,
 * and warnings (tyre / low battery / offline) shown only when active.
 * Responsive via CSS Container Queries and fully keyboard accessible.
 * Auto-discovers this integration's entities:
 *   type: custom:lepas-card
 * Options:
 *   title: "My Car"          # header title (default: the vehicle's name)
 *   image: "/local/car.png"  # header photo (overrides the one set in the integration options)
 *   show_all: true           # also list every remaining entity, grouped
 *   entities: [...]          # append your own rows (entity ids)
 *   integration: "lepas"     # platform to collect (default)
 *   prefix: "lepas_"         # object_id fallback prefix
 */
class LepasCard extends HTMLElement {
  setConfig(config) {
    this.config = Object.assign(
      { integration: "lepas", prefix: "lepas_", show_all: false },
      config || {}
    );
  }
  getCardSize() { return 4; }

  _dead(s) { return !s || ["unavailable", "unknown", ""].includes(s.state); }
  _num(s) { const n = s ? parseFloat(s.state) : NaN; return isNaN(n) ? null : n; }
  // Display a value the way Home Assistant would: respects the entity's display precision
  // and unit conversion.
  _disp(s) {
    const h = this._hass;
    if (h && typeof h.formatEntityState === "function") {
      try { return h.formatEntityState(s); } catch (e) { /* fall through */ }
    }
    const n = parseFloat(s.state);
    const u = s.attributes.unit_of_measurement;
    if (isNaN(n)) return u ? `${s.state} ${u}` : s.state;
    const dp = s.attributes.suggested_display_precision;
    const v = typeof dp === "number" ? n.toFixed(dp) : (Number.isInteger(n) ? `${n}` : `${Math.round(n)}`);
    return u ? `${v} ${u}` : v;
  }

  _collect(hass) {
    const c = this.config, out = [];
    const strip = (o) => o.startsWith(c.prefix) ? o.slice(c.prefix.length) : o;
    const reg = hass.entities;
    if (reg) for (const id in reg) {
      if (reg[id].platform !== c.integration) continue;
      const s = hass.states[id]; if (s) out.push({ id, key: strip(id.slice(id.indexOf(".") + 1)), s });
    }
    if (!out.length) for (const id in hass.states) {
      const o = id.slice(id.indexOf(".") + 1);
      if (o.startsWith(c.prefix)) out.push({ id, key: strip(o), s: hass.states[id] });
    }
    return out;
  }

  _find(items, ...keys) {
    for (const k of keys) { const f = items.find((r) => r.key === k); if (f) return f; }
    return null;
  }
  _esc(s) { return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
  _h(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  _imgUrl(s) {
    s = String(s || "");
    if (!/^(https?:\/\/|\/|data:image\/)/i.test(s)) return "";
    return s.replace(/["'()\\<>\s]/g, encodeURIComponent);
  }

  _batteryIcon(v, charging) {
    if (charging) return "mdi:battery-charging";
    if (isNaN(v)) return "mdi:battery";
    const s = Math.round(v / 10) * 10;
    return s >= 100 ? "mdi:battery" : s <= 0 ? "mdi:battery-outline" : `mdi:battery-${s}`;
  }
  _batteryColor(v) {
    if (isNaN(v)) return "#94A3B8";
    if (v <= 15) return "#ff5252";
    if (v <= 30) return "#f5a623";
    return "#00D2FF";
  }
  _moreInfo(id) {
    this.dispatchEvent(new CustomEvent("hass-more-info",
      { bubbles: true, composed: true, detail: { entityId: id } }));
  }
  _deviceId(hass, items) {
    const reg = hass.entities;
    if (!reg) return null;
    for (const { id } of items) { const d = reg[id] && reg[id].device_id; if (d) return d; }
    return null;
  }
  _navigate(path) {
    history.pushState(null, "", path);
    this.dispatchEvent(new Event("location-changed", { bubbles: true, composed: true }));
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.content) {
      const card = document.createElement("ha-card");
      const style = document.createElement("style");
      style.textContent = `
        ha-card {
          container-type: inline-size;
          background: #0F141C;
          border: 1px solid rgba(0, 210, 255, 0.16);
          border-radius: 16px;
          overflow: hidden;
          color: #F1F5F9;
          font-family: var(--ha-card-font-family, inherit);
        }
        .hero {
          position: relative;
          min-height: 180px;
          background-color: #0F141C;
          background-size: cover;
          background-position: center;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }
        .hero.photo { min-height: 200px; }
        .scrim {
          position: absolute;
          inset: 0;
          background: linear-gradient(180deg, rgba(15, 20, 28, 0.45) 0%, rgba(15, 20, 28, 0.1) 40%, rgba(15, 20, 28, 0.85) 90%, #0F141C 100%);
        }
        .hero-content {
          position: relative;
          width: 100%;
          padding: 16px;
          box-sizing: border-box;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          min-height: 200px;
        }
        .hero-top {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 8px;
        }
        .pill {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 4px 10px;
          border-radius: 999px;
          background: rgba(15, 20, 28, 0.75);
          border: 1px solid rgba(0, 210, 255, 0.2);
          font-size: 0.72rem;
          font-weight: 700;
          letter-spacing: 0.06em;
          color: #F1F5F9;
          -webkit-backdrop-filter: blur(6px);
          backdrop-filter: blur(6px);
        }
        .dot {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          display: inline-block;
        }
        .batt {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 5px 12px;
          cursor: pointer;
          background: rgba(15, 20, 28, 0.75);
          border: 1px solid rgba(0, 210, 255, 0.25);
          border-radius: 999px;
          -webkit-backdrop-filter: blur(8px);
          backdrop-filter: blur(8px);
          color: #F1F5F9;
        }
        .batt ha-icon { --mdc-icon-size: 20px; }
        .batt b { font-size: 1.05rem; font-weight: 700; }
        .hero-bottom {
          margin-top: auto;
        }
        .name {
          font-size: 1.35rem;
          font-weight: 700;
          line-height: 1.2;
          color: #F1F5F9;
          letter-spacing: -0.01em;
          text-shadow: 0 2px 6px rgba(0, 0, 0, 0.7);
        }
        .sub {
          font-size: 0.85rem;
          color: #94A3B8;
          margin-top: 4px;
          display: flex;
          align-items: center;
          gap: 8px;
          text-shadow: 0 1px 4px rgba(0, 0, 0, 0.6);
        }
        .sub ha-icon { --mdc-icon-size: 16px; color: #00D2FF; }
        .metrics {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 1px;
          background: rgba(0, 210, 255, 0.12);
          border-top: 1px solid rgba(0, 210, 255, 0.16);
        }
        @container (max-width: 380px) {
          .metrics {
            grid-template-columns: repeat(2, 1fr);
          }
        }
        .metric {
          background: #151D28;
          padding: 12px 6px;
          text-align: center;
          cursor: pointer;
          transition: background 0.15s ease;
        }
        .metric:hover {
          background: #1c2736;
        }
        .metric .v {
          font-size: 1.05rem;
          font-weight: 700;
          color: #F1F5F9;
          line-height: 1.2;
        }
        .metric .l {
          font-size: 0.72rem;
          letter-spacing: 0.03em;
          text-transform: uppercase;
          color: #94A3B8;
          margin-top: 4px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 4px;
        }
        .metric .l ha-icon {
          --mdc-icon-size: 14px;
          color: #00D2FF;
        }
        .warns {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          padding: 12px 14px;
          background: #0F141C;
          border-top: 1px solid rgba(0, 210, 255, 0.16);
        }
        .warn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          font-size: .82rem;
          font-weight: 600;
          color: #ff5252;
          background: rgba(255, 82, 82, 0.12);
          border: 1px solid rgba(255, 82, 82, 0.28);
          padding: 5px 12px;
          border-radius: 999px;
          cursor: pointer;
        }
        .warn ha-icon { --mdc-icon-size: 15px; }
        .grp {
          padding: 12px 16px 4px;
          font-weight: 600;
          font-size: .82rem;
          color: #00D2FF;
          text-transform: uppercase;
          letter-spacing: .05em;
          background: #0F141C;
          border-top: 1px solid rgba(0, 210, 255, 0.16);
        }
        .row {
          display: flex;
          justify-content: space-between;
          padding: 8px 16px;
          cursor: pointer;
          font-size: .92rem;
          background: #0F141C;
          color: #F1F5F9;
          transition: background 0.15s ease;
        }
        .row:hover {
          background: #151D28;
        }
        .row .val {
          font-weight: 600;
          color: #0A84FF;
        }
        [role="button"]:focus-visible {
          outline: 2px solid #00D2FF;
          outline-offset: -2px;
        }
      `;
      this.content = document.createElement("div");
      card.appendChild(style); card.appendChild(this.content); this.appendChild(card);
      const handleInteract = (target) => {
        const el = target.closest("[data-e]");
        if (el) { this._moreInfo(el.getAttribute("data-e")); return; }
        const dev = target.closest("[data-device]");
        if (dev && dev.getAttribute("data-device")) {
          this._navigate(`/config/devices/device/${dev.getAttribute("data-device")}`);
        }
      };
      this.content.addEventListener("click", (e) => {
        handleInteract(e.target);
      });
      this.content.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          const actionable = e.target.closest("[data-e], [data-device]");
          if (actionable) {
            e.preventDefault();
            handleInteract(actionable);
          }
        }
      });
    }
    try {
      this._render(hass);
    } catch (e) {
      this.content.innerHTML =
        `<div style="padding:16px;color:#ff5252">Lepas card error: ${e && e.message ? e.message : e}</div>`;
    }
  }

  _render(hass) {
    const cfg = this.config;
    const items = this._collect(hass);
    const nameHolder = items.find((r) => r.s && r.s.attributes && r.s.attributes.friendly_name);
    const nameSrc = nameHolder ? nameHolder.s.attributes.friendly_name : null;
    const device = nameSrc ? nameSrc.split(" ").slice(0, 2).join(" ") : "Lepas";
    const deviceRe = this._esc(device);
    const title = cfg.title || device;

    const bat = this._find(items, "battery") || items.find((r) =>
      r.s && r.s.attributes && r.s.attributes.device_class === "battery" && r.s.attributes.unit_of_measurement === "%");
    const evRange = this._find(items, "electric_range");
    const fuelRange = this._find(items, "fuel_range", "petrol_range_miles", "total_range");
    const chgPower = this._find(items, "charging_power");
    const chargeState = this._find(items, "charging_status");
    const charging = this._find(items, "charging");
    const plug = this._find(items, "charging_cable");
    const odo = this._find(items, "odometer");
    const conn = this._find(items, "connection");

    const isCharging = charging ? charging.s.state === "on"
      : (chargeState && /charg/i.test(chargeState.s.state) && !/not/i.test(chargeState.s.state));
    const batV = bat ? this._num(bat.s) : NaN;
    const isOnline = !conn || (conn.s && conn.s.state === "on");

    const lock = this._find(items, "lock");
    const lockText = lock && !this._dead(lock.s)
      ? (lock.s.state === "locked" ? "Locked" : "Unlocked") : "—";
    const lockIcon = lock && lock.s.state === "unlocked" ? "mdi:lock-open-variant" : "mdi:lock";

    const ac = this._find(items, "air_conditioner", "climate");
    const acOn = ac && !this._dead(ac.s) && (ac.s.state === "on" || ac.s.state === "cool" || ac.s.state === "heat");

    // ---- hero (photo, dark-studio fallback or gradient) ----
    const imgAttr = items.map((r) => r.s && r.s.attributes && r.s.attributes.vehicle_image).find(Boolean);
    const img = cfg.image || imgAttr || "/lepas_card/lepas-hero.png?v=1.15.1";
    const safeImg = this._imgUrl(img);
    const deviceId = this._deviceId(hass, items);

    const connDotColor = isOnline ? "#00D2FF" : "#94A3B8";

    let subParts = [];
    if (isCharging) {
      subParts.push('<ha-icon icon="mdi:flash"></ha-icon>Charging');
    }
    subParts.push('<ha-icon icon="' + lockIcon + '"></ha-icon>' + this._h(lockText));
    if (acOn) {
      subParts.push('<ha-icon icon="mdi:fan"></ha-icon>Climate On');
    }
    const sub = '<div class="sub">' + subParts.join(' <span style="opacity:0.35">·</span> ') + '</div>';

    const battBadge = (bat && !this._dead(bat.s))
      ? `<div class="batt" role="button" tabindex="0" data-e="${this._h(bat.id)}">
           <ha-icon icon="${this._batteryIcon(batV, isCharging)}" style="color:${this._batteryColor(batV)}"></ha-icon>
           <b>${isNaN(batV) ? this._h(bat.s.state) : Math.round(batV)}%</b></div>`
      : "";

    const hero = `
      <div class="hero ${safeImg ? "photo" : ""}" style="${safeImg ? `background-image:url('${safeImg}')` : ""}"
           ${deviceId ? `role="button" tabindex="0" data-device="${this._h(deviceId)}"` : ""}>
        <div class="scrim"></div>
        <div class="hero-content">
          <div class="hero-top">
            <div class="pill">
              <span class="dot" style="background:${connDotColor}"></span>
              <span>LEPAS CONNECT</span>
            </div>
            ${battBadge}
          </div>
          <div class="hero-bottom">
            <div class="name">${this._h(title)}</div>
            ${sub}
          </div>
        </div>
      </div>`;

    // ---- 4 metrics strip (EV Range · Fuel/Total · Charging · Odometer) ----
    const metric = (label, icon, value, entityId) => {
      const isActionable = Boolean(entityId);
      return `
        <div class="metric" ${isActionable ? `role="button" tabindex="0" data-e="${this._h(entityId)}"` : ""}>
          <div class="v">${this._h(value)}</div>
          <div class="l"><ha-icon icon="${icon}"></ha-icon>${this._h(label)}</div>
        </div>`;
    };

    // 1) EV Range
    const evVal = evRange && !this._dead(evRange.s) ? this._disp(evRange.s) : "—";
    const evId = evRange ? evRange.id : null;

    // 2) Fuel / Total Range
    const fuelVal = fuelRange && !this._dead(fuelRange.s) ? this._disp(fuelRange.s) : "—";
    const fuelLabel = fuelRange && fuelRange.key === "total_range" ? "Total Range" : "Fuel Range";
    const fuelIcon = fuelRange && fuelRange.key === "total_range" ? "mdi:map-marker-distance" : "mdi:gas-station";
    const fuelId = fuelRange ? fuelRange.id : null;

    // 3) Charging Power / State
    let chgVal = "Idle";
    let chgLabel = "Charging";
    let chgIcon = "mdi:power-plug";
    let chgId = null;
    if (isCharging) {
      if (chgPower && !this._dead(chgPower.s) && this._num(chgPower.s) > 0) {
        chgVal = this._disp(chgPower.s);
        chgIcon = "mdi:ev-station";
        chgId = chgPower.id;
      } else {
        chgVal = "Charging";
        chgIcon = "mdi:battery-charging";
        chgId = charging ? charging.id : (chargeState ? chargeState.id : null);
      }
    } else if (chargeState && !this._dead(chargeState.s)) {
      chgVal = chargeState.s.state;
      chgId = chargeState.id;
    } else if (charging && !this._dead(charging.s)) {
      chgVal = charging.s.state === "on" ? "Charging" : "Idle";
      chgId = charging.id;
    }

    // 4) Odometer / Cable
    let odoVal = "—";
    let odoLabel = "Odometer";
    let odoIcon = "mdi:counter";
    let odoId = null;
    if (odo && !this._dead(odo.s)) {
      odoVal = this._disp(odo.s);
      odoId = odo.id;
    } else if (plug && !this._dead(plug.s)) {
      odoVal = plug.s.state === "on" ? "Plugged in" : "Unplugged";
      odoLabel = "Cable";
      odoIcon = "mdi:power-plug";
      odoId = plug.id;
    }

    const metrics = `
      <div class="metrics">
        ${metric("EV Range", "mdi:lightning-bolt-circle", evVal, evId)}
        ${metric(fuelLabel, fuelIcon, fuelVal, fuelId)}
        ${metric(chgLabel, chgIcon, chgVal, chgId)}
        ${metric(odoLabel, odoIcon, odoVal, odoId)}
      </div>`;

    // ---- warnings (only active) ----
    const warns = [];
    items.filter((r) => /tire.*warning|tyre.*warning/.test(r.key) && r.s && r.s.state === "on")
      .forEach((r) => warns.push({ id: r.id, icon: "mdi:car-tire-alert",
        text: (r.s.attributes.friendly_name || r.key).replace(new RegExp("^" + deviceRe + "\\s*", "i"), "").replace(/warning/i, "").trim() }));
    const low = this._find(items, "low_battery");
    if (low && low.s && low.s.state === "on") warns.push({ id: low.id, icon: "mdi:battery-alert", text: "Battery low" });
    if (conn && conn.s && conn.s.state === "off") warns.push({ id: conn.id, icon: "mdi:wifi-off", text: "Offline" });
    const warnHtml = warns.length ? `
      <div class="warns">
        ${warns.map((w) => `
          <div class="warn" role="button" tabindex="0" data-e="${this._h(w.id)}">
            <ha-icon icon="${w.icon}"></ha-icon>${this._h(w.text)}
          </div>`).join("")}
      </div>` : "";

    // ---- optional extra rows / full list ----
    let extra = "";
    const used = new Set([bat, evRange, fuelRange, chgPower, chargeState, charging, plug, odo, low, conn].filter(Boolean).map((r) => r.id));
    const rowFor = (id) => {
      const s = hass.states[id]; if (!s) return "";
      const name = (s.attributes.friendly_name || id).replace(new RegExp("^" + deviceRe + "\\s*", "i"), "").trim() || id;
      return `<div class="row" role="button" tabindex="0" data-e="${this._h(id)}"><div>${this._h(name)}</div><div class="val">${this._h(this._disp(s))}</div></div>`;
    };
    if (Array.isArray(cfg.entities) && cfg.entities.length) {
      extra = `<div class="grp">Details</div>` + cfg.entities.map((e) => rowFor(typeof e === "string" ? e : e.entity)).join("");
    } else if (cfg.show_all) {
      const rest = items.filter((r) => !used.has(r.id) && !this._dead(r.s) && r.s.attributes.entity_category !== "diagnostic");
      if (rest.length) extra = `<div class="grp">More</div>` +
        rest.sort((a, b) => a.key.localeCompare(b.key)).map((r) => rowFor(r.id)).join("");
    }

    this.content.innerHTML = hero + metrics + warnHtml + extra;
  }

  static getStubConfig() { return { type: "custom:lepas-card" }; }
}
if (!customElements.get("lepas-card")) {
  customElements.define("lepas-card", LepasCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "lepas-card")) {
  window.customCards.push({
    type: "lepas-card",
    name: "Lepas Card",
    preview: true,
    description: "Sleek summary card for the Lepas Connect integration (photo, battery, range, charging, warnings).",
  });
}
