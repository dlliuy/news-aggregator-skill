#!/usr/bin/env python3
"""
增量抓取外资观点新闻
- 每30分钟运行一次
- 用 article_id（从 URL 提取）去重
- 追加到 SQLite 数据库
- 提取观点方向和重要性
"""

import os
import sys
import sqlite3
import re
from datetime import datetime, date, timedelta

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_news import fetch_wallstreetcn, enrich_items_with_content, extract_article_id

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'foreign_views.db')

# 观点关键词
VIEWPOINT_PATTERNS = [
    (r'看多|看好|bullish|overweight|买入|增持|升级|上调', '看多'),
    (r'看空|承压|bearish|underweight|卖出|减持|降级|下调|风险', '看空'),
]

# 机构关键词
INSTITUTION_KEYWORDS = [
    '高盛', 'Goldman', '摩根士丹利', '大摩', 'Morgan Stanley',
    '瑞银', 'UBS', '花旗', 'Citigroup', '美银', 'Bank of America',
    '贝莱德', 'BlackRock', '桥水', 'Bridgewater', 'PIMCO',
    '太平洋投资', '景顺', 'Invesco'
]

# 板块轮动排除（非市场轮动）
SECTOR_EXCLUDE_PATTERNS = [
    r'央行.*增持',
    r'国家队',
    r'社保基金',
]

# 中国观点排除（娱乐/社会）
CHINA_EXCLUDE_PATTERNS = [
    r'相亲', r'娱乐', r'明星', r'八卦',
    r'网红', r'直播', r'带货',
]


