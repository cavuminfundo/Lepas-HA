"""Contract, WebView compatibility, asset integrity, and JS test suite for LepasCard v2."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
LOVELACE_DIR = REPO / "custom_components" / "lepas" / "lovelace"
CARD_JS = LOVELACE_DIR / "lepas-card.js"
CARD_TEST_MJS = REPO / "tests" / "lepas_card.test.mjs"

HERO_PNGS = (
    "lepas-hero.png",
    "lepas-hero-grey.png",
    "lepas-hero-teal.png",
    "lepas-hero-violet.png",
    "lepas-hero-black.png",
    "lepas-hero-white.png",
)
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _require_node_20() -> str:
    node = shutil.which("node")
    if not node:
        pytest.fail("Node.js >= 20 is required to verify lepas-card.js, but `node` was not found in PATH.")
    res = subprocess.run([node, "-v"], capture_output=True, text=True, check=False)
    if res.returncode != 0:
        pytest.fail(f"Failed to query Node.js version: {res.stderr.strip()}")
    raw = res.stdout.strip().lstrip("v")
    major = int(raw.split(".", 1)[0]) if raw else 0
    if major < 20:
        pytest.fail(f"Node.js >= 20 is required to run Lovelace card tests, found v{raw}.")
    return node


def test_node_syntax_and_no_top_level_esm_in_card_js() -> None:
    """Verify node --check passes (CJS parse) and no top-level import/export exists."""
    node = _require_node_20()
    assert CARD_JS.is_file(), f"Missing card file: {CARD_JS}"

    res = subprocess.run([node, "--check", str(CARD_JS)], capture_output=True, text=True, check=False)
    assert res.returncode == 0, f"node --check failed:\n{res.stderr}\n{res.stdout}"

    source = CARD_JS.read_text(encoding="utf-8")
    no_comments = re.sub(r"/\*[\s\S]*?\*/", "", source)
    no_comments = re.sub(r"^\s*//.*$", "", no_comments, flags=re.MULTILINE)
    assert not re.search(r"^\s*(?:import|export)\b", no_comments, flags=re.MULTILINE), (
        "lepas-card.js must have zero top-level import/export statements so node --check passes."
    )


def test_no_optional_chaining_or_nullish_coalescing_ci_guard() -> None:
    """Enforce exact .github/workflows/card.yml rule and zero occurrences anywhere in lepas-card.js."""
    node = _require_node_20()
    source = CARD_JS.read_text(encoding="utf-8")

    # Exact CI workflow check
    ci_script = """
      const fs = require("fs");
      const f = process.argv[1];
      const code = fs.readFileSync(f, "utf8")
        .replace(/\\/\\*[\\s\\S]*?\\*\\//g, "")
        .replace(/^\\s*\\/\\/.*$/gm, "");
      const m = code.match(/\\?\\.[A-Za-z0-9_$([]|\\?\\?/);
      if (m) { console.error(m[0]); process.exit(1); }
    """
    res = subprocess.run([node, "-e", ci_script, str(CARD_JS)], capture_output=True, text=True, check=False)
    assert res.returncode == 0, (
        f"Optional chaining / nullish coalescing found by card.yml CI guard: {res.stderr.strip()}"
    )

    # Strict check anywhere in file (including comments, strings, regexes)
    assert "?." not in source, "Token '?.' must not appear anywhere in lepas-card.js"
    assert "??" not in source, "Token '??' must not appear anywhere in lepas-card.js"


def test_lepas_card_node_unit_suite() -> None:
    """Execute the full Node 20+ DOM unit & behavior test suite for LepasCard and LepasCardEditor."""
    node = _require_node_20()
    assert CARD_TEST_MJS.is_file(), f"Missing JS test file: {CARD_TEST_MJS}"

    res = subprocess.run(
        [node, "--test", str(CARD_TEST_MJS)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, (
        f"node --test {CARD_TEST_MJS.name} failed (exit {res.returncode}):\n"
        f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    )


def test_hero_png_assets_exist_valid_and_tracked() -> None:
    """Verify all 6 Lepas L8 hero PNGs exist, have valid PNG magic bytes, and are git-tracked."""
    tracked: set[str] | None = None
    if os.path.exists(REPO / ".git"):
        ls_res = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "custom_components/lepas/lovelace/"],
            capture_output=True,
            text=True,
            check=True,
        )
        tracked = {line.strip() for line in ls_res.stdout.splitlines() if line.strip()}

    for filename in HERO_PNGS:
        path = LOVELACE_DIR / filename
        assert path.is_file(), f"Missing hero PNG asset: {path}"
        with path.open("rb") as fh:
            header = fh.read(len(PNG_MAGIC))
        assert header == PNG_MAGIC, f"Invalid PNG magic bytes in {path}: {header!r}"
        if tracked is not None:
            rel = f"custom_components/lepas/lovelace/{filename}"
            assert rel in tracked, f"Hero PNG asset is not tracked by git: {rel}"


def test_card_version_and_matte_titanium_design_tokens() -> None:
    """Verify v1.24.0 cache-busting query, customCards tag, and Matte Titanium OEM tokens."""
    source = CARD_JS.read_text(encoding="utf-8")

    assert re.search(r"\?v=1\.24\.0\b", source), "Expected ?v=1.24.0 cache-busting query in lepas-card.js"
    assert re.search(r"\?v=\d+\.\d+\.\d+\b", source), "Expected semver ?v=X.Y.Z query in lepas-card.js"
    assert 'type: "lepas-card"' in source, "window.customCards must register type: 'lepas-card' (no custom: prefix)"
    assert ":host-context" not in source, "lepas-card.js must NOT use :host-context()"
    assert "container-type: inline-size" in source, "lepas-card.js must declare container-type: inline-size"

    source_upper = source.upper()
    assert "#00D2FF" not in source_upper, "lepas-card.js must NOT contain neon cyan #00D2FF"

    required_tokens = [
        "#111317",
        "#181B20",
        "#21252C",
        "#F3F4F6",
        "#34D399",
        "#60A5FA",
        "#F59E0B",
        "#EF4444",
    ]
    for token in required_tokens:
        assert token.upper() in source_upper, f"Missing Matte Titanium token {token} in lepas-card.js"
