#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEC EDGAR 13F Holdings Fetcher for Augur

Fetches real 13F filing data from SEC EDGAR for known investor CIK numbers.
Updates personas/evolution/ with accurate holdings data.

Known CIK mappings:
  Berkshire Hathaway  : 0001067983
  ARK Investment Mgmt : 0001697748
  HHLR Advisors       : 0001762304  (张磊/Hillhouse; formerly Hillhouse Capital Advisors)
  Himalaya Capital    : 0001709323  (李录/Li Lu; Seattle WA)
  H&H International  : 0001810182  (段永平/Duan Yongping)
"""

import json
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import urllib.request
import urllib.parse

BASE_URL = "https://data.sec.gov"
ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"
EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index"

# Known investor CIK numbers (verified from SEC EDGAR)
INVESTOR_CIKS = {
    "buffett": {
        "name": "Warren Buffett / Berkshire Hathaway",
        "cik": "0001067983",
        "entity": "BERKSHIRE HATHAWAY INC",
    },
    "cathie_wood": {
        "name": "Cathie Wood / ARK Investment Management",
        "cik": "0001697748",
        "entity": "ARK INVESTMENT MANAGEMENT LLC",
    },
    "zhang_lei": {
        "name": "张磊 / HHLR Advisors (Hillhouse)",
        "cik": "0001762304",
        "entity": "HHLR ADVISORS, LTD.",
    },
    "li_lu": {
        "name": "李录 / Himalaya Capital",
        "cik": "0001709323",
        "entity": "HIMALAYA CAPITAL MANAGEMENT, LLC",
    },
    "duan_yongping": {
        "name": "段永平 / H&H International Investment",
        "cik": "0001810182",
        "entity": "H&H INTERNATIONAL INVESTMENT LLC",
    },
}

HEADERS = {
    "User-Agent": "Augur Investment Research lanzhihao1986@gmail.com",
    "Accept": "application/json",
}


def _get(url: str) -> Optional[dict]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [WARN] GET {url}: {e}", file=sys.stderr)
        return None


def get_latest_13f_accession(cik: str) -> Optional[str]:
    """Return the accession number of the most recent 13F-HR filing."""
    cik_clean = cik.lstrip("0")
    url = f"{BASE_URL}/cgi-bin/browse-edgar?action=getcompany&CIK={cik_clean}&type=13F-HR&dateb=&owner=include&count=5&search_text=&output=atom"
    # Use submissions endpoint instead — more reliable JSON
    submissions_url = f"{BASE_URL}/submissions/CIK{cik.zfill(10)}.json"
    data = _get(submissions_url)
    if not data:
        return None

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accessions = filings.get("accessionNumber", [])
    dates = filings.get("filingDate", [])

    for i, form in enumerate(forms):
        if form in ("13F-HR", "13F-HR/A"):
            return accessions[i], dates[i]
    return None, None


def get_holdings_from_13f(cik: str, accession: str) -> List[Dict]:
    """Parse holdings from a 13F filing accession number."""
    import re as _re
    accession_fmt = accession.replace("-", "")
    cik_num = cik.lstrip("0")
    base = f"{ARCHIVES_URL}/{cik_num}/{accession_fmt}"

    # Fetch the htm index to discover the infotable XML filename
    index_htm = f"{base}/{accession}-index.htm"
    idx_req = urllib.request.Request(index_htm, headers={"User-Agent": HEADERS["User-Agent"]})
    infotable_url = None
    try:
        with urllib.request.urlopen(idx_req, timeout=15) as resp:
            html = resp.read().decode(errors="replace")
        # Find any .xml that is NOT primary_doc and NOT xslForm (rendered version)
        for href in _re.findall(r'href="(/Archives/edgar/data/[^"]+\.xml)"', html, _re.IGNORECASE):
            fname = href.split("/")[-1].lower()
            if fname != "primary_doc.xml" and "xslform" not in href.lower():
                infotable_url = f"https://www.sec.gov{href}"
                break
    except Exception as e:
        print(f"  [WARN] Could not fetch filing index: {e}", file=sys.stderr)

    if not infotable_url:
        return []

    req = urllib.request.Request(infotable_url, headers={
        "User-Agent": HEADERS["User-Agent"],
        "Accept": "application/xml",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_content = resp.read().decode(errors="replace")
    except Exception as e:
        print(f"  [WARN] Could not fetch infotable: {e}", file=sys.stderr)
        return []

    return _parse_infotable_xml(xml_content)


def _parse_infotable_xml(xml: str) -> List[Dict]:
    """Simple XML parser for 13F infotable without external dependencies."""
    holdings = []
    import re

    entries = re.split(r"<infoTable>|<ns1:infoTable>", xml, flags=re.IGNORECASE)[1:]
    for entry in entries:
        def extract(tag: str) -> str:
            for t in [tag, f"ns1:{tag}"]:
                m = re.search(rf"<{t}[^>]*>(.*?)</{t}>", entry, re.DOTALL | re.IGNORECASE)
                if m:
                    return m.group(1).strip()
            return ""

        name = extract("nameOfIssuer")
        value_str = extract("value")
        shares_str = extract("sshPrnamt")
        cusip = extract("cusip")
        put_call = extract("putCall")

        if not name:
            continue

        try:
            value = int(value_str.replace(",", "")) * 1000 if value_str else 0
        except ValueError:
            value = 0
        try:
            shares = int(shares_str.replace(",", "")) if shares_str else 0
        except ValueError:
            shares = 0

        holdings.append({
            "name": name,
            "cusip": cusip,
            "value_usd": value,
            "shares": shares,
            "put_call": put_call,
        })

    return sorted(holdings, key=lambda x: x["value_usd"], reverse=True)


def fetch_investor_holdings(investor_id: str, top_n: int = 20) -> Optional[Dict]:
    """Fetch and return the top holdings for a known investor."""
    info = INVESTOR_CIKS.get(investor_id)
    if not info:
        print(f"Unknown investor: {investor_id}")
        return None

    cik = info["cik"]
    print(f"Fetching 13F for {info['name']} (CIK: {cik})...")

    result = get_latest_13f_accession(cik)
    if not result or result[0] is None:
        print(f"  No 13F filing found for {info['name']}")
        return None

    accession, filing_date = result
    print(f"  Latest 13F: {accession} ({filing_date})")

    time.sleep(0.5)  # SEC rate limit courtesy
    holdings = get_holdings_from_13f(cik, accession)

    if not holdings:
        print(f"  Could not parse holdings from {accession}")
        return None

    total_value = sum(h["value_usd"] for h in holdings)
    top = holdings[:top_n]

    for h in top:
        h["pct_portfolio"] = (h["value_usd"] / total_value * 100) if total_value else 0

    return {
        "investor_id": investor_id,
        "investor_name": info["name"],
        "cik": cik,
        "filing_date": filing_date,
        "accession": accession,
        "total_13f_value_usd": total_value,
        "top_holdings": top,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }


def save_holdings(data: Dict, output_dir: Path) -> Path:
    """Save holdings JSON to personas/evolution/."""
    output_dir.mkdir(parents=True, exist_ok=True)
    investor_id = data["investor_id"]
    out_path = output_dir / f"{investor_id}_13f.json"
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"  Saved: {out_path}")
    return out_path


def print_holdings_table(data: Dict, max_rows: int = 15) -> None:
    """Print a summary table to stdout."""
    print(f"\n{'='*60}")
    print(f"  {data['investor_name']}")
    print(f"  Filing: {data['filing_date']}  |  Total 13F: ${data['total_13f_value_usd']/1e9:.2f}B")
    print(f"{'='*60}")
    print(f"  {'Issuer':<35} {'Value($M)':>10} {'%Port':>7}")
    print(f"  {'-'*35} {'-'*10} {'-'*7}")
    for h in data["top_holdings"][:max_rows]:
        name = h["name"][:34]
        val = h["value_usd"] / 1e6
        pct = h["pct_portfolio"]
        print(f"  {name:<35} {val:>10,.1f} {pct:>7.2f}%")
    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fetch 13F holdings from SEC EDGAR")
    parser.add_argument("investors", nargs="*", default=list(INVESTOR_CIKS.keys()),
                        help="Investor IDs to fetch (default: all)")
    parser.add_argument("--output-dir", default="personas/evolution",
                        help="Output directory for JSON files")
    parser.add_argument("--top-n", type=int, default=20,
                        help="Number of top holdings to save")
    parser.add_argument("--no-save", action="store_true",
                        help="Print only, don't save files")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    success, failed = [], []

    for investor_id in args.investors:
        if investor_id not in INVESTOR_CIKS:
            print(f"[SKIP] Unknown investor: {investor_id}. Known: {list(INVESTOR_CIKS.keys())}")
            continue
        data = fetch_investor_holdings(investor_id, top_n=args.top_n)
        if data:
            print_holdings_table(data)
            if not args.no_save:
                save_holdings(data, output_dir)
            success.append(investor_id)
        else:
            failed.append(investor_id)
        time.sleep(1)  # SEC rate limit: 10 req/s

    print(f"\nDone. Success: {success}  |  Failed: {failed}")


if __name__ == "__main__":
    main()
