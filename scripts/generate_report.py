#!/usr/bin/env python3
"""
外资观点日报生成器
从 foreign_views.db 读取当日数据，生成 Markdown 日报
输出路径: /home/ubuntu/.openclaw/workspace/etf_tracker/reports/foreign_views_YYYY-MM-DD.md
"""

import os
import sys
import sqlite3
import glob
from datetime import date, datetime, timedelta

# 数据库路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(SKILL_DIR, 'data', 'foreign_views.db')

# 报告输出目录
REPORTS_DIR = '/home/ubuntu/.openclaw/workspace/etf_tracker/reports'

CATEGORY_META = {
    'institutional_views': {
        'icon': '🏦',
        'label': '机构观点',
    },
    'sector_rotation': {
        'icon': '🔄',
        'label': '板块轮动',
    },
    'china_views': {
        'icon': '📊',
        'label': '中国/亚洲观点',
    },
}


def load_today_news(report_date=None):
    """从数据库加载指定日期的新闻，按分类分组"""
    if report_date is None:
        report_date = date.today().strftime('%Y-%m-%d')

    if not os.path.exists(DB_PATH):
        return {}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT * FROM news
        WHERE fetched_at LIKE ?
        ORDER BY time DESC, id DESC
    ''', (f'{report_date}%',))

    rows = c.fetchall()
    conn.close()

    result = {}
    for row in rows:
        cat = row['category']
        if cat not in result:
            result[cat] = []
        result[cat].append(dict(row))

    return result


def format_article(num, item):
    """格式化单篇文章为 Markdown"""
    cat_meta = CATEGORY_META.get(item['category'], {'icon': '📰', 'label': item['category']})
    lines = []
    lines.append(f"### {num}. {item['title']}")
    lines.append(f"> **来源**: {item['source']} | **时间**: {item.get('time', '未知')}")
    lines.append(f"> **分类**: {cat_meta['icon']} {cat_meta['label']}")

    if item.get('url'):
        lines.append(f"> **链接**: [{item['url']}]({item['url']})")

    content = item.get('content') or item.get('content_short', '')
    if content:
        summary = content[:300].replace('\n', ' ').strip()
        lines.append(f"> **摘要**: {summary}")

    lines.append('')
    return '\n'.join(lines)


def generate_report(report_date=None):
    """生成日报"""
    if report_date is None:
        report_date = date.today().strftime('%Y-%m-%d')

    data = load_today_news(report_date)

    if not data:
        return None, 0

    lines = []
    lines.append(f'# 外资观点日报 - {report_date}')
    lines.append('')
    lines.append(f'> 自动生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    lines.append(f'> 数据来源: 华尔街见闻')
    lines.append('')
    lines.append('---')
    lines.append('')

    total_count = 0

    for cat_key in ['institutional_views', 'sector_rotation', 'china_views']:
        items = data.get(cat_key, [])
        if not items:
            continue

        cat_meta = CATEGORY_META[cat_key]
        lines.append(f'## {cat_meta["icon"]} {cat_meta["label"]}')
        lines.append('')

        for i, item in enumerate(items, 1):
            lines.append(format_article(i, item))

        lines.append('---')
        lines.append('')
        total_count += len(items)

    if total_count == 0:
        return None, 0

    lines.append(f'*共 {total_count} 条，完整浏览请查看源链接。*')
    lines.append('')

    return '\n'.join(lines), total_count


def save_report(markdown, report_date=None):
    """保存日报到文件"""
    if report_date is None:
        report_date = date.today().strftime('%Y-%m-%d')

    os.makedirs(REPORTS_DIR, exist_ok=True)
    filepath = os.path.join(REPORTS_DIR, f'foreign_views_{report_date}.md')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(markdown)

    # 也保存一份 latest
    latest_path = os.path.join(REPORTS_DIR, 'foreign_views_latest.md')
    with open(latest_path, 'w', encoding='utf-8') as f:
        f.write(markdown)

    return filepath


def cleanup_old_reports(days=90):
    """删除超过指定天数的旧日报文件"""
    cutoff = date.today() - timedelta(days=days)
    pattern = os.path.join(REPORTS_DIR, 'foreign_views_????-??-??.md')

    deleted = 0
    for filepath in glob.glob(pattern):
        filename = os.path.basename(filepath)
        # 提取日期: foreign_views_2026-06-07.md → 2026-06-07
        try:
            file_date_str = filename.replace('foreign_views_', '').replace('.md', '')
            file_date = datetime.strptime(file_date_str, '%Y-%m-%d').date()
            if file_date < cutoff:
                os.remove(filepath)
                deleted += 1
        except ValueError:
            continue

    if deleted:
        print(f"[generate_report] 🗑️ 清理 {deleted} 个旧日报（{cutoff}前）", file=sys.stderr)


def main():
    today = date.today().strftime('%Y-%m-%d')

    # 支持命令行指定日期: python3 generate_report.py 2026-06-06
    report_date = sys.argv[1] if len(sys.argv) > 1 else today

    print(f"[generate_report] 生成 {report_date} 日报...", file=sys.stderr)

    markdown, count = generate_report(report_date)

    if markdown is None:
        print(f"[generate_report] {report_date} 无数据，跳过", file=sys.stderr)
    else:
        filepath = save_report(markdown, report_date)
        print(f"[generate_report] 已保存: {filepath} ({count} 条)", file=sys.stderr)
        print(markdown)

    # 清理旧日报文件
    # cleanup_old_reports(days=90)  # 已禁用自动清理


if __name__ == '__main__':
    main()
