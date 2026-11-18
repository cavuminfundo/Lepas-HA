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
    this.clientX = init.clientX !== undefined ? init.clientX : 0;
    this.clientY = init.clientY !== undefined ? init.clientY : 0;
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
  getRootNode() {
    let cur = this;
    while (cur.parentNode) cur = cur.parentNode;
    return cur;
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
    this.returnValue = "";
    this.clientWidth = 400;
    this.offsetWidth = 400;
    this.scrollTop = 0;
    this.scrollHeight = 0;
    this.clientHeight = 0;
  }
  get open() {
    return this.hasAttribute("open");
  }
  set open(v) {
    if (v) this.setAttribute("open", "");
    else this.removeAttribute("open");
  }
  showModal() {
    this.open = true;
  }
  close(val) {
    const wasOpen = this.open;
    if (val !== undefined) this.returnValue = String(val);
    this.open = false;
    if (wasOpen) {
      this.dispatchEvent(new MiniEvent("close", { bubbles: false, cancelable: false }));
    }
  }
  getBoundingClientRect() {
    return { left: 100, right: 300, top: 100, bottom: 240 };
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
      v === "" && (k === "checked" || k === "disabled" || k === "selected" || k === "open")
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
  assert.equal(h.CARD_VERSION, "1.22.1");

  // Default grey
  assert.equal(h.resolveHeroImage({}, []), "/lepas_card/lepas-hero-grey.png?v=1.22.1");

  // All 5 canonical colors
  for (const c of ["grey", "teal", "violet", "black", "white"]) {
    assert.equal(
      h.resolveHeroImage({ color: c }, []),
      `/lepas_card/lepas-hero-${c}.png?v=1.22.1`
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
      `/lepas_card/lepas-hero-${expected}.png?v=1.22.1`
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

test("v1.22.0 Native <dialog> modal confirmation for all 10 stateless + 5 sensitive stateful actions", async () => {
  const hass = makeFullHass({
    "button.lepas_remote_start": makeState("button.lepas_remote_start", "unknown"),
    "button.lepas_refresh_full_status": makeState("button.lepas_refresh_full_status", "unknown"),
    "button.lepas_apply_departure_schedule": makeState("button.lepas_apply_departure_schedule", "unknown"),
    "switch.lepas_quick_departure": makeState("switch.lepas_quick_departure", "on"),
    "sensor.lepas_scheduled_departure": makeState("sensor.lepas_scheduled_departure", "Disattivata", {
      attiva: false,
    }),
  }, "en");
  const card = createCard({ default_tab: "security" }, hass);
  const styleText = card.shadowRoot.querySelector("style")?.textContent || "";

  // Obsolete 4s inline confirmation styles must be removed; dialog rules must obey modern-web-guidance
  assert.equal(styleText.includes(".is-confirming"), false, "Obsolete .is-confirming style must be removed");
  assert.equal(styleText.includes(".confirm-bar"), false, "Obsolete .confirm-bar style must be removed");
  assert.ok(styleText.includes("dialog:modal"), "CSS must include dialog:modal");
  assert.ok(styleText.includes("dialog::backdrop"), "CSS must include dialog::backdrop");
  assert.ok(styleText.includes("overscroll-behavior: contain"), "CSS must contain scroll on modal/backdrop");
  assert.ok(styleText.includes("overflow: hidden"), "CSS must set overflow: hidden on dialog::backdrop");
  assert.ok(styleText.includes(".badge.is-coral"), "CSS must include .badge.is-coral");

  const dlg = card.shadowRoot.querySelector('dialog[data-bind="confirmDialog"]');
  assert.ok(dlg, "Native <dialog data-bind='confirmDialog'> must exist inside Shadow DOM");
  assert.equal(dlg.getAttribute("aria-labelledby"), "lp-confirm-title");
  assert.equal(dlg.hasAttribute("role"), false, "Native <dialog> must NOT have role='dialog'");
  assert.equal(dlg.hasAttribute("aria-modal"), false, "Native <dialog> must NOT have aria-modal");
  assert.equal(dlg.querySelector("form"), null, "Dialog must use explicit buttons instead of <form method='dialog'>");
  assert.equal(dlg.open, false, "Dialog must start closed");

  const cancelBtn = dlg.querySelector('button[type="button"][data-dialog-action="cancel"]');
  const confirmBtn = dlg.querySelector('button[type="button"][data-dialog-action="confirm"]');
  const actionTxtEl = dlg.querySelector('[data-bind="confirmDialogAction"]');
  assert.ok(cancelBtn && confirmBtn && actionTxtEl, "Dialog action controls and label must exist");
  assert.equal(cancelBtn.hasAttribute("autofocus"), true, "Safe Cancel button must carry autofocus");

  const modalCases = [
    // 5 sensitive stateful actions (+ quick variants)
    { selector: '[data-action-id="unlock"]', domain: "lock", service: "unlock", entityId: "lock.lepas_lock", label: "Unlock" },
    { selector: '[data-action-id="quick_unlock"]', domain: "lock", service: "unlock", entityId: "lock.lepas_lock", label: "Unlock" },
    { selector: '[data-action-id="trunk_open"]', domain: "cover", service: "open_cover", entityId: "cover.lepas_trunk", label: "Trunk: Open" },
    { selector: '[data-action-id="quick_trunk_open"]', domain: "cover", service: "open_cover", entityId: "cover.lepas_trunk", label: "Trunk: Open" },
    { selector: '[data-action-id="windows_open"]', domain: "cover", service: "open_cover", entityId: "cover.lepas_windows", label: "Windows: Open" },
    { selector: '[data-action-id="sunroof_open"]', domain: "cover", service: "open_cover", entityId: "cover.lepas_sunroof", label: "Sunroof: Open" },
    { selector: '[data-action-id="alarm_toggle"]', domain: "switch", service: "turn_off", entityId: "switch.lepas_alarm", label: "Alarm: OFF" },
    // 10 stateless commands (+ sec_flash_lights alias)
    { selector: '[data-action-id="wake_car"]', domain: "button", service: "press", entityId: "button.lepas_wake_car", label: "Wake car" },
    { selector: '[data-action-id="refresh_location"]', domain: "button", service: "press", entityId: "button.lepas_refresh_location", label: "Refresh pos." },
    { selector: '[data-action-id="refresh_full"]', domain: "button", service: "press", entityId: "button.lepas_refresh_full_status", label: "Full status" },
    { selector: '[data-action-id="locate_gps"]', domain: "button", service: "press", entityId: "button.lepas_locate_car_gps", label: "Locate GPS" },
    { selector: '[data-action-id="flash_lights"]', domain: "button", service: "press", entityId: "button.lepas_find_car_flash_lights", label: "Flash lights" },
    { selector: '[data-action-id="sec_flash_lights"]', domain: "button", service: "press", entityId: "button.lepas_find_car_flash_lights", label: "Flash lights" },
    { selector: '[data-action-id="vent_windows"]', domain: "button", service: "press", entityId: "button.lepas_vent_windows", label: "Vent windows" },
    { selector: '[data-action-id="vent_sunroof"]', domain: "button", service: "press", entityId: "button.lepas_vent_sunroof", label: "Vent sunroof" },
    { selector: '[data-action-id="remote_start"]', domain: "button", service: "press", entityId: "button.lepas_remote_start", label: "Remote start" },
    { selector: '[data-action-id="apply_charging_schedule"]', domain: "button", service: "press", entityId: "button.lepas_apply_charging_schedule", label: "Apply schedule" },
    { selector: '[data-action-id="apply_departure_schedule"]', domain: "button", service: "press", entityId: "button.lepas_apply_departure_schedule", label: "Apply to car" },
  ];

  for (const mc of modalCases) {
    const beforeCalls = hass.calls.length;
    const btn = card.shadowRoot.querySelector(mc.selector);
    assert.ok(btn, `Missing modal-confirmed button ${mc.selector}`);

    // 1st click opens modal without calling service or adding inline confirming state
    btn.click();
    assert.equal(hass.calls.length, beforeCalls, `Clicking ${mc.selector} must NOT callService before modal confirm`);
    assert.equal(dlg.open, true, `Dialog must open on ${mc.selector}`);
    assert.equal(btn.getAttribute("data-confirming"), null, `${mc.selector} must NOT set data-confirming`);
    assert.equal(btn.querySelector(".confirm-bar"), null, `${mc.selector} must NOT render .confirm-bar`);
    assert.equal(actionTxtEl.textContent, mc.label);

    // Cancel button closes dialog without calling service and resets returnValue
    cancelBtn.click();
    assert.equal(dlg.open, false, `Cancel must close dialog for ${mc.selector}`);
    assert.equal(dlg.returnValue, "", "Dialog returnValue must reset to '' on close");
    assert.equal(hass.calls.length, beforeCalls, `Cancel must NOT callService for ${mc.selector}`);

    // Re-open and confirm -> closes dialog, resets returnValue, calls service ONCE
    btn.click();
    assert.equal(dlg.open, true);
    confirmBtn.click();
    await Promise.resolve();
    assert.equal(dlg.open, false);
    assert.equal(dlg.returnValue, "");
    assert.equal(hass.calls.length, beforeCalls + 1, `Confirm must callService once for ${mc.selector}`);
    assert.equal(hass.calls[beforeCalls].domain, mc.domain);
    assert.equal(hass.calls[beforeCalls].service, mc.service);
    assert.equal(hass.calls[beforeCalls].data.entity_id, mc.entityId);
  }

  // Esc ('cancel' event) dismisses dialog without calling service
  const beforeEsc = hass.calls.length;
  card.shadowRoot.querySelector('[data-action-id="unlock"]').click();
  assert.equal(dlg.open, true);
  const cancelEv = new MiniEvent("cancel", { cancelable: true });
  dlg.dispatchEvent(cancelEv);
  assert.equal(cancelEv.defaultPrevented, true);
  assert.equal(dlg.open, false);
  assert.equal(hass.calls.length, beforeEsc);

  // Drag-safe light dismiss: pointerdown inside + pointerup outside stays open; outside + outside closes
  card.shadowRoot.querySelector('[data-action-id="unlock"]').click();
  assert.equal(dlg.open, true);
  dlg.dispatchEvent(new MiniEvent("pointerdown", { clientX: 150, clientY: 150 }));
  dlg.dispatchEvent(new MiniEvent("pointerup", { clientX: 10, clientY: 10 }));
  assert.equal(dlg.open, true, "Selection drag ending outside dialog must NOT dismiss");

  dlg.dispatchEvent(new MiniEvent("pointerdown", { clientX: 10, clientY: 10 }));
  dlg.dispatchEvent(new MiniEvent("pointerup", { clientX: 150, clientY: 150 }));
  assert.equal(dlg.open, true, "Pointer press outside releasing inside must NOT dismiss");

  dlg.dispatchEvent(new MiniEvent("pointerdown", { clientX: 10, clientY: 10 }));
  dlg.dispatchEvent(new MiniEvent("pointerup", { clientX: 10, clientY: 10 }));
  assert.equal(dlg.open, false, "Backdrop click outside dialog rect must dismiss");
  assert.equal(hass.calls.length, beforeEsc);

  // Older Android WebView fallback (no showModal / no close)
  const fallbackCard = createCard({ default_tab: "security" }, makeFullHass({}, "it"));
  const fbDlg = fallbackCard.shadowRoot.querySelector('dialog[data-bind="confirmDialog"]');
  fbDlg.showModal = undefined;
  fbDlg.close = undefined;
  fallbackCard.shadowRoot.querySelector('[data-action-id="unlock"]').click();
  assert.equal(fbDlg.hasAttribute("open"), true, "Fallback must set open attribute when showModal is missing");
  assert.equal(fbDlg.open, true);
  fbDlg.querySelector('[data-dialog-action="confirm"]').click();
  await Promise.resolve();
  assert.equal(fbDlg.hasAttribute("open"), false, "Fallback confirm must remove open attribute");
  assert.equal(fallbackCard._hass.calls.length, 1);
  assert.equal(fallbackCard._hass.calls[0].service, "unlock");
});

test("Direct 1-tap actions call hass.callService immediately (non-destructive stateful controls)", async () => {
  const hass = makeFullHass({
    "lock.lepas_lock": makeState("lock.lepas_lock", "unlocked"),
    "cover.lepas_trunk": makeState("cover.lepas_trunk", "open"),
  }, "en");
  const card = createCard({}, hass);
  const dlg = card.shadowRoot.querySelector('dialog[data-bind="confirmDialog"]');

  // Lock (when unlocked)
  card.shadowRoot.querySelector('[data-action-id="lock_now"]').click();
  // Climate toggle
  card.shadowRoot.querySelector('[data-action-id="climate_toggle"]').click();
  // Climate temp +
  card.shadowRoot.querySelector('[data-action-id="temp_up"]').click();
  // Seat toggle
  card.shadowRoot.querySelector('[data-action-id="seat_driver_heat"]').click();
  // Quick departure toggle
  card.shadowRoot.querySelector('[data-action-id="quick_departure_toggle"]').click();
  // Number set_value (climate duration 20 or 30)
  card.shadowRoot.querySelector('[data-action-id="climate_duration"][data-value="30"]').click();
  // Time set_value
  const startInput = card.shadowRoot.querySelector('[data-entity-input="time.lepas_charge_start_time"]');
  startInput.value = "01:30";
  startInput.dispatchEvent(new Event("change", { bubbles: true }));
  // Charge days chip toggle -> lepas.set_charging_schedule (apply: false)
  const daySatChip = card.shadowRoot.querySelector('[data-charge-day="6"]');
  assert.ok(daySatChip, "Saturday charge-day chip missing");
  daySatChip.click();

  await Promise.resolve();
  assert.equal(dlg.open, false, "Non-destructive 1-tap actions must NEVER open confirm modal");

  const sigs = hass.calls.map((c) => `${c.domain}.${c.service}:${c.data.entity_id || ""}`);
  assert.ok(sigs.includes("lock.lock:lock.lepas_lock"));
  assert.ok(sigs.includes("climate.set_hvac_mode:climate.lepas_climate"));
  assert.ok(sigs.includes("climate.set_temperature:climate.lepas_climate"));
  assert.ok(sigs.includes("switch.turn_on:switch.lepas_driver_seat_heating"));
  assert.ok(sigs.includes("switch.turn_on:switch.lepas_quick_departure"));
  assert.ok(sigs.includes("number.set_value:number.lepas_climate_duration"));
  assert.ok(sigs.includes("time.set_value:time.lepas_charge_start_time"));
  assert.ok(
    hass.calls.some(
      (c) =>
        c.domain === "lepas" &&
        c.service === "set_charging_schedule" &&
        c.data.apply === false &&
        Array.isArray(c.data.days) &&
        c.data.days.join(",") === "1,2,3,4,5,6"
    )
  );
});

test("State, focus preservation on set hass(), and rejected callService error banner", async () => {
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

  // Open unlock modal
  card.shadowRoot.querySelector('[data-action-id="unlock"]').click();
  const dlg = card.shadowRoot.querySelector('dialog[data-bind="confirmDialog"]');
  assert.equal(dlg.open, true);
  assert.equal(card.shadowRoot.querySelector('[data-action-id="unlock"]').getAttribute("data-confirming"), null);

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

  // Preserved activeTab, expandedDay, open modal, focus, and in-progress input value
  assert.equal(card.shadowRoot.querySelector('[data-tab="charging"]').classList.contains("is-active"), true);
  assert.ok(card.shadowRoot.querySelector('[data-day-editor="fri"]'), "Expanded Friday must survive set hass()");
  assert.equal(card.shadowRoot.querySelector('dialog[data-bind="confirmDialog"]').open, true);
  assert.equal(card.shadowRoot.activeElement, timeInput);
  assert.equal(timeInput.value, "04:15");

  // Dismiss modal before proceeding
  card.shadowRoot.querySelector('[data-dialog-action="cancel"]').click();
  assert.equal(dlg.open, false);

  // Toggle Friday departure switch and time inside expanded day editor
  card.shadowRoot.querySelector('[data-action-id="day_toggle_fri"]').click();
  const friTime = card.shadowRoot.querySelector('[data-entity-input="time.lepas_departure_fri_time"]');
  friTime.value = "08:45";
  friTime.dispatchEvent(new Event("change", { bubbles: true }));
  await Promise.resolve();
  assert.ok(hass.calls.some((c) => c.domain === "switch" && c.service === "turn_off" && c.data.entity_id === "switch.lepas_departure_fri_enabled"));
  assert.ok(hass.calls.some((c) => c.domain === "time" && c.service === "set_value" && c.data.entity_id === "time.lepas_departure_fri_time" && c.data.time === "08:45:00"));

  // Rejected service call clears pending and shows inline non-blocking error banner + coral cmdResultBadge
  shouldReject = true;
  card.shadowRoot.querySelector('[data-action-id="apply_charging_schedule"]').click();
  assert.equal(dlg.open, true);
  card.shadowRoot.querySelector('[data-dialog-action="confirm"]').click();
  await Promise.resolve();
  await Promise.resolve();

  const errBanner = card.shadowRoot.querySelector('[role="alert"].error-banner');
  assert.ok(errBanner, "Error banner must render on rejected callService");
  assert.ok(errBanner.textContent.includes("Vehicle timeout"));
  const cmdBadge = card.shadowRoot.querySelector('[data-bind="cmdResultBadge"]');
  assert.equal(cmdBadge.classList.contains("hidden"), false);
  assert.equal(cmdBadge.classList.contains("is-coral"), true);
  assert.equal(cmdBadge.classList.contains("is-emerald"), false);
  assert.ok(cmdBadge.textContent.startsWith("Command failed · "));
  assert.ok(cmdBadge.textContent.endsWith("✕"));

  // Cleanup dialog/pending state on disconnect
  card.shadowRoot.querySelector('[data-action-id="unlock"]').click();
  assert.equal(dlg.open, true);
  card.disconnectedCallback();
  assert.equal(dlg.open, false, "disconnectedCallback must close open dialog");
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

test("v1.20.0 Hero 2:1 stage, separate .hero-meta with data-device, and heroStateBadge DOM stability", () => {
  const hass = makeFullHass({}, "it");
  const card = createCard({ title: "Lepas L8" }, hass);
  const styleText = card.shadowRoot.querySelector("style")?.textContent || "";

  const heroStage = card.shadowRoot.querySelector(".hero-stage");
  const heroMeta = card.shadowRoot.querySelector(".hero-meta");
  assert.ok(heroStage, ".hero-stage must exist");
  assert.ok(heroMeta, ".hero-meta must exist");
  assert.ok(styleText.includes("aspect-ratio: 2 / 1"), "Hero stage CSS must declare aspect-ratio: 2 / 1");
  assert.ok(styleText.includes("object-fit: contain"), "Hero image CSS must declare object-fit: contain");

  const heroTitle = heroMeta.querySelector('[data-bind="heroTitle"]');
  const heroSub = heroMeta.querySelector('[data-bind="heroSub"]');
  assert.ok(heroTitle, "heroTitle must reside inside .hero-meta");
  assert.ok(heroSub, "heroSub must reside inside .hero-meta");
  assert.equal(heroStage.querySelector('[data-bind="heroTitle"]'), null, "heroTitle must NOT overlay .hero-stage");
  assert.equal(heroMeta.getAttribute("data-device"), "dev_lepas_1", ".hero-meta must keep data-device");

  const badge = heroMeta.querySelector('[data-bind="heroStateBadge"]');
  assert.ok(badge, "[data-bind='heroStateBadge'] must always exist in DOM");
  assert.equal(badge.classList.contains("hidden"), false, "Active charging shows heroStateBadge");

  // Switching charging & climate off hides badge via .hidden without rebuilding .hero-stage
  const nextHass = makeFullHass({
    "switch.lepas_charging": makeState("switch.lepas_charging", "off"),
    "sensor.lepas_charging_status": makeState("sensor.lepas_charging_status", "Idle"),
    "climate.lepas_climate": makeState("climate.lepas_climate", "off", { temperature: 21 }),
  }, "it");
  card.hass = nextHass;
  assert.equal(card.shadowRoot.querySelector(".hero-stage"), heroStage, "DOM skeleton must NOT rebuild on state change");
  assert.equal(card.shadowRoot.querySelector('[data-bind="heroStateBadge"]').classList.contains("hidden"), true);
});

test("v1.20.0 SVG icons on tabs & 4 panels, aria-selected sync, and zero stark white active fills", () => {
  const hass = makeFullHass({}, "it");
  const card = createCard({ layout: "compact", default_tab: "overview" }, hass);
  const styleText = card.shadowRoot.querySelector("style")?.textContent || "";

  assert.ok(!styleText.includes(".tab-btn.is-active { background: var(--lp-text)"), "Tab active must NOT use stark white var(--lp-text) background");
  assert.ok(!styleText.includes(".day-chip.is-expanded { background: var(--lp-text)"), "Expanded day chip must NOT use stark white var(--lp-text) background");
  assert.ok(!/background:\s*var\(--lp-text\)/.test(styleText), "No element may use background: var(--lp-text)");

  const tabBtns = card.shadowRoot.querySelectorAll("[data-tab]");
  assert.equal(tabBtns.length, 4);
  for (const tb of tabBtns) {
    assert.ok(tb.querySelector("svg"), `Tab ${tb.getAttribute("data-tab")} must contain inline <svg>`);
    const expectedSelected = tb.getAttribute("data-tab") === "overview" ? "true" : "false";
    assert.equal(tb.getAttribute("aria-selected"), expectedSelected);
  }

  for (const panelName of ["overview", "climate", "charging", "security"]) {
    const panel = card.shadowRoot.querySelector(`[data-panel="${panelName}"]`);
    assert.ok(panel, `Panel ${panelName} missing`);
    assert.ok(panel.querySelector("svg"), `Panel ${panelName} must render inline SVG icons`);
  }

  // Tab switch updates aria-selected
  card.shadowRoot.querySelector('[data-tab="charging"]').click();
  assert.equal(card.shadowRoot.querySelector('[data-tab="overview"]').getAttribute("aria-selected"), "false");
  assert.equal(card.shadowRoot.querySelector('[data-tab="charging"]').getAttribute("aria-selected"), "true");

  // Dynamic button preserves icon & exact textContent across _applyBindings and opens modal without mutating button label
  const unlockBtn = card.shadowRoot.querySelector('[data-action-id="unlock"]');
  assert.ok(unlockBtn.querySelector("svg"), "Dynamic unlock button must keep SVG icon after _applyBindings");
  assert.equal(unlockBtn.textContent, "Sblocca");
  unlockBtn.click();
  assert.ok(unlockBtn.querySelector("svg"), "Dynamic unlock button must keep SVG icon when modal opens");
  assert.equal(unlockBtn.textContent, "Sblocca");
  assert.equal(unlockBtn.getAttribute("data-confirming"), null);
  assert.equal(card.shadowRoot.querySelector('dialog[data-bind="confirmDialog"]').open, true);
  assert.equal(card.shadowRoot.querySelector('[data-bind="confirmDialogAction"]').textContent, "Sblocca");
  card.shadowRoot.querySelector('[data-dialog-action="cancel"]').click();
  card.disconnectedCallback();
});

test("v1.20.0 formatMetric strips .00 on odometer km even with hass.formatEntityState while preserving bar/kWh decimals", () => {
  const h = LepasCard._helpers;
  assert.equal(typeof h.formatMetric, "function");

  assert.equal(h.formatMetric(makeState("sensor.lepas_odometer", "551.0", { unit_of_measurement: "km" }), "it"), "551 km");
  assert.equal(h.formatMetric(makeState("sensor.lepas_tire_pressure_front_left", "2.55", { unit_of_measurement: "bar" }), "it"), "2.55 bar");
  assert.equal(h.formatMetric(makeState("sensor.lepas_home_charging_energy", "34.94", { unit_of_measurement: "kWh" }), "it"), "34.94 kWh");

  const hass = makeFullHass({
    "sensor.lepas_odometer": makeState("sensor.lepas_odometer", "551.0", { unit_of_measurement: "km" }),
    "sensor.lepas_tire_pressure_front_left": makeState("sensor.lepas_tire_pressure_front_left", "2.55", { unit_of_measurement: "bar" }),
    "sensor.lepas_home_charging_energy": makeState("sensor.lepas_home_charging_energy", "34.94", { unit_of_measurement: "kWh" }),
  }, "it");
  hass.formatEntityState = (stateObj) => {
    if (stateObj && stateObj.entity_id === "sensor.lepas_odometer") return "551,00 km";
    return `${stateObj.state} ${stateObj.attributes?.unit_of_measurement || ""}`.trim();
  };

  const card = createCard({}, hass);
  const odoVal = card.shadowRoot.querySelector('[data-bind="mOdoVal"]');
  assert.equal(odoVal.textContent, "551 km");
  assert.ok(card.shadowRoot.querySelector('[data-bind="heroSub"]').textContent.includes("551 km"));
  assert.ok(card.shadowRoot.querySelector('[data-tpms="front_left"]').textContent.includes("2.55 bar"));
  assert.ok(card.shadowRoot.querySelector('[data-bind="homeEnergyBadge"]').textContent.includes("34.94 kWh"));
});

test("v1.20.0 Scheduled Charging L-D chips, single-day guard, presets, onFailure fallback/error, and manual vs departure mode", async () => {
  const h = LepasCard._helpers;
  assert.deepEqual(h.computeToggleDays([3], 3), [3], "computeToggleDays single-day guard must keep [3]");
  assert.equal(h.presetForDays([6, 7]), "weekend");
  assert.deepEqual(h.presetDaysForKey("weekdays"), [1, 2, 3, 4, 5]);

  let rejectError = null;
  const hass = makeFullHass({
    "switch.lepas_sync_charge_to_departure": makeState("switch.lepas_sync_charge_to_departure", "off"),
    "sensor.lepas_next_departure": makeState("sensor.lepas_next_departure", "Domani mer 07:30", {
      planned_charge_start: "01:00",
    }),
  }, "it");
  hass.callService = (domain, service, data) => {
    hass.calls.push({ domain, service, data });
    if (rejectError && domain === "lepas" && service === "set_charging_schedule") {
      return Promise.reject(rejectError);
    }
    return Promise.resolve();
  };

  const card = createCard({ layout: "compact", default_tab: "charging" }, hass);
  const dayChips = card.shadowRoot.querySelectorAll("[data-charge-day]");
  assert.equal(dayChips.length, 7);
  for (let d = 1; d <= 5; d += 1) {
    assert.equal(card.shadowRoot.querySelector(`[data-charge-day="${d}"]`).classList.contains("is-active"), true);
  }
  assert.equal(card.shadowRoot.querySelector('[data-charge-day="6"]').classList.contains("is-active"), false);
  assert.equal(card.shadowRoot.querySelector('[data-charge-day="7"]').classList.contains("is-active"), false);

  const heroStageBefore = card.shadowRoot.querySelector(".hero-stage");

  // Tap day 6 -> optimistic update + lepas.set_charging_schedule(apply=false) without DOM rebuild or tab reset
  card.shadowRoot.querySelector('[data-charge-day="6"]').click();
  await Promise.resolve();
  assert.equal(card.shadowRoot.querySelector(".hero-stage"), heroStageBefore);
  assert.equal(card.shadowRoot.querySelector('[data-tab="charging"]').classList.contains("is-active"), true);
  assert.equal(card.shadowRoot.querySelector('[data-charge-day="6"]').classList.contains("is-active"), true);
  assert.deepEqual(hass.calls[0], {
    domain: "lepas",
    service: "set_charging_schedule",
    data: { days: [1, 2, 3, 4, 5, 6], apply: false },
  });

  // Preset weekend
  card.shadowRoot.querySelector('[data-charge-preset="weekend"]').click();
  await Promise.resolve();
  assert.deepEqual(hass.calls[1], {
    domain: "lepas",
    service: "set_charging_schedule",
    data: { days: [6, 7], apply: false },
  });

  // Fallback when set_charging_schedule fails with "service not found" and days match preset "weekend"
  rejectError = new Error("Service lepas.set_charging_schedule not found");
  const cardFb = createCard({ default_tab: "charging" }, makeFullHass({}, "it"));
  cardFb._hass.callService = (domain, service, data) => {
    cardFb._hass.calls.push({ domain, service, data });
    if (domain === "lepas" && service === "set_charging_schedule") {
      return Promise.reject(rejectError);
    }
    return Promise.resolve();
  };
  cardFb.shadowRoot.querySelector('[data-charge-preset="weekend"]').click();
  await Promise.resolve();
  await Promise.resolve();
  assert.ok(
    cardFb._hass.calls.some(
      (c) =>
        c.domain === "select" &&
        c.service === "select_option" &&
        c.data.entity_id === "select.lepas_charge_days" &&
        c.data.option === "weekend"
    ),
    "Must fallback to select.select_option when set_charging_schedule service not found"
  );

  // Generic error clears optimistic days back to entity state and shows error banner
  const cardErr = createCard({ default_tab: "charging" }, makeFullHass({}, "it"));
  cardErr._hass.callService = (domain, service, data) => {
    cardErr._hass.calls.push({ domain, service, data });
    if (domain === "lepas") return Promise.reject(new Error("Gateway busy"));
    return Promise.resolve();
  };
  cardErr.shadowRoot.querySelector('[data-charge-day="6"]').click();
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(cardErr.shadowRoot.querySelector('[data-charge-day="6"]').classList.contains("is-active"), false);
  const errEl = cardErr.shadowRoot.querySelector('[role="alert"].error-banner');
  assert.equal(errEl.classList.contains("hidden"), false);
  assert.ok(errEl.textContent.includes("Gateway busy"));

  // Single-day guard in DOM: tapping the sole active day [3] never sends days: []
  const singleHass = makeFullHass({
    "select.lepas_charge_days": makeState("select.lepas_charge_days", "custom", {
      options: ["all_days", "weekdays", "weekend", "mon_wed_fri", "tue_thu_sat", "custom"],
      days: [3],
    }),
  }, "it");
  const singleCard = createCard({ default_tab: "charging" }, singleHass);
  singleCard.shadowRoot.querySelector('[data-charge-day="3"]').click();
  await Promise.resolve();
  assert.equal(singleCard.shadowRoot.querySelector('[data-charge-day="3"]').classList.contains("is-active"), true);
  assert.equal(
    singleHass.calls.some((c) => Array.isArray(c.data && c.data.days) && c.data.days.length === 0),
    false,
    "Must NEVER send days: []"
  );

  // Segmented mode: manual vs departure
  const manualBox = card.shadowRoot.querySelector(".manual-charge-box");
  const depBox = card.shadowRoot.querySelector(".departure-charge-box");
  assert.ok(manualBox && depBox);
  assert.equal(manualBox.classList.contains("hidden"), false);
  assert.equal(depBox.classList.contains("hidden"), true);

  // Tapping manual when already off is a no-op
  const beforeManualCalls = hass.calls.length;
  card.shadowRoot.querySelector('[data-charge-mode="manual"]').click();
  assert.equal(hass.calls.length, beforeManualCalls);

  // Tapping departure when off calls switch.turn_on
  card.shadowRoot.querySelector('[data-charge-mode="departure"]').click();
  await Promise.resolve();
  assert.deepEqual(hass.calls[beforeManualCalls], {
    domain: "switch",
    service: "turn_on",
    data: { entity_id: "switch.lepas_sync_charge_to_departure" },
  });

  // When sync_charge_to_departure is ON, .departure-charge-box is visible and shows planned_charge_start "01:00"
  const depHass = makeFullHass({
    "switch.lepas_sync_charge_to_departure": makeState("switch.lepas_sync_charge_to_departure", "on"),
    "sensor.lepas_next_departure": makeState("sensor.lepas_next_departure", "Domani mer 07:30", {
      planned_charge_start: "01:00",
    }),
  }, "it");
  card.hass = depHass;
  assert.equal(card.shadowRoot.querySelector(".manual-charge-box").classList.contains("hidden"), true);
  assert.equal(card.shadowRoot.querySelector(".departure-charge-box").classList.contains("hidden"), false);
  assert.ok(card.shadowRoot.querySelector(".departure-charge-box").textContent.includes("01:00"));

  // Tapping manual when on calls switch.turn_off
  card.shadowRoot.querySelector('[data-charge-mode="manual"]').click();
  await Promise.resolve();
  assert.deepEqual(depHass.calls[0], {
    domain: "switch",
    service: "turn_off",
    data: { entity_id: "switch.lepas_sync_charge_to_departure" },
  });
});

test("v1.20.0 Translated departure_climate_mode options in it, en, nl", () => {
  const h = LepasCard._helpers;
  assert.equal(h.translateOption("departure_climate_mode", "at_home", "it"), "Solo a casa");
  assert.equal(h.translateOption("departure_climate_mode", "anywhere", "it"), "Ovunque");
  assert.equal(h.translateOption("departure_climate_mode", "off", "it"), "Disattivato");
  assert.equal(h.translateOption("departure_climate_mode", "at_home", "en"), "Home only");
  assert.equal(h.translateOption("departure_climate_mode", "at_home", "nl"), "Alleen thuis");

  for (const [lang, expected] of [
    ["it", ["Solo a casa", "Ovunque", "Disattivato"]],
    ["en", ["Home only", "Anywhere", "Off"]],
    ["nl", ["Alleen thuis", "Overal", "Uitgeschakeld"]],
  ]) {
    const card = createCard({ default_tab: "charging" }, makeFullHass({}, lang));
    const sel = card.shadowRoot.querySelector('[data-entity-input="select.lepas_departure_climate_mode"]');
    assert.ok(sel, `departure_climate_mode select missing for ${lang}`);
    const optionTexts = sel.querySelectorAll("option").map((o) => o.textContent.trim());
    assert.deepEqual(optionTexts, expected);
    assert.equal(optionTexts.includes("at_home"), false);
  }
});

test("v1.20.0 TPMS localized wheel labels and grouped security/closures buttons", () => {
  const cardIt = createCard({ default_tab: "security" }, makeFullHass({}, "it"));
  assert.ok(cardIt.shadowRoot.querySelector('[data-tpms="front_left"]').textContent.includes("ANT SX"));
  assert.ok(cardIt.shadowRoot.querySelector('[data-tpms="front_right"]').textContent.includes("ANT DX"));
  assert.ok(cardIt.shadowRoot.querySelector('[data-tpms="rear_left"]').textContent.includes("POST SX"));
  assert.ok(cardIt.shadowRoot.querySelector('[data-tpms="rear_right"]').textContent.includes("POST DX"));

  const cardEn = createCard({ default_tab: "security" }, makeFullHass({}, "en"));
  assert.ok(cardEn.shadowRoot.querySelector('[data-tpms="front_left"]').textContent.includes("FL"));
  assert.ok(cardEn.shadowRoot.querySelector('[data-tpms="front_right"]').textContent.includes("FR"));
  assert.ok(cardEn.shadowRoot.querySelector('[data-tpms="rear_left"]').textContent.includes("RL"));
  assert.ok(cardEn.shadowRoot.querySelector('[data-tpms="rear_right"]').textContent.includes("RR"));

  const closuresGrp = cardIt.shadowRoot.querySelector('[data-security-group="closures"]');
  const securityGrp = cardIt.shadowRoot.querySelector('[data-security-group="security"]');
  assert.ok(closuresGrp, "Closures group missing");
  assert.ok(securityGrp, "Security group missing");
  assert.ok(closuresGrp.querySelector('[data-action-id="unlock"]'));
  assert.ok(closuresGrp.querySelector('[data-action-id="trunk_open"]'));
  assert.ok(securityGrp.querySelector('[data-action-id="alarm_toggle"]'));
  assert.ok(securityGrp.querySelector('[data-action-id="locate_gps"]'));
});

test("v1.20.1 Time inputs block manual keyboard typing and open picker on click", () => {
  const card = createCard({ default_tab: "charging" }, makeFullHass({}, "it"));
  const timeInputs = card.shadowRoot.querySelectorAll('input[type="time"]');
  assert.ok(timeInputs.length >= 2, "Expected scheduled charge and quick departure time inputs");

  for (const inp of timeInputs) {
    assert.equal(inp.getAttribute("inputmode"), "none", "Time input must disable mobile keyboard via inputmode=none");
    assert.equal(inp.hasAttribute("readonly"), false, "Time input must NOT set readonly so showPicker() stays valid");
  }

  const target = timeInputs[0];
  let pickerCalls = 0;
  target.showPicker = () => {
    pickerCalls += 1;
  };

  // Typing digits or Backspace must be prevented
  for (const key of ["1", "5", "Backspace", "Delete", "a"]) {
    const ev = new Event("keydown", { bubbles: true, cancelable: true });
    ev.key = key;
    target.dispatchEvent(ev);
    assert.equal(ev.defaultPrevented, true, `Key ${key} must be blocked on time input`);
  }

  // beforeinput / paste must also be prevented
  const bi = new Event("beforeinput", { bubbles: true, cancelable: true });
  target.dispatchEvent(bi);
  assert.equal(bi.defaultPrevented, true);
  const pasteEv = new Event("paste", { bubbles: true, cancelable: true });
  target.dispatchEvent(pasteEv);
  assert.equal(pasteEv.defaultPrevented, true);

  // Navigation keys Tab / Escape stay allowed
  for (const allowed of ["Tab", "Escape"]) {
    const ev = new Event("keydown", { bubbles: true, cancelable: true });
    ev.key = allowed;
    target.dispatchEvent(ev);
    assert.equal(ev.defaultPrevented, false, `Key ${allowed} must NOT be blocked`);
  }

  // Clicking or pressing Enter/Space opens the picker via showPicker()
  target.click();
  assert.equal(pickerCalls, 1, "Clicking time input must open picker");
  const enterEv = new Event("keydown", { bubbles: true, cancelable: true });
  enterEv.key = "Enter";
  target.dispatchEvent(enterEv);
  assert.equal(enterEv.defaultPrevented, true);
  assert.equal(pickerCalls, 2, "Pressing Enter on time input must open picker");
});

test("v1.21.2 Scheduled car departure readout & adaptive Apply/Disable on car button", async () => {
  // When car has an active plan and HA has no departures -> shows car time & "Disattiva su auto"
  const hassOff = makeFullHass({
    "switch.lepas_quick_departure": makeState("switch.lepas_quick_departure", "off"),
    "switch.lepas_departure_mon_enabled": makeState("switch.lepas_departure_mon_enabled", "off"),
    "switch.lepas_departure_wed_enabled": makeState("switch.lepas_departure_wed_enabled", "off"),
    "switch.lepas_departure_fri_enabled": makeState("switch.lepas_departure_fri_enabled", "off"),
    "sensor.lepas_next_departure": makeState("sensor.lepas_next_departure", "Disattivata", {
      departure_at: null,
    }),
    "switch.lepas_native_departure_sync": makeState("switch.lepas_native_departure_sync", "off"),
    "button.lepas_apply_departure_schedule": makeState("button.lepas_apply_departure_schedule", "unknown"),
    "sensor.lepas_scheduled_departure": makeState("sensor.lepas_scheduled_departure", "06:35", {
      attiva: true,
      orario: "06:35",
      giorni: [1, 2, 3, 4, 5, 6, 7],
      riepilogo: "06:35 · lun, mar, mer, gio, ven, sab, dom",
      synced_with_ha: false,
    }),
  }, "it");

  const card = createCard({ layout: "compact", default_tab: "charging" }, hassOff);

  assert.equal(card.shadowRoot.querySelector('[data-action-id="native_departure_sync_toggle"]'), null, "Sync su auto toggle must be omitted from card");
  assert.equal(card.shadowRoot.querySelector('[data-bind="depSyncBadge"]'), null, "Ambiguous sync badge must be omitted from card");

  const nextTxt = card.shadowRoot.querySelector('[data-bind="nextDepText"]');
  const schedTxt = card.shadowRoot.querySelector('[data-bind="schedDepText"]');
  const applyBtn = card.shadowRoot.querySelector('[data-action-id="apply_departure_schedule"]');
  assert.ok(nextTxt && schedTxt && applyBtn);
  assert.equal(nextTxt.textContent, "Attiva", "Prossima partenza must show 'Attiva' when car has active plan and HA has none");
  assert.equal(applyBtn.classList.contains("hidden"), false);
  assert.ok(schedTxt.textContent.includes("06:35"), `Expected next car departure time 06:35, got: ${schedTxt.textContent}`);
  assert.equal(schedTxt.textContent.includes("lun, mar"), false, `Car departure readout must show next occurrence instead of full weekday list, got: ${schedTxt.textContent}`);
  assert.ok(applyBtn.textContent.includes("Disattiva su auto"), `Expected 'Disattiva su auto' when HA has no active departures, got: ${applyBtn.textContent}`);

  // Clicking button opens confirm dialog with "Disattiva su auto", then confirming calls button.press
  const dlg = card.shadowRoot.querySelector('dialog[data-bind="confirmDialog"]');
  applyBtn.click();
  assert.equal(hassOff.calls.length, 0);
  assert.equal(dlg.open, true);
  assert.equal(card.shadowRoot.querySelector('[data-bind="confirmDialogAction"]').textContent, "Disattiva su auto");
  card.shadowRoot.querySelector('[data-dialog-action="confirm"]').click();
  await Promise.resolve();
  assert.equal(dlg.open, false);
  assert.deepEqual(hassOff.calls[0], {
    domain: "button",
    service: "press",
    data: { entity_id: "button.lepas_apply_departure_schedule" },
  });

  // When BOTH HA and car have no active departure -> button is hidden and schedDepText shows noScheduledDeparture
  card.hass = makeFullHass({
    "switch.lepas_quick_departure": makeState("switch.lepas_quick_departure", "off"),
    "switch.lepas_departure_mon_enabled": makeState("switch.lepas_departure_mon_enabled", "off"),
    "switch.lepas_departure_wed_enabled": makeState("switch.lepas_departure_wed_enabled", "off"),
    "switch.lepas_departure_fri_enabled": makeState("switch.lepas_departure_fri_enabled", "off"),
    "sensor.lepas_next_departure": makeState("sensor.lepas_next_departure", "Disattivata", {
      departure_at: null,
    }),
    "button.lepas_apply_departure_schedule": makeState("button.lepas_apply_departure_schedule", "unknown"),
    "sensor.lepas_scheduled_departure": makeState("sensor.lepas_scheduled_departure", "Disattivata", {
      attiva: false,
      orario: "06:35",
      riepilogo: "Disattivata (06:35 · lun)",
    }),
  }, "it");
  const bothOffBtn = card.shadowRoot.querySelector('[data-action-id="apply_departure_schedule"]');
  assert.ok(bothOffBtn);
  assert.equal(bothOffBtn.classList.contains("hidden"), true, "Button must be hidden when both HA and car have no active plan");
  assert.equal(card.shadowRoot.querySelector('[data-bind="nextDepText"]').textContent, "Disattivata");
  assert.equal(card.shadowRoot.querySelector('[data-bind="schedDepText"]').textContent, "Nessuna partenza programmata");

  // When HA has an active departure & car plan is disabled -> shows "Nessuna partenza programmata" & "Applica su auto"
  card.hass = makeFullHass({
    "switch.lepas_quick_departure": makeState("switch.lepas_quick_departure", "on"),
    "button.lepas_apply_departure_schedule": makeState("button.lepas_apply_departure_schedule", "unknown"),
    "sensor.lepas_scheduled_departure": makeState("sensor.lepas_scheduled_departure", "Disattivata", {
      attiva: false,
      orario: "06:35",
      riepilogo: "Disattivata (06:35 · lun)",
    }),
  }, "it");
  const schedOffTxt = card.shadowRoot.querySelector('[data-bind="schedDepText"]');
  const applyOnBtn = card.shadowRoot.querySelector('[data-action-id="apply_departure_schedule"]');
  assert.equal(schedOffTxt.textContent, "Nessuna partenza programmata");
  assert.equal(applyOnBtn.classList.contains("hidden"), false);
  assert.ok(applyOnBtn.textContent.includes("Applica su auto"), `Expected 'Applica su auto' when HA has active departure, got: ${applyOnBtn.textContent}`);

  // Also works with IT entity alias sensor.lepas_partenza_programmata in nl
  const nlCard = createCard({ default_tab: "charging" }, makeFullHass({
    "sensor.lepas_partenza_programmata": makeState("sensor.lepas_partenza_programmata", "Disattivata", {
      attiva: false,
    }),
  }, "nl"));
  assert.equal(nlCard.shadowRoot.querySelector('[data-bind="schedDepText"]').textContent, "Geen gepland vertrek");

  // Graceful omission when entities absent
  const minimalCard = createCard({ default_tab: "charging" }, makeFullHass({}, "it"));
  assert.equal(minimalCard.shadowRoot.querySelector('[data-action-id="apply_departure_schedule"]'), null);
  assert.equal(minimalCard.shadowRoot.querySelector('[data-bind="schedDepText"]'), null);
});

test("v1.21.0 Dynamic departure climate extras: strict allowlist, XSS escaping, service call, mutual exclusion, and failure rollback", async () => {
  const h = LepasCard._helpers;
  assert.ok(Array.isArray(h.ALLOWED_CLIMATE_EXTRAS), "ALLOWED_CLIMATE_EXTRAS helper must exist");
  assert.equal(h.ALLOWED_CLIMATE_EXTRAS.length, 12);
  assert.equal(typeof h.filterAllowedClimateExtras, "function");
  assert.deepEqual(
    h.filterAllowedClimateExtras(["steering_wheel_heating", "<img onerror=alert(1)>", "toString", "__proto__", "windshield_defog"]),
    ["steering_wheel_heating", "windshield_defog"]
  );

  const initialExtras = ["driver_seat_heating", "<img onerror=alert(1)>"];
  const hass = makeFullHass({
    "sensor.lepas_next_departure": makeState("sensor.lepas_next_departure", "Domani mer 07:30", {
      departure_at: "2026-11-18T07:30:00+01:00",
      allowed_climate_extras: [
        "steering_wheel_heating",
        "driver_seat_heating",
        "driver_seat_ventilation",
        "<img onerror=alert(1)>",
        "injected_unknown_extra",
      ],
      climate_extras: initialExtras,
    }),
  }, "it");

  const card = createCard({ layout: "compact", default_tab: "charging" }, hass);
  const chips = card.shadowRoot.querySelectorAll("[data-climate-extra]");
  assert.equal(chips.length, 3, "Only allowlisted climate extras may render");
  assert.equal(card.shadowRoot.querySelector("img[onerror]"), null);
  assert.equal(card.shadowRoot.innerHTML.includes("onerror=alert"), false);

  const heatChip = card.shadowRoot.querySelector('[data-climate-extra="driver_seat_heating"]');
  const ventChip = card.shadowRoot.querySelector('[data-climate-extra="driver_seat_ventilation"]');
  const steerChip = card.shadowRoot.querySelector('[data-climate-extra="steering_wheel_heating"]');
  assert.ok(heatChip && ventChip && steerChip);
  assert.equal(heatChip.classList.contains("is-active"), true);
  assert.equal(heatChip.getAttribute("aria-pressed"), "true");
  assert.equal(ventChip.classList.contains("is-active"), false);

  // Clicking ventilation chip with config_entry_id present sends { entry_id, extras } and resolves seat mutual exclusion
  const entryHass = makeFullHass({
    "sensor.lepas_next_departure": makeState("sensor.lepas_next_departure", "Domani mer 07:30", {
      allowed_climate_extras: ["steering_wheel_heating", "driver_seat_heating", "driver_seat_ventilation"],
      climate_extras: ["driver_seat_heating", "steering_wheel_heating"],
    }),
  }, "it");
  entryHass.entities["sensor.lepas_next_departure"].config_entry_id = "entry_lepas_1";
  const entryCard = createCard({ default_tab: "charging" }, entryHass);
  entryCard.shadowRoot.querySelector('[data-climate-extra="driver_seat_ventilation"]').click();
  await Promise.resolve();
  assert.deepEqual(entryHass.calls[0], {
    domain: "lepas",
    service: "set_departure_climate_extras",
    data: {
      entry_id: "entry_lepas_1",
      extras: ["steering_wheel_heating", "driver_seat_ventilation"],
    },
  });

  // When config_entry_id is absent, entry_id is omitted gracefully; on rejection pending clears & HA state stays unmutated
  let rejectPending;
  const cachedArr = ["driver_seat_heating"];
  const failHass = makeFullHass({
    "sensor.lepas_next_departure": makeState("sensor.lepas_next_departure", "Domani mer 07:30", {
      allowed_climate_extras: ["steering_wheel_heating", "driver_seat_heating", "driver_seat_ventilation"],
      climate_extras: cachedArr,
    }),
  }, "en");
  failHass.callService = (domain, service, data) => {
    failHass.calls.push({ domain, service, data });
    return new Promise((_, reject) => {
      rejectPending = reject;
    });
  };
  const failCard = createCard({ default_tab: "charging" }, failHass);
  const steerFailChip = failCard.shadowRoot.querySelector('[data-climate-extra="steering_wheel_heating"]');
  steerFailChip.click();

  // While in flight: pending class is set and entry_id omitted
  assert.equal(failCard.shadowRoot.querySelector('[data-climate-extra="steering_wheel_heating"]').classList.contains("is-pending"), true);
  assert.equal(Object.prototype.hasOwnProperty.call(failHass.calls[0].data, "entry_id"), false);
  assert.deepEqual(failHass.calls[0], {
    domain: "lepas",
    service: "set_departure_climate_extras",
    data: { extras: ["driver_seat_heating", "steering_wheel_heating"] },
  });

  // Reject service call -> clears pending, reverts active state, shows error, leaves cached HA state unmutated
  rejectPending(new Error("Vehicle asleep"));
  await Promise.resolve();
  await Promise.resolve();

  const settledSteer = failCard.shadowRoot.querySelector('[data-climate-extra="steering_wheel_heating"]');
  assert.equal(settledSteer.classList.contains("is-pending"), false, "Pending class must clear on failure");
  assert.equal(settledSteer.classList.contains("is-active"), false, "Failed chip must revert to un-activated state");
  assert.equal(failCard.shadowRoot.querySelector('[data-climate-extra="driver_seat_heating"]').classList.contains("is-active"), true);
  assert.deepEqual(cachedArr, ["driver_seat_heating"], "Cached HA state attribute array must NEVER be mutated");
  assert.equal(failCard.shadowRoot.querySelector('[role="alert"].error-banner').classList.contains("hidden"), false);

  // Absent / empty allowed_climate_extras hides the climate extras sub-box
  const noExtrasCard = createCard({ default_tab: "charging" }, makeFullHass({}, "it"));
  assert.equal(noExtrasCard.shadowRoot.querySelector('[data-bind="depExtrasBox"]'), null);
});

test("v1.21.0 Battery preheat sub-box visibility and controls (cat. 216)", async () => {
  // Hidden when cat. 216 entities are absent
  const noBatCard = createCard({ default_tab: "charging" }, makeFullHass({}, "it"));
  assert.equal(noBatCard.shadowRoot.querySelector('[data-bind="batteryHeatBox"]'), null);

  // Visible when cat. 216 entities are present
  const hass = makeFullHass({
    "switch.lepas_battery_pack_heat": makeState("switch.lepas_battery_pack_heat", "off"),
    "time.lepas_battery_pack_heat_time": makeState("time.lepas_battery_pack_heat_time", "07:00:00"),
    "switch.lepas_sync_battery_heat_to_departure": makeState("switch.lepas_sync_battery_heat_to_departure", "on"),
    "sensor.lepas_next_departure": makeState("sensor.lepas_next_departure", "Domani mer 07:30", {
      battery_heat_start: "07:00",
    }),
  }, "it");

  const card = createCard({ layout: "compact", default_tab: "charging" }, hass);
  const box = card.shadowRoot.querySelector('[data-bind="batteryHeatBox"]');
  assert.ok(box, "Battery preheat sub-box must render when cat. 216 entities exist");

  const hint = box.querySelector('[data-bind="batteryHeatSyncHint"]');
  assert.ok(hint);
  assert.equal(hint.classList.contains("hidden"), false);
  assert.ok(hint.textContent.includes("07:00"));

  const heatBtn = box.querySelector('[data-action-id="battery_pack_heat_toggle"]');
  const syncBtn = box.querySelector('[data-action-id="sync_battery_heat_toggle"]');
  const timeInput = box.querySelector('[data-entity-input="time.lepas_battery_pack_heat_time"]');
  assert.ok(heatBtn && syncBtn && timeInput);
  assert.equal(timeInput.getAttribute("inputmode"), "none");
  assert.equal(timeInput.value, "07:00");

  heatBtn.click();
  await Promise.resolve();
  assert.deepEqual(hass.calls[0], {
    domain: "switch",
    service: "turn_on",
    data: { entity_id: "switch.lepas_battery_pack_heat" },
  });

  syncBtn.click();
  await Promise.resolve();
  assert.deepEqual(hass.calls[1], {
    domain: "switch",
    service: "turn_off",
    data: { entity_id: "switch.lepas_sync_battery_heat_to_departure" },
  });

  timeInput.value = "06:30";
  timeInput.dispatchEvent(new Event("change", { bubbles: true }));
  await Promise.resolve();
  assert.deepEqual(hass.calls[2], {
    domain: "time",
    service: "set_value",
    data: { entity_id: "time.lepas_battery_pack_heat_time", time: "06:30:00" },
  });
});

test("v1.21.3 formatCarNextDeparture computes concise next occurrence (Oggi/Domani/Weekday) across IT/EN/NL", () => {
  const h = LepasCard._helpers;
  assert.equal(typeof h.formatCarNextDeparture, "function");

  const wedMorning = new Date(2026, 10, 18, 5, 30, 0); // Wed 05:30 local
  const wedEvening = new Date(2026, 10, 18, 20, 10, 0); // Wed 20:10 local

  assert.equal(h.formatCarNextDeparture("06:35", [1, 2, 3, 4, 5, 6, 7], wedMorning, h.getTexts("it")), "Oggi 06:35");
  assert.equal(h.formatCarNextDeparture("06:35", [1, 2, 3, 4, 5, 6, 7], wedEvening, h.getTexts("it")), "Domani 06:35");
  assert.equal(h.formatCarNextDeparture("06:35", [1, 2, 3, 4, 5, 6, 7], wedEvening, h.getTexts("en")), "Tomorrow 06:35");
  assert.equal(h.formatCarNextDeparture("06:35", [1, 2, 3, 4, 5, 6, 7], wedEvening, h.getTexts("nl")), "Morgen 06:35");
  assert.equal(h.formatCarNextDeparture("06:35", [5], wedEvening, h.getTexts("it")), "Ven 06:35");
  assert.equal(h.formatCarNextDeparture("06:35", [3], wedEvening, h.getTexts("it")), "Mer 06:35");
  assert.equal(h.formatCarNextDeparture("06:35", [], wedEvening, h.getTexts("it")), "06:35");
});

test("v1.21.0 IT/EN/NL i18n labels for native departure, battery heat, and all 12 climate extras", () => {
  const h = LepasCard._helpers;
  const requiredKeys = [
    "today",
    "tomorrow",
    "departureActive",
    "noScheduledDeparture",
    "disableOnCar",
    "applyDeparture",
    "carDeparturePlan",
    "depClimateExtras",
    "batteryPreheat",
    "batteryPreheatTime",
    "syncBatteryHeat",
    "batteryHeatHint",
  ];
  const extraKeys = [
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

  for (const lang of ["it", "en", "nl"]) {
    const dict = h.getTexts(lang);
    for (const k of requiredKeys) {
      assert.equal(typeof dict[k], "string", `Missing I18N.${lang}.${k}`);
      assert.ok(dict[k].trim().length > 0, `Empty I18N.${lang}.${k}`);
    }
    assert.ok(dict.climateExtraLabels && typeof dict.climateExtraLabels === "object", `Missing I18N.${lang}.climateExtraLabels`);
    for (const ek of extraKeys) {
      assert.equal(typeof dict.climateExtraLabels[ek], "string", `Missing I18N.${lang}.climateExtraLabels.${ek}`);
      assert.ok(dict.climateExtraLabels[ek].trim().length > 0, `Empty I18N.${lang}.climateExtraLabels.${ek}`);
    }
  }
  assert.notEqual(h.getTexts("it").batteryPreheat, h.getTexts("en").batteryPreheat);
  assert.notEqual(h.getTexts("en").batteryPreheat, h.getTexts("nl").batteryPreheat);
});

test("v1.21.1 Compact departure panel: unified header, compact summary, 2-col sorted seat climate extras", () => {
  const hass = makeFullHass({
    "sensor.lepas_next_departure": makeState("sensor.lepas_next_departure", "Disattivata", {
      allowed_climate_extras: [
        "windshield_defog",
        "passenger_seat_ventilation",
        "driver_seat_heating",
        "rear_window_heating",
        "passenger_seat_heating",
        "driver_seat_ventilation",
      ],
      climate_extras: [],
    }),
    "sensor.lepas_scheduled_departure": makeState("sensor.lepas_scheduled_departure", "06:35", {
      attiva: true,
      riepilogo: "06:35 · lun, mar, mer, gio, ven, sab, dom",
      synced_with_ha: false,
    }),
    "switch.lepas_native_departure_sync": makeState("switch.lepas_native_departure_sync", "off"),
    "button.lepas_apply_departure_schedule": makeState("button.lepas_apply_departure_schedule", "unknown"),
  }, "it");

  const card = createCard({ layout: "compact", default_tab: "charging" }, hass);
  const depSurface = card.shadowRoot.querySelector('[data-bind="depSurface"]');
  assert.ok(depSurface, "Departure surface must expose data-bind='depSurface'");

  // Unified header: depSurface renders top .sec-hdr without ambiguous depSyncBadge
  const topHdr = depSurface.querySelector(".sec-hdr");
  assert.ok(topHdr, "depSurface must render top .sec-hdr");
  assert.equal(topHdr.querySelector('[data-bind="depSyncBadge"]'), null);

  // Compact summary holds both nextDepText and schedDepText inside one .dep-summary container
  const summary = depSurface.querySelector(".dep-summary");
  assert.ok(summary, "Departure summary must group nextDep and schedDep into .dep-summary");
  assert.ok(summary.querySelector('[data-bind="nextDepText"]'));
  assert.ok(summary.querySelector('[data-bind="schedDepText"]'));

  // 2-column grid with canonical seat-first ordering and explicit seat labels
  const grid = depSurface.querySelector(".climate-extras-grid");
  assert.ok(grid, "Climate extras must render inside .climate-extras-grid");
  const keys = Array.from(grid.querySelectorAll("[data-climate-extra]")).map((el) => el.getAttribute("data-climate-extra"));
  assert.deepEqual(keys, [
    "driver_seat_heating",
    "driver_seat_ventilation",
    "passenger_seat_heating",
    "passenger_seat_ventilation",
    "rear_window_heating",
    "windshield_defog",
  ]);
  const driverHeatLbl = grid.querySelector('[data-climate-extra="driver_seat_heating"] span').textContent.toLowerCase();
  assert.ok(driverHeatLbl.includes("sedile"), `Expected 'sedile' in Italian seat label, got: ${driverHeatLbl}`);

  const h = LepasCard._helpers;
  assert.ok(h.getTexts("en").climateExtraLabels.driver_seat_heating.toLowerCase().includes("seat"));
  assert.ok(h.getTexts("nl").climateExtraLabels.driver_seat_heating.toLowerCase().includes("stoel"));
});

test("v1.22.0 CONFIRM_ACTIONS helper contract, dynamic departure label, fail-closed rebuild, and 1-tap non-destructive controls", async () => {
  const h = LepasCard._helpers;
  assert.ok(h.CONFIRM_ACTIONS && typeof h.CONFIRM_ACTIONS === "object", "CONFIRM_ACTIONS must be exported on _helpers");
  assert.equal(Object.isFrozen(h.CONFIRM_ACTIONS), true, "CONFIRM_ACTIONS must be immutable");
  assert.equal(h.isSensitiveAction, undefined, "Obsolete isSensitiveAction must be removed");

  const expectedModalActions = [
    "wake_car",
    "refresh_location",
    "refresh_full",
    "locate_gps",
    "flash_lights",
    "sec_flash_lights",
    "vent_windows",
    "vent_sunroof",
    "remote_start",
    "apply_charging_schedule",
    "apply_departure_schedule",
    "unlock",
    "quick_unlock",
    "trunk_open",
    "quick_trunk_open",
    "windows_open",
    "sunroof_open",
    "alarm_toggle",
  ];
  assert.deepEqual(Object.keys(h.CONFIRM_ACTIONS).sort(), expectedModalActions.slice().sort());

  for (const lang of ["it", "en", "nl"]) {
    const dict = h.getTexts(lang);
    for (const key of ["confirmModalTitle", "confirmModalHint", "confirmCancel", "confirmSend", "lastCommand", "commandSendError"]) {
      assert.equal(typeof dict[key], "string", `Missing I18N.${lang}.${key}`);
      assert.ok(dict[key].trim().length > 0, `Empty I18N.${lang}.${key}`);
    }
  }

  // Dynamic apply_departure_schedule modal label when HA has active departure -> "Applica su auto"
  const hassDepOn = makeFullHass({
    "switch.lepas_quick_departure": makeState("switch.lepas_quick_departure", "on"),
    "button.lepas_apply_departure_schedule": makeState("button.lepas_apply_departure_schedule", "unknown"),
    "sensor.lepas_scheduled_departure": makeState("sensor.lepas_scheduled_departure", "Disattivata", { attiva: false }),
  }, "it");
  const depCard = createCard({ default_tab: "charging" }, hassDepOn);
  const depDlg = depCard.shadowRoot.querySelector('dialog[data-bind="confirmDialog"]');
  depCard.shadowRoot.querySelector('[data-action-id="apply_departure_schedule"]').click();
  assert.equal(depDlg.open, true);
  assert.equal(depCard.shadowRoot.querySelector('[data-bind="confirmDialogAction"]').textContent, "Applica su auto");

  // structKey rebuild while modal is open (e.g. language change or new entity) clears modal fail-closed
  depCard.hass = makeFullHass({
    "switch.lepas_quick_departure": makeState("switch.lepas_quick_departure", "on"),
    "button.lepas_apply_departure_schedule": makeState("button.lepas_apply_departure_schedule", "unknown"),
    "sensor.lepas_scheduled_departure": makeState("sensor.lepas_scheduled_departure", "Disattivata", { attiva: false }),
  }, "en");
  assert.equal(depCard.shadowRoot.querySelector('dialog[data-bind="confirmDialog"]').open, false, "structKey rebuild must fail-closed close modal");
  assert.equal(hassDepOn.calls.length, 0);

  // Remaining non-destructive stateful switches/macros stay 1-tap immediate
  const hassStateful = makeFullHass({
    "switch.lepas_battery_pack_heat": makeState("switch.lepas_battery_pack_heat", "off"),
    "switch.lepas_sync_battery_heat_to_departure": makeState("switch.lepas_sync_battery_heat_to_departure", "off"),
  }, "it");
  const stCard = createCard({}, hassStateful);
  const stDlg = stCard.shadowRoot.querySelector('dialog[data-bind="confirmDialog"]');
  stCard.shadowRoot.querySelector('[data-action-id="cool_everything"]').click();
  stCard.shadowRoot.querySelector('[data-action-id="heat_everything"]').click();
  stCard.shadowRoot.querySelector('[data-action-id="charging_toggle"]').click();
  stCard.shadowRoot.querySelector('[data-action-id="scheduled_charging_toggle"]').click();
  stCard.shadowRoot.querySelector('[data-action-id="battery_pack_heat_toggle"]').click();
  stCard.shadowRoot.querySelector('[data-action-id="sync_battery_heat_toggle"]').click();
  await Promise.resolve();
  assert.equal(stDlg.open, false);
  assert.equal(hassStateful.calls.length, 6);
});

test("v1.22.0 formatCommandOutcome and cmdResultBadge concise outcome in IT/EN/NL without raw debug strings", async () => {
  const h = LepasCard._helpers;
  assert.equal(typeof h.formatCommandOutcome, "function", "formatCommandOutcome must be exported on _helpers");

  const tsIso = new Date(2026, 10, 18, 20, 10, 0).toISOString();
  const tsNewerIso = new Date(2026, 10, 18, 20, 15, 0).toISOString();
  const enTime = new Date(tsIso).toLocaleTimeString("en", { hour: "2-digit", minute: "2-digit" });

  // Absent / dead state with no local feedback -> null
  assert.equal(h.formatCommandOutcome(null, null, "it"), null);
  assert.equal(h.formatCommandOutcome(makeState("sensor.lepas_command_result", "unavailable"), null, "it"), null);
  assert.equal(h.formatCommandOutcome(makeState("sensor.lepas_command_result", "unknown"), null, "en"), null);

  // Success backend states across IT/EN/NL
  const okObj = { state: "Comando eseguito e confermato dall'auto ✅", last_changed: tsIso };
  assert.deepEqual(h.formatCommandOutcome(okObj, null, "it"), { text: "Ultimo comando · 20:10 ✓", ok: true });
  assert.deepEqual(h.formatCommandOutcome(okObj, null, "en"), { text: `Last command · ${enTime} ✓`, ok: true });
  assert.deepEqual(h.formatCommandOutcome(okObj, null, "nl"), { text: "Laatste opdracht · 20:10 ✓", ok: true });

  // Single-climate notice is explicitly non-fatal per backend contract
  const climateNotice = {
    state: "Comando ricevuto dall'auto — unica segnalazione: clima. Da sola non indica un guasto.",
    last_changed: tsIso,
  };
  assert.deepEqual(h.formatCommandOutcome(climateNotice, null, "it"), { text: "Ultimo comando · 20:10 ✓", ok: true });

  // Pending ⏳ counts as non-error
  const inProgress = { state: "Comando in esecuzione sull'auto… ⏳", last_changed: tsIso };
  assert.deepEqual(h.formatCommandOutcome(inProgress, null, "it"), { text: "Ultimo comando · 20:10 ✓", ok: true });

  // Backend errors / partial failures / rejections across IT/EN/NL
  for (const errState of [
    "Eseguito solo in parte ⚠️ — l'auto segnala un problema su: sedili",
    "Comando rifiutato dal backend ❌",
    "Errore di connessione",
    "Command failed",
    "Richiesta scaduta",
    "Veicolo bloccato",
  ]) {
    const resIt = h.formatCommandOutcome({ state: errState, last_changed: tsIso }, null, "it");
    assert.deepEqual(resIt, { text: "Errore invio comando · 20:10 ✕", ok: false }, `Expected failure for '${errState}'`);
  }
  assert.deepEqual(
    h.formatCommandOutcome({ state: "Comando rifiutato ❌", last_changed: tsIso }, null, "en"),
    { text: `Command failed · ${enTime} ✕`, ok: false }
  );
  assert.deepEqual(
    h.formatCommandOutcome({ state: "Comando rifiutato ❌", last_changed: tsIso }, null, "nl"),
    { text: "Opdracht mislukt · 20:10 ✕", ok: false }
  );

  // Local feedback overrides older backend state, and yields once newer backend state arrives
  const localErr = { ok: false, ts: new Date(2026, 10, 18, 20, 12, 0).getTime() };
  assert.deepEqual(
    h.formatCommandOutcome(okObj, localErr, "it"),
    { text: "Errore invio comando · 20:12 ✕", ok: false }
  );
  const newerBackendOk = { state: "Comando eseguito e confermato dall'auto ✅", last_changed: tsNewerIso };
  assert.deepEqual(
    h.formatCommandOutcome(newerBackendOk, localErr, "it"),
    { text: "Ultimo comando · 20:15 ✓", ok: true }
  );

  // DOM cmdResultBadge test: hides raw debug text, toggles .is-emerald/.is-coral, and shows local rejection even when sensor is unavailable
  const hassOk = makeFullHass({
    "sensor.lepas_command_result": Object.assign(
      makeState("sensor.lepas_command_result", "Comando eseguito e confermato dall'auto ✅"),
      { last_changed: tsIso }
    ),
  }, "it");
  const card = createCard({}, hassOk);
  const badge = card.shadowRoot.querySelector('[data-bind="cmdResultBadge"]');
  assert.ok(badge);
  assert.equal(badge.classList.contains("hidden"), false);
  assert.equal(badge.classList.contains("is-emerald"), true);
  assert.equal(badge.classList.contains("is-coral"), false);
  assert.equal(badge.textContent, "Ultimo comando · 20:10 ✓");
  assert.equal(card.shadowRoot.innerHTML.includes("Comando eseguito e confermato dall'auto"), false, "Raw debug text must NEVER render in DOM");

  // When sensor is unavailable/absent and a command fails locally -> badge still renders in coral
  let rejectCmd = true;
  const hassUnavail = makeFullHass({
    "sensor.lepas_command_result": makeState("sensor.lepas_command_result", "unavailable"),
  }, "it");
  hassUnavail.callService = (domain, service, data) => {
    hassUnavail.calls.push({ domain, service, data });
    if (rejectCmd) return Promise.reject(new Error("PIN error"));
    return Promise.resolve();
  };
  const cardUnavail = createCard({}, hassUnavail);
  const badgeUnavail = cardUnavail.shadowRoot.querySelector('[data-bind="cmdResultBadge"]');
  assert.equal(badgeUnavail.classList.contains("hidden"), true, "Badge hidden when sensor unavailable and no local feedback");

  cardUnavail.shadowRoot.querySelector('[data-action-id="flash_lights"]').click();
  cardUnavail.shadowRoot.querySelector('[data-dialog-action="confirm"]').click();
  await Promise.resolve();
  await Promise.resolve();

  assert.equal(badgeUnavail.classList.contains("hidden"), false, "Local failure feedback must show badge even if sensor unavailable");
  assert.equal(badgeUnavail.classList.contains("is-coral"), true);
  assert.equal(badgeUnavail.classList.contains("is-emerald"), false);
  assert.ok(badgeUnavail.textContent.startsWith("Errore invio comando · "));
  assert.ok(badgeUnavail.textContent.endsWith("✕"));

  // Subsequent resolved command flips badge back to emerald
  rejectCmd = false;
  cardUnavail.shadowRoot.querySelector('[data-action-id="climate_quick"]').click();
  await Promise.resolve();
  assert.equal(badgeUnavail.classList.contains("is-emerald"), true);
  assert.equal(badgeUnavail.classList.contains("is-coral"), false);
  assert.ok(badgeUnavail.textContent.startsWith("Ultimo comando · "));
  assert.ok(badgeUnavail.textContent.endsWith("✓"));
});

test("v1.22.1 stopPropagation on internal controls, incremental dayEditor without rebuild, scrollTop preservation, overflow-anchor", async () => {
  const hass = makeFullHass({
    "switch.lepas_sync_charge_to_departure": makeState("switch.lepas_sync_charge_to_departure", "off"),
    "sensor.lepas_next_departure": makeState("sensor.lepas_next_departure", "Disattivata", {
      climate_extras: ["driver_seat_heating"],
      allowed_climate_extras: ["driver_seat_heating", "steering_wheel_heating"],
    }),
  }, "it");

  const outerHost = new MiniElement("div");
  outerHost.scrollHeight = 1400;
  outerHost.clientHeight = 600;
  outerHost.scrollTop = 360;
  const outerShadow = outerHost.attachShadow({ mode: "open" });
  const wrapper = new MiniElement("div");
  outerShadow.appendChild(wrapper);

  const card = createCard({ layout: "compact", default_tab: "overview" }, hass);
  wrapper.appendChild(card);

  let leakedClicks = 0;
  outerHost.addEventListener("click", () => { leakedClicks += 1; });

  // 1. overflow-anchor: none on :host and ha-card
  const styleText = card.shadowRoot.querySelector("style")?.textContent || "";
  assert.match(styleText, /:host\s*\{[^}]*overflow-anchor:\s*none/);
  assert.match(styleText, /ha-card\s*\{[^}]*overflow-anchor:\s*none/);

  // 2. stopPropagation on tabEl, dayChip, chgDayEl, chgPresetEl, chgModeEl, cliExtraEl
  card.shadowRoot.querySelector('[data-tab="charging"]').click();
  card.shadowRoot.querySelector('[data-day-chip="fri"]').click();
  card.shadowRoot.querySelector('[data-charge-day="2"]').click();
  card.shadowRoot.querySelector('[data-charge-preset="weekdays"]').click();
  card.shadowRoot.querySelector('[data-charge-mode="departure"]').click();
  card.shadowRoot.querySelector('[data-climate-extra="steering_wheel_heating"]').click();
  assert.equal(leakedClicks, 0, "Internal card clicks must NOT propagate out of shadow DOM");

  // 3. Incremental dayEditor toggle (same ha-card & editor node reference, zero innerHTML rebuild)
  const haCardBefore = card.shadowRoot.querySelector("ha-card");
  const friEditor = card.shadowRoot.querySelector('[data-day-editor="fri"]');
  const monEditor = card.shadowRoot.querySelector('[data-day-editor="mon"]');
  assert.ok(friEditor && monEditor, "Day editor panels must be pre-mounted");
  assert.equal(friEditor.classList.contains("hidden"), false, "Expanded fri editor must be visible");
  assert.equal(monEditor.classList.contains("hidden"), true, "Collapsed mon editor must stay hidden");

  card.shadowRoot.querySelector('[data-day-chip="mon"]').click();
  assert.equal(card.shadowRoot.querySelector("ha-card"), haCardBefore, "dayChip toggle must NOT rebuild ha-card DOM");
  assert.equal(friEditor.classList.contains("hidden"), true);
  assert.equal(monEditor.classList.contains("hidden"), false);

  card.shadowRoot.querySelector('[data-day-chip="mon"]').click();
  assert.equal(monEditor.classList.contains("hidden"), true);

  // 4. scrollTop preserved across Shadow DOM ancestor even when innerHTML resets scrollTop
  let proto = card.shadowRoot;
  let targetDesc = null;
  while (proto && !targetDesc) {
    targetDesc = Object.getOwnPropertyDescriptor(proto, "innerHTML");
    proto = Object.getPrototypeOf(proto);
  }
  Object.defineProperty(card.shadowRoot, "innerHTML", {
    configurable: true,
    get() { return targetDesc.get.call(this); },
    set(v) {
      targetDesc.set.call(this, v);
      outerHost.scrollTop = 0; // Simulate browser resetting ancestor scroll on DOM wipe
    },
  });
  outerHost.scrollTop = 415;
  card.hass = makeFullHass({}, "en"); // Triggers structKey rebuild
  assert.equal(outerHost.scrollTop, 415, "scrollTop of Shadow DOM scrollable ancestor must be preserved across _render");
  await Promise.resolve();
});
