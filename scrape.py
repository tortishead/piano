#!/usr/bin/env python3
"""Scrape all used instruments from C. Bechstein Centren and dump to JSON."""
import re, json, html, sys, os
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen, Request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

CITY_LABEL = {
    "augsburg": "Augsburg", "berlin": "Berlin", "bielefeld": "Bielefeld",
    "dresden": "Dresden", "duesseldorf": "Düsseldorf", "essen": "Essen",
    "frankfurt-am-main": "Frankfurt am Main", "hamburg": "Hamburg",
    "hannover": "Hannover", "karlsruhe": "Karlsruhe", "kempten": "Kempten",
    "koeln": "Köln", "leipzig": "Leipzig", "muenchen": "München",
    "nuernberg": "Nürnberg", "stuttgart": "Stuttgart", "tuebingen": "Tübingen",
}


def get(url):
    for _ in range(3):
        try:
            with urlopen(Request(url, headers=UA), timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            pass
    return ""


def strip(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).replace("\xa0", " ").strip()


def prop(h, name):
    m = re.search(r'itemprop="%s"[^>]*>(.*?)</' % name, h, re.S)
    return strip(m.group(1)) if m else ""


def parse(url):
    h = get(url)
    if not h:
        return None
    city = url.split("/centren/")[1].split("/")[0]

    def money(txt):
        # matches 7.900 / 7.900,-- / 17.990,- / € 5.690,00
        m = re.search(r"\b(\d{1,3}(?:\.\d{3})+|\d{3,})\b", txt)
        return int(m.group(1).replace(".", "")) if m else 0

    price_block = re.search(r'<div class="price-info.*?</div>', h, re.S)
    price = uvp = rent = 0
    if price_block:
        pb = price_block.group(0)
        old = re.search(r'class="old-price">(.*?)<', pb)
        uvp = money(strip(old.group(1))) if old else 0
        txt = strip(re.sub(r'<span class="old-price">.*?</span>', "", pb, flags=re.S))
        mr = re.search(r"Miete[:\s]*([\d.]+)", txt)
        if mr:
            rent = int(mr.group(1).rstrip(".").replace(".", ""))
            txt = txt[: mr.start()]
        price = money(txt)

    brand = ""
    mb = re.search(r'class="segment-head product-used">\s*<h5[^>]*>(.*?)</h5>', h, re.S)
    if mb:
        brand = strip(mb.group(1))

    desc = prop(h, "description")
    body = ""
    mb2 = re.search(r'id="product-description".*?>(.*?)</section>', h, re.S)
    if mb2:
        body = strip(mb2.group(1))

    blob = desc + " || " + body
    year = ""
    my = re.search(r"Baujahr[:\s]*(?:ca\.\s*)?(\d{4})", blob)
    if my:
        year = my.group(1)

    sublocation = ""
    msl = re.search(r"Standort[:\s]+([A-ZÄÖÜ][\wÄÖÜäöüß .-]{2,30})", body)
    if msl:
        sublocation = msl.group(1).strip(" .")

    finish = ""
    mf = re.search(r"Ausf(?:ü|ue)hrung[:\s]+([^|]{2,60}?)(?:Baujahr|Standort|Preis|$)", body)
    if mf:
        finish = mf.group(1).strip(" .-")

    def num(v):
        m = re.search(r"[\d,.]+", v)
        return m.group(0) if m else ""

    img = prop(h, "image")
    if img and not img.startswith("http"):
        img = "https://www.bechstein.com" + img

    return {
        "city": CITY_LABEL.get(city, city.title()),
        "city_slug": city,
        "sublocation": sublocation,
        "brand": brand,
        "model": prop(h, "model") or prop(h, "name"),
        "category": prop(h, "category"),
        "price": price,
        "uvp": uvp,
        "rent": rent,
        "year": year,
        "finish": finish,
        # source markup swaps the height/weight units; numbers themselves are correct
        "width_cm": num(prop(h, "width")),
        "height_cm": num(prop(h, "height")),
        "depth_cm": num(prop(h, "depth")),
        "weight_kg": num(prop(h, "weight")),
        "description": desc,
        "body": body[:600],
        "image": img,
        "url": url,
    }


SITEMAP = "https://www.bechstein.com/sitemap.xml"
LISTINGS = ["gebrauchte-instrumente", "gebrauchte-instrumente/gebrauchte-klaviere",
            "gebrauchte-instrumente/gebrauchte-fluegel"]


def discover():
    """Collect every used-instrument page of the German centren.

    The per-centre sitemaps cover most of them; Nürnberg publishes none, so the
    listing pages are crawled too and the two sets merged.
    """
    index = get(SITEMAP)
    found = set()
    maps = [u.replace("&amp;", "&") for u in re.findall(r"<loc>(.*?)</loc>", index)
            if "centerUsedProducts" in u]
    with ThreadPoolExecutor(max_workers=8) as ex:
        for body in ex.map(get, maps):
            found.update(re.findall(r"<loc>(.*?)</loc>", body))

    pages = ["https://www.bechstein.com/centren/%s/%s/" % (c, p)
             for c in CITY_LABEL for p in LISTINGS]
    with ThreadPoolExecutor(max_workers=8) as ex:
        for body in ex.map(get, pages):
            found.update("https://www.bechstein.com" + m for m in
                         re.findall(r"/centren/[a-z-]+/gebrauchtes-instrument/[a-z0-9-]+/", body))

    german = sorted(u for u in found
                    if u.split("/centren/")[1].split("/")[0] in CITY_LABEL)
    open("all_urls.txt", "w").write("\n".join(german) + "\n")
    return german


def main():
    if len(sys.argv) > 1:
        urls = sorted(set(l.strip() for l in open(sys.argv[1]) if l.strip()))
    else:
        urls = discover()
    print("fetching", len(urls), file=sys.stderr)
    out = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        for i, r in enumerate(ex.map(parse, urls)):
            if r:
                out.append(r)
            if i % 25 == 0:
                print(i, file=sys.stderr)
    json.dump(out, open("instruments.json", "w"), ensure_ascii=False, indent=1)
    print("wrote", len(out), file=sys.stderr)


if __name__ == "__main__":
    main()
