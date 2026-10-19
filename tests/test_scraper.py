import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import httpx

import scraper


NOW = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)
TITLE = '<span id="productTitle">Prodotto di prova</span>'


def main_price(price="29,99 €", extra=""):
    return (TITLE + '<div id="corePriceDisplay_desktop_feature_div">'
            f'<span class="a-price priceToPay"><span class="a-offscreen">{price}</span></span>'
            + extra + '</div>')


class ProductParserTests(unittest.TestCase):
    def test_cents_reference_and_timestamp(self):
        page = main_price("1.249,90 €", '<span class="basisPrice">Prezzo consigliato: '
                          '<span class="a-price a-text-price"><span class="a-offscreen">'
                          '1.399,00 €</span></span></span>')
        self.assertEqual(scraper.parse_product_page(page, NOW), {
            "amount": 1249.90, "currency": "EUR", "source": "amazon-page",
            "checkedAt": "2026-10-19T12:00:00Z", "expiresAt": "2026-10-20T00:00:00Z",
            "referenceAmount": 1399.00, "referenceType": "list",
        })

    def test_split_price_preserves_cents(self):
        page = TITLE + '<div id="corePrice_feature_div"><span class="a-price">' \
            '<span class="a-price-whole">1.249<span>,</span></span>' \
            '<span class="a-price-fraction">95</span><span class="a-price-symbol">€</span>' \
            '</span></div>'
        self.assertEqual(scraper.parse_product_page(page, NOW)["amount"], 1249.95)

    def test_blank_screen_reader_price_falls_back_to_visible_cents(self):
        page = TITLE + '<div id="corePriceDisplay_desktop_feature_div">' \
            '<span class="a-price priceToPay"><span class="a-offscreen"> </span>' \
            '<span aria-hidden="true"><span class="a-price-whole">18<span>,</span></span>' \
            '<span class="a-price-fraction">05</span><span class="a-price-symbol">€</span>' \
            '</span></span><span class="basisPrice">Prezzo consigliato:' \
            '<span class="a-price a-text-price"><span class="a-offscreen">19,00€</span>' \
            '</span></span></div>'
        offer = scraper.parse_product_page(page, NOW)
        self.assertEqual((offer["amount"], offer["referenceAmount"], offer["referenceType"]),
                         (18.05, 19.00, "list"))
        with self.assertRaisesRegex(scraper.ScrapeError, "no_main_eur_price"):
            scraper.parse_product_page(page.replace('class="a-offscreen"> </span>',
                                                    'class="a-offscreen">USD 18.05</span>'), NOW)

    def test_other_prices_never_replace_main_price(self):
        unrelated = '<div id="recommendations"><span class="a-price">' \
            '<span class="a-offscreen">1,00 €</span></span></div>'
        self.assertEqual(scraper.parse_product_page(unrelated + main_price(), NOW)["amount"], 29.99)
        with self.assertRaisesRegex(scraper.ScrapeError, "no_main_eur_price"):
            scraper.parse_product_page(TITLE + unrelated, NOW)

    def test_rejects_subscription_monthly_and_list_only_prices(self):
        for component in (
            '<div id="sns-price"><span class="a-price"><span class="a-offscreen">9,99 €</span></span></div>',
            '<div>Rate da <span class="a-price"><span class="a-offscreen">9,99 €</span></span> al mese</div>',
            '<span class="a-price a-text-price"><span class="a-offscreen">49,99 €</span></span>',
        ):
            with self.subTest(component=component):
                with self.assertRaisesRegex(scraper.ScrapeError, "no_main_eur_price"):
                    scraper.parse_product_page(TITLE + '<div id="corePrice_feature_div">'
                                               + component + '</div>', NOW)

    def test_one_time_price_wins_over_subscription(self):
        page = main_price("19,99 €") + '<div id="oneTimeBuyBox"><span class="a-price">' \
            '<span class="a-offscreen">24,99 €</span></span></div>'
        self.assertEqual(scraper.parse_product_page(page, NOW)["amount"], 24.99)

    def test_currency_bad_or_ambiguous_values(self):
        for price in ("29,99 $", "USD 29.99", "29,99", "0,00 €", "29,99–39,99 €",
                      "3,999 €", "29,99 € al mese", "NaN €"):
            with self.subTest(price=price):
                with self.assertRaisesRegex(scraper.ScrapeError, "no_main_eur_price"):
                    scraper.parse_product_page(main_price(price), NOW)

    def test_missing_product_block_and_unavailable(self):
        fixtures = (
            ('<span class="a-offscreen">29,99 €</span>', "not_a_product_page"),
            ('<title>Robot Check</title><form action="/errors/validateCaptcha"></form>', "captcha_or_block"),
            (main_price() + '<div id="availability">Attualmente non disponibile.</div>', "unavailable"),
            (main_price() + '<div id="twisterAvailability">Currently unavailable.</div>', "unavailable"),
        )
        for page, reason in fixtures:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(scraper.ScrapeError, reason):
                    scraper.parse_product_page(page, NOW)

    def test_reference_requires_explicit_label_and_higher_amount(self):
        for label, amount in (("Risparmia", "49,99"), ("Prezzo precedente", "19,99")):
            page = main_price(extra=f'<span>{label}<span class="a-text-price">'
                              f'<span class="a-offscreen">{amount} €</span></span></span>')
            self.assertNotIn("referenceAmount", scraper.parse_product_page(page, NOW))
        page = main_price(extra='<span>Prezzo precedente: <span class="a-text-price">'
                          '<span class="a-offscreen">39,99 €</span></span></span>')
        self.assertEqual(scraper.parse_product_page(page, NOW)["referenceType"], "previous")

    def test_english_euro_amount(self):
        page = main_price("€40.99", '<span>List Price: <span class="a-text-price">'
                          '<span class="a-offscreen">€49.99</span></span></span>')
        offer = scraper.parse_product_page(page, NOW)
        self.assertEqual((offer["amount"], offer["referenceAmount"]), (40.99, 49.99))


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.products = [
            {"titolo": "Scelta editoriale", "descrizione": "Motivo", "limite": "Limite",
             "link": "https://amzn.to/existing", "categoria": "Computer", "featured": True,
             "immagine": "image.jpg", "prezzo": 99},
            {"titolo": "Altro", "link": "https://amzn.to/other", "offerta": {
                "amount": 49.99, "checkedAt": "2026-10-18T12:00:00Z",
                "expiresAt": "2026-10-19T00:00:00Z", "source": "amazon-page", "currency": "EUR"}},
        ]

    def test_partial_failure_preserves_every_product_and_editorial_field(self):
        original = copy.deepcopy(self.products)
        offer = scraper.parse_product_page(main_price(), NOW)
        with patch("scraper.fetch_offer", side_effect=[offer, httpx.ReadTimeout("failed")]):
            updated, report = scraper.update_catalog(self.products, Mock(), delay=0)
        self.assertEqual(self.products, original)
        self.assertEqual(len(updated), len(original))
        self.assertEqual(updated[1], original[1])
        self.assertEqual({key: value for key, value in updated[0].items() if key != "offerta"}, original[0])
        self.assertEqual(updated[0]["offerta"], offer)
        self.assertEqual((report["attempted"], report["updated"], report["failed"]), (2, 1, 1))
        self.assertEqual(report["errors"], [{"index": 1, "reason": "ReadTimeout"}])

    def test_limit_keeps_remaining_products_and_delays_between_requests(self):
        offer = scraper.parse_product_page(main_price(), NOW)
        sleep = Mock()
        with patch("scraper.fetch_offer", return_value=offer) as fetch:
            updated, report = scraper.update_catalog(self.products, Mock(), limit=1, sleep=sleep)
        fetch.assert_called_once()
        sleep.assert_not_called()
        self.assertEqual(updated[1], self.products[1])
        self.assertEqual(report["skipped"], 1)
        with patch("scraper.fetch_offer", return_value=offer):
            scraper.update_catalog(self.products, Mock(), delay=2, sleep=sleep)
        sleep.assert_called_once_with(2)

    def test_main_all_failed_keeps_original_file_and_reports_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / "dati.json"
            report = Path(directory) / "report.json"
            before = json.dumps(self.products, ensure_ascii=False)
            catalog.write_text(before, encoding="utf-8")
            with patch("scraper.fetch_offer", side_effect=scraper.ScrapeError("captcha_or_block")):
                code = scraper.main(["--catalog", str(catalog), "--report", str(report), "--delay", "0"])
            self.assertEqual(code, 1)
            self.assertEqual(catalog.read_text(encoding="utf-8"), before)
            self.assertEqual(json.loads(report.read_text())["failed"], 2)

    def test_atomic_write_preserves_target_when_serialization_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text("original", encoding="utf-8")
            with self.assertRaises(TypeError):
                scraper.atomic_json(path, {"invalid": object()})
            self.assertEqual(path.read_text(encoding="utf-8"), "original")
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_fetch_rejects_wrong_destination_and_calls_status_check(self):
        response = Mock(url="https://example.com", content=b"unexpected")
        client = Mock()
        client.get.return_value = response
        with self.assertRaisesRegex(scraper.ScrapeError, "unexpected_redirect"):
            scraper.fetch_offer(client, "https://amzn.to/existing")
        response.raise_for_status.assert_called_once()


if __name__ == "__main__":
    unittest.main()
