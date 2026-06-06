#!/usr/bin/env python3
"""Capture README product screenshots from local dashboard."""
from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "images"
BASE = "http://127.0.0.1:8000"


async def switch_lang(page, lang: str) -> None:
    await page.evaluate(
        """(lang) => {
            if (typeof setLanguage === 'function') setLanguage(lang);
            else if (typeof applyLanguage === 'function') applyLanguage(lang);
            else localStorage.setItem('augur-lang', lang);
        }""",
        lang,
    )
    await page.wait_for_timeout(400)


async def main() -> None:
    shots = [
        ("screenshots/dashboard-hd2d.png", f"{BASE}/", {"width": 1280, "height": 800}),
        ("screenshots/personas-hd2d.png", f"{BASE}/personas", {"width": 1280, "height": 800}),
        ("screenshots/history.png", f"{BASE}/history", {"width": 1440, "height": 900}),
        ("screenshots/report-hd2d.png", f"{BASE}/stocks?ticker=NVDA", {"width": 1280, "height": 800}),
        ("zh/hero-banner.png", f"{BASE}/", {"width": 1400, "height": 520}),
        ("en/hero-banner.png", f"{BASE}/", {"width": 1400, "height": 520}),
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for rel, url, vp in shots:
            page = await browser.new_page(viewport=vp)
            await page.goto(url, wait_until="networkidle", timeout=30000)
            if "hero-banner" in rel:
                lang = "zh" if rel.startswith("zh") else "en"
                await switch_lang(page, lang)
                await page.wait_for_timeout(600)
            dest = OUT / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(dest), type="png")
            print(f"wrote {dest} ({dest.stat().st_size // 1024} KB)")
            await page.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
