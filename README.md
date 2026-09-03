# Gebrauchte Klaviere & Flügel · C. Bechstein Centren

Every used piano and grand offered by the German C. Bechstein Centren and Partner-Centren,
scraped from their individual listing pages and put on one filterable page.

**Live:** https://USERNAME.github.io/REPO/

## What it does

- Filter by location and brand (both multi-select), by type, by price ceiling, free-text search
- Sort by price, year, location, discount, or "changes first"
- Your selection is remembered (localStorage + the URL, so a filtered view is shareable)
- Marks what changed since your last visit: new offers, price cuts, price rises, and
  listings that disappeared

## Build

```sh
python3 scrape.py            # discover + scrape every German centre -> instruments.json
python3 build_page.py --pages # -> docs/index.html   (photos hotlinked from bechstein.com)
python3 build_page.py         # -> bechstein_gebrauchte.html (photos inlined, needs thumbs.json)
python3 fetch_thumbs.py       # top up thumbs.json for the inlined build (macOS: sips + cwebp)
```

`.github/workflows/refresh.yml` re-runs the scrape weekly and commits when the listings move,
which is what makes the "since your last visit" marks meaningful.

## Scope and attribution

Private, non-commercial index with no connection to C. Bechstein Pianoforte AG. It stores
facts only — brand, model, year, dimensions, price, location — and links every card to the
seller's own page, where the description and contact details live. Photos are not copied:
they load directly from bechstein.com.
