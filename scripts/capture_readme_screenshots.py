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
    await page.wait_for_timeout(600)


async def wait_stocks_analysis(page) -> None:
    await page.wait_for_function(
        """() => {
            const r = document.getElementById('results');
            const s = document.getElementById('exec-score');
            return r && r.classList.contains('show') && s && s.textContent && s.textContent !== '--';
        }""",
        timeout=120000,
    )
    await page.wait_for_timeout(1000)


async def capture_svg_png(browser, svg_rel: str, dest_rel: str, width: int, height: int) -> None:
    svg_path = (ROOT / svg_rel).resolve()
    page = await browser.new_page(viewport={"width": width, "height": height})
    await page.goto(svg_path.as_uri(), wait_until="load")
    dest = OUT / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(dest), type="png")
    print(f"wrote {dest} ({dest.stat().st_size // 1024} KB)")
    await page.close()


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()

        # Stocks first — homepage loads many APIs and can trip rate limits.
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await page.goto(f"{BASE}/stocks?ticker=NVDA", wait_until="domcontentloaded", timeout=60000)
        await wait_stocks_analysis(page)

        dest = OUT / "screenshots/report-hd2d.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(dest), type="png")
        print(f"wrote {dest} ({dest.stat().st_size // 1024} KB)")

        dest = OUT / "screenshots/04-bullish-critical.png"
        await page.locator(".debate").first.screenshot(path=str(dest), type="png")
        print(f"wrote {dest} ({dest.stat().st_size // 1024} KB)")
        await page.close()

        # README cover art (召唤猫头鹰 HD-2D hero) — hand-maintained; do not auto-capture.
        # Paths: docs/images/zh/hero-banner.png, docs/images/en/hero-banner.png
        simple_shots = [
            ("screenshots/dashboard-hd2d.png", f"{BASE}/", {"width": 1280, "height": 800}, None),
            ("screenshots/personas-hd2d.png", f"{BASE}/personas", {"width": 1280, "height": 800}, None),
            ("screenshots/history.png", f"{BASE}/history", {"width": 1440, "height": 900}, None),
        ]

        for rel, url, vp, lang in simple_shots:
            page = await browser.new_page(viewport=vp)
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(2000)
            if lang:
                await switch_lang(page, lang)
            dest = OUT / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(dest), type="png")
            print(f"wrote {dest} ({dest.stat().st_size // 1024} KB)")
            await page.close()

        await capture_svg_png(
            browser,
            "docs/images/skills-deploy-en.svg",
            "screenshots/05-available-everywhere.png",
            1000,
            380,
        )

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
