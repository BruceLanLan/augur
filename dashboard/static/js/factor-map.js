// Shared factor→category mapping for persona metadata.factors breakdowns.
// Used by both compare.html (multi-agent radar) and stocks.html (single-agent
// detail modal) so the ~70-key mapping table has exactly one copy.
(function (global) {
    var FACTOR_MAP = {
        valuation: [
            'valuation', 'valuation_acceptability', 'relative_valuation',
            'valuation_reasonableness', 'valuation_fairness',  // duan_yongping, zhang_lei
            'peg', 'distressed_discount',                      // lynch, marks
            'intrinsic_value_discount', 'crypto_valuation'     // li_lu, dayu
        ],
        growth: [
            'disruption_score', 'ark_framework', 'innovation_diffusion', 'tam_size',
            'ai_exposure', 'tam_expansion', 'growth_franchise', 'earnings_predictability',
            'revenue_growth_score',
            'growth', 'growth_durability',                     // lynch, fisher
            'long_term_bet', 'structural_opportunity',         // thiel, zhang_lei
            'ai_compute_demand', 'industry_tailwinds'          // serenity, li_lu
        ],
        quality: [
            'moat', 'financial_strength', 'management_quality', 'brand_moat', 'pricing_power',
            'moat_reinforcement', 'management_vision', 'compute_infrastructure',
            'vertical_integration', 'fundamental', 'earnings_quality',
            'business_clarity', 'long_term_durability',        // duan_yongping
            'management_integrity', 'moat_quality',            // duan_yongping
            'margin_sustainability', 'sales_organization', 'scuttlebutt',  // fisher
            'competitive_position', 'understandability',       // li_lu, lynch
            'quality',                                         // lynch
            'second_level_thinking',                           // marks
            'contra_bet', 'moat_durability', 'psychological', 'selection_rigor',  // munger
            'founder_quality', 'monopoly_power', 'technology_moat',               // thiel
            'business_model_quality', 'competitive_moat', 'management_excellence', // zhang_lei
            'information_edge'                                 // dayu
        ],
        momentum: [
            'trend_strength', 'macro_outlook', 'momentum', 'macro_background', 'momentum_signal',
            'momentum_sentiment', 'china_structural_theme', 'macro_score',
            'pendulum_position', 'narrative_timing',           // marks, dayu
            'exit_signal', 'inflection_condition',             // soros
            'market_bias', 'trend_reinforcement',              // soros
            'contrarian_timing',                               // thiel
            'geopolitical_catalyst', 'options_iv_momentum'    // serenity
        ],
        safety: [
            'risk_adjusted', 'debt_safety', 'coverage_score',
            'financial_soundness', 'risk_pricing',             // li_lu, marks
            'risk_capital', 'stablecoin_signal',               // dayu
            'risk_sizing', 'liquidity'                         // serenity, soros
        ]
    };

    // These factor names represent "bad risk" (high = risky -> invert to safety score)
    var INVERT = {
        tech_risk: true, liquidity_risk: true, downside_risk: true,
        supply_chain_bottleneck: true  // serenity: high bottleneck risk = lower safety
    };

    var CATEGORIES = ['valuation', 'growth', 'quality', 'momentum', 'safety'];

    function catAvg(factors, category) {
        var keys = FACTOR_MAP[category] || [];
        var vals = [];
        keys.forEach(function (k) {
            if (factors[k] !== undefined) {
                var v = parseFloat(factors[k]) || 0;
                vals.push(INVERT[k] ? 10 - v : v);
            }
        });
        if (category === 'safety') {
            Object.keys(factors).forEach(function (k) {
                if (INVERT[k] && vals.indexOf(parseFloat(factors[k])) === -1) {
                    vals.push(10 - (parseFloat(factors[k]) || 0));
                }
            });
        }
        if (!vals.length) return null;
        return vals.reduce(function (s, v) { return s + v; }, 0) / vals.length;
    }

    function hasFactors(factors) {
        return !!(factors && Object.keys(factors).length >= 3);
    }

    global.AugurFactorMap = {
        FACTOR_MAP: FACTOR_MAP,
        INVERT: INVERT,
        CATEGORIES: CATEGORIES,
        catAvg: catAvg,
        hasFactors: hasFactors
    };
})(window);
