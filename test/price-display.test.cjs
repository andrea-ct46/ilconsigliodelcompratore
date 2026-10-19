'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { getPriceView } = require('../price-display.js');

// Synthetic fixtures only; these values are never added to the live catalogue.
const now = Date.parse('2026-10-19T10:00:00Z');
const fixture = (overrides = {}) => ({ offerta: {
  amount: 80, currency: 'EUR', source: 'amazon-creators-api',
  checkedAt: '2026-10-19T09:00:00Z', expiresAt: '2026-10-20T09:00:00Z',
  referenceAmount: 100, referenceType: 'list', ...overrides
} });
const price = n => new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(n);

test('formats a verified, current EUR offer and its stated reference', () => {
  assert.deepEqual(getPriceView(fixture(), now), {
    currentPrice: price(80), referencePrice: price(100),
    referenceLabel: 'Prezzo consigliato', discountPercent: 20,
    checkedAtDate: '19/10/2026, 11:00'
  });
  assert.equal(getPriceView(fixture({ referenceType: 'previous' }), now).referenceLabel, 'Prezzo precedente');
  assert.equal(getPriceView(fixture({ amount: 949, referenceAmount: 1129 }), now).discountPercent, 16);
});

test('missing offers and historical prices are not displayed', () => {
  for (const product of [null, undefined, {}, { prezzo: '80,00 €' }, { offerta: [] }]) {
    assert.equal(getPriceView(product, now), null);
  }
});

test('rejects missing or malformed amounts, currencies and sources', () => {
  for (const amount of [undefined, null, 0, -1, 0.001, 3.999, '80', NaN, Infinity]) {
    assert.equal(getPriceView(fixture({ amount }), now), null);
  }
  for (const currency of [undefined, 'USD', 'eur']) {
    assert.equal(getPriceView(fixture({ currency }), now), null);
  }
  for (const source of [undefined, 'firecrawl', 'manual', 'amazon', 'amazon-served']) {
    assert.equal(getPriceView(fixture({ source }), now), null);
  }
  for (const source of ['amazon-creators-api', 'amazon-pa-api']) {
    assert.ok(getPriceView(fixture({ source }), now));
  }
});

test('requires valid timestamps with explicit timezones and a maximum 24-hour lifetime', () => {
  for (const checkedAt of [undefined, '', 'invalid', '2026-10-19T09:00:00', '2026-02-30T09:00:00Z']) {
    assert.equal(getPriceView(fixture({ checkedAt }), now), null);
  }
  for (const expiresAt of [undefined, '', '2026-10-20T09:00:00', '2026-10-20T09:00:01Z', '2026-10-19T08:00:00Z']) {
    assert.equal(getPriceView(fixture({ expiresAt }), now), null);
  }
  assert.ok(getPriceView(fixture({ checkedAt: '2026-10-19T11:00:00+02:00' }), now));
});

test('hides expired, stale and future-dated offers', () => {
  assert.equal(getPriceView(fixture({ expiresAt: '2026-10-19T10:00:00Z' }), now), null);
  assert.equal(getPriceView(fixture({ checkedAt: '2026-10-18T08:59:59Z' }), now), null);
  assert.equal(getPriceView(fixture({ checkedAt: '2026-10-19T10:05:01Z' }), now), null);
  assert.ok(getPriceView(fixture({ checkedAt: '2026-10-19T10:05:00Z' }), now));
  assert.equal(getPriceView(fixture(), NaN), null);
});

test('invalid reference data cannot create a discount or crossed-out price', () => {
  for (const referenceAmount of [undefined, null, 0, 79, 80, '100', NaN, Infinity]) {
    const view = getPriceView(fixture({ referenceAmount }), now);
    assert.equal(view.currentPrice, price(80));
    assert.equal(view.referencePrice, null);
    assert.equal(view.referenceLabel, null);
    assert.equal(view.discountPercent, null);
  }
  assert.equal(getPriceView(fixture({ referenceType: 'sale' }), now).discountPercent, null);
  assert.equal(getPriceView(fixture({ referenceType: undefined }), now).referencePrice, null);
  assert.equal(getPriceView(fixture({ referenceAmount: 80.01 }), now).discountPercent, null);
  assert.equal(getPriceView(fixture({ amount: 0.01 }), now).discountPercent, null);
});
