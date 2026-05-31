/**
 * Augur i18n - 国际化支持
 * 支持中文(zh)和英文(en)切换，持久化到 localStorage
 */
window.I18N = {
    zh: {
        // Sidebar nav
        "nav-dashboard": "仪表盘",
        "nav-stocks": "股票分析",
        "nav-signals": "信号监控",
        "nav-backtest": "回测",
        "nav-personas": "人格系统",
        "nav-create-persona": "创建投资人",
        "nav-settings": "设置",
        // Nav group labels
        "group-analysis": "分析",
        "group-investors": "投资人",
        "group-system": "系统",
        // Sidebar footer
        "status-ready": "系统就绪",
        "theme-dark": "深色",
        "theme-light": "浅色",
        "powered-by": "Powered by Augur",
        // Bottom nav
        "bottom-home": "首页",
        "bottom-analysis": "分析",
        "bottom-masters": "大师",
        "bottom-backtest": "回测",
        "bottom-settings": "设置",
        // Index page sections
        "section-market-overview": "全球市场总览",
        "section-hot-tickers": "热门标的实时行情",
        "section-featured-personas": "精选投资人",
        "section-how-it-works": "工作原理",
        "section-recent": "最近分析",
        "section-datasource": "数据源状态",
        "section-fear-greed": "恐慌与贪婪指标",
        "section-macro": "宏观经济快照",
        // Buttons
        "btn-analyze": "分析",
        "btn-refresh": "刷新",
        "btn-view-all-personas": "查看全部 18 位",
        "btn-detail": "查看各位大师详情",
        "btn-report": "生成深度分析报告",
        // How it works
        "how-step1-title": "1. 输入代码",
        "how-step1-desc": "只需股票代码，系统自动获取实时数据（也可手动填指标）",
        "how-step2-title": "2. 多Agent分析",
        "how-step2-desc": "18 位投资大师从各自视角独立分析",
        "how-step3-title": "3. 共识决策",
        "how-step3-desc": "行业加权、机制感知，形成最终共识信号",
        // Hero
        "hero-subtitle": "输入股票代码，一键获得18位大师共识",
        "hero-placeholder": "输入股票代码 (AAPL / NVDA / 0700.HK)",
        // Scanner
        "scanner_title": "市场扫描器",
        "scanner_desc": "选择预设列表或输入自定义股票代码，一键让18位大师快速评分",
        "scanner_preset_tech": "科技巨头",
        "scanner_preset_china": "中概股",
        "scanner_preset_crypto": "加密货币",
        "scanner_custom_label": "自定义标的 (逗号分隔)",
        "scanner_limit": "最多20个标的",
        "scanner_run": "开始扫描",
        "scanner_results_title": "扫描结果",
        "nav_scanner": "扫描器",
        // Alert & Notification
        "alert_threshold_title": "监控告警设置",
        "alert_threshold_label": "评分阈值",
        "alert_channel_label": "通知渠道",
        "alert_save": "保存告警设置",
        // Report actions
        "download_report": "下载报告",
        "copy_report": "复制报告",
        // Lang toggle
        "lang-label": "EN"
    },
    en: {
        // Sidebar nav
        "nav-dashboard": "Dashboard",
        "nav-stocks": "Stocks",
        "nav-signals": "Signals",
        "nav-backtest": "Backtest",
        "nav-personas": "Personas",
        "nav-create-persona": "Create Persona",
        "nav-settings": "Settings",
        // Nav group labels
        "group-analysis": "Analysis",
        "group-investors": "Investors",
        "group-system": "System",
        // Sidebar footer
        "status-ready": "System Ready",
        "theme-dark": "Dark",
        "theme-light": "Light",
        "powered-by": "Powered by Augur",
        // Bottom nav
        "bottom-home": "Home",
        "bottom-analysis": "Analyze",
        "bottom-masters": "Masters",
        "bottom-backtest": "Backtest",
        "bottom-settings": "Settings",
        // Index page sections
        "section-market-overview": "Global Market Overview",
        "section-hot-tickers": "Hot Tickers",
        "section-featured-personas": "Featured Investors",
        "section-how-it-works": "How It Works",
        "section-recent": "Recent Analyses",
        "section-datasource": "Data Sources",
        "section-fear-greed": "Fear & Greed Index",
        "section-macro": "Macro Snapshot",
        // Buttons
        "btn-analyze": "Analyze",
        "btn-refresh": "Refresh",
        "btn-view-all-personas": "View All 18",
        "btn-detail": "View Details",
        "btn-report": "Generate Report",
        // How it works
        "how-step1-title": "1. Enter Ticker",
        "how-step1-desc": "Just a ticker symbol - real-time data fetched automatically",
        "how-step2-title": "2. Multi-Agent Analysis",
        "how-step2-desc": "18 investment masters analyze independently",
        "how-step3-title": "3. Consensus",
        "how-step3-desc": "Industry-weighted consensus signal",
        // Hero
        "hero-subtitle": "Enter a ticker, get consensus from 18 masters",
        "hero-placeholder": "Enter ticker (AAPL / NVDA / 0700.HK)",
        // Scanner
        "scanner_title": "Market Scanner",
        "scanner_desc": "Select a preset list or enter custom tickers for quick scoring by 18 masters",
        "scanner_preset_tech": "Tech Giants",
        "scanner_preset_china": "China ADRs",
        "scanner_preset_crypto": "Crypto",
        "scanner_custom_label": "Custom Tickers (comma separated)",
        "scanner_limit": "Max 20 tickers",
        "scanner_run": "Run Scanner",
        "scanner_results_title": "Scan Results",
        "nav_scanner": "Scanner",
        // Alert & Notification
        "alert_threshold_title": "Alert Threshold Settings",
        "alert_threshold_label": "Score Threshold",
        "alert_channel_label": "Notification Channel",
        "alert_save": "Save Alert Settings",
        // Report actions
        "download_report": "Download Report",
        "copy_report": "Copy Report",
        // Lang toggle
        "lang-label": "中"
    }
};

(function() {
    var _currentLang = 'zh';

    function initI18n() {
        var saved = localStorage.getItem('augur-lang');
        if (saved && (saved === 'zh' || saved === 'en')) {
            _currentLang = saved;
        } else {
            var navLang = (navigator.language || navigator.userLanguage || 'zh').toLowerCase();
            _currentLang = navLang.startsWith('zh') ? 'zh' : 'en';
        }
        applyLanguage(_currentLang);
    }

    function applyLanguage(lang) {
        _currentLang = lang;
        var dict = window.I18N[lang];
        if (!dict) return;
        var els = document.querySelectorAll('[data-i18n]');
        for (var i = 0; i < els.length; i++) {
            var key = els[i].getAttribute('data-i18n');
            if (dict[key] !== undefined) {
                if (els[i].tagName === 'INPUT' && els[i].hasAttribute('placeholder')) {
                    els[i].placeholder = dict[key];
                } else {
                    els[i].textContent = dict[key];
                }
            }
        }
        // Update lang label
        var langLabel = document.getElementById('lang-label');
        if (langLabel) {
            langLabel.textContent = lang === 'zh' ? 'EN' : '\u4E2D';
        }
    }

    function toggleLanguage() {
        var newLang = _currentLang === 'zh' ? 'en' : 'zh';
        localStorage.setItem('augur-lang', newLang);
        applyLanguage(newLang);
    }

    // Expose globally
    window.initI18n = initI18n;
    window.applyLanguage = applyLanguage;
    window.toggleLanguage = toggleLanguage;

    // Init on DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initI18n);
    } else {
        initI18n();
    }
})();
