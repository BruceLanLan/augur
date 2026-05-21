# -*- coding: utf-8 -*-
"""
Persona Evolution Tracker — 投资人人格进化追踪系统

跟踪每位投资人的：
- 持仓变化（历史上在不同时间点买了/卖了什么）
- 风格漂移（投资哲学是否发生了变化）
- 新闻影响（关键事件是否改变了判断）
- 时间线（重大决策的时间点）

当前内置数据：12位投资人全部完善
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PERSONA_EVOLUTION_DIR = Path(__file__).parent / "evolution"


class PersonaEvolutionTracker:
    """追踪投资人人格的动态变化"""

    def __init__(self):
        self._cache: Dict[str, dict] = {}
        PERSONA_EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)

    def get_evolution(self, persona_id: str) -> dict:
        """获取某个投资人的完整进化历程"""
        path = PERSONA_EVOLUTION_DIR / f"{persona_id}.json"
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
        return self._get_default_evolution(persona_id)

    def _get_default_evolution(self, persona_id: str) -> dict:
        """返回默认进化数据（12位投资人全部完善）"""
        _ALL_EVOLUTIONS = {
            "buffett": {
                "persona_id": "buffett", "name": "Warren Buffett",
                "timeline": [
                    {"date": "1965", "event": "控股伯克希尔哈撒韦", "impact": "从合伙基金转向控股集团模式"},
                    {"date": "1972", "event": "收购See's Candies", "impact": "确立品牌护城河投资理念"},
                    {"date": "1988", "event": "建仓可口可乐", "impact": "经典护城河投资案例"},
                    {"date": "2008", "event": "金融危机期间投资高盛/GE", "impact": "危机中逆向投资"},
                    {"date": "2011", "event": "建仓IBM", "impact": "首次重仓科技股(后失败退出)"},
                    {"date": "2016", "event": "建仓苹果", "impact": "从拒绝科技股到重仓苹果"},
                    {"date": "2020", "event": "疫情期抛售航空股", "impact": "承认判断失误、及时止损"},
                    {"date": "2023-2024", "event": "持续减持苹果、增持现金", "impact": "估值过高信号下的防御策略"},
                    {"date": "2025", "event": "建仓CRCL(稳定币)", "impact": "首次进入加密领域"},
                ],
                "style_shifts": [
                    {"from": "纯价值投资", "to": "价值+成长", "reason": "苹果的成功让巴菲特接受优质成长"},
                    {"from": "拒绝科技股", "to": "拥抱科技龙头", "reason": "科技公司已形成强大护城河"},
                    {"from": "美国为主", "to": "关注日本/全球", "reason": "日本商社投资成功"},
                    {"from": "传统金融", "to": "接受加密生态", "reason": "CRCL投资的信号意义"},
                ],
                "current_portfolio_themes": [
                    "苹果(第一大持仓)", "美国银行/美国运通(金融)",
                    "可口可乐/卡夫亨氏(消费)", "日本五大商社", "CRCL(新领域)"
                ],
                "current_biases": {"prefers_large_cap": True, "high_cash_position": True,
                                   "cautious_on_valuation": True, "open_to_new_ideas": True}
            },
            "graham": {
                "persona_id": "graham", "name": "Benjamin Graham",
                "timeline": [
                    {"date": "1914", "event": "华尔街实习", "impact": "初入金融行业"},
                    {"date": "1926", "event": "成立合伙基金", "impact": "早期价值投资实践"},
                    {"date": "1934", "event": "出版《证券分析》", "impact": "创立价值投资学科"},
                    {"date": "1949", "event": "出版《聪明的投资者》", "impact": "面向普通投资者的经典"},
                    {"date": "1950s", "event": "哥伦比亚大学任教", "impact": "培养包括巴菲特在内的学生"},
                    {"date": "1976", "event": "去世", "impact": "留下完整价值投资体系"},
                ],
                "style_shifts": [
                    {"from": "证券分析起步", "to": "系统化安全边际框架", "reason": "大萧条后总结出价值投资体系"},
                    {"from": "积极型投资", "to": "防御型投资哲学", "reason": "年龄增长后更强调保守"},
                ],
                "current_portfolio_themes": [
                    "低估大盘股(PE<15)", "破净股(PB<1.5)",
                    "高股息企业", "高流动性资产"
                ],
                "current_biases": {"strict_value": True, "prefers_tangible_assets": True,
                                   "avoids_speculation": True, "high_diversification": True}
            },
            "lynch": {
                "persona_id": "lynch", "name": "Peter Lynch",
                "timeline": [
                    {"date": "1969", "event": "加入富达投资", "impact": "开始投资生涯"},
                    {"date": "1977", "event": "接管麦哲伦基金", "impact": "管理传奇基金的开端"},
                    {"date": "1980s", "event": "连续13年战胜市场", "impact": "年化收益率29%"},
                    {"date": "1989", "event": "出版《One Up On Wall Street》", "impact": "向散户分享投资智慧"},
                    {"date": "1990", "event": "退休", "impact": "激流勇退，专注慈善和教育"},
                ],
                "style_shifts": [
                    {"from": "传统基金分析", "to": "GARP成长投资", "reason": "发现优质成长比纯价值回报更高"},
                    {"from": "机构投资方法", "to": "散户优势理论", "reason": "散户可以在消费中发现牛股"},
                ],
                "current_portfolio_themes": [
                    "消费成长股", "PEG<1.5的标的",
                    "六类股票分类(缓慢/稳健/快速/周期/困境/隐蔽)",
                    "日常消费品中发现的机会"
                ],
                "current_biases": {"growth_at_reasonable_price": True, "consumer_focus": True,
                                   "prefers_understandable_business": True, "medium_term_hold": True}
            },
            "dalio": {
                "persona_id": "dalio", "name": "Ray Dalio",
                "timeline": [
                    {"date": "1975", "event": "创立桥水基金", "impact": "从两居室公寓开始的宏观投资生涯"},
                    {"date": "1987", "event": "股灾中做多债券获利", "impact": "桥水一战成名"},
                    {"date": "1996", "event": "提出全天候策略", "impact": "风险平价理论的开端"},
                    {"date": "2008", "event": "金融危机中为客户盈利", "impact": "全天候策略验证"},
                    {"date": "2017", "event": "出版《原则》", "impact": "从投资延伸到人生/管理原则"},
                    {"date": "2020", "event": "疫情中精准预测", "impact": "债务周期理论再次验证"},
                    {"date": "2022", "event": "退休交班", "impact": "从桥水控制权退出"},
                ],
                "style_shifts": [
                    {"from": "宏观交易者", "to": "系统化全天候投资者", "reason": "认识到分散化是唯一的免费午餐"},
                    {"from": "不公开", "to": "公开原则与知识分享", "reason": "希望帮助更多人理解经济机器"},
                    {"from": "美国中心", "to": "全球宏观+中国重仓", "reason": "中国崛起是历史性机遇"},
                ],
                "current_portfolio_themes": [
                    "风险平价四象限配置", "长期国债(通缩对冲)",
                    "黄金/大宗商品(通胀对冲)", "股票(增长资产)",
                    "中国资产(长期看好)"
                ],
                "current_biases": {"macro_over_micro": True, "systematic_process": True,
                                   "top_down_approach": True, "debt_cycle_focus": True}
            },
            "munger": {
                "persona_id": "munger", "name": "Charlie Munger",
                "timeline": [
                    {"date": "1962", "event": "成立律所Munger Tolles", "impact": "律师背景奠定底层思维"},
                    {"date": "1965", "event": "退出律所专注投资", "impact": "从律师转型投资人"},
                    {"date": "1972", "event": "推动收购See's Candies", "impact": "从捡烟蒂到护城河投资的关键转变"},
                    {"date": "1975", "event": "与巴菲特合并投资", "impact": "形成伯克希尔双核投资文化"},
                    {"date": "2008", "event": "建仓比亚迪", "impact": "新能源/中国机遇的远见投资"},
                    {"date": "2023", "event": "去世(享年99岁)", "impact": "留下格栅理论和多元思维模型"},
                ],
                "style_shifts": [
                    {"from": "律师/格雷厄姆式", "to": "格栅理论/多元思维", "reason": "发现跨学科知识比纯金融更有力量"},
                    {"from": "纯投资", "to": "经营思维+投资结合", "reason": "控股企业比买卖股票收益更高"},
                ],
                "current_portfolio_themes": [
                    "伯克希尔控股企业", "Costco(会员模式标杆)",
                    "比亚迪(新能源)", "喜诗糖果(品牌定价权)"
                ],
                "current_biases": {"mental_models": True, "inversion_thinking": True,
                                   "circle_of_competence": True, "lifelong_learning": True}
            },
            "soros": {
                "persona_id": "soros", "name": "George Soros",
                "timeline": [
                    {"date": "1969", "event": "创立量子基金", "impact": "全球最著名宏观对冲基金诞生"},
                    {"date": "1973", "event": "做空多国货币", "impact": "在固定汇率体系崩溃中获利"},
                    {"date": "1992", "event": "做空英镑(黑色星期三)", "impact": "一天赚10亿美元"},
                    {"date": "1997", "event": "亚洲金融危机", "impact": "做空泰铢/东南亚货币"},
                    {"date": "2000s", "event": "转型慈善", "impact": "开放社会基金会"},
                    {"date": "2011", "event": "基金转为家族办公室", "impact": "不再管理外部资金"},
                ],
                "style_shifts": [
                    {"from": "证券分析起步", "to": "宏观反身性交易", "reason": "发现传统价值投资无法解释市场泡沫"},
                    {"from": "追求回报", "to": "慈善优先", "reason": "赚够后回馈社会"},
                ],
                "current_portfolio_themes": [
                    "宏观对冲头寸", "货币/利率衍生品",
                    "地缘政治事件交易", "全球化趋势转换"
                ],
                "current_biases": {"reflexivity_driven": True, "macro_sizing": True,
                                   "contrarian_entry": True, "trend_following_exit": True}
            },
            "marks": {
                "persona_id": "marks", "name": "Howard Marks",
                "timeline": [
                    {"date": "1985", "event": "创立Oaktree资本", "impact": "专注困境债务和另类投资"},
                    {"date": "1990s", "event": "建立不良资产投资体系", "impact": "成为困境债务投资领导者"},
                    {"date": "2000年", "event": "科技泡沫中坚持价值", "impact": "避开互联网泡沫崩溃"},
                    {"date": "2008", "event": "金融危机中大规模买入", "impact": "困境资产投资的经典时刻"},
                    {"date": "2010s", "event": "备忘录风靡华尔街", "impact": "投资思考的深度分享"},
                    {"date": "2019", "event": "Oaktree部分出售给Brookfield", "impact": "行业整合趋势"},
                ],
                "style_shifts": [
                    {"from": "传统信贷分析", "to": "周期定位投资", "reason": "发现理解周期比理解公司更重要"},
                    {"from": "简单买入持有", "to": "钟摆定位(极端是机会)", "reason": "情绪钟摆的极端才是最佳买卖点"},
                    {"from": "美国为主", "to": "全球困境投资", "reason": "不良资产机会全球化"},
                ],
                "current_portfolio_themes": [
                    "周期底部资产", "困境债务重组",
                    "高收益债(risk-on/off)", "另类投资"
                ],
                "current_biases": {"cycle_awareness": True, "contrarian_nature": True,
                                   "risk_consciousness": True, "patient_capital": True}
            },
            "cathie_wood": {
                "persona_id": "cathie_wood", "name": "Cathie Wood",
                "timeline": [
                    {"date": "2014", "event": "创立ARK Invest", "impact": "专注颠覆性创新的投资公司"},
                    {"date": "2017-2018", "event": "重仓特斯拉", "impact": "早期准确判断电动车颠覆传统车企"},
                    {"date": "2020", "event": "ARK基金业绩爆发", "impact": "5支基金平均回报>100%"},
                    {"date": "2021-2022", "event": "利率上升后大幅回撤", "impact": "成长股估值压缩的教训"},
                    {"date": "2023", "event": "提前布局AI赛道", "impact": "精准判断AI/区块链/基因革命"},
                    {"date": "2024", "event": "推出现实资产ETF", "impact": "策略更加多元化"},
                ],
                "style_shifts": [
                    {"from": "传统基本面分析", "to": "创新平台式投资", "reason": "发现线性估值无法衡量指数级增长"},
                    {"from": "纯二级市场", "to": "一级+二级融合", "reason": "深入创业公司了解颠覆性技术"},
                    {"from": "纯成长", "to": "成长+现实资产混合", "reason": "利率环境变化促使策略进化"},
                ],
                "current_portfolio_themes": [
                    "AI/机器学习平台", "基因编辑/精准医疗",
                    "区块链/数字钱包", "自动化/机器人",
                    "能源存储/电动化"
                ],
                "current_biases": {"innovation_focus": True, "long_term_horizon_5y": True,
                                   "high_conviction_concentrated": True, "ignore_macro_noise": True}
            },
            "fisher": {
                "persona_id": "fisher", "name": "Philip Fisher",
                "timeline": [
                    {"date": "1931", "event": "创立Fisher & Company", "impact": "开始独立投资管理"},
                    {"date": "1955", "event": "投资摩托罗拉(持有20+年)", "impact": "经典成长股投资案例"},
                    {"date": "1958", "event": "出版《怎样选择成长股》", "impact": "成长股投资的圣经"},
                    {"date": "1960s", "event": "拒绝科技泡沫炒作", "impact": "坚持能力圈原则"},
                    {"date": "1980", "event": "儿子入职继续管理", "impact": "家族投资传承"},
                    {"date": "1999", "event": "科技泡沫中再次保持清醒", "impact": "晚年验证成长投资框架的有效性"},
                ],
                "style_shifts": [
                    {"from": "公司分析起步", "to": "闲聊法(Scuttlebutt)", "reason": "发现财报之外的软信息更有价值"},
                    {"from": "集中持股", "to": "超级集中(<10只)", "reason": "最了解的公司才值得重仓"},
                ],
                "current_portfolio_themes": [
                    "高研发投入企业(>10%)", "高毛利率(>50%)",
                    "优秀管理层(深度访谈)", "长期增长确定性"
                ],
                "current_biases": {"growth_at_any_price": False, "deep_research": True,
                                   "scuttlebutt_method": True, "long_term_only": True}
            },
            "arps": {
                "persona_id": "arps", "name": "ARPS Crypto/Gold",
                "timeline": [
                    {"date": "2017", "event": "Crypto市场初识", "impact": "认识到数字资产是新兴资产类别"},
                    {"date": "2020", "event": "疫情后宏观分析体系建立", "impact": "黄金+比特币的避险逻辑"},
                    {"date": "2021", "event": "中国挖矿禁令", "impact": "算力迁移改变加密格局"},
                    {"date": "2022", "event": "FTX崩溃/黄金重新崛起", "impact": "中心化交易所信任崩塌"},
                    {"date": "2024", "event": "BTC ETF获批", "impact": "传统资本大规模入场通道打开"},
                    {"date": "2025", "event": "美国战略BTC储备", "impact": "国家层面认可数字资产"},
                ],
                "style_shifts": [
                    {"from": "纯Crypto", "to": "Crypto+黄金双线", "reason": "地缘风险上升，黄金重新成为核心配置"},
                    {"from": "技术分析为主", "to": "宏观+Crypto链上数据", "reason": "美元周期是更大级别的驱动力"},
                ],
                "current_portfolio_themes": [
                    "BTC(数字黄金)", "黄金(实物+ETF)",
                    "矿企股票", "美元对冲资产"
                ],
                "current_biases": {"hard_assets": True, "anti_fiat": True,
                                   "macro_driven": True, "long_term_bullish_crypto": True}
            },
            "aschenbrenner": {
                "persona_id": "aschenbrenner", "name": "Leopold Aschenbrenner",
                "timeline": [
                    {"date": "2019", "event": "OpenAI工作经历", "impact": "深入了解前沿AI能力"},
                    {"date": "2023", "event": "发表AI地缘格局分析", "impact": "提出AI是新的工业革命"},
                    {"date": "2024", "event": "建立投资框架", "impact": "从研究转型投资"},
                    {"date": "2025", "event": "AI算力需求非线性增长被验证", "impact": "推理时代的算力需求远超预期"},
                    {"date": "2026", "event": "AI投资框架成熟", "impact": "建立AI产业链多维分析体系"},
                ],
                "style_shifts": [
                    {"from": "AI安全研究员", "to": "AI地缘投资分析", "reason": "认识AI的经济影响远超安全议题"},
                    {"from": "纯研究", "to": "研究驱动投资", "reason": "最好的AI判断必须转化为投资决策"},
                ],
                "current_portfolio_themes": [
                    "AI算力基础设施", "数据中心/电力/芯片",
                    "AI应用平台", "地缘政治对冲"
                ],
                "current_biases": {"ai_centric": True, "compute_as_commodity": True,
                                   "scaling_hypothesis": True, "geopolitical_awareness": True}
            },
            "dayu": {
                "persona_id": "dayu", "name": "大宇 (BTCdayu)",
                "timeline": [
                    {"date": "2021前", "event": "技术分析阶段", "impact": "沉迷K线，方向错误"},
                    {"date": "2021-519", "event": "币圈519大清洗逃顶", "impact": "信息优势验证——消息面秒杀一切理论"},
                    {"date": "2021-LUNA", "event": "LUNA暴雷", "impact": "金融领域没有大而不能倒"},
                    {"date": "2022-FTX", "event": "FTX爆雷做空大赚", "impact": "做空是合理的盈亏比工具"},
                    {"date": "2023-BONK", "event": "BONK一周5倍", "impact": "情绪投机的经典操作"},
                    {"date": "2023-进化", "event": "看准+重仓1.0→2.0", "impact": "小资金求快→大资金求稳"},
                    {"date": "2024", "event": "看准+重仓3.0", "impact": "均衡体系成熟:核心+高风险+稳定币"},
                    {"date": "2025-2026", "event": "CRCL研究+AI赛道", "impact": "稳定币是美元第二增长曲线"},
                ],
                "style_shifts": [
                    {"from": "纯技术分析", "to": "信息差+情绪判断", "reason": "技术分析方向错了"},
                    {"from": "传统价值投资", "to": "币圈实事求是", "reason": "传统理论在币圈会亏很惨"},
                    {"from": "看准全仓", "to": "三重仓位管理", "reason": "资金体量变大后必须改变玩法"},
                    {"from": "纯币圈", "to": "AI+币圈双线程", "reason": "AI是新时代最大的机会"},
                ],
                "current_portfolio_themes": [
                    "ETH(核心持仓)", "BTC(辅助核心)",
                    "稳定币生息(安全垫)", "Meme币/新叙事(10%高风险)",
                    "CRCL(长期研究)"
                ],
                "current_biases": {
                    "momentum_over_value": True, "information_advantage_key": True,
                    "small_cap_preference": True, "contrarian_at_extremes": True,
                }
            },
        }
        return _ALL_EVOLUTIONS.get(persona_id, {
            "persona_id": persona_id, "name": persona_id,
            "timeline": [], "style_shifts": [],
            "current_portfolio_themes": [], "current_biases": {}
        })

    def list_available(self) -> List[dict]:
        """列出所有有进化数据的投资人"""
        ids = ["buffett", "graham", "lynch", "dalio", "munger", "soros",
               "marks", "cathie_wood", "fisher", "arps", "aschenbrenner", "dayu"]
        return [self.get_evolution(aid) for aid in ids]

    def record_event(self, persona_id: str, date_str: str, event: str, impact: str):
        """新增一个进化事件"""
        evo = self.get_evolution(persona_id)
        evo.setdefault("timeline", []).append({
            "date": date_str, "event": event, "impact": impact
        })
        self._save(persona_id, evo)

    def record_style_shift(self, persona_id: str, from_style: str, to_style: str, reason: str):
        """记录风格漂移"""
        evo = self.get_evolution(persona_id)
        evo.setdefault("style_shifts", []).append({
            "from": from_style, "to": to_style, "reason": reason
        })
        self._save(persona_id, evo)

    def get_current_context(self, persona_id: str) -> dict:
        """获取投资人当前状态摘要（用于分析时注入Agent）"""
        evo = self.get_evolution(persona_id)
        return {
            "persona_id": persona_id,
            "name": evo.get("name", persona_id),
            "current_biases": evo.get("current_biases", {}),
            "current_portfolio_themes": evo.get("current_portfolio_themes", []),
            "latest_events": evo.get("timeline", [])[-3:],
            "style_evolution": [s["to"] for s in evo.get("style_shifts", [])],
        }

    def print_status(self, persona_id: str = None) -> str:
        """打印投资人进化状态"""
        if persona_id:
            evos = [self.get_evolution(persona_id)]
        else:
            evos = self.list_available()
        lines = []
        for evo in evos:
            name = evo.get("name", evo["persona_id"])
            events = len(evo.get("timeline", []))
            shifts = len(evo.get("style_shifts", []))
            lines.append(f"  {evo['persona_id']:>18} | {name:<25} | {events} events | {shifts} shifts")
        return "\n".join(lines)

    def _save(self, persona_id: str, data: dict):
        path = PERSONA_EVOLUTION_DIR / f"{persona_id}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
