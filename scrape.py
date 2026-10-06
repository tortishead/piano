#!/usr/bin/env python3
"""Fetch all used instruments of the German C. Bechstein Centren and dump to JSON.

Since the October 2026 relaunch bechstein.com runs on WordPress and publishes the
listings as the `used_instrument` post type, so this reads the REST API instead of
scraping HTML.
"""
import re, json, html, sys
from urllib.request import urlopen, Request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
API = "https://bechstein.com/wp-json/wp/v2/"

CITY_LABEL = {
    "augsburg": "Augsburg", "berlin": "Berlin", "bielefeld": "Bielefeld",
    "dresden": "Dresden", "duesseldorf": "Düsseldorf", "essen": "Essen",
    "frankfurt-am-main": "Frankfurt am Main", "hamburg": "Hamburg",
    "hannover": "Hannover", "karlsruhe": "Karlsruhe", "kempten": "Kempten",
    "koeln": "Köln", "leipzig": "Leipzig", "muenchen": "München",
    "nuernberg": "Nürnberg", "stuttgart": "Stuttgart", "tuebingen": "Tübingen",
}


def get_json(url):
    """GET a REST endpoint; raise after three failures so a broken run never ships empty data."""
    err = None
    for _ in range(3):
        try:
            with urlopen(Request(url, headers=UA), timeout=60) as r:
                return json.load(r), r.headers
        except Exception as e:
            err = e
    raise RuntimeError("%s: %s" % (url, err))


def get_all(path):
    out, page = [], 1
    while True:
        sep = "&" if "?" in path else "?"
        data, headers = get_json("%s%s%sper_page=100&page=%d" % (API, path, sep, page))
        out += data
        if page >= int(headers.get("X-WP-TotalPages", 1)):
            return out
        page += 1


def strip(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s).replace("\xa0", " ")).strip()


def to_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def parse(post, centres):
    m = post["meta"]
    city = centres.get(str(m.get("used_instrument_center_id")))
    if city not in CITY_LABEL or m.get("used_instrument_availability") != "available":
        return None

    body = strip(m.get("used_instrument_description") or post["content"]["rendered"])

    year = m.get("used_instrument_year", "")
    my = re.search(r"Baujahr[:\s]*(?:ca\.\s*)?(\d{4})", body)
    if not year and my:
        year = my.group(1)

    rent = 0
    mr = re.search(r"(\d{2,4})\s*,?-*\s*(?:€\s*)?/\s*Monat", body)
    if mr:
        rent = int(mr.group(1))

    sublocation = ""
    msl = re.search(r"Standort[:\s]+([A-ZÄÖÜ][\wÄÖÜäöüß .-]{2,30})", body)
    if msl:
        sublocation = msl.group(1).strip(" .")

    finish = ""
    mf = re.search(r"Ausf(?:ü|ue)hrung[:\s]+([^|]{2,60}?)(?:Baujahr|Standort|Preis|$)", body)
    if mf:
        finish = mf.group(1).strip(" .-")

    media = post.get("_embedded", {}).get("wp:featuredmedia") or [{}]

    return {
        "city": CITY_LABEL[city],
        "city_slug": city,
        "sublocation": sublocation,
        "brand": strip(m.get("used_instrument_brand_text")),
        "model": strip(m.get("used_instrument_model")) or strip(post["title"]["rendered"]),
        "category": strip(m.get("used_instrument_type_text")),
        "price": to_int(m.get("used_instrument_price")),
        "uvp": to_int(m.get("used_instrument_original_price")),
        "rent": rent,
        "year": year,
        "finish": finish,
        "width_cm": m.get("used_instrument_width_cm", ""),
        "height_cm": m.get("used_instrument_height_cm", ""),
        "depth_cm": m.get("used_instrument_depth_cm") or m.get("used_instrument_length_cm", ""),
        "description": strip(post["excerpt"]["rendered"]),
        "body": body[:600],
        "image": media[0].get("source_url", ""),
        "url": post["link"],
    }


def main():
    centres = {str(c["id"]): c["slug"] for c in get_all("cbc_center?_fields=id,slug")}
    posts = get_all("used_instrument?_embed=wp:featuredmedia")
    print("fetched", len(posts), file=sys.stderr)
    out = sorted((r for r in (parse(p, centres) for p in posts) if r), key=lambda r: r["url"])
    if not out:
        sys.exit("no listings parsed; the API shape probably changed")
    open("all_urls.txt", "w").write("".join(r["url"] + "\n" for r in out))
    json.dump(out, open("instruments.json", "w"), ensure_ascii=False, indent=1)
    print("wrote", len(out), file=sys.stderr)


if __name__ == "__main__":
    main()
