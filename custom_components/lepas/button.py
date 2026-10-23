"""Button: i comandi auto (catalogo core/commands) + sveglia + aggiorna posizione."""
from __future__ import annotations

import logging

from homeassistant.components.button import ENTITY_ID_FORMAT, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COMMANDS_AS_RICH_ENTITY, DOMAIN
from .entity import LepasEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    from .core import commands as CMD

    ents: list[ButtonEntity] = []
    for key, spec in CMD.COMMANDS:
        # i comandi che ora hanno un lock/switch/cover dedicato NON diventano pulsanti
        if key in COMMANDS_AS_RICH_ENTITY:
            continue
        ents.append(LepasCommandButton(coord, key, spec))
    ents.append(LepasActionButton(coord, "Lepas Sveglia auto", "wake", coord.async_wake))
    ents.append(LepasActionButton(coord, "Lepas Aggiorna posizione", "refresh_pos", coord.async_probe))
    # Aggiorna stato completo: forza odometro/batteria/tensione REALI accendendo brevemente il
    # clima (unico modo per accendere l'alta tensione, da cui dipendono i dati freschi).
    ents.append(LepasActionButton(coord, "Lepas Aggiorna stato completo", "refresh_full",
                                    coord.async_refresh_full_status))
    # recupero sessione: azioni "di servizio" → categoria diagnostica (fuori dai controlli)
    ents.append(LepasActionButton(coord, "Lepas Richiedi codice OTP", "otp_request",
                                    coord.async_request_otp, category=EntityCategory.DIAGNOSTIC))
    ents.append(LepasActionButton(coord, "Lepas Conferma OTP", "otp_confirm",
                                    coord.async_confirm_otp, category=EntityCategory.DIAGNOSTIC))
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
        "otp_request": "mdi:email-fast",
        "otp_confirm": "mdi:check-decagram",
    }

    def __init__(self, coord, name: str, suffix: str, action, category=None) -> None:
        super().__init__(coord, name, suffix, entity_id_format=ENTITY_ID_FORMAT)
        self._action = action
        self._attr_icon = self._ICONS.get(suffix, "mdi:gesture-tap-button")
        # Il codice arriva via SMS se l'account è registrato con un numero: mostrare comunque
        # una busta significherebbe promettere una mail che non arriverà mai.
        if suffix == "otp_request" and (getattr(coord, "phone", "") or ""):
            self._attr_icon = "mdi:message-text-fast"
        if category is not None:
            self._attr_entity_category = category

    async def async_press(self) -> None:
        # [LOW] sveglia/sonda/OTP: l'esito va nei sensori diagnostici; logga e non
        # propagare un'eccezione grezza nella UI.
        try:
            await self._action()
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Lepas: azione «%s» non riuscita", self._raw_name)
