"""Scrape linked pages from a Google Sheet and save them as JSON.

The script expects a worksheet (default: "palms") that contains a column
labeled "Member Name" and an unnamed column that stores the URL to scrape
for each row. It will fetch each URL, capture the response metadata and
body, and persist one JSON file per row using the member name as the file
name.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from typing import List, Sequence

import gspread
import requests


DEFAULT_WORKSHEET_NAME = "palms"
USER_AGENT = "python-scraper/1.0"


def sanitize_filename(name: str) -> str:
    """Convert a string into a safe filename segment."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9\-_. ]+", "", name)
    name = re.sub(r"[\s_]+", "-", name)
    return name.strip("-.")


def resolve_column(headers: Sequence[str], expected: str) -> int:
    """Find a header index by case-insensitive match."""
    for idx, header in enumerate(headers):
        if header.strip().lower() == expected.lower():
            return idx
    raise ValueError(f"Worksheet is missing required column: {expected!r}")


def resolve_unnamed_column(headers: Sequence[str]) -> int:
    """Return the index of the first unnamed header cell."""
    for idx, header in enumerate(headers):
        if not header.strip():
            return idx
    raise ValueError("Worksheet is missing the unnamed link column.")


def fetch_page(url: str) -> dict:
    """Retrieve a URL and return response metadata and body."""
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    return {
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type", ""),
        "body": response.text,
    }


def fetch_sheet_rows(sheet_id: str, worksheet_name: str, creds_path: str) -> List[List[str]]:
    """Load all rows from the worksheet."""
    client = gspread.service_account(filename=creds_path)
    worksheet = client.open_by_key(sheet_id).worksheet(worksheet_name)
    return worksheet.get_all_values()


def scrape_links(sheet_id: str, worksheet_name: str, creds_path: str, output_dir: str) -> None:
    """Scrape each link in the sheet and write individual JSON files."""
    rows = fetch_sheet_rows(sheet_id, worksheet_name, creds_path)
    if not rows:
        raise ValueError("Worksheet is empty.")

    headers, data_rows = rows[0], rows[1:]
    member_idx = resolve_column(headers, "member name")
    link_idx = resolve_unnamed_column(headers)

    os.makedirs(output_dir, exist_ok=True)

    for row_number, row in enumerate(data_rows, start=2):
        member_name = row[member_idx].strip() if len(row) > member_idx else ""
        url = row[link_idx].strip() if len(row) > link_idx else ""

        if not member_name or not url:
            continue

        print(f"[row {row_number}] Fetching {url} for {member_name}")

        try:
            response = fetch_page(url)
        except requests.RequestException as exc:  # pylint: disable=broad-except
            print(f"  ! Failed to fetch {url}: {exc}")
            response = {
                "status_code": None,
                "content_type": None,
                "body": None,
                "error": str(exc),
            }

        filename = sanitize_filename(member_name) or f"entry-{row_number}"
        payload = {
            "member_name": member_name,
            "url": url,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "response": response,
        }

        path = os.path.join(output_dir, f"{filename}.json")
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2)

        print(f"  → Saved {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet-id", required=True, help="Google Sheet ID")
    parser.add_argument(
        "--worksheet",
        default=DEFAULT_WORKSHEET_NAME,
        help=f"Worksheet name (default: {DEFAULT_WORKSHEET_NAME})",
    )
    parser.add_argument(
        "--creds",
        default=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"),
        help="Path to the Google service account JSON file",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory where JSON files will be written",
    )

    args = parser.parse_args()
    if not args.creds:
        parser.error("--creds is required (or set GOOGLE_SERVICE_ACCOUNT_FILE)")
    return args


def main() -> None:
    args = parse_args()
    scrape_links(
        sheet_id=args.sheet_id,
        worksheet_name=args.worksheet,
        creds_path=args.creds,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
