"""Tests for brand PNG assets and Lovelace hero image."""

import hashlib
from pathlib import Path

import pytest
from PIL import Image

REPO = str(Path(__file__).resolve().parent.parent)

BRAND_SPECS = [
    ("icon.png", 256, 256),
    ("icon@2x.png", 512, 512),
    ("dark_icon.png", 256, 256),
    ("dark_icon@2x.png", 512, 512),
    ("logo.png", 362, 256),
    ("logo@2x.png", 724, 512),
    ("dark_logo.png", 362, 256),
    ("dark_logo@2x.png", 724, 512),
]

LEGACY_OJ_SHA256 = {
    "icon.png": {
        "3e9b1f79a950df683ce667f5169a9e334df5dbe94e225fbe3eb0ebaeaa4e3ff1",
        "70d90eccfd3eb624c948ed14bc31e82861aba78ba2dcff3608aac94793d7cdcd",
        "ec74facf70cfe94cd59098da3a12cfc6f5df6fec17c69c66a5ff7ea65fb60c4b",
    },
    "icon@2x.png": {
        "1633cd6b0f89f14414863d21ac084d864d615c69bca8d095754497803932041f",
        "80af4580822f9f865d0903feea3474000efce68f979fc4cd44b3b380501acf2a",
    },
    "dark_icon.png": {
        "f8cb3c0acc1e0c7eafd7bd53cd517d8b4851087ab538bf3b6f446faed4d3f03a",
        "ec74facf70cfe94cd59098da3a12cfc6f5df6fec17c69c66a5ff7ea65fb60c4b",
    },
    "dark_icon@2x.png": {
        "b0fc811909880c90551e7b69301eaef6732fd80457bf18c5edb84e4fd2f7f709",
        "80af4580822f9f865d0903feea3474000efce68f979fc4cd44b3b380501acf2a",
    },
    "logo.png": {
        "40b67e13e120bc7d6b1ad05e346867ecc4b23d36abcd9686041916dfabecc69d",
        "bdd41abca26eb29700162d191e275001e9c17c6075e97b6740563e96573579aa",
    },
    "logo@2x.png": {
        "47f104e79f4bcc65952902b9b639bf790801961c7c20f29e0331f318d30b9b4a",
        "252e76e51e0cd061acf42505ed0cf5cb96ee191feab9ffebc3e1be17a1d6263e",
    },
    "dark_logo.png": {
        "2025e0b6659ca5d9e1c10c2a7579207dac95d3cec9b020269e07230f3ac31a79",
        "bdd41abca26eb29700162d191e275001e9c17c6075e97b6740563e96573579aa",
    },
    "dark_logo@2x.png": {
        "5e75815058c79f32f7a8896bbca6075e7e965158c77425fe812262d45c6f14c6",
        "252e76e51e0cd061acf42505ed0cf5cb96ee191feab9ffebc3e1be17a1d6263e",
    },
}


@pytest.mark.parametrize("filename,width,height", BRAND_SPECS)
def test_brand_png_dimensions_and_rgba_format(filename, width, height):
    """Brand PNG must have exact Home Assistant dimensions and RGBA mode."""
    asset_path = f"{REPO}/custom_components/lepas/brand/{filename}"
    assert Path(asset_path).is_file(), f"Asset {filename} does not exist"

    with Image.open(asset_path) as img:
        assert img.format == "PNG", f"{filename} format is {img.format}, expected PNG"
        assert img.size == (width, height), (
            f"{filename} size is {img.size}, expected ({width}, {height})"
        )
        assert img.mode == "RGBA", f"{filename} mode is {img.mode}, expected RGBA"


@pytest.mark.parametrize("filename,width,height", BRAND_SPECS)
def test_brand_png_not_legacy_upstream(filename, width, height):
    """Brand assets must not match upstream legacy icons."""
    asset_path = f"{REPO}/custom_components/lepas/brand/{filename}"
    data = Path(asset_path).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    assert digest not in LEGACY_OJ_SHA256[filename], (
        f"{filename} matches legacy upstream SHA-256 ({digest})"
    )


@pytest.mark.parametrize("filename,width,height", BRAND_SPECS)
def test_brand_png_has_transparent_corners_and_gold_brand_accent(
    filename, width, height
):
    """Verify brand PNGs have transparent corners, visible art, and gold accent."""
    asset_path = Path(REPO) / "custom_components" / "lepas" / "brand" / filename
    with Image.open(asset_path) as img:
        rgba = img.convert("RGBA")
        w, h = rgba.size
        corners = [
            rgba.getpixel((0, 0))[3],
            rgba.getpixel((w - 1, 0))[3],
            rgba.getpixel((0, h - 1))[3],
            rgba.getpixel((w - 1, h - 1))[3],
        ]
        assert all(a == 0 for a in corners), (
            f"{filename} must have transparent corners, got alpha {corners}"
        )

        pixels = list(rgba.getdata())
        opaque = [p for p in pixels if p[3] > 200]
        assert len(opaque) > (w * h) * 0.05, f"{filename} appears nearly blank"

        gold_pixels = [p for p in opaque if p[0] >= 180 and p[1] >= 120 and p[2] <= 90]
        assert len(gold_pixels) >= 20, (
            f"{filename} missing warm gold-yellow brand accent"
        )

        neon_cyan_pixels = [
            p
            for p in pixels
            if p[3] > 32 and p[0] <= 40 and p[1] >= 180 and p[2] >= 220
        ]
        assert len(neon_cyan_pixels) == 0, (
            f"{filename} contains forbidden neon-cyan pixels"
        )


def test_hero_asset_exists_and_is_optimized():
    """Lovelace hero asset must exist at 960x480 as PNG in RGB or RGBA mode."""
    hero_path = f"{REPO}/custom_components/lepas/lovelace/lepas-hero.png"
    assert Path(hero_path).is_file(), "lepas-hero.png does not exist"

    with Image.open(hero_path) as img:
        assert img.format == "PNG", f"Hero format is {img.format}, expected PNG"
        assert img.size == (960, 480), f"Hero size is {img.size}, expected (960, 480)"
        assert img.mode in ("RGB", "RGBA"), (
            f"Hero mode is {img.mode}, expected RGB or RGBA"
        )
