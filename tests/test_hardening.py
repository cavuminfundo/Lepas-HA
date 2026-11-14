"""Test mirati per i fix di security hardening (log MQTT, permessi atomici token, XSS card)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEPAS_DIR = ROOT / "custom_components" / "lepas"


def test_mqtt_on_connect_log_masks_tuserid() -> None:
    """Il log INFO di on_connect non deve esporre il topic contenente self.tuserid."""
    src = (LEPAS_DIR / "coordinator.py").read_text(encoding="utf-8")
    assert 'f"app/{self.channel_id}/***/account/msgCenter/msg"' in src
    assert '"[auto] MQTT on_connect rc=%s → %s (sub %s)",\n                         rc, "connesso" if ok else "RIFIUTATO", topic' not in src


def test_token_tmp_opened_with_0600_mode() -> None:
    """I file .tmp dei token devono essere creati direttamente con permessi 0o600 via os.open."""
    for rel in ("core/wake.py", "core/prova_token.py"):
        src = (LEPAS_DIR / rel).read_text(encoding="utf-8")
        assert "os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)" in src, (
            f"{rel} deve aprire il file temporaneo con os.open(..., 0o600)"
        )
        assert 'open(tmp, "w"' not in src, (
            f"{rel} non deve usare open(tmp, 'w') prima di os.chmod"
        )


def test_lepas_card_error_catch_escapes_html() -> None:
    """Il blocco catch di lepas-card.js deve sanitizzare l'errore con this._h(...)."""
    src = (LEPAS_DIR / "lovelace" / "lepas-card.js").read_text(encoding="utf-8")
    assert "Lepas card error: ${this._h(e && e.message ? e.message : e)}" in src
