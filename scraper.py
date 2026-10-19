"""Refresh only dated offers in the existing curated catalogue.

Failures keep the previous offer and its original expiry. Editorial fields,
affiliate links and legacy prezzo are never overwritten. No CAPTCHA bypass.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urlparse

import httpx
from lxml import etree, html


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.5",
}


def cls(name):
    return f"contains(concat(' ', normalize-space(@class), ' '), ' {name} ')"


PRICE_SELECTORS = [
    f"//*[@id='{scope}']//*[{cls(class_name)} and not({cls('a-text-price')})]"
    for scope, class_name in (
        ("oneTimeBuyBox", "a-price"), ("newAccordionRow_0", "a-price"),
        ("corePriceDisplay_desktop_feature_div", "priceToPay"),
        ("corePriceDisplay_desktop_feature_div", "apexPriceToPay"),
        ("corePriceDisplay_mobile_feature_div", "priceToPay"),
        ("corePrice_feature_div", "a-price"), ("corePrice_desktop", "a-price"),
        ("corePrice_mobile_feature_div", "a-price"),
        ("corePriceDisplay_desktop_feature_div", "a-price"),
        ("corePriceDisplay_mobile_feature_div", "a-price"),
        ("apex_desktop", "priceToPay"), ("apex_desktop", "apexPriceToPay"),
        ("apex_mobile", "priceToPay"), ("buyNewSection", "a-price"),
    )
] + [f"//*[@id='{identity}']" for identity in (
    "price_inside_buybox", "newBuyBoxPrice", "priceblock_dealprice",
    "priceblock_ourprice", "priceblock_saleprice",
)]
REFERENCE_SCOPES = (
    "corePriceDisplay_desktop_feature_div", "corePriceDisplay_mobile_feature_div",
    "corePrice_feature_div", "corePrice_desktop", "corePrice_mobile_feature_div",
    "apex_desktop", "apex_mobile", "price",
)
EXCLUDED_CONTEXT = re.compile(
    r"sns|subscribe|subscription|installment|monthly|recommend|comparison|"
    r"coupon|usedbuy|usedprice|kindleunlimited|sponsored", re.I
)
PAYMENT_TEXT = re.compile(
    r"/\s*(?:mese|month)|al mese|per month|mensil|rate da|iscriviti|abbonament", re.I
)


class ScrapeError(ValueError):
    """The page cannot provide an unambiguous current product price."""


def text(node):
    return " ".join(node.text_content().split())


def utc_stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_euro(value: str) -> float | None:
    value = " ".join(value.replace("\u00a0", " ").replace("\u202f", " ").split())
    if not re.search(r"€|\bEUR\b", value, re.I) or re.search(r"[$£¥]|USD|GBP", value, re.I):
        return None
    cleaned = re.sub(r"€|\bEUR\b", "", value, flags=re.I).strip()
    # Reject ranges, monthly/coupon text and multiple amounts.
    if not re.fullmatch(r"(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{2})?|\d+\.\d{2}", cleaned):
        return None
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", cleaned):
        cleaned = cleaned.replace(".", "")
    amount = Decimal(cleaned)
    return float(amount) if Decimal("0.01") <= amount <= Decimal("1000000") else None


def node_price(node):
    hidden = node.xpath(f".//*[{cls('a-offscreen')}]")
    if hidden:
        hidden_text = text(hidden[0])
        # Amazon sometimes leaves this accessibility span empty. A populated
        # but invalid/non-EUR value is contradictory and must not be ignored.
        if hidden_text:
            return parse_euro(hidden_text)
    whole = node.xpath(f".//*[{cls('a-price-whole')}]")
    fraction = node.xpath(f".//*[{cls('a-price-fraction')}]")
    symbol = node.xpath(f".//*[{cls('a-price-symbol')}]")
    if whole and fraction and symbol:
        integer = re.sub(r"[\s,.]+$", "", text(whole[0]))
        cents = text(fraction[0])
        if re.fullmatch(r"\d{2}", cents):
            return parse_euro(f"{integer},{cents} {text(symbol[0])}")
        return None
    return parse_euro(text(node))


def excluded_price(node):
    if "a-text-price" in node.get("class", "").split():
        return True
    for ancestor in [node, *node.iterancestors()]:
        if ancestor.tag in ("body", "html"):
            break
        attrs = " ".join(ancestor.get(key, "") for key in ("id", "class", "data-feature-name"))
        if EXCLUDED_CONTEXT.search(attrs):
            return True
    parent = node.getparent()
    nearby = text(parent) if parent is not None else ""
    return len(nearby) < 180 and PAYMENT_TEXT.search(nearby) is not None


def reference_price(tree, current):
    for identity in REFERENCE_SCOPES:
        for scope in tree.xpath("//*[@id=$identity]", identity=identity):
            for candidate in scope.xpath(f".//*[{cls('a-text-price')}]"):
                amount = node_price(candidate)
                if amount is None or amount <= current:
                    continue
                parent = candidate.getparent()
                for _ in range(3):
                    if parent is None:
                        break
                    label = text(parent).lower()
                    if "prezzo precedente" in label or "previous price" in label:
                        return amount, "previous"
                    if "prezzo consigliato" in label or "list price" in label or "rrp:" in label:
                        return amount, "list"
                    if parent is scope:
                        break
                    parent = parent.getparent()
    return None


def parse_product_page(content, checked_at=None):
    try:
        tree = html.fromstring(content)
    except (etree.ParserError, ValueError) as error:
        raise ScrapeError("invalid_html") from error
    titles = tree.xpath("//title")
    if (tree.xpath('//form[contains(@action,"validateCaptcha")] | //*[@id="captchacharacters"]')
            or any("robot check" in text(title).lower() for title in titles)):
        raise ScrapeError("captcha_or_block")
    product_titles = tree.xpath('//*[@id="productTitle"]')
    if not product_titles or not text(product_titles[0]):
        raise ScrapeError("not_a_product_page")
    for availability in tree.xpath('//*[@id="availability" or @id="availabilityInsideBuyBox_feature_div" or @id="twisterAvailability"]'):
        value = text(availability).lower()
        if any(marker in value for marker in (
            "non disponibile", "non sappiamo se o quando", "currently unavailable", "out of stock"
        )):
            raise ScrapeError("unavailable")
    amount = None
    for selector in PRICE_SELECTORS:
        for candidate in tree.xpath(selector):
            if not excluded_price(candidate):
                amount = node_price(candidate)
                if amount is not None:
                    break
        if amount is not None:
            break
    if amount is None:
        raise ScrapeError("no_main_eur_price")
    checked_at = checked_at or datetime.now(timezone.utc)
    if checked_at.tzinfo is None:
        raise ValueError("checked_at must include a timezone")
    offer = {
        "amount": amount, "currency": "EUR", "source": "amazon-page",
        "checkedAt": utc_stamp(checked_at),
        "expiresAt": utc_stamp(checked_at + timedelta(hours=12)),
    }
    reference = reference_price(tree, amount)
    if reference is not None:
        offer["referenceAmount"], offer["referenceType"] = reference
    return offer


def is_amazon_url(url, allow_short=False):
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    return (parsed.scheme == "https" and not parsed.username and not parsed.password
            and (hostname == "amazon.it" or hostname.endswith(".amazon.it")
                 or (allow_short and hostname == "amzn.to")))


def fetch_offer(client, url):
    if not is_amazon_url(url, allow_short=True):
        raise ScrapeError("unsupported_product_url")
    response = client.get(url)
    response.raise_for_status()
    if not is_amazon_url(str(response.url)):
        raise ScrapeError("unexpected_redirect")
    if len(response.content) > 8 * 1024 * 1024:
        raise ScrapeError("page_too_large")
    return parse_product_page(response.content)


def update_catalog(products, client, limit=None, delay=2, sleep=time.sleep):
    updated = deepcopy(products)
    report = {"checkedAt": utc_stamp(datetime.now(timezone.utc)), "products": len(products),
              "attempted": 0, "updated": 0, "failed": 0, "skipped": 0, "errors": []}
    count = len(products) if limit is None else min(limit, len(products))
    for index, product in enumerate(updated[:count]):
        if index and delay:
            sleep(delay)
        report["attempted"] += 1
        try:
            if not isinstance(product, dict):
                raise ScrapeError("invalid_catalog_entry")
            product["offerta"] = fetch_offer(client, product.get("link", ""))
            report["updated"] += 1
            print(f"[{index + 1}/{count}] Prezzo aggiornato", flush=True)
        except (httpx.HTTPError, ScrapeError, TypeError, ValueError) as error:
            report["failed"] += 1
            # Never persist full HTML, headers or request exception URLs.
            reason = str(error) if isinstance(error, ScrapeError) else type(error).__name__
            report["errors"].append({"index": index, "reason": reason})
            print(f"[{index + 1}/{count}] Non aggiornato: {reason}", flush=True)
    report["skipped"] = len(products) - report["attempted"]
    report["finishedAt"] = utc_stamp(datetime.now(timezone.utc))
    return updated, report


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", delete=False) as handle:
            temporary = handle.name
            json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path(__file__).with_name("dati.json"))
    parser.add_argument("--report", type=Path, default=Path(__file__).with_name("scraper-report.json"))
    parser.add_argument("--limit", type=int, default=None, help="Aggiorna solo i primi N prodotti")
    parser.add_argument("--delay", type=float, default=2, help="Pausa tra richieste, in secondi")
    args = parser.parse_args(argv)
    if (args.limit is not None and args.limit < 1) or args.delay < 0:
        parser.error("--limit deve essere positivo e --delay non negativo")
    with args.catalog.open(encoding="utf-8") as handle:
        products = json.load(handle)
    if not isinstance(products, list):
        parser.error("Il catalogo deve essere una lista JSON")
    with httpx.Client(headers=HEADERS, timeout=httpx.Timeout(25, connect=10),
                      follow_redirects=True, max_redirects=10) as client:
        updated, report = update_catalog(products, client, args.limit, args.delay)
    atomic_json(args.report, report)
    if report["updated"]:
        atomic_json(args.catalog, updated)
    print(json.dumps({key: value for key, value in report.items() if key != "errors"}, ensure_ascii=False))
    return 1 if products and report["updated"] == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
