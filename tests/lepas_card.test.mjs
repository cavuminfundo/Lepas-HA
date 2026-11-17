import test from "node:test";
import assert from "node:assert/strict";

// ---- Minimal real-tree DOM / CustomElements / ShadowDOM shim for Node 20+ ----
const VOID_TAGS = new Set([
  "area", "base", "br", "col", "embed", "hr", "img", "input",
  "link", "meta", "param", "source", "track", "wbr",
]);

function decodeEntities(str) {
  return String(str)
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, "&");
}

function escapeAttr(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

class MiniEvent {
  constructor(type, init = {}) {
    this.type = String(type);
    this.bubbles = Boolean(init.bubbles);
    this.composed = Boolean(init.composed);
    this.cancelable = Boolean(init.cancelable);
    this.defaultPrevented = false;
    this.propagationStopped = false;
    this.target = null;
    this.currentTarget = null;
    this.key = init.key || "";
  }
  preventDefault() {
    if (this.cancelable) this.defaultPrevented = true;
  }
  stopPropagation() {
    this.propagationStopped = true;
  }
}

class MiniCustomEvent extends MiniEvent {
  constructor(type, init = {}) {
    super(type, init);
    this.detail = init.detail !== undefined ? init.detail : null;
  }
}

class MiniStyle {
  constructor(owner) {
    this._owner = owner;
    this._map = Object.create(null);
  }
  set cssText(val) {
    this._map = Object.create(null);
    for (const part of String(val || "").split(";")) {
      const idx = part.indexOf(":");
      if (idx > 0) {
        const k = part.slice(0, idx).trim();
        const v = part.slice(idx + 1).trim();
        if (k) this._map[k] = v;
      }
    }
  }
  get cssText() {
    return Object.entries(this._map)
      .map(([k, v]) => `${k}:${v}`)
      .join(";");
  }
  setProperty(k, v) {
    if (v == null || v === "") delete this._map[k];
    else this._map[k] = String(v);
  }
  getPropertyValue(k) {
    return this._map[k] || "";
  }
}

class MiniClassList {
  constructor(el) {
    this._el = el;
  }
  _list() {
    const raw = this._el.getAttribute("class") || "";
    return raw.trim() ? raw.trim().split(/\s+/) : [];
  }
  _save(arr) {
    if (arr.length) this._el.setAttribute("class", arr.join(" "));
    else this._el.removeAttribute("class");
  }
  contains(cls) {
    return this._list().includes(cls);
  }
  add(...tokens) {
    const arr = this._list();
    for (const t of tokens) {
      if (t && !arr.includes(t)) arr.push(t);
    }
    this._save(arr);
  }
  remove(...tokens) {
    const arr = this._list().filter((c) => !tokens.includes(c));
    this._save(arr);
  }
  toggle(token, force) {
    const has = this.contains(token);
    const shouldHave = force === undefined ? !has : Boolean(force);
    if (shouldHave) this.add(token);
    else this.remove(token);
    return shouldHave;
  }
}

function splitTopLevelSelectors(selector) {
  const out = [];
  let depth = 0;
  let quote = "";
  let start = 0;
  for (let i = 0; i < selector.length; i += 1) {
    const ch = selector[i];
    if (quote) {
      if (ch === quote && selector[i - 1] !== "\\") quote = "";
      continue;
    }
    if (ch === '"' || ch === "'") {
      quote = ch;
    } else if (ch === "[" || ch === "(") {
      depth += 1;
    } else if (ch === "]" || ch === ")") {
      depth = Math.max(0, depth - 1);
    } else if (ch === "," && depth === 0) {
      out.push(selector.slice(start, i).trim());
      start = i + 1;
    }
  }
  const tail = selector.slice(start).trim();
  if (tail) out.push(tail);
  return out;
}

function tokenizeCompound(part) {
  const tokens = [];
  let i = 0;
  while (i < part.length) {
    const ch = part[i];
    if (ch === "#") {
      i += 1;
      const m = part.slice(i).match(/^[A-Za-z0-9_-]+/);
      if (!m) break;
      tokens.push({ kind: "id", value: m[0] });
      i += m[0].length;
    } else if (ch === ".") {
      i += 1;
      const m = part.slice(i).match(/^[A-Za-z0-9_-]+/);
      if (!m) break;
      tokens.push({ kind: "class", value: m[0] });
      i += m[0].length;
    } else if (ch === "[") {
      const end = part.indexOf("]", i);
      if (end < 0) break;
      const inner = part.slice(i + 1, end).trim();
      const eq = inner.indexOf("=");
      if (eq < 0) {
        tokens.push({ kind: "attr", name: inner.toLowerCase(), value: null });
      } else {
        let name = inner.slice(0, eq).trim();
        let op = "=";
        if (name.endsWith("*") || name.endsWith("^") || name.endsWith("$")) {
          op = name.slice(-1) + "=";
          name = name.slice(0, -1).trim();
        }
        let val = inner.slice(eq + 1).trim();
        if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
          val = val.slice(1, -1);
        }
        tokens.push({ kind: "attr", name: name.toLowerCase(), op, value: val });
      }
      i = end + 1;
    } else {
      const m = part.slice(i).match(/^[A-Za-z0-9_*-]+/);
      if (!m) {
        i += 1;
        continue;
      }
      if (m[0] !== "*") tokens.push({ kind: "tag", value: m[0].toLowerCase() });
      i += m[0].length;
    }
  }
  return tokens;
}

function splitChain(singleSelector) {
  const segments = [];
  let buf = "";
  let depth = 0;
  let quote = "";
  for (let i = 0; i < singleSelector.length; i += 1) {
    const ch = singleSelector[i];
    if (quote) {
      buf += ch;
      if (ch === quote && singleSelector[i - 1] !== "\\") quote = "";
      continue;
    }
    if (ch === '"' || ch === "'") {
      quote = ch;
      buf += ch;
    } else if (ch === "[" || ch === "(") {
      depth += 1;
      buf += ch;
    } else if (ch === "]" || ch === ")") {
      depth = Math.max(0, depth - 1);
      buf += ch;
    } else if (depth === 0 && (ch === ">" || /\s/.test(ch))) {
      if (buf.trim()) segments.push({ type: "sel", value: buf.trim() });
      buf = "";
      if (ch === ">") {
        if (segments.length && segments[segments.length - 1].type !== "comb") {
          segments.push({ type: "comb", value: ">" });
        }
      } else if (segments.length && segments[segments.length - 1].type === "sel") {
        segments.push({ type: "comb", value: " " });
      }
    } else {
      buf += ch;
    }
  }
  if (buf.trim()) segments.push({ type: "sel", value: buf.trim() });
  while (segments.length && segments[segments.length - 1].type === "comb") segments.pop();
  return segments;
}

const _parsedSelectorCache = new Map();
function getParsedSelector(selector) {
  let compiled = _parsedSelectorCache.get(selector);
  if (!compiled) {
    compiled = splitTopLevelSelectors(selector).map((part) =>
      splitChain(part).map((seg) =>
        seg.type === "sel" ? { type: "sel", tokens: tokenizeCompound(seg.value) } : seg
      )
    );
    _parsedSelectorCache.set(selector, compiled);
  }
  return compiled;
}

