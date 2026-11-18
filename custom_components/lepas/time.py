"""Time: orari di configurazione locali (non comandi diretti all'auto).

Come i number di configurazione, queste entità NON inviano nulla all'auto da sole:
memorizzano una preferenza usata dagli altri controlli al momento dell'invio.
  - Ricarica programmata · orario di inizio: l'ora (HH:MM) da cui far partire la
    ricarica. Lo switch "Ricarica programmata" compone il piano `chargeAppointControl`
    usando questo valore.

Perché un'entità `time` e non un number 0–23: l'auto accetta l'orario in MINUTI dalla
mezzanotte → con un selettore orario si può scegliere anche i minuti, non solo l'ora intera.
Il riferimento è la mezzanotte LOCALE: misurato il 2026-08-10 rileggendo nell'app il piano
scritto da qui con `startTime = 0` (mostra 00:00; se il filo fosse UTC mostrerebbe 02:00).

È RestoreEntity → al riavvio di HA ripristina l'ultimo orario impostato e lo riscrive
sul coordinator (da cui lo switch lo legge come `charge_start_minutes`).
"""
from __future__ import annotations

from datetime import time

from homeassistant.components.time import ENTITY_ID_FORMAT, TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, entity_allowed
from .entity import LepasEntity
from .naming import ID_PREFIX
from .scheduler import DEPARTURE_DAY_SLUGS

# (nome, suffix, attributo-minuti sul coordinator, default HH, default MM, icona, object_id, translation_key)
TIMES = [
    ("Lepas Ricarica · orario di inizio", "ricarica_orario_inizio",
     "charge_start_minutes", 8, 0, "mdi:clock-start", None, None),
    ("Lepas Quick departure time", "quick_departure_time",
     "quick_departure_minutes", 18, 0, "mdi:clock-fast",
     f"{ID_PREFIX}_quick_departure_time", "quick_departure_time"),
    ("Lepas Battery pack heat time", "battery_pack_heat_time",
     "battery_heat_minutes", 7, 0, "mdi:battery-clock-outline",
     f"{ID_PREFIX}_battery_pack_heat_time", "battery_pack_heat_time"),
]


def _parse_hhmm(raw: str | None) -> time | None:
    if not raw or raw in ("unknown", "unavailable"):
        return None
    try:
        hh, mm, *_ = (int(p) for p in raw.split(":"))
        return time(hour=hh, minute=mm)
    except (ValueError, TypeError):
        return None


def _minutes_to_time(mins: object, fallback: time) -> time:
    if mins is not None:
        try:
            m = int(mins) % 1440
            return time(hour=m // 60, minute=m % 60)
        except (TypeError, ValueError):
            pass
    return fallback


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    ents: list[TimeEntity] = [
        LepasConfigTime(coord, *spec)
        for spec in TIMES
        if entity_allowed(coord, "time", spec[1])
    ]
    ents.extend(
        LepasWeeklyDepartureTime(coord, day, slug)
        for day, slug in DEPARTURE_DAY_SLUGS.items()
        if entity_allowed(coord, "time", f"departure_{slug}_time")
    )
    add(ents)


class LepasConfigTime(LepasEntity, TimeEntity, RestoreEntity):
    """Selettore orario di configurazione locale: pubblica i minuti-da-mezzanotte sul coordinator."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coord,
        name,
        suffix,
        attr,
        def_h,
        def_m,
        icon,
        object_id: str | None = None,
        translation_key: str | None = None,
    ) -> None:
        super().__init__(
            coord,
            name,
            suffix,
            object_id=object_id,
            entity_id_format=ENTITY_ID_FORMAT,
            translation_key=translation_key,
        )
        self._attr = attr
        self._attr_icon = icon
        self._value = time(hour=def_h, minute=def_m)
        setattr(coord, attr, def_h * 60 + def_m)   # default subito disponibile allo switch

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        parsed = _parse_hhmm(last.state if last is not None else None)
        if parsed is not None:
            self._value = parsed
        self._push()
        if parsed is not None and hasattr(self.coordinator, "notify_schedule_changed"):
            self.coordinator.notify_schedule_changed(
                sync_charge=False, sync_native=False, sync_battery=False
            )

    def _push(self) -> None:
        setattr(self.coordinator, self._attr, self._value.hour * 60 + self._value.minute)

    @property
    def native_value(self) -> time:
        return _minutes_to_time(getattr(self.coordinator, self._attr, None), self._value)

    async def async_set_value(self, value: time) -> None:
        # i secondi non servono (l'auto ragiona in minuti) → li azzeriamo
        self._value = value.replace(second=0, microsecond=0)
        self._push()
        if self._attr == "battery_heat_minutes":
            if getattr(self.coordinator, "battery_heat_enabled", False):
                await self.coordinator.async_apply_battery_pack_heat(
                    minutes=self._value.hour * 60 + self._value.minute
                )
            elif hasattr(self.coordinator, "notify_schedule_changed"):
                self.coordinator.notify_schedule_changed(
                    sync_charge=False, sync_native=False, sync_battery=False
                )
        elif hasattr(self.coordinator, "notify_schedule_changed"):
            is_quick = self._attr == "quick_departure_minutes"
            self.coordinator.notify_schedule_changed(
                sync_charge=(
                    is_quick
                    and bool(getattr(self.coordinator, "quick_departure_enabled", False))
                ),
                sync_native=is_quick,
                sync_battery=is_quick,
            )
        self.async_write_ha_state()


class LepasWeeklyDepartureTime(LepasEntity, TimeEntity, RestoreEntity):
    """Target departure time for a single ISO weekday (1..7)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coord, day: int, slug: str) -> None:
        super().__init__(
            coord,
            f"Lepas Departure {slug} time",
            f"departure_{slug}_time",
            object_id=f"{ID_PREFIX}_departure_{slug}_time",
            entity_id_format=ENTITY_ID_FORMAT,
            translation_key=f"departure_{slug}_time",
        )
        self._day = day
        self._fallback = time(hour=7, minute=0)

    def _push_minutes(self, mins: int) -> bool:
        weekly = self.coordinator.departure_weekly
        enabled, _ = weekly.get(self._day, (False, 420))
        weekly[self._day] = (enabled, mins)
        return enabled

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        parsed = _parse_hhmm(last.state if last is not None else None)
        if parsed is not None:
            self._fallback = parsed
            self._push_minutes(parsed.hour * 60 + parsed.minute)
            if hasattr(self.coordinator, "notify_schedule_changed"):
                self.coordinator.notify_schedule_changed(
                    sync_charge=False, sync_native=False, sync_battery=False
                )

    @property
    def native_value(self) -> time:
        entry = self.coordinator.departure_weekly.get(self._day)
        mins = entry[1] if entry else None
        return _minutes_to_time(mins, self._fallback)

    async def async_set_value(self, value: time) -> None:
        cleaned = value.replace(second=0, microsecond=0)
        self._fallback = cleaned
        enabled = self._push_minutes(cleaned.hour * 60 + cleaned.minute)
        if hasattr(self.coordinator, "notify_schedule_changed"):
            self.coordinator.notify_schedule_changed(
                sync_charge=bool(enabled), sync_native=True, sync_battery=True
            )
        self.async_write_ha_state()
