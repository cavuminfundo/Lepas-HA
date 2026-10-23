"""Test di validazione statica e compatibilità WebView per LepasCard Lovelace UI.

Verifica:
1) Compatibilità Android WebView (zero ?. o ??, protezione accessi annidati).
2) Dark Tech Automotive theme, CSS Container Queries, accessibilità tastiera,
   4 metriche veicolo e indicatore live di connessione.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CARD_PATH = Path(f"{REPO}/custom_components/lepas/lovelace/lepas-card.js")


def _read_card_source() -> str:
    """Legge il sorgente JavaScript di LepasCard."""
    assert CARD_PATH.exists(), f"File non trovato: {CARD_PATH}"
    return CARD_PATH.read_text(encoding="utf-8")


def _strip_js_comments(source: str) -> str:
    """Rimuove commenti a blocco (/*...*/) e a riga singola (//...).

    Preserva le stringhe ed evita falsi positivi da protocolli (http://, https://).
    """
    no_block = re.sub(r"/\*[\s\S]*?\*/", "", source)
    lines = []
    for line in no_block.splitlines():
        # Rimuove commenti a riga singola // che non siano preceduti da ':' o '\'
        m = re.search(r"(?<![:\\])\s*//.*$", line)
        if m:
            lines.append(line[: m.start()])
        else:
            lines.append(line)
    return "\n".join(lines)


def test_lepas_card_js_webview_compat() -> None:
    """Verifica la compatibilità di lepas-card.js con vecchie Android System WebView.

    - lepas-card.js deve esistere.
    - Non deve contenere optional chaining (`?.`) fuori dai commenti.
    - Non deve contenere nullish coalescing (`??`) fuori dai commenti.
    - Deve proteggere l'accesso a vehicle_image con guard complete:
      `r.s && r.s.attributes && r.s.attributes.vehicle_image`.
    """
    assert CARD_PATH.exists(), f"File non trovato: {CARD_PATH}"
    source = _read_card_source()
    code_without_comments = _strip_js_comments(source)

    # Verifica assenza di optional chaining (?.)
    assert "?." not in code_without_comments, (
        "Trovato operatore optional chaining (?.) nel codice attivo di lepas-card.js. "
        "Le vecchie versioni di Android WebView falliscono il parsing di (?.)."
    )

    # Verifica assenza di nullish coalescing (??)
    assert "??" not in code_without_comments, (
        "Trovato operatore nullish coalescing (??) nel codice attivo di lepas-card.js. "
        "Le vecchie versioni di Android WebView falliscono il parsing di (??)."
    )

    # Verifica protezione accesso a vehicle_image
    assert "r.s && r.s.attributes && r.s.attributes.vehicle_image" in source, (
        "L'accesso ad attributi di vehicle_image deve essere protetto con "
        "`r.s && r.s.attributes && r.s.attributes.vehicle_image` per evitare TypeError."
    )


def test_lepas_card_dark_tech_theme_and_4_metrics() -> None:
    """Verifica il tema Dark Tech Automotive, Container Queries, a11y e le 4 metriche."""
    source = _read_card_source()

    # 1. Fallback hero con cache busting
    assert "/lepas_card/lepas-hero.png?v=1.14.0" in source, (
        "Manca il fallback hero dark-studio `/lepas_card/lepas-hero.png?v=1.14.0`"
    )

    # 2. Palette Dark Tech Automotive (WCAG AA/AAA)
    dark_tech_palette = [
        "#0F141C",  # Obsidian dark background
        "#151D28",  # Tile dark surface
        "#00D2FF",  # Electric cyan accent
        "#0A84FF",  # Automotive blue accent
        "#F1F5F9",  # Primary high-contrast text
        "#94A3B8",  # Secondary muted text
    ]
    source_upper = source.upper()
    for color in dark_tech_palette:
        assert color.upper() in source_upper, (
            f"Colore {color} della palette Dark Tech Automotive mancante in lepas-card.js"
        )

    # 3. CSS Container Queries
    assert "container-type: inline-size" in source, (
        "Manca la direttiva CSS Container Query `container-type: inline-size`"
    )
    assert "@container" in source, (
        "Mancano le regole responsive `@container` per la card"
    )

    # 4. Accessibilità da tastiera
    assert 'role="button"' in source, (
        'Manca l\'attributo accessibile `role="button"` sugli elementi interattivi'
    )
    assert 'tabindex="0"' in source, (
        'Manca `tabindex="0"` per rendere navigabili da tastiera gli elementi interattivi'
    )
    assert ":focus-visible" in source, (
        "Manca la pseudo-classe CSS `:focus-visible` per l'indicatore di focus da tastiera"
    )

    # 5. Le 4 metriche core
    metrics = ["electric_range", "fuel_range", "charging_power", "odometer"]
    for m in metrics:
        assert m in source, f"Metrica veicolo '{m}' mancante in lepas-card.js"

    # 6. Indicatore live legato a connection
    assert "connection" in source, (
        "Manca la gestione dell'entità `connection` per l'indicatore live di connessione"
    )