function matchesTokens(el, tokens) {
  if (!el || el.nodeType !== 1 || !tokens.length) return false;
  for (const tok of tokens) {
    if (tok.kind === "tag" && el._tag !== tok.value) return false;
    if (tok.kind === "id" && el.getAttribute("id") !== tok.value) return false;
    if (tok.kind === "class" && !el.classList.contains(tok.value)) return false;
    if (tok.kind === "attr") {
      const attrVal = el.getAttribute(tok.name);
      if (tok.value === null) {
        if (attrVal === null) return false;
      } else if (attrVal === null) {
        return false;
      } else if (tok.op === "=" && attrVal !== tok.value) {
        return false;
      } else if (tok.op === "*=" && !attrVal.includes(tok.value)) {
        return false;
      } else if (tok.op === "^=" && !attrVal.startsWith(tok.value)) {
        return false;
      } else if (tok.op === "$=" && !attrVal.endsWith(tok.value)) {
        return false;
      }
    }
  }
  return true;
}

function matchesCompiledChain(el, segs) {
  if (!segs.length) return false;
  let idx = segs.length - 1;
  if (!matchesTokens(el, segs[idx].tokens)) return false;
  let cur = el;
  idx -= 1;
  while (idx >= 0) {
    const comb = segs[idx].value;
    const prevTokens = segs[idx - 1].tokens;
    if (comb === ">") {
      cur = cur.parentNode;
      if (!cur || !matchesTokens(cur, prevTokens)) return false;
    } else {
      let anc = cur.parentNode;
      let matched = null;
      while (anc) {
        if (anc.nodeType === 1 && matchesTokens(anc, prevTokens)) {
          matched = anc;
          break;
        }
        anc = anc.parentNode;
      }
      if (!matched) return false;
      cur = matched;
    }
    idx -= 2;
  }
  return true;
}

function matchesSelector(el, selector) {
  const compiled = getParsedSelector(selector);
  for (const chain of compiled) {
    if (matchesCompiledChain(el, chain)) return true;
  }
  return false;
}

function parseAttributes(attrStr) {
  const attrs = Object.create(null);
  const re = /([A-Za-z_:][A-Za-z0-9_.:-]*)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
  let m;
  while ((m = re.exec(attrStr)) !== null) {
    const name = m[1].toLowerCase();
    const val = m[2] !== undefined ? m[2] : (m[3] !== undefined ? m[3] : (m[4] !== undefined ? m[4] : ""));
    attrs[name] = decodeEntities(val);
  }
  return attrs;
}

function parseHtmlInto(parent, html) {
  const stack = [parent];
  const src = String(html || "");
  let pos = 0;
  const tagRe = /<!--[\s\S]*?-->|<\/([A-Za-z0-9_-]+)\s*>|<([A-Za-z0-9_-]+)([^>]*?)(\/?)>/g;
  let m;
  while ((m = tagRe.exec(src)) !== null) {
    const top = stack[stack.length - 1];
    if (m.index > pos) {
      const txt = src.slice(pos, m.index);
      if (top._tag === "style" || top._tag === "script") {
        top.appendChild(new MiniText(txt));
      } else {
        top.appendChild(new MiniText(decodeEntities(txt)));
      }
    }
    pos = tagRe.lastIndex;
    if (m[0].startsWith("<!--")) continue;
    if (m[1]) {
      const closing = m[1].toLowerCase();
      for (let i = stack.length - 1; i >= 1; i -= 1) {
        if (stack[i]._tag === closing) {
          stack.length = i;
          break;
        }
      }
      continue;
    }
    const tag = m[2].toLowerCase();
    const attrs = parseAttributes(m[3] || "");
    const selfClose = Boolean(m[4]) || VOID_TAGS.has(tag);
    const el = new MiniElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      el.setAttribute(k, v);
    }
    top.appendChild(el);
    if (tag === "style") {
      // Capture raw style block until </style>
      const closeIdx = src.toLowerCase().indexOf("</style>", pos);
      if (closeIdx >= 0) {
        el.appendChild(new MiniText(src.slice(pos, closeIdx)));
        pos = closeIdx + "</style>".length;
        tagRe.lastIndex = pos;
        continue;
      }
    }
    if (!selfClose) {
      stack.push(el);
    }
  }
  if (pos < src.length) {
    stack[stack.length - 1].appendChild(new MiniText(decodeEntities(src.slice(pos))));
  }
}

class MiniText {
  constructor(text) {
    this.nodeType = 3;
    this.nodeValue = String(text);
    this.parentNode = null;
  }
  get textContent() {
    return this.nodeValue;
  }
  set textContent(v) {
    this.nodeValue = String(v == null ? "" : v);
  }
}

class MiniNodeContainer {
  constructor() {
    this.childNodes = [];
    this.parentNode = null;
    this._listeners = Object.create(null);
  }
  get children() {
    return this.childNodes.filter((n) => n.nodeType === 1);
  }
  appendChild(node) {
    if (node.parentNode && typeof node.parentNode.removeChild === "function") {
      node.parentNode.removeChild(node);
    }
    node.parentNode = this;
    this.childNodes.push(node);
    return node;
  }
  removeChild(node) {
    const idx = this.childNodes.indexOf(node);
    if (idx >= 0) {
      this.childNodes.splice(idx, 1);
      node.parentNode = null;
    }
    return node;
  }
  replaceChildren(...nodes) {
    for (const child of [...this.childNodes]) this.removeChild(child);
    for (const n of nodes) this.appendChild(n);
  }
  addEventListener(type, fn) {
    if (!this._listeners[type]) this._listeners[type] = [];
    this._listeners[type].push(fn);
  }
  removeEventListener(type, fn) {
    if (!this._listeners[type]) return;
    this._listeners[type] = this._listeners[type].filter((f) => f !== fn);
  }
  dispatchEvent(ev) {
    if (!ev.target) ev.target = this;
    let cur = this;
    while (cur) {
      ev.currentTarget = cur;
      const fns = (cur._listeners && cur._listeners[ev.type]) ? [...cur._listeners[ev.type]] : [];
      for (const fn of fns) {
        fn.call(cur, ev);
      }
      if (ev.propagationStopped || !ev.bubbles) break;
      if (cur.nodeType === 11) {
        if (!ev.composed) break;
        cur = cur.host || null;
      } else {
        cur = cur.parentNode || null;
      }
    }
    return !ev.defaultPrevented;
  }
  querySelectorAll(selector) {
    const res = [];
    const walk = (node) => {
      for (const ch of node.childNodes) {
        if (ch.nodeType === 1) {
          if (matchesSelector(ch, selector)) res.push(ch);
          walk(ch);
        }
      }
    };
    walk(this);
    return res;
  }
  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }
  get textContent() {
    return this.childNodes.map((c) => c.textContent).join("");
  }
  set textContent(v) {
    this.childNodes = [];
    if (v !== null && v !== undefined && String(v) !== "") {
      this.appendChild(new MiniText(String(v)));
    }
  }
  get innerHTML() {
    const isRawText = this._tag === "style" || this._tag === "script";
    return this.childNodes.map((c) => {
      if (c.nodeType === 3) {
        if (isRawText) return c.nodeValue;
        return String(c.nodeValue)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;");
      }
      return c.outerHTML;
    }).join("");
  }
  set innerHTML(html) {
    this.childNodes = [];
    parseHtmlInto(this, html);
  }
}

