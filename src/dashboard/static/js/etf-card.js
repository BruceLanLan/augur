/* ETF overview card for the stock page (v14).
 * Input: the `etf_overview` object from /api/analyze (see dashboard/etf_overview.py);
 * null/undefined for equities -> renders nothing.
 * Units follow augur/etf.py: expense_ratio and top10_weight are 0-1 decimals,
 * premium_pct and spread_pct are already percent, aum_usd_bn is billions of USD.
 */
(function (root) {
    'use strict';

    function esc(s) {
        return String(s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    function tr(key, fallback) {
        return (root && typeof root.t === 'function') ? root.t(key, fallback) : fallback;
    }

    function isNum(v) { return typeof v === 'number' && isFinite(v); }

    function fmtAum(v) { return isNum(v) ? '$' + v.toFixed(v >= 100 ? 0 : v >= 10 ? 1 : 2) + 'B' : '--'; }
    function fmtPct(v, digits) { return isNum(v) ? v.toFixed(digits) + '%' : '--'; }
    function fmtDecPct(v, digits) { return isNum(v) ? (v * 100).toFixed(digits) + '%' : '--'; }
    function fmtSigned(v) { return isNum(v) ? (v > 0 ? '+' : '') + v.toFixed(2) + '%' : '--'; }

    function cell(key, label, value, note) {
        // '--' = the data source did not report it; muted so it reads as
        // "unknown" rather than as a value.
        var na = value === '--';
        return '<div class="etf-card__cell">' +
            '<span class="etf-card__label" data-i18n="' + key + '">' + esc(tr(key, label)) + '</span>' +
            (na
                ? '<span class="etf-card__value etf-card__value--na" title="' + esc(tr('etf-na-tip', 'Not reported by the data source')) + '">--</span>'
                : '<span class="etf-card__value">' + esc(value) + '</span>') +
            (note ? '<span class="etf-card__note">' + note + '</span>' : '') +
            '</div>';
    }

    function buildEtfCardHtml(ov) {
        if (!ov || typeof ov !== 'object') return '';
        var navNote = '';
        if (isNum(ov.nav)) {
            navNote = '<span data-i18n="etf-nav">' + esc(tr('etf-nav', 'NAV')) + '</span> ' +
                esc(ov.nav.toFixed(ov.nav < 10 ? 4 : 2) + (ov.currency ? ' ' + ov.currency : ''));
            if (ov.nav_date) navNote += ' · ' + esc(ov.nav_date);
            if (ov.nav_date_inferred) {
                navNote += ' <span class="etf-card__inferred" data-i18n="etf-nav-inferred">' +
                    esc(tr('etf-nav-inferred', '(date inferred)')) + '</span>';
            }
        } else if (ov.nav_date) {
            navNote = '<span data-i18n="etf-nav-as-of">' + esc(tr('etf-nav-as-of', 'NAV as of')) + '</span> ' + esc(ov.nav_date);
            if (ov.nav_date_inferred) {
                navNote += ' <span class="etf-card__inferred" data-i18n="etf-nav-inferred">' +
                    esc(tr('etf-nav-inferred', '(date inferred)')) + '</span>';
            }
        }
        return '<div class="card etf-card" role="region" aria-label="ETF overview">' +
            '<div class="etf-card__head">' +
            '<div class="sec-title" data-i18n="etf-card-title">' + esc(tr('etf-card-title', 'ETF Overview')) + '</div>' +
            (ov.source ? '<div class="etf-card__source"><span data-i18n="etf-source">' + esc(tr('etf-source', 'Source')) + '</span>: ' + esc(ov.source) + '</div>' : '') +
            '</div>' +
            '<div class="etf-card__grid">' +
            cell('etf-aum', 'AUM', fmtAum(ov.aum_usd_bn)) +
            cell('etf-expense', 'Expense ratio', fmtDecPct(ov.expense_ratio, 2)) +
            cell('etf-premium', 'Premium / NAV', fmtSigned(ov.premium_pct), navNote) +
            cell('etf-top10', 'Top-10 weight', fmtDecPct(ov.top10_weight, 1)) +
            cell('etf-category', 'Category', ov.category || '--') +
            cell('etf-spread', 'Bid/ask spread', fmtPct(ov.spread_pct, 3)) +
            '</div>' +
            '</div>';
    }

    function renderEtfCard(container, ov) {
        if (!container) return;
        var html = buildEtfCardHtml(ov);
        container.innerHTML = html;
        container.style.display = html ? '' : 'none';
    }

    root.buildEtfCardHtml = buildEtfCardHtml;
    root.renderEtfCard = renderEtfCard;
})(typeof window !== 'undefined' ? window : this);
