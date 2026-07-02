"""Misc API routes: health, robots.txt, manifest, sitemap, cache management."""

import time as _time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response

from dashboard.deps import _APP_START_TIME, get_registry

router = APIRouter()

_STATIC_DIR = Path(__file__).parent.parent / "static"


@router.get("/health", summary="健康检查")
async def health():
    return {"status": "ok", "agents": len(get_registry().get_all())}


@router.get("/robots.txt", response_class=PlainTextResponse, summary="Robots.txt", include_in_schema=False)
async def robots_txt():
    return "User-agent: *\nAllow: /\nSitemap: https://augur.example.com/sitemap.xml\n"


@router.get("/manifest.json", include_in_schema=False)
async def pwa_manifest():
    manifest_path = _STATIC_DIR / "manifest.json"
    if manifest_path.exists():
        return FileResponse(manifest_path, media_type="application/manifest+json")
    raise HTTPException(status_code=404)


@router.get("/sitemap.xml", summary="Sitemap XML", include_in_schema=False)
async def sitemap_xml():
    base = "https://augur.example.com"
    urls = ["/", "/stocks", "/personas", "/signals", "/scanner", "/backtest", "/settings", "/watchlist"]
    xml_entries = "\n".join(
        f"  <url><loc>{base}{u}</loc><changefreq>daily</changefreq></url>"
        for u in urls
    )
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{xml_entries}
</urlset>'''
    return Response(content=xml, media_type="application/xml")


@router.get("/api/health", summary="扩展健康检查")
async def api_health_extended():
    """Extended health check - returns datasource reachability, cache info, uptime."""
    datasources = []
    try:
        from augur.datasources import available_sources
        sources = available_sources()
        for src in sources:
            datasources.append({"name": src, "reachable": True})
    except Exception as e:
        datasources.append({"name": "unknown", "reachable": False, "error": str(e)})

    try:
        from augur.data import cache_stats
        cache = cache_stats()
    except Exception:
        try:
            from augur.data import cache_info
            cache = cache_info()
        except Exception:
            cache = {}

    uptime = _time.time() - _APP_START_TIME

    return {
        "status": "ok",
        "agents": len(get_registry().get_all()),
        "datasources": datasources,
        "cache": cache,
        "uptime_seconds": round(uptime, 1),
        "version": "7.8.3",
    }


@router.post("/api/cache/clear", summary="清除数据缓存")
async def api_cache_clear():
    """Clear the data cache to force fresh fetches."""
    from augur.data import clear_cache
    clear_cache()
    return {"status": "ok", "message": "Cache cleared"}


@router.get("/api/cache/info", summary="缓存状态信息")
async def api_cache_info():
    """Return cache size and TTL info."""
    from augur.data import cache_info
    info = cache_info()
    return {"status": "ok", "cache": info}