class MiniShadowRoot extends MiniNodeContainer {
  constructor(host) {
    super();
    this.nodeType = 11;
    this.host = host;
    this.activeElement = null;
  }
}

class MiniElement extends MiniNodeContainer {
  constructor(tagName) {
    super();
    this.nodeType = 1;
    this._tag = String(tagName || "div").toLowerCase();
    this.tagName = this._tag.toUpperCase();
    this._attrs = Object.create(null);
    this.style = new MiniStyle(this);
    this.classList = new MiniClassList(this);
    this.shadowRoot = null;
    this._value = "";
    this._checked = false;
    this._disabled = false;
    this.clientWidth = 400;
    this.offsetWidth = 400;
  }
  get id() {
    return this.getAttribute("id") || "";
  }
  set id(v) {
    this.setAttribute("id", v);
  }
  get className() {
    return this.getAttribute("class") || "";
  }
  set className(v) {
    this.setAttribute("class", v);
  }
  get value() {
    if (this._tag === "select" && !this._value) {
      const opt = this.querySelector("option[selected]") || this.querySelector("option");
      return opt ? (opt.getAttribute("value") ?? opt.textContent) : "";
    }
    return this._value;
  }
  set value(v) {
    this._value = v == null ? "" : String(v);
    this._attrs.value = this._value;
  }
  get checked() {
    return this._checked;
  }
  set checked(v) {
    this._checked = Boolean(v);
    if (this._checked) this._attrs.checked = "";
    else delete this._attrs.checked;
  }
  get disabled() {
    return this._disabled;
  }
  set disabled(v) {
    this._disabled = Boolean(v);
    if (this._disabled) this._attrs.disabled = "";
    else delete this._attrs.disabled;
  }
  attachShadow() {
    if (!this.shadowRoot) {
      this.shadowRoot = new MiniShadowRoot(this);
    }
    return this.shadowRoot;
  }
  setAttribute(name, value) {
    const k = String(name).toLowerCase();
    const v = value == null ? "" : String(value);
    this._attrs[k] = v;
    if (k === "value") this._value = v;
    if (k === "checked") this._checked = true;
    if (k === "disabled") this._disabled = true;
    if (k === "style") this.style.cssText = v;
  }
  getAttribute(name) {
    const k = String(name).toLowerCase();
    if (k === "style") {
      const s = this.style.cssText;
      return s || (Object.prototype.hasOwnProperty.call(this._attrs, "style") ? this._attrs.style : null);
    }
    return Object.prototype.hasOwnProperty.call(this._attrs, k) ? this._attrs[k] : null;
  }
  hasAttribute(name) {
    return Object.prototype.hasOwnProperty.call(this._attrs, String(name).toLowerCase());
  }
  removeAttribute(name) {
    const k = String(name).toLowerCase();
    delete this._attrs[k];
    if (k === "checked") this._checked = false;
    if (k === "disabled") this._disabled = false;
    if (k === "style") this.style.cssText = "";
  }
  closest(selector) {
    let cur = this;
    while (cur && cur.nodeType === 1) {
      if (matchesSelector(cur, selector)) return cur;
      cur = cur.parentNode;
    }
    return null;
  }
  focus() {
    let root = this.parentNode;
    while (root && root.parentNode) root = root.parentNode;
    if (root && root.nodeType === 11) {
      root.activeElement = this;
      globalThis.document.activeElement = root.host;
    } else {
      globalThis.document.activeElement = this;
    }
  }
  click() {
    this.dispatchEvent(new MiniEvent("click", { bubbles: true, composed: true, cancelable: true }));
  }
  get outerHTML() {
    const attrEntries = Object.entries(this._attrs).map(([k, v]) =>
      v === "" && (k === "checked" || k === "disabled" || k === "selected")
        ? k
        : `${k}="${escapeAttr(v)}"`
    );
    const attrStr = attrEntries.length ? " " + attrEntries.join(" ") : "";
    if (VOID_TAGS.has(this._tag)) return `<${this._tag}${attrStr}>`;
    return `<${this._tag}${attrStr}>${this.innerHTML}</${this._tag}>`;
  }
}

class MiniHTMLElement extends MiniElement {
  constructor() {
    super("div");
    const ctorTag = registeredTagsByCtor.get(this.constructor);
    if (ctorTag) {
      this._tag = ctorTag;
      this.tagName = ctorTag.toUpperCase();
    }
  }
  connectedCallback() {}
  disconnectedCallback() {}
}

const registry = new Map();
const registeredTagsByCtor = new Map();

globalThis.Event = MiniEvent;
globalThis.CustomEvent = MiniCustomEvent;
globalThis.HTMLElement = MiniHTMLElement;
globalThis.window = globalThis;
globalThis.history = {
  calls: [],
  pushState(state, title, url) {
    this.calls.push({ state, title, url });
  },
};
globalThis.customElements = {
  define(name, ctor) {
    const tag = String(name).toLowerCase();
    registry.set(tag, ctor);
    registeredTagsByCtor.set(ctor, tag);
  },
  get(name) {
    return registry.get(String(name).toLowerCase());
  },
};
globalThis.document = {
  activeElement: null,
  body: new MiniElement("body"),
  createElement(tag) {
    const lower = String(tag).toLowerCase();
    const Ctor = registry.get(lower);
    if (Ctor) return new Ctor();
    return new MiniElement(lower);
  },
};

// Dynamically import the card AFTER all DOM shims are installed
await import("../custom_components/lepas/lovelace/lepas-card.js");

const LepasCard = globalThis.customElements.get("lepas-card");
const LepasCardEditor = globalThis.customElements.get("lepas-card-editor");

function makeState(entityId, state, attrs = {}) {
  return {
    entity_id: entityId,
    state: String(state),
    attributes: Object.assign({ friendly_name: entityId }, attrs),
  };
}

