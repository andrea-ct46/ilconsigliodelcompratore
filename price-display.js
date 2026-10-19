// Sources identify where an offer was collected; timestamps control its visibility.
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.ICCPrices = api;
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';

  const MAX_AGE_MS = 24 * 60 * 60 * 1000;
  const MAX_CLOCK_SKEW_MS = 5 * 60 * 1000;
  const SOURCES = new Set(['amazon-creators-api', 'amazon-pa-api', 'amazon-page']);
  const euros = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' });
  const updatedDate = new Intl.DateTimeFormat('it-IT', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Rome'
  });

  function parseTimestamp(value) {
    if (typeof value !== 'string') return NaN;
    // An explicit timezone is required; local browser time must not affect expiry.
    const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,3})?(Z|[+-](\d{2}):(\d{2}))$/.exec(value);
    if (!match) return NaN;
    const [, year, month, day, hour, minute, second, , offsetHour, offsetMinute] = match;
    const calendar = new Date(0);
    calendar.setUTCFullYear(Number(year), Number(month), 0);
    if (Number(month) < 1 || Number(month) > 12 || Number(day) < 1 ||
        Number(day) > calendar.getUTCDate() || Number(hour) > 23 ||
        Number(minute) > 59 || Number(second) > 59 ||
        Number(offsetHour || 0) > 23 || Number(offsetMinute || 0) > 59) return NaN;
    return Date.parse(value);
  }

  function isAmount(value) {
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0.01) return false;
    const cents = value * 100;
    return Number.isSafeInteger(Math.round(cents)) && Math.abs(cents - Math.round(cents)) < 0.000001;
  }

  // Source tags describe feed provenance.
  // Only a dated, unexpired offer is usable. The legacy `prezzo` field is ignored.
  function getPriceView(product, nowMs) {
    const now = nowMs === undefined ? Date.now() : nowMs;
    if (typeof now !== 'number' || !Number.isFinite(now)) return null;
    const offer = product && product.offerta;
    if (!offer || typeof offer !== 'object' || Array.isArray(offer) ||
        !isAmount(offer.amount) || offer.currency !== 'EUR' || !SOURCES.has(offer.source)) return null;

    const checkedAt = parseTimestamp(offer.checkedAt);
    const expiresAt = parseTimestamp(offer.expiresAt);
    if (!Number.isFinite(checkedAt) || !Number.isFinite(expiresAt) ||
        checkedAt > now + MAX_CLOCK_SKEW_MS || checkedAt < now - MAX_AGE_MS ||
        expiresAt <= checkedAt || expiresAt <= now || expiresAt - checkedAt > MAX_AGE_MS) return null;

    const validReference = isAmount(offer.referenceAmount) && offer.referenceAmount > offer.amount &&
      (offer.referenceType === 'list' || offer.referenceType === 'previous');
    const discount = validReference ? Math.round((1 - offer.amount / offer.referenceAmount) * 100) : 0;
    const hasReference = validReference && discount >= 1 && discount < 100;
    return {
      currentPrice: euros.format(offer.amount),
      referencePrice: hasReference ? euros.format(offer.referenceAmount) : null,
      referenceLabel: hasReference ? (offer.referenceType === 'list' ? 'Prezzo consigliato' : 'Prezzo precedente') : null,
      discountPercent: hasReference ? discount : null,
      checkedAtDate: updatedDate.format(checkedAt)
    };
  }

  return Object.freeze({ getPriceView });
});