def init_db():
    """初始化数据库"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id TEXT UNIQUE NOT NULL,
            url TEXT NOT NULL,
            title TEXT NOT NULL,
            content_short TEXT,
            source TEXT NOT NULL,
            time TEXT,
            content TEXT,
            category TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            pushed INTEGER DEFAULT 0,
            importance INTEGER DEFAULT 1,
            viewpoint TEXT
        )
    ''')

    # 兼容旧表结构迁移
    _migrate_if_needed(c)

    conn.commit()
    conn.close()


def _migrate_if_needed(cursor):
    """迁移旧表结构"""
    try:
        cursor.execute("SELECT importance FROM news LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor.execute("ALTER TABLE news ADD COLUMN importance INTEGER DEFAULT 1")
            cursor.execute("ALTER TABLE news ADD COLUMN viewpoint TEXT")
            print("[DB] 已迁移旧表结构（新增 importance, viewpoint 列）", file=sys.stderr)
        except Exception as e:
            print(f"[DB] 迁移失败: {e}", file=sys.stderr)


def extract_viewpoint(title):
    """从标题提取观点方向"""
    for pattern, label in VIEWPOINT_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return label
    return None


def has_institution(title):
    """检查标题是否包含机构名"""
    for kw in INSTITUTION_KEYWORDS:
        if kw.lower() in title.lower():
            return True
    return False


def is_excluded(title, patterns):
    """检查标题是否匹配排除模式"""
    for pattern in patterns:
        if re.search(pattern, title, re.IGNORECASE):
            return True
    return False


def calculate_importance(title, category):
    """计算重要性等级"""
    # 机构观点：有机构名 + 观点词 → 3，仅机构名 → 2
    if category == 'institutional_views':
        if has_institution(title):
            viewpoint = extract_viewpoint(title)
            return 3 if viewpoint else 2
        return 1

    # 板块轮动：排除央行增持等，有方向词 → 3，仅关键词 → 2
    if category == 'sector_rotation':
        if is_excluded(title, SECTOR_EXCLUDE_PATTERNS):
            return 0  # 排除
        if re.search(r'流入|流出|轮动', title, re.IGNORECASE):
            return 3
        return 2

    # 中国观点：排除娱乐/社会，投资相关 → 3，其他 → 2
    if category == 'china_views':
        if is_excluded(title, CHINA_EXCLUDE_PATTERNS):
            return 0  # 排除
        if re.search(r'A股|港股|投资|基金|股票', title, re.IGNORECASE):
            return 3
        return 2

    return 1


def is_duplicate(article_id):
    """检查 article_id 是否已存在"""
    if not article_id:
        return True
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id FROM news WHERE article_id = ?', (article_id,))
    result = c.fetchone()
    conn.close()
    return result is not None


def save_news(item, category):
    """保存新闻到数据库，返回 True=新增"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 计算重要性
    importance = calculate_importance(item.get('title', ''), category)
    viewpoint = extract_viewpoint(item.get('title', ''))

    # importance=0 排除，不保存
    if importance == 0:
        return False

    try:
        enriched = item.get('content', '')
        if not enriched or len(enriched) < 50:
            enriched = item.get('content_short', '')

        c.execute('''
            INSERT OR IGNORE INTO news 
            (article_id, url, title, content_short, source, time, content, category, fetched_at, importance, viewpoint)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item.get('article_id', ''),
            item.get('url', ''),
            item.get('title', ''),
            item.get('content_short', ''),
            item.get('source', ''),
            item.get('time', ''),
            enriched,
            category,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            importance,
            viewpoint
        ))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"Error saving news: {e}", file=sys.stderr)
        return False
    finally:
        conn.close()


def cleanup_old_news(days=90):
    """删除超过指定天数的旧记录"""
    cutoff = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM news WHERE fetched_at < ?', (cutoff,))
        old_count = c.fetchone()[0]

        if old_count > 0:
            c.execute('DELETE FROM news WHERE fetched_at < ?', (cutoff,))
            conn.commit()
            print(f"[cleanup] 🗑️ 清理 {old_count} 条旧记录（{cutoff}前）", file=sys.stderr)

        conn.close()
    except Exception as e:
        print(f"[cleanup] 清理失败: {e}", file=sys.stderr)


def fetch_and_save():
    """抓取并保存新闻"""
    init_db()

    # 三类抓取配置
    configs = [
        ('institutional_views', 50,
         "高盛,Goldman,摩根士丹利,大摩,Morgan Stanley,瑞银,UBS,花旗,Citigroup,美银,Bank of America,贝莱德,BlackRock,桥水,Bridgewater,PIMCO,太平洋投资,景顺,Invesco,看多,看空,买入,卖出,升级,降级,bullish,bearish,upgrade,downgrade,overweight,underweight"),
        ('sector_rotation', 50,
         "板块轮动,资金流入,资金流出,增持,减持,超配,低配,sector rotation,capital flow,inflow,outflow,轮动,流向"),
        ('china_views', 50,
         "中国,A股,港股,中概,China,Chinese stocks"),
    ]

    stats = {}

    for category, limit, keywords in configs:
        print(f"[{category}] Fetching...", file=sys.stderr)
        items = fetch_wallstreetcn(limit, keywords)
        total = len(items)

        # 过滤出新增的
        new_items = [item for item in items if not is_duplicate(item.get('article_id'))]

        saved_count = 0
        excluded_count = 0

        if new_items:
            # 批量 enrich 正文
            new_items = enrich_items_with_content(new_items)
            for item in new_items:
                if save_news(item, category):
                    saved_count += 1
                else:
                    excluded_count += 1

        stats[category] = {'total': total, 'new': saved_count, 'excluded': excluded_count}
        print(f"[{category}] {saved_count} new / {total} total ({excluded_count} excluded)", file=sys.stderr)

    # 打印统计
    total_new = sum(s['new'] for s in stats.values())
    total_excluded = sum(s['excluded'] for s in stats.values())
    total_all = sum(s['total'] for s in stats.values())
    print(f"\n=== Fetch Summary ===", file=sys.stderr)
    for category, stat in stats.items():
        print(f"  {category}: {stat['new']} new / {stat['total']} total (excluded: {stat['excluded']})", file=sys.stderr)
    print(f"  Total: {total_new} new / {total_all} total (excluded: {total_excluded})", file=sys.stderr)

    return stats


if __name__ == '__main__':
    fetch_and_save()