function makeFullHass(overrides = {}, lang = "it") {
  const calls = [];
  const states = {
    "binary_sensor.lepas_connection": makeState("binary_sensor.lepas_connection", "on", { friendly_name: "Lepas Connection" }),
    "binary_sensor.lepas_at_home": makeState("binary_sensor.lepas_at_home", "on", { friendly_name: "Lepas At home" }),
    "binary_sensor.lepas_car_awake": makeState("binary_sensor.lepas_car_awake", "off", { friendly_name: "Lepas Car awake" }),
    "binary_sensor.lepas_charging_cable": makeState("binary_sensor.lepas_charging_cable", "on", { friendly_name: "Lepas Charging cable" }),
    "binary_sensor.lepas_air_purification": makeState("binary_sensor.lepas_air_purification", "on", { friendly_name: "Lepas Air purification" }),
    "binary_sensor.lepas_front_left_door": makeState("binary_sensor.lepas_front_left_door", "off"),
    "binary_sensor.lepas_front_right_door": makeState("binary_sensor.lepas_front_right_door", "off"),
    "binary_sensor.lepas_rear_left_door": makeState("binary_sensor.lepas_rear_left_door", "off"),
    "binary_sensor.lepas_rear_right_door": makeState("binary_sensor.lepas_rear_right_door", "off"),
    "binary_sensor.lepas_hood": makeState("binary_sensor.lepas_hood", "off"),
    "binary_sensor.lepas_tailgate_moving": makeState("binary_sensor.lepas_tailgate_moving", "off"),
    "binary_sensor.lepas_front_left_window": makeState("binary_sensor.lepas_front_left_window", "off"),
    "binary_sensor.lepas_front_right_window": makeState("binary_sensor.lepas_front_right_window", "off"),
    "binary_sensor.lepas_rear_left_window": makeState("binary_sensor.lepas_rear_left_window", "off"),
    "binary_sensor.lepas_rear_right_window": makeState("binary_sensor.lepas_rear_right_window", "off"),
    "binary_sensor.lepas_sunroof_blind": makeState("binary_sensor.lepas_sunroof_blind", "off"),
    "binary_sensor.lepas_tire_warning_front_left": makeState("binary_sensor.lepas_tire_warning_front_left", "off"),
    "binary_sensor.lepas_tire_warning_front_right": makeState("binary_sensor.lepas_tire_warning_front_right", "off"),
    "binary_sensor.lepas_tire_warning_rear_left": makeState("binary_sensor.lepas_tire_warning_rear_left", "off"),
    "binary_sensor.lepas_tire_warning_rear_right": makeState("binary_sensor.lepas_tire_warning_rear_right", "off"),
    "binary_sensor.lepas_low_battery": makeState("binary_sensor.lepas_low_battery", "off"),
    "sensor.lepas_battery": makeState("sensor.lepas_battery", "78", { unit_of_measurement: "%", device_class: "battery" }),
    "sensor.lepas_electric_range": makeState("sensor.lepas_electric_range", "112", { unit_of_measurement: "km" }),
    "sensor.lepas_total_range": makeState("sensor.lepas_total_range", "420", { unit_of_measurement: "km" }),
    "sensor.lepas_fuel_range": makeState("sensor.lepas_fuel_range", "308", { unit_of_measurement: "km" }),
    "sensor.lepas_charging_power": makeState("sensor.lepas_charging_power", "6.6", { unit_of_measurement: "kW" }),
    "sensor.lepas_charging_status": makeState("sensor.lepas_charging_status", "Charging"),
    "sensor.lepas_remaining_charge_time": makeState("sensor.lepas_remaining_charge_time", "95", { unit_of_measurement: "min" }),
    "sensor.lepas_hv_battery_voltage": makeState("sensor.lepas_hv_battery_voltage", "398", { unit_of_measurement: "V" }),
    "sensor.lepas_hv_battery_current": makeState("sensor.lepas_hv_battery_current", "16.5", { unit_of_measurement: "A" }),
    "sensor.lepas_home_charging_energy": makeState("sensor.lepas_home_charging_energy", "142.3", { unit_of_measurement: "kWh" }),
    "sensor.lepas_away_charging_energy": makeState("sensor.lepas_away_charging_energy", "38.1", { unit_of_measurement: "kWh" }),
    "sensor.lepas_fast_charging_port": makeState("sensor.lepas_fast_charging_port", "Disconnected"),
    "sensor.lepas_odometer": makeState("sensor.lepas_odometer", "12450", { unit_of_measurement: "km" }),
    "sensor.lepas_car_data_updated": makeState("sensor.lepas_car_data_updated", "2026-11-17T20:15:00Z"),
    "sensor.lepas_command_result": makeState("sensor.lepas_command_result", "OK"),
    "sensor.lepas_set_temperature_left": makeState("sensor.lepas_set_temperature_left", "21.5", { unit_of_measurement: "°C" }),
    "sensor.lepas_set_temperature_right": makeState("sensor.lepas_set_temperature_right", "22.0", { unit_of_measurement: "°C" }),
    "sensor.lepas_rear_center_seat_heating": makeState("sensor.lepas_rear_center_seat_heating", "0"),
    "sensor.lepas_rear_center_seat_ventilation": makeState("sensor.lepas_rear_center_seat_ventilation", "0"),
    "sensor.lepas_tire_pressure_front_left": makeState("sensor.lepas_tire_pressure_front_left", "2.50", { unit_of_measurement: "bar" }),
    "sensor.lepas_tire_pressure_front_right": makeState("sensor.lepas_tire_pressure_front_right", "2.51", { unit_of_measurement: "bar" }),
    "sensor.lepas_tire_pressure_rear_left": makeState("sensor.lepas_tire_pressure_rear_left", "2.48", { unit_of_measurement: "bar" }),
    "sensor.lepas_tire_pressure_rear_right": makeState("sensor.lepas_tire_pressure_rear_right", "2.49", { unit_of_measurement: "bar" }),
    "sensor.lepas_tire_temperature_front_left": makeState("sensor.lepas_tire_temperature_front_left", "24", { unit_of_measurement: "°C" }),
    "sensor.lepas_tire_temperature_front_right": makeState("sensor.lepas_tire_temperature_front_right", "24", { unit_of_measurement: "°C" }),
    "sensor.lepas_tire_temperature_rear_left": makeState("sensor.lepas_tire_temperature_rear_left", "23", { unit_of_measurement: "°C" }),
    "sensor.lepas_tire_temperature_rear_right": makeState("sensor.lepas_tire_temperature_rear_right", "23", { unit_of_measurement: "°C" }),
    "sensor.lepas_sunroof_movement_state": makeState("sensor.lepas_sunroof_movement_state", "idle"),
    "sensor.lepas_scheduled_charging_window": makeState("sensor.lepas_scheduled_charging_window", "23:00 → (+1g) 05:00 · Lun–Ven", {
      start_time: "23:00",
      end_time: "05:00",
      next_day: true,
      duration_hours: 6,
      days: [1, 2, 3, 4, 5],
      synced_with_car: true,
    }),
    "sensor.lepas_next_departure": makeState("sensor.lepas_next_departure", "Domani mer 07:30 (Clima 07:15)", {
      departure_at: "2026-11-18T07:30:00+01:00",
      climate_start_at: "2026-11-18T07:15:00+01:00",
      source: "weekly",
      weekday: 3,
      climate_mode: "at_home",
      sync_charging: true,
      planned_charge_start: "01:30",
    }),
    "lock.lepas_lock": makeState("lock.lepas_lock", "locked"),
    "climate.lepas_climate": makeState("climate.lepas_climate", "off", {
      temperature: 21.0,
      min_temp: 16,
      max_temp: 30,
      target_temperature_step: 0.5,
      hvac_modes: ["off", "heat_cool"],
    }),
    "cover.lepas_trunk": makeState("cover.lepas_trunk", "closed"),
    "cover.lepas_windows": makeState("cover.lepas_windows", "closed"),
    "cover.lepas_sunroof": makeState("cover.lepas_sunroof", "closed"),
    "switch.lepas_charging": makeState("switch.lepas_charging", "on"),
    "switch.lepas_scheduled_charging": makeState("switch.lepas_scheduled_charging", "on"),
    "switch.lepas_alarm": makeState("switch.lepas_alarm", "on"),
    "switch.lepas_cool_everything": makeState("switch.lepas_cool_everything", "off"),
    "switch.lepas_heat_everything": makeState("switch.lepas_heat_everything", "off"),
    "switch.lepas_windshield_defrost": makeState("switch.lepas_windshield_defrost", "off"),
    "switch.lepas_windshield_defog": makeState("switch.lepas_windshield_defog", "off"),
    "switch.lepas_rear_window_heating": makeState("switch.lepas_rear_window_heating", "off"),
    "switch.lepas_steering_wheel_heating": makeState("switch.lepas_steering_wheel_heating", "off"),
    "switch.lepas_driver_seat_heating": makeState("switch.lepas_driver_seat_heating", "off"),
    "switch.lepas_driver_seat_ventilation": makeState("switch.lepas_driver_seat_ventilation", "off"),
    "switch.lepas_passenger_seat_heating": makeState("switch.lepas_passenger_seat_heating", "off"),
    "switch.lepas_passenger_seat_ventilation": makeState("switch.lepas_passenger_seat_ventilation", "off"),
    "switch.lepas_rear_left_seat_heating": makeState("switch.lepas_rear_left_seat_heating", "off"),
    "switch.lepas_rear_left_seat_ventilation": makeState("switch.lepas_rear_left_seat_ventilation", "off"),
    "switch.lepas_rear_right_seat_heating": makeState("switch.lepas_rear_right_seat_heating", "off"),
    "switch.lepas_rear_right_seat_ventilation": makeState("switch.lepas_rear_right_seat_ventilation", "off"),
    "switch.lepas_quick_departure": makeState("switch.lepas_quick_departure", "off"),
    "switch.lepas_sync_charge_to_departure": makeState("switch.lepas_sync_charge_to_departure", "on"),
    "switch.lepas_departure_mon_enabled": makeState("switch.lepas_departure_mon_enabled", "on"),
    "switch.lepas_departure_tue_enabled": makeState("switch.lepas_departure_tue_enabled", "off"),
    "switch.lepas_departure_wed_enabled": makeState("switch.lepas_departure_wed_enabled", "on"),
    "switch.lepas_departure_thu_enabled": makeState("switch.lepas_departure_thu_enabled", "off"),
    "switch.lepas_departure_fri_enabled": makeState("switch.lepas_departure_fri_enabled", "on"),
    "switch.lepas_departure_sat_enabled": makeState("switch.lepas_departure_sat_enabled", "off"),
    "switch.lepas_departure_sun_enabled": makeState("switch.lepas_departure_sun_enabled", "off"),
    "number.lepas_climate_duration": makeState("number.lepas_climate_duration", "15", { min: 5, max: 30, step: 5 }),
    "number.lepas_charge_duration": makeState("number.lepas_charge_duration", "6", { min: 1, max: 12, step: 1 }),
    "time.lepas_charge_start_time": makeState("time.lepas_charge_start_time", "23:00:00"),
    "time.lepas_quick_departure_time": makeState("time.lepas_quick_departure_time", "07:30:00"),
    "time.lepas_departure_mon_time": makeState("time.lepas_departure_mon_time", "07:30:00"),
    "time.lepas_departure_tue_time": makeState("time.lepas_departure_tue_time", "07:30:00"),
    "time.lepas_departure_wed_time": makeState("time.lepas_departure_wed_time", "07:30:00"),
    "time.lepas_departure_thu_time": makeState("time.lepas_departure_thu_time", "07:30:00"),
    "time.lepas_departure_fri_time": makeState("time.lepas_departure_fri_time", "07:30:00"),
    "time.lepas_departure_sat_time": makeState("time.lepas_departure_sat_time", "09:00:00"),
    "time.lepas_departure_sun_time": makeState("time.lepas_departure_sun_time", "09:00:00"),
    "select.lepas_charge_days": makeState("select.lepas_charge_days", "weekdays", {
      options: ["all_days", "weekdays", "weekend", "mon_wed_fri", "tue_thu_sat", "custom"],
      days: [1, 2, 3, 4, 5],
    }),
    "select.lepas_departure_climate_mode": makeState("select.lepas_departure_climate_mode", "at_home", {
      options: ["at_home", "anywhere", "off"],
    }),
    "button.lepas_find_car_flash_lights": makeState("button.lepas_find_car_flash_lights", "unknown"),
    "button.lepas_wake_car": makeState("button.lepas_wake_car", "unknown"),
    "button.lepas_refresh_location": makeState("button.lepas_refresh_location", "unknown"),
    "button.lepas_locate_car_gps": makeState("button.lepas_locate_car_gps", "unknown"),
    "button.lepas_vent_windows": makeState("button.lepas_vent_windows", "unknown"),
    "button.lepas_vent_sunroof": makeState("button.lepas_vent_sunroof", "unknown"),
    "button.lepas_apply_charging_schedule": makeState("button.lepas_apply_charging_schedule", "unknown"),
    "device_tracker.lepas_location": makeState("device_tracker.lepas_location", "home", {
      latitude: 45.464211,
      longitude: 9.189982,
      vin: "L1234567890ABCDEF",
    }),
  };

  Object.assign(states, overrides);
  for (const [k, v] of Object.entries(states)) {
    if (v === null) delete states[k];
  }

  const entities = {};
  for (const id of Object.keys(states)) {
    entities[id] = { platform: "lepas", device_id: "dev_lepas_1" };
  }

  return {
    locale: { language: lang },
    language: lang,
    states,
    entities,
    calls,
    callService(domain, service, data) {
      calls.push({ domain, service, data });
      return Promise.resolve();
    },
  };
}

