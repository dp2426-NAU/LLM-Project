"""
Fetches SEC final rule documents from the EDGAR full-text search API.
Saves them as .txt files in data/sample_regulations/.

Usage:
    python scripts/fetch_sec_rules.py --query "record retention" --limit 3
"""

import argparse
import logging
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index?q={query}&dateRange=custom&startdt=2020-01-01&forms=34-Act"
EDGAR_BASE = "https://www.sec.gov"


def search_edgar(query: str, limit: int = 3) -> list[dict]:
    url = f"https://efts.sec.gov/LATEST/search-index?q={query}&forms=rule&dateRange=custom&startdt=2020-01-01"
    logger.info("Searching EDGAR: %s", url)
    try:
        with httpx.Client(timeout=20, headers={"User-Agent": "RegDelta/1.0 research@example.com"}) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error("EDGAR search failed: %s", e)
        return []

    hits = data.get("hits", {}).get("hits", [])
    return hits[:limit]


def fetch_document(filing_url: str) -> str | None:
    try:
        with httpx.Client(timeout=30, headers={"User-Agent": "RegDelta/1.0 research@example.com"}) as client:
            resp = client.get(filing_url)
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", filing_url, e)
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch SEC final rules from EDGAR")
    parser.add_argument("--query", default="record retention electronic communications", help="Search query")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--output-dir", default="data/sample_regulations")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    hits = search_edgar(args.query, args.limit)
    if not hits:
        logger.warning("No results found. Using placeholder data.")
        return

    for i, hit in enumerate(hits):
        source = hit.get("_source", {})
        file_date = source.get("file_date", "unknown")
        entity = source.get("entity_name", f"sec_rule_{i}")
        safe_name = entity.lower().replace(" ", "_").replace("/", "_")[:50]

        file_url = source.get("file_url", "")
        if not file_url:
            continue

        text = fetch_document(f"{EDGAR_BASE}{file_url}")
        if text:
            out_path = output_dir / f"{safe_name}_{file_date}.txt"
            out_path.write_text(text[:50000], encoding="utf-8")
            logger.info("Saved: %s (%d chars)", out_path.name, len(text))


if __name__ == "__main__":
    main()
