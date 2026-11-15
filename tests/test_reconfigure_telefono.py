"""«Configura»: menu reconfigure e rimozione dei vecchi passi email/telefono.

Con il passaggio al flusso password-only e l'eliminazione dell'OTP, la riconfigurazione
dell'account non ha più motivo di commutare tra email ed SMS. Il menu di riconfigurazione
espone esclusivamente l'aggiornamento del PIN per i comandi remoti.
"""
from __future__ import annotations

import pytest
from homeassistant import config_entries, data_entry_flow

import fixtures as FX
from custom_components.lepas.config_flow import LepasConfigFlow
from custom_components.lepas.const import CONF_PIN, DOMAIN


async def _menu(hass, entry):
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
    )


async def test_il_menu_reconfigure_offre_solo_pin(hass, integrazione_avviata):
    """Il menu di riconfigurazione offre solo l'aggiornamento del PIN."""
    r = await _menu(hass, integrazione_avviata)
    assert r["type"] is data_entry_flow.FlowResultType.MENU
    assert r["step_id"] == "reconfigure"
    assert r["menu_options"] == ["reconfigure_pin"]


def test_vecchi_step_reconfigure_rimossi():
    """I vecchi step reconfigure_email e reconfigure_phone non devono più esistere."""
    assert not hasattr(LepasConfigFlow, "async_step_reconfigure_email")
    assert not hasattr(LepasConfigFlow, "async_step_reconfigure_phone")


async def test_reconfigure_pin_aggiorna_entry(hass, integrazione_avviata):
    """Scegliere reconfigure_pin permette di aggiornare il PIN e azzera il lockout."""
    r = await _menu(hass, integrazione_avviata)
    step = await hass.config_entries.flow.async_configure(
        r["flow_id"], {"next_step_id": "reconfigure_pin"}
    )
    assert step["type"] is data_entry_flow.FlowResultType.FORM
    assert step["step_id"] == "reconfigure_pin"

    res = await hass.config_entries.flow.async_configure(
        step["flow_id"], {CONF_PIN: "9876"}
    )
    await hass.async_block_till_done()

    assert res["type"] is data_entry_flow.FlowResultType.ABORT
    assert res["reason"] == "reconfigure_successful"
    assert integrazione_avviata.data[CONF_PIN] == "9876"


async def test_reconfigure_pin_vuoto_rifiutato(hass, integrazione_avviata):
    """Un PIN vuoto viene rifiutato con pin_required."""
    r = await _menu(hass, integrazione_avviata)
    step = await hass.config_entries.flow.async_configure(
        r["flow_id"], {"next_step_id": "reconfigure_pin"}
    )
    res = await hass.config_entries.flow.async_configure(
        step["flow_id"], {CONF_PIN: "   "}
    )
    assert res["type"] is data_entry_flow.FlowResultType.FORM
    assert res["errors"]["base"] == "pin_required"


async def test_reconfigure_senza_entry_abortisce(hass):
    """Se l'entry da riconfigurare non esiste, il flow abortisce."""
    r = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": "inesistente"},
    )
    assert r["type"] is data_entry_flow.FlowResultType.ABORT
    assert r["reason"] == "reconfigure_no_entry"