function createCard(config = {}, hass = null) {
  const card = document.createElement("lepas-card");
  card.setConfig(config);
  if (hass) card.hass = hass;
  return card;
}

test("LepasCard metadata, registration, Shadow DOM, and container queries", () => {
  assert.ok(LepasCard, "LepasCard custom element must be registered");
  assert.ok(LepasCardEditor, "LepasCardEditor custom element must be registered");
  assert.deepEqual(LepasCard.getStubConfig(), { type: "custom:lepas-card" });
  assert.deepEqual(LepasCard.getGridOptions(), { columns: 12, min_columns: 4, rows: "auto" });

  const editor = LepasCard.getConfigElement();
  assert.equal(editor.tagName, "LEPAS-CARD-EDITOR");

  const regEntry = window.customCards.find((c) => c.type === "lepas-card");
  assert.ok(regEntry, "customCards registration missing (must use 'lepas-card' without 'custom:' prefix)");
  assert.ok(
    !window.customCards.some((c) => c.type === "custom:lepas-card"),
    "window.customCards must NOT include 'custom:' prefix in type"
  );

  const card = createCard({}, makeFullHass());
  assert.ok(card.shadowRoot, "LepasCard must use Shadow DOM");
  const styleText = card.shadowRoot.querySelector("style")?.textContent || "";
  assert.ok(styleText.includes("container-type: inline-size"), "Must declare container-type: inline-size");
  assert.ok(!styleText.includes(":host-context("), "Must NOT use :host-context()");
  assert.ok(!styleText.toUpperCase().includes("#00D2FF"), "Must NOT use neon cyan #00D2FF");
});

