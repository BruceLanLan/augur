# -*- coding: utf-8 -*-
"""
Persona Evolution Tracker — 投资人人格进化追踪系统

跟踪每个投资人的：
- 持仓变化（历史上在不同时间点买了/卖了什么）
- 风格漂移（投资哲学是否发生了变化）
- 新闻影响（关键事件是否改变了判断）
- 时间线（重大决策的时间点）
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, date

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
        """返回默认进化数据"""
        evolutions = {
            "buffett": {
                "persona_id": "buffett",
                "name": "Warren Buffett",
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
                    "苹果(第一大持仓)",
                    "美国银行/美国运通(金融)",
                    "可口可乐/卡夫亨氏(消费)",
                    "日本五大商社",
                    "CRCL(新领域)"
                ],
                "current_biases": {
                    "prefers_large_cap": True,
                    "high_cash_position": True,
                    "cautious_on_valuation": True,
                    "open_to_new_ideas": True,
                }
            },
            "dayu": {
                "persona_id": "dayu",
                "name": "大宇 (BTCdayu)",
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
                    "ETH(核心持仓)",
                    "BTC(辅助核心)",
                    "稳定币生息(安全垫)",
                    "Meme币/新叙事(10%高风险)",
                    "CRCL(长期研究)"
                ],
                "current_biases": {
                    "momentum_over_value": True,
                    "information_advantage_key": True,
                    "small_cap_preference": True,
                    "contrarian_at_extremes": True,
                }
            }
        }
        return evolutions.get(persona_id, {"persona_id": persona_id, "name": persona_id, "timeline": [], "style_shifts": []})
    
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
    
    def _save(self, persona_id: str, data: dict):
        path = PERSONA_EVOLUTION_DIR / f"{persona_id}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
