# python-scraper

A small utility that reads a Google Sheet, fetches the links in an unnamed
column, and saves one JSON file per row using the member name as the file
name.

## Prerequisites

- Python 3.10+
- A Google service account JSON credentials file with access to the Sheet.
- The Sheet ID and the worksheet name (defaults to `palms`).

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

1. Share the Google Sheet with the service account email from your
   credentials file.
2. Identify the Sheet ID (the long token between `/d/` and `/edit` in the URL).
3. Ensure the worksheet has a `Member Name` column and an unnamed column that
   holds the URLs to scrape.

Run the scraper:

```bash
python scraper.py --sheet-id <SHEET_ID> --creds /path/to/creds.json \
  --worksheet palms --output-dir output
```

Each successful row produces `<output-dir>/<member-name>.json` with the URL,
retrieval timestamp, HTTP metadata, and page body.