test("Color and hero image resolution, aliases, and precedence", () => {
  const h = LepasCard._helpers;
  assert.ok(h, "LepasCard._helpers must be exposed");

  // Default grey
  assert.equal(h.resolveHeroImage({}, []), "/lepas_card/lepas-hero-grey.png?v=1.19.1");

  // All 5 canonical colors
  for (const c of ["grey", "teal", "violet", "black", "white"]) {
    assert.equal(
      h.resolveHeroImage({ color: c }, []),
      `/lepas_card/lepas-hero-${c}.png?v=1.19.1`
    );
  }

  // Tolerant aliases
  const aliases = [
    ["grigio", "grey"],
    ["viola", "violet"],
    ["purple", "violet"],
    ["nero", "black"],
    ["bianco", "white"],
    ["verde", "teal"],
    ["ottanio", "teal"],
    ["green", "teal"],
    [" VIOLA ", "violet"],
  ];
  for (const [alias, expected] of aliases) {
    assert.equal(
      h.resolveHeroImage({ color: alias }, []),
      `/lepas_card/lepas-hero-${expected}.png?v=1.19.1`
    );
  }

  // Precedence: config.image > vehicle_image > color
  const itemsWithAttr = [
    { id: "sensor.lepas_battery", s: makeState("sensor.lepas_battery", "80", { vehicle_image: "/local/from_attr.png" }) },
  ];
  assert.equal(
    h.resolveHeroImage({ color: "teal", image: "https://cdn.example.com/custom.png" }, itemsWithAttr),
    "https://cdn.example.com/custom.png"
  );
  assert.equal(
    h.resolveHeroImage({ color: "teal" }, itemsWithAttr),
    "/local/from_attr.png"
  );
});

test("URL sanitization rejects dangerous schemes and accepts safe image URLs", () => {
  const h = LepasCard._helpers;
  const card = createCard({});

  const rejected = [
    "javascript:alert(1)",
    "JAVASCRIPT:alert(1)",
    "//evil.example/x.png",
    "data:image/svg+xml;base64,PHN2Zz4=",
    "data:text/html;base64,PHNjcmlwdD4=",
  ];
  for (const bad of rejected) {
    assert.equal(h.sanitizeUrl(bad), "", `Should reject ${bad}`);
    assert.equal(card._imgUrl(bad), "", `_imgUrl should reject ${bad}`);
  }

  const accepted = [
    "https://example.com/car.png?v=1",
    "http://homeassistant.local:8123/local/car.jpg",
    "/lepas_card/x.png",
    "data:image/png;base64,AAA",
  ];
  for (const ok of accepted) {
    assert.equal(h.sanitizeUrl(ok), ok, `Should accept ${ok}`);
    assert.equal(card._imgUrl(ok), ok, `_imgUrl should accept ${ok}`);
  }
});

test("LepasCardEditor renders controls and preserves extra YAML keys on config-changed", () => {
  const editor = LepasCard.getConfigElement();
  editor.hass = makeFullHass({}, "en");
  editor.setConfig({
    type: "custom:lepas-card",
    color: "grey",
    layout: "auto",
    default_tab: "overview",
    title: "My SUV",
    image: "/local/my.png",
    show_all: false,
    entities: ["sensor.custom_extra"],
    prefix: "mycar_",
    integration: "lepas",
  });

  const events = [];
  editor.addEventListener("config-changed", (ev) => events.push(ev.detail.config));

  assert.ok(editor.shadowRoot, "Editor must use Shadow DOM");
  const tealSwatch = editor.shadowRoot.querySelector('[data-color="teal"]');
  assert.ok(tealSwatch, "Color swatch for teal missing");
  tealSwatch.click();

  assert.equal(events.length, 1);
  assert.equal(events[0].color, "teal");
  assert.deepEqual(events[0].entities, ["sensor.custom_extra"]);
  assert.equal(events[0].prefix, "mycar_");
  assert.equal(events[0].integration, "lepas");

  const layoutSelect = editor.shadowRoot.querySelector('[data-field="layout"]');
  assert.ok(layoutSelect, "Layout select missing");
  layoutSelect.value = "cockpit";
  layoutSelect.dispatchEvent(new Event("change", { bubbles: true }));
  assert.equal(events[1].layout, "cockpit");

  const tabSelect = editor.shadowRoot.querySelector('[data-field="default_tab"]');
  assert.ok(tabSelect, "Default tab select missing");
  tabSelect.value = "charging";
  tabSelect.dispatchEvent(new Event("change", { bubbles: true }));
  assert.equal(events[2].default_tab, "charging");

  const showAll = editor.shadowRoot.querySelector('[data-field="show_all"]');
  assert.ok(showAll, "show_all checkbox missing");
  showAll.checked = true;
  showAll.dispatchEvent(new Event("change", { bubbles: true }));
  assert.equal(events[3].show_all, true);
  assert.equal(events[3].prefix, "mycar_");
});

test("Layout modes and default_tab switching", () => {
  const hass = makeFullHass({}, "it");
  const compact = createCard({ layout: "compact", default_tab: "climate" }, hass);
  const haCard = compact.shadowRoot.querySelector("ha-card");
  assert.equal(haCard.getAttribute("data-layout"), "compact");
  assert.equal(compact.shadowRoot.querySelector('[data-tab="climate"]').classList.contains("is-active"), true);
  assert.equal(compact.shadowRoot.querySelector('[data-panel="climate"]').classList.contains("is-active"), true);

  const cockpit = createCard({ layout: "cockpit" }, hass);
  assert.equal(cockpit.shadowRoot.querySelector("ha-card").getAttribute("data-layout"), "cockpit");

  // Switching tab updates active tab and panel
  compact.shadowRoot.querySelector('[data-tab="security"]').click();
  assert.equal(compact.shadowRoot.querySelector('[data-tab="security"]').classList.contains("is-active"), true);
  assert.equal(compact.shadowRoot.querySelector('[data-panel="security"]').classList.contains("is-active"), true);
});

