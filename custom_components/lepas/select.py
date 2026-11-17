"""Select entities for charging days and departure pre-climate mode."""
from __future__ import annotations

from homeassistant.components.select import ENTITY_ID_FORMAT, SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, entity_allowed
from .entity import LepasEntity
from .naming import ID_PREFIX
from .scheduler import CHARGE_DAYS_PRESETS, parse_days_input, preset_for_days

_CLIMATE_MODES = ["at_home", "anywhere", "off"]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback
) -> None:
    """Set up Lepas select entities."""
    coord = hass.data[DOMAIN][entry.entry_id]
    ents: list[SelectEntity] = []
    if entity_allowed(coord, "select", "charge_days"):
        ents.append(LepasChargeDaysSelect(coord))
    if entity_allowed(coord, "select", "departure_climate_mode"):
        ents.append(LepasDepartureClimateModeSelect(coord))
    add(ents)


class LepasChargeDaysSelect(LepasEntity, SelectEntity, RestoreEntity):
    """Select active weekdays preset (or custom) for scheduled charging."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:calendar-week"
    _attr_options = [*CHARGE_DAYS_PRESETS.keys(), "custom"]

    def __init__(self, coord) -> None:
        super().__init__(
            coord,
            "Lepas Charge days",
            "charge_days",
            object_id=f"{ID_PREFIX}_charge_days",
            entity_id_format=ENTITY_ID_FORMAT,
            translation_key="charge_days",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is None or last.state in (None, "", "unknown", "unavailable"):
            return
        if last.state in CHARGE_DAYS_PRESETS:
            self.coordinator.charge_days = list(CHARGE_DAYS_PRESETS[last.state])
        elif last.state == "custom":
            raw_days = last.attributes.get("days")
            if raw_days is not None:
                try:
                    self.coordinator.charge_days = parse_days_input(raw_days)
                except ValueError:
                    return
        else:
            return
        if hasattr(self.coordinator, "notify_schedule_changed"):
            self.coordinator.notify_schedule_changed()

    @property
    def current_option(self) -> str:
        return preset_for_days(getattr(self.coordinator, "charge_days", None))

    @property
    def extra_state_attributes(self) -> dict[str, list[int]]:
        return {"days": list(getattr(self.coordinator, "charge_days", [1, 2, 3, 4, 5, 6, 7]))}

    async def async_select_option(self, option: str) -> None:
        if option in CHARGE_DAYS_PRESETS:
            self.coordinator.charge_days = list(CHARGE_DAYS_PRESETS[option])
        elif option != "custom":
            raise ValueError(f"Unsupported charge days option: {option!r}")
        if hasattr(self.coordinator, "notify_schedule_changed"):
            self.coordinator.notify_schedule_changed()
        self.async_write_ha_state()


class LepasDepartureClimateModeSelect(LepasEntity, SelectEntity, RestoreEntity):
    """Select automatic pre-climate safety mode for scheduled departures."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:thermostat-auto"
    _attr_options = list(_CLIMATE_MODES)

    def __init__(self, coord) -> None:
        super().__init__(
            coord,
            "Lepas Departure climate mode",
            "departure_climate_mode",
            object_id=f"{ID_PREFIX}_departure_climate_mode",
            entity_id_format=ENTITY_ID_FORMAT,
            translation_key="departure_climate_mode",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in _CLIMATE_MODES:
            self.coordinator.departure_climate_mode = last.state
            if hasattr(self.coordinator, "notify_schedule_changed"):
                self.coordinator.notify_schedule_changed()

    @property
    def current_option(self) -> str:
        mode = getattr(self.coordinator, "departure_climate_mode", "at_home")
        return mode if mode in _CLIMATE_MODES else "at_home"

    async def async_select_option(self, option: str) -> None:
        if option not in _CLIMATE_MODES:
            raise ValueError(f"Unsupported departure climate mode: {option!r}")
        self.coordinator.departure_climate_mode = option
        if hasattr(self.coordinator, "notify_schedule_changed"):
            self.coordinator.notify_schedule_changed()
        self.async_write_ha_state()
