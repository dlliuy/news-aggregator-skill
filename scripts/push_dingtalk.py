#!/usr/bin/env python3
"""
外资观点钉钉推送
从 foreign_views.db 读取未推送且重要性>=2的文章，批量推送到钉钉群
"""

import os
import sys
import sqlite3
import subprocess
from datetime import datetime

# 路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(SKILL_DIR, 'data', 'foreign_views.db')

# 钉钉配置
DINGTALK_TARGET = 'cidP3MXkkKxqb8QjpVWXLZ0rA=='
OPENCLAW_BIN = '/home/ubuntu/.nvm/versions/node/v24.21.0/bin/openclaw'

# 日志路径
LOG_PATH = '/home/ubuntu/.openclaw/workspace/etf_tracker/cron_foreign_views.log'

CATEGORY_ICONS = {
    'institutional_views': '🏦',
    'sector_rotation': '🔄',
    'china_views': '📊',
}

CATEGORY_LABELS = {
    'institutional_views': '外资观点',
    'sector_rotation': '资金流向',
    'china_views': '中国观点',
}


def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {msg}"
    print(line, file=sys.stderr)
    try:
        with open(LOG_PATH, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


def load_unpushed():
    """加载未推送且重要性>=2的文章"""
    if not os.path.exists(DB_PATH):
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT * FROM news
        WHERE pushed = 0 AND importance >= 2
        ORDER BY importance DESC, time DESC, id DESC
        LIMIT 20
    ''')

    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def mark_pushed(article_ids):
    """标记已推送"""
    if not article_ids:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executemany(
        'UPDATE news SET pushed = 1 WHERE article_id = ?',
        [(aid,) for aid in article_ids]
    )
    conn.commit()
    conn.close()


def format_message(item):
    """格式化单条消息"""
    cat = item.get('category', '')
    icon = CATEGORY_ICONS.get(cat, '📰')
    label = CATEGORY_LABELS.get(cat, cat)

    lines = [f'{icon} 【{label}】{item["title"]}']

    # 观点方向（机构观点）
    if item.get('viewpoint'):
        lines.append(f'观点: {item["viewpoint"]}')

    if item.get('time'):
        lines.append(f'时间: {item["time"]}')

    content = item.get('content') or item.get('content_short', '')
    if content:
        summary = content[:200].replace('\n', ' ').strip()
        lines.append(f'摘要: {summary}')

    if item.get('url'):
        lines.append(f'详情: {item["url"]}')

    return '\n'.join(lines)


def push_to_dingtalk(message):
    """发送单条消息到钉钉"""
    try:
        result = subprocess.run(
            [OPENCLAW_BIN, 'message', 'send',
             '--channel', 'dingtalk-connector',
             '--target', DINGTALK_TARGET,
             '--account', '__default__',
             '--message', message],
            capture_output=True, timeout=30
        )
        success = result.returncode == 0
        if not success:
            log(f'钉钉推送失败: {result.stderr.decode()[:200]}')
        return success
    except Exception as e:
        log(f'钉钉推送异常: {e}')
        return False


def main():
    log('开始推送外资观点...')

    items = load_unpushed()

    if not items:
        log('无待推送文章（importance>=2），跳过')
        return

    log(f'共 {len(items)} 条待推送')

    pushed_ids = []
    for i, item in enumerate(items, 1):
        msg = format_message(item)
        log(f'推送 {i}/{len(items)}: {item["title"][:40]} (importance={item.get("importance", 1)})')

        if push_to_dingtalk(msg):
            pushed_ids.append(item['article_id'])
        else:
            continue

    if pushed_ids:
        mark_pushed(pushed_ids)
        log(f'✅ 已推送并标记 {len(pushed_ids)}/{len(items)} 条')

    log('推送完成')


if __name__ == '__main__':
    main()