test("4s inline confirmation: 1st tap arms, 2nd tap dispatches, 4s timeout disarms", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout", "Date"] });

  const hass = makeFullHass({
    "button.lepas_remote_start": makeState("button.lepas_remote_start", "unknown"),
  }, "en");
  const card = createCard({ default_tab: "security" }, hass);

  const sensitiveCases = [
    { selector: '[data-action-id="unlock"]', domain: "lock", service: "unlock", entityId: "lock.lepas_lock" },
    { selector: '[data-action-id="trunk_open"]', domain: "cover", service: "open_cover", entityId: "cover.lepas_trunk" },
    { selector: '[data-action-id="windows_open"]', domain: "cover", service: "open_cover", entityId: "cover.lepas_windows" },
    { selector: '[data-action-id="sunroof_open"]', domain: "cover", service: "open_cover", entityId: "cover.lepas_sunroof" },
    { selector: '[data-action-id="vent_windows"]', domain: "button", service: "press", entityId: "button.lepas_vent_windows" },
    { selector: '[data-action-id="vent_sunroof"]', domain: "button", service: "press", entityId: "button.lepas_vent_sunroof" },
    { selector: '[data-action-id="alarm_toggle"]', domain: "switch", service: "turn_off", entityId: "switch.lepas_alarm" },
    { selector: '[data-action-id="remote_start"]', domain: "button", service: "press", entityId: "button.lepas_remote_start" },
  ];

  for (const sc of sensitiveCases) {
    const beforeCalls = hass.calls.length;
    const btn = card.shadowRoot.querySelector(sc.selector);
    assert.ok(btn, `Missing sensitive button ${sc.selector}`);

    // 1st tap arms inline confirmation without calling service
    btn.click();
    assert.equal(hass.calls.length, beforeCalls, `1st tap on ${sc.selector} must NOT callService`);
    assert.equal(card.shadowRoot.querySelector(sc.selector).getAttribute("data-confirming"), "true");
    assert.ok(card.shadowRoot.querySelector(sc.selector).textContent.includes("Confirm?"));

    // Expire 4s timeout -> disarms without calling service
    t.mock.timers.tick(4000);
    assert.equal(hass.calls.length, beforeCalls, `Timeout on ${sc.selector} must NOT callService`);
    assert.notEqual(card.shadowRoot.querySelector(sc.selector).getAttribute("data-confirming"), "true");

    // Re-arm and tap 2nd time within 4s -> dispatches service
    card.shadowRoot.querySelector(sc.selector).click();
    assert.equal(hass.calls.length, beforeCalls);
    t.mock.timers.tick(1500);
    card.shadowRoot.querySelector(sc.selector).click();
    await Promise.resolve();

    assert.equal(hass.calls.length, beforeCalls + 1, `2nd tap on ${sc.selector} must callService`);
    assert.equal(hass.calls[beforeCalls].domain, sc.domain);
    assert.equal(hass.calls[beforeCalls].service, sc.service);
    assert.equal(hass.calls[beforeCalls].data.entity_id, sc.entityId);
  }
});

test("Direct 1-tap actions call hass.callService immediately", async () => {
  const hass = makeFullHass({
    "lock.lepas_lock": makeState("lock.lepas_lock", "unlocked"),
    "cover.lepas_trunk": makeState("cover.lepas_trunk", "open"),
  }, "en");
  const card = createCard({}, hass);

  // Lock (when unlocked)
  card.shadowRoot.querySelector('[data-action-id="lock_now"]').click();
  // Climate toggle
  card.shadowRoot.querySelector('[data-action-id="climate_toggle"]').click();
  // Climate temp +
  card.shadowRoot.querySelector('[data-action-id="temp_up"]').click();
  // Seat toggle
  card.shadowRoot.querySelector('[data-action-id="seat_driver_heat"]').click();
  // Apply charging schedule
  card.shadowRoot.querySelector('[data-action-id="apply_charging_schedule"]').click();
  // Quick departure toggle
  card.shadowRoot.querySelector('[data-action-id="quick_departure_toggle"]').click();
  // Number set_value (climate duration 20 or 30)
  card.shadowRoot.querySelector('[data-action-id="climate_duration"][data-value="30"]').click();
  // Time set_value
  const startInput = card.shadowRoot.querySelector('[data-entity-input="time.lepas_charge_start_time"]');
  startInput.value = "01:30";
  startInput.dispatchEvent(new Event("change", { bubbles: true }));
  // Select select_option
  const daysSelect = card.shadowRoot.querySelector('[data-entity-input="select.lepas_charge_days"]');
  daysSelect.value = "weekend";
  daysSelect.dispatchEvent(new Event("change", { bubbles: true }));

  await Promise.resolve();

  const sigs = hass.calls.map((c) => `${c.domain}.${c.service}:${c.data.entity_id}`);
  assert.ok(sigs.includes("lock.lock:lock.lepas_lock"));
  assert.ok(sigs.includes("climate.set_hvac_mode:climate.lepas_climate"));
  assert.ok(sigs.includes("climate.set_temperature:climate.lepas_climate"));
  assert.ok(sigs.includes("switch.turn_on:switch.lepas_driver_seat_heating"));
  assert.ok(sigs.includes("button.press:button.lepas_apply_charging_schedule"));
  assert.ok(sigs.includes("switch.turn_on:switch.lepas_quick_departure"));
  assert.ok(sigs.includes("number.set_value:number.lepas_climate_duration"));
  assert.ok(sigs.includes("time.set_value:time.lepas_charge_start_time"));
  assert.ok(sigs.includes("select.select_option:select.lepas_charge_days"));
});

test("State, focus preservation on set hass(), and rejected callService error banner", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout", "Date"] });

  let shouldReject = false;
  const hass = makeFullHass({}, "en");
  hass.callService = (domain, service, data) => {
    hass.calls.push({ domain, service, data });
    if (shouldReject) return Promise.reject(new Error("Vehicle timeout"));
    return Promise.resolve();
  };

  const card = createCard({ layout: "compact", default_tab: "overview" }, hass);
  // Switch to charging tab and expand Friday
  card.shadowRoot.querySelector('[data-tab="charging"]').click();
  card.shadowRoot.querySelector('[data-day-chip="fri"]').click();

  // Arm unlock confirm
  card.shadowRoot.querySelector('[data-action-id="unlock"]').click();
  assert.equal(card.shadowRoot.querySelector('[data-action-id="unlock"]').getAttribute("data-confirming"), "true");

  // Focus time input
  const timeInput = card.shadowRoot.querySelector('[data-entity-input="time.lepas_charge_start_time"]');
  timeInput.focus();
  timeInput.value = "04:15";

  // Trigger unrelated hass update
  const nextHass = makeFullHass({
    "sensor.lepas_battery": makeState("sensor.lepas_battery", "79", { unit_of_measurement: "%", device_class: "battery" }),
  }, "en");
  nextHass.callService = hass.callService;
  card.hass = nextHass;

  // Preserved activeTab, expandedDay, confirmState, focus, and in-progress input value
  assert.equal(card.shadowRoot.querySelector('[data-tab="charging"]').classList.contains("is-active"), true);
  assert.ok(card.shadowRoot.querySelector('[data-day-editor="fri"]'), "Expanded Friday must survive set hass()");
  assert.equal(card.shadowRoot.querySelector('[data-action-id="unlock"]').getAttribute("data-confirming"), "true");
  assert.equal(card.shadowRoot.activeElement, timeInput);
  assert.equal(timeInput.value, "04:15");

  // Toggle Friday departure switch and time inside expanded day editor
  card.shadowRoot.querySelector('[data-action-id="day_toggle_fri"]').click();
  const friTime = card.shadowRoot.querySelector('[data-entity-input="time.lepas_departure_fri_time"]');
  friTime.value = "08:45";
  friTime.dispatchEvent(new Event("change", { bubbles: true }));
  await Promise.resolve();
  assert.ok(hass.calls.some((c) => c.domain === "switch" && c.service === "turn_off" && c.data.entity_id === "switch.lepas_departure_fri_enabled"));
  assert.ok(hass.calls.some((c) => c.domain === "time" && c.service === "set_value" && c.data.entity_id === "time.lepas_departure_fri_time" && c.data.time === "08:45:00"));

  // Rejected service call clears pending and shows inline non-blocking error banner
  shouldReject = true;
  card.shadowRoot.querySelector('[data-action-id="apply_charging_schedule"]').click();
  await Promise.resolve();
  await Promise.resolve();

  const errBanner = card.shadowRoot.querySelector('[role="alert"].error-banner');
  assert.ok(errBanner, "Error banner must render on rejected callService");
  assert.ok(errBanner.textContent.includes("Vehicle timeout"));

  // Cleanup timer on disconnect
  card.disconnectedCallback();
});

