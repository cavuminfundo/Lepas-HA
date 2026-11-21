"""Number: parametri di configurazione locali (non comandi diretti all'auto).

Questi cursori NON inviano nulla all'auto da soli: memorizzano le preferenze usate
dagli altri controlli al momento dell'invio.
  - Durata clima (min): durata `times` del comando airControl della climate entity.
  - Ricarica programmata · durata (ore): compone il piano `chargeAppointControl`
    insieme all'orario di inizio (entità `time`, vedi time.py) quando si accende lo
    switch "Ricarica programmata".

Sono RestoreNumber → al riavvio di HA ripristinano l'ultimo valore impostato e lo
riscrivono sul coordinator (da cui climate/switch lo leggono).
"""
from __future__ import annotations

import itertools
import math

from homeassistant.components.number import (
    ENTITY_ID_FORMAT,
    NumberMode,
    RestoreNumber,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, entity_allowed
from .core.commands import durata_ammessa
from .entity import LepasEntity

# (nome, suffix, attributo sul coordinator, min, max, step, default, unità, icona)
NUMBERS = [
    ("Lepas Durata clima", "clima_durata", "clima_duration",
     5, 30, 5, 15, UnitOfTime.MINUTES, "mdi:timer-cog"),
    ("Lepas Durata preriscaldamento partenza", "partenza_preclima_durata",
     "departure_preclimate_duration",
     5, 30, 5, 15, UnitOfTime.MINUTES, "mdi:car-clock"),
    # L'ORA di inizio è ora un'entità `time` (HH:MM, vedi time.py): più precisa del
    # vecchio cursore 0–23 perché l'auto accetta i minuti. Qui resta solo la DURATA.
    ("Lepas Ricarica · durata", "ricarica_durata_ore", "charge_duration_hours",
     1, 12, 1, 6, UnitOfTime.HOURS, "mdi:battery-clock"),
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    add([LepasConfigNumber(coord, *spec) for spec in NUMBERS if entity_allowed(coord, "number", spec[1])])


class LepasConfigNumber(LepasEntity, RestoreNumber):
    """Cursore di configurazione locale: scrive il proprio valore sul coordinator."""

    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coord, name, suffix, attr, vmin, vmax, step, default, unit, icon) -> None:
        super().__init__(coord, name, suffix, entity_id_format=ENTITY_ID_FORMAT)
        self._attr = attr
        self._allowed_durations: list[int] = []
        if attr in ("clima_duration", "departure_preclimate_duration") and hasattr(coord, "air_durations"):
            raw_allowed = coord.air_durations() or ()
            allowed = sorted(
                {
                    int(d)
                    for d in raw_allowed
                    if isinstance(d, int) and not isinstance(d, bool) and d > 0
                }
            )
            if allowed:
                self._allowed_durations = allowed
                vmin = min(allowed)
                vmax = max(allowed)
                if len(allowed) >= 2:
                    diffs = [b - a for a, b in itertools.pairwise(allowed) if b > a]
                    step = math.gcd(*diffs) if diffs else step
                else:
                    step = min(step, allowed[0])
        self._attr_native_min_value = vmin
        self._attr_native_max_value = vmax
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._value = self._snap_value(default)
        self._push()

    def _snap_value(self, value: float) -> float:
        fallback = (
            self._value
            if hasattr(self, "_value")
            else (float(self._allowed_durations[0]) if self._allowed_durations else 0.0)
        )
        try:
            num = float(value)
        except (TypeError, ValueError):
            return fallback
        if not math.isfinite(num):
            return fallback
        if not self._allowed_durations:
            return num
        corrected = durata_ammessa(num, self._allowed_durations)
        return float(corrected) if corrected is not None else float(int(num))

    @property
    def extra_state_attributes(self) -> dict[str, list[int]] | None:
        if self._allowed_durations:
            return {"allowed_durations": list(self._allowed_durations)}
        return None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        raw_val = last.native_value if last is not None else None
        if raw_val is None:
            last_state = await self.async_get_last_state()
            if last_state is not None:
                raw_val = last_state.state
        restored = False
        if raw_val is not None:
            try:
                parsed = float(raw_val)
            except (TypeError, ValueError, OverflowError):
                parsed = math.nan
            if math.isfinite(parsed):
                self._value = self._snap_value(parsed)
                restored = True
        self._push()
        if (
            restored
            and self._attr in ("charge_duration_hours", "departure_preclimate_duration")
            and hasattr(self.coordinator, "notify_schedule_changed")
        ):
            self.coordinator.notify_schedule_changed()

    def _push(self) -> None:
        # mantieni il valore come int quando è intero (orari/giorni), così i body comando
        # non finiscono con "8.0" dove l'app usa interi.
        v = int(self._value) if float(self._value).is_integer() else self._value
        setattr(self.coordinator, self._attr, v)

    @property
    def native_value(self) -> float:
        val = getattr(self.coordinator, self._attr, None)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        self._value = self._snap_value(value)
        self._push()
        if (
            self._attr in ("charge_duration_hours", "departure_preclimate_duration")
            and hasattr(self.coordinator, "notify_schedule_changed")
        ):
            self.coordinator.notify_schedule_changed(
                sync_charge=(self._attr == "charge_duration_hours")
            )
        self.async_write_ha_state()
