# 🏦 外资观点日报 Instructions

> **INPUT**: JSON object with `institutional_views` and `sector_rotation` sections.
> **OUTPUT**: A focused report on foreign institutional views and capital flows.

---

## 🎯 Focus Areas

1.  **Institutional Views**: Goldman Sachs, Morgan Stanley, UBS, Citigroup, Bank of America, BlackRock, Bridgewater, PIMCO views on markets
2.  **Sector Rotation**: Capital flows between sectors, regions, asset classes
3.  **China/Asia Views**: Foreign perspectives on Chinese stocks, A-shares, Hong Kong, Asia markets
4.  **Macro Data**: Fed, PBOC, inflation, employment, GDP with institutional interpretations

---

## 📝 Report Structure

### Part 1: 🏦 机构观点 (Institutional Views)

*Format*:
```markdown
#### N. [标题](url)
> **机构**: 高盛 | **观点**: 看多/看空/中性 | **标的**: 中国科技股 | **时间**: 09:48
> **摘要**: 一句话中文摘要。
> **深度解读**: 💡 核心逻辑、催化剂、风险点。
```

*观点提取规则*:
- 看多关键词: 看多, 买入, 增持, 超配, bullish, overweight, upgrade
- 看空关键词: 看空, 卖出, 减持, 低配, bearish, underweight, downgrade
- 中性关键词: 中性, 持有, 观望, neutral, hold

### Part 2: 🔄 板块轮动 (Sector Rotation)

*Format*:
```markdown
#### N. [标题](url)
> **方向**: 科技 → 能源 | **规模**: 如有 | **时间**: 09:48
> **摘要**: 资金流向说明。
> **驱动因素**: 💡 轮动原因、持续性判断。
```

### Part 3: 📊 数据解读 (Data & Macro)

*Format*:
```markdown
#### N. [标题](url)
> **数据**: 中国PMI | **实际**: 49.5 | **预期**: 50.2 | **时间**: 09:48
> **市场反应**: 资产价格变动。
> **机构解读**: 💡 主流机构如何解读该数据。
```

---

## ⚠️ Filtering Rules (Critical)

**必须包含至少一个关键词才输出**:

**机构关键词**:
```
高盛, Goldman, 摩根士丹利, 大摩, Morgan Stanley, 瑞银, UBS, 
花旗, Citigroup, 美银, Bank of America, 贝莱德, BlackRock,
桥水, Bridgewater, PIMCO, 太平洋投资, 景顺, Invesco
```

**资金流向关键词**:
```
资金流入, 资金流出, 板块轮动, sector rotation, 
增持, 减持, 超配, 低配, 外资, 北向资金, QFII,
capital flow, inflow, outflow
```

**观点关键词**:
```
看多, 看空, 买入, 卖出, 升级, 降级, 
bullish, bearish, upgrade, downgrade,
overweight, underweight
```

---

## 🎯 Output Rules

1.  **Volume**: 输出不少于 **10 条** 有效内容（不足则标注"今日外资观点较少"）
2.  **Language**: 全部简体中文，保留英文机构名
3.  **Anti-Hallucination**: 仅使用 JSON 中的数据，不编造观点
4.  **Focus**: 只输出外资观点相关内容，过滤掉纯国内新闻