test("Entity mapping: SVG blueprint, TPMS, SoC ring + progress, 4+1 seats, charging timeline, departure strip, graceful omission", () => {
  const hass = makeFullHass({
    "binary_sensor.lepas_front_left_door": makeState("binary_sensor.lepas_front_left_door", "on"),
    "binary_sensor.lepas_tailgate_moving": makeState("binary_sensor.lepas_tailgate_moving", "on"),
    "binary_sensor.lepas_sunroof_blind": makeState("binary_sensor.lepas_sunroof_blind", "on"),
    "cover.lepas_sunroof": makeState("cover.lepas_sunroof", "open"),
    "cover.lepas_windows": makeState("cover.lepas_windows", "open"),
    "cover.lepas_trunk": makeState("cover.lepas_trunk", "open"),
    "binary_sensor.lepas_tire_warning_rear_right": makeState("binary_sensor.lepas_tire_warning_rear_right", "on"),
  }, "it");
  const card = createCard({}, hass);

  // SVG blueprint state classes
  assert.ok(card.shadowRoot.querySelector('[data-bp-part="front_left_door"].is-open'));
  assert.ok(card.shadowRoot.querySelector('[data-bp-part="sunroof"].is-open'));
  assert.ok(card.shadowRoot.querySelector('[data-bp-part="windows"].is-open'));
  assert.ok(card.shadowRoot.querySelector('[data-bp-part="trunk"].is-open'));
  assert.ok(card.shadowRoot.querySelector('[data-bp-part="tailgate_moving"].is-moving'));
  assert.ok(card.shadowRoot.querySelector('[data-bp-part="sunroof_blind"].is-open'));

  // 4 corner TPMS + rear right warning
  const rrTpms = card.shadowRoot.querySelector('[data-tpms="rear_right"]');
  assert.ok(rrTpms.classList.contains("is-alert"));
  assert.ok(rrTpms.textContent.includes("2.49"));

  // SoC ring + accessible <progress>
  const prog = card.shadowRoot.querySelector('progress[max="100"]');
  assert.ok(prog);
  assert.equal(prog.getAttribute("value"), "78");
  const ring = card.shadowRoot.querySelector('[data-soc-ring]');
  assert.ok(ring);
  assert.ok(ring.getAttribute("stroke-dashoffset"));

  // 4+1 seats: rear center is read-only (no button/action)
  assert.ok(card.shadowRoot.querySelector('[data-seat-readonly="rear_center"]'));
  assert.equal(card.shadowRoot.querySelector('[data-action-id="seat_rear_center_heat"]'), null);

  // Scheduled charging timeline (crosses midnight -> 2 bars)
  const timelineSegs = card.shadowRoot.querySelectorAll('[data-timeline-seg]');
  assert.equal(timelineSegs.length, 2);

  // 7-day departure strip (Italian L M M G V S D)
  const dayChips = card.shadowRoot.querySelectorAll('[data-day-chip]');
  assert.equal(dayChips.length, 7);
  assert.equal(dayChips[0].textContent.trim().slice(0, 1), "L");
  assert.equal(dayChips[6].textContent.trim().slice(0, 1), "D");

  // Graceful omission when optional entities missing
  const sparseHass = makeFullHass({
    "sensor.lepas_rear_center_seat_heating": null,
    "sensor.lepas_rear_center_seat_ventilation": null,
    "button.lepas_vent_sunroof": null,
    "button.lepas_remote_start": null,
    "switch.lepas_windshield_defrost": null,
  }, "nl");
  const sparseCard = createCard({}, sparseHass);
  assert.equal(sparseCard.shadowRoot.querySelector('[data-action-id="remote_start"]'), null);
  assert.equal(sparseCard.shadowRoot.querySelector('[data-action-id="vent_sunroof"]'), null);
  assert.equal(sparseCard.shadowRoot.querySelector('[data-seat-readonly="rear_center"]'), null);
  // Dutch weekday strip (M D W D V Z Z)
  const nlChips = sparseCard.shadowRoot.querySelectorAll('[data-day-chip]');
  assert.equal(nlChips[2].textContent.trim().slice(0, 1), "W");
  assert.equal(nlChips[6].textContent.trim().slice(0, 1), "Z");
});

test("Security & Privacy: XSS escaping and ZERO VIN or raw GPS coordinates in DOM", () => {
  const hass = makeFullHass({
    "sensor.lepas_battery": makeState("sensor.lepas_battery", "85", {
      friendly_name: '<img src=x onerror=alert(1)>Battery',
      unit_of_measurement: "%",
      device_class: "battery",
      vin: "L1234567890SECRET",
    }),
  }, "en");
  const card = createCard({
    title: '<script>alert("xss")</script>Lepas L8',
    show_all: true,
  }, hass);

  const html = card.shadowRoot.innerHTML;
  assert.equal(card.shadowRoot.querySelector("script"), null, "No injected <script> tag allowed");
  assert.equal(card.shadowRoot.querySelector("img[onerror]"), null, "No injected <img> tag allowed");
  assert.ok(!html.includes("L1234567890ABCDEF"), "VIN from tracker must NEVER appear in DOM");
  assert.ok(!html.includes("L1234567890SECRET"), "VIN from battery must NEVER appear in DOM");
  assert.ok(!html.includes("45.464211"), "Raw latitude must NEVER appear in DOM");
  assert.ok(!html.includes("9.189982"), "Raw longitude must NEVER appear in DOM");
});
