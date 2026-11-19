"""Button: i comandi auto (catalogo core/commands) + sveglia + aggiorna posizione."""
from __future__ import annotations

import logging

from homeassistant.components.button import ENTITY_ID_FORMAT, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COMMANDS_AS_RICH_ENTITY, DOMAIN, entity_allowed
from .entity import LepasEntity
from .naming import ID_PREFIX

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    from .core import commands as CMD

    ents: list[ButtonEntity] = []
    for key, spec in CMD.COMMANDS:
        # i comandi che ora hanno un lock/switch/cover dedicato NON diventano pulsanti
        if key in COMMANDS_AS_RICH_ENTITY:
            continue
        suffix = f"cmd_{key}"
        if entity_allowed(coord, "button", suffix):
            ents.append(LepasCommandButton(coord, key, spec))
    if entity_allowed(coord, "button", "wake"):
        ents.append(LepasActionButton(coord, "Lepas Sveglia auto", "wake", coord.async_wake))
    if entity_allowed(coord, "button", "refresh_pos"):
        ents.append(LepasActionButton(coord, "Lepas Aggiorna posizione", "refresh_pos", coord.async_probe))
    # Aggiorna stato completo: forza odometro/batteria/tensione REALI accendendo brevemente il
    # clima (unico modo per accendere l'alta tensione, da cui dipendono i dati freschi).
    if entity_allowed(coord, "button", "refresh_full"):
        ents.append(LepasActionButton(coord, "Lepas Aggiorna stato completo", "refresh_full",
                                        coord.async_refresh_full_status))
    if entity_allowed(coord, "button", "apply_charging_schedule"):
        ents.append(
            LepasActionButton(
                coord,
                "Lepas Apply charging schedule",
                "apply_charging_schedule",
                coord.async_apply_charging_schedule,
                category=EntityCategory.CONFIG,
                object_id=f"{ID_PREFIX}_apply_charging_schedule",
                translation_key="apply_charging_schedule",
            )
        )
    if entity_allowed(coord, "button", "apply_departure_schedule"):
        ents.append(
            LepasActionButton(
                coord,
                "Lepas Apply departure schedule",
                "apply_departure_schedule",
                coord.async_apply_departure_schedule,
                category=EntityCategory.CONFIG,
                object_id=f"{ID_PREFIX}_apply_departure_schedule",
                translation_key="apply_departure_schedule",
            )
        )
    if entity_allowed(coord, "button", "reset_consumption_from_start"):
        ents.append(
            LepasActionButton(
                coord,
                "Lepas Reset consumption from start",
                "reset_consumption_from_start",
                coord.async_reset_consumption_from_start,
                category=EntityCategory.CONFIG,
                object_id=f"{ID_PREFIX}_reset_consumption_from_start",
                translation_key="reset_consumption_from_start",
            )
        )
    if entity_allowed(coord, "button", "reset_charging_from_start"):
        ents.append(
            LepasActionButton(
                coord,
                "Lepas Reset charging from start",
                "reset_charging_from_start",
                coord.async_reset_charging_from_start,
                category=EntityCategory.CONFIG,
                object_id=f"{ID_PREFIX}_reset_charging_from_start",
                translation_key="reset_charging_from_start",
            )
        )
    add(ents)


class LepasCommandButton(LepasEntity, ButtonEntity):
    """Un pulsante per comando del catalogo. Il tap = consenso esplicito all'attuazione."""

    def __init__(self, coord, key: str, spec: dict) -> None:
        super().__init__(coord, f"Lepas {spec['name']}", f"cmd_{key}",
                         object_id=f"{DOMAIN}_{key}", entity_id_format=ENTITY_ID_FORMAT)
        self._key = key
        if spec.get("icon"):
            self._attr_icon = spec["icon"]

    async def async_press(self) -> None:
        # [LOW] l'esito (anche di errore) è già pubblicato nei sensori diagnostici
        # (cmd_status) dal coordinator: qui logghiamo senza propagare un'eccezione grezza.
        try:
            await self.coordinator.async_send_command(self._key)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Lepas: comando «%s» non riuscito", self._key)


class LepasActionButton(LepasEntity, ButtonEntity):
    """Pulsante per un'azione del coordinator (sveglia/sonda)."""

    _ICONS = {
        "wake": "mdi:car-connected",
        "refresh_pos": "mdi:crosshairs-gps",
        "refresh_full": "mdi:car-info",
        "apply_charging_schedule": "mdi:calendar-sync",
        "apply_departure_schedule": "mdi:calendar-export",
        "reset_consumption_from_start": "mdi:restart",
        "reset_charging_from_start": "mdi:restart",
    }

    def __init__(
        self,
        coord,
        name: str,
        suffix: str,
        action,
        category=None,
        *,
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
        self._action = action
        self._attr_icon = self._ICONS.get(suffix, "mdi:gesture-tap-button")
        if category is not None:
            self._attr_entity_category = category

    async def async_press(self) -> None:
        # [LOW] sveglia/sonda: l'esito va nei sensori diagnostici; logga e non
        # propagare un'eccezione grezza nella UI.
        try:
            await self._action()
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Lepas: azione «%s» non riuscita", self._raw_name)
