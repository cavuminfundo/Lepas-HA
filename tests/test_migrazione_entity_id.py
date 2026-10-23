"""La migrazione degli entity_id: quello che succede a chi e' GIA' installato.

Il codice da solo non basta, ed e' il punto che si dimentica piu' facilmente. Home
Assistant ritrova un'entita' dal suo `unique_id` e riusa l'`entity_id` che ha in registro:
l'entity_id calcolato dal codice vale solo alla PRIMA registrazione. Senza la migrazione,
chi e' gia' installato terrebbe `sensor.lepas_batteria` per sempre e solo le installazioni
nuove avrebbero i nomi inglesi.

Questi test girano sulla funzione di migrazione con un registro preparato a mano, perche'
e' l'unico modo di simulare "un'installazione che esiste da prima".
"""
from __future__ import annotations

import pytest


async def _migra(hass, entry):
    from custom_components.lepas import _async_migrate_entity_ids
    await _async_migrate_entity_ids(hass, entry)


@pytest.fixture
def registro(hass):
    from homeassistant.helpers import entity_registry as er
    return er.async_get(hass)


async def test_una_entita_vecchia_viene_rinominata(hass, config_entry, registro):
    """Il caso normale: c'era `sensor.lepas_batteria`, diventa
    `sensor.lepas_battery`, e l'unique_id NON si tocca - e' l'identita', e
    cambiarla trasformerebbe un rename in una entita' nuova e vuota."""
    voce = registro.async_get_or_create(
        "sensor", "lepas", "VINFINTO_batteria",
        suggested_object_id="lepas_batteria", config_entry=config_entry)
    assert voce.entity_id == "sensor.lepas_batteria"

    await _migra(hass, config_entry)

    dopo = registro.async_get("sensor.lepas_battery")
    assert dopo is not None, "l'entita' non e' stata rinominata"
    assert dopo.unique_id == "VINFINTO_batteria", "l'unique_id non deve muoversi"
    assert registro.async_get("sensor.lepas_batteria") is None


async def test_non_sovrascrive_un_nome_gia_occupato(hass, config_entry, registro):
    """L'unico modo in cui questa migrazione perde dati, e il motivo per cui qui si salta.

    Se il nome di destinazione esiste gia', il recorder scrive "Cannot migrate history ...
    already in use" nel log e lascia lo storico indietro. Nessuna eccezione e nessun test
    rosso: se ne accorgerebbe fra mesi chi apre un grafico. Quindi la vecchia resta dov'e'
    e il fatto viene dichiarato, invece di rinominare e perdere lo storico in silenzio."""
    registro.async_get_or_create(
        "sensor", "lepas", "VINFINTO_batteria",
        suggested_object_id="lepas_batteria", config_entry=config_entry)
    # qualcun altro occupa gia' il posto di arrivo
    registro.async_get_or_create(
        "sensor", "altra_integrazione", "occupante",
        suggested_object_id="lepas_battery")

    await _migra(hass, config_entry)

    assert registro.async_get("sensor.lepas_batteria") is not None, \
        "la vecchia doveva restare dov'era invece di perdere lo storico"
    assert registro.async_get("sensor.lepas_battery").unique_id == "occupante"


async def test_una_entita_gia_inglese_non_viene_toccata(hass, config_entry, registro):
    """La migrazione deve poter girare a ogni avvio senza fare niente: e' quello che
    succede dal secondo riavvio in poi, per sempre."""
    voce = registro.async_get_or_create(
        "sensor", "lepas", "VINFINTO_batteria",
        suggested_object_id="lepas_battery", config_entry=config_entry)
    prima = voce.entity_id

    await _migra(hass, config_entry)
    await _migra(hass, config_entry)

    assert registro.async_get(prima) is not None
    assert registro.async_get(prima).unique_id == "VINFINTO_batteria"


async def test_una_entita_fuori_tabella_resta_com_e(hass, config_entry, registro):
    """Chi non e' in ENGLISH_KEYS non si muove. Vale per un'entita' aggiunta dopo la
    tabella da qualcuno che non sa che la tabella esiste."""
    registro.async_get_or_create(
        "sensor", "lepas", "VINFINTO_sconosciuta",
        suggested_object_id="lepas_cosa_sconosciuta", config_entry=config_entry)

    await _migra(hass, config_entry)

    assert registro.async_get("sensor.lepas_cosa_sconosciuta") is not None

