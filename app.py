#!/usr/bin/env python3
"""到期管家 - 简单的到期事项跟踪"""
import sqlite3
import os
from datetime import datetime, date
from urllib.parse import urlparse
from flask import Flask, request, jsonify, render_template_string, redirect

DB = os.environ.get("DB_PATH", "/data/expiry.db")
app = Flask(__name__)

CATEGORIES = {
    "domain": "域名",
    "credit_card": "信用卡",
    "membership": "会员",
    "subscription": "订阅",
    "certificate": "证书",
    "other": "其他",
}

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'other',
            expiry_date TEXT NOT NULL,
            notes TEXT DEFAULT '',
            reminder_days INTEGER DEFAULT 30,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        conn.execute("ALTER TABLE items ADD COLUMN url TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE items ADD COLUMN price TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE items ADD COLUMN auto_task INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def get_status(expiry_str, reminder_days=30):
    exp = datetime.strptime(expiry_str, "%Y-%m-%d").date()
    today = date.today()
    delta = (exp - today).days
    if delta < 0:
        return "expired", delta
    elif delta <= 7:
        return "critical", delta
    elif delta <= reminder_days:
        return "approaching", delta
    else:
        return "upcoming", delta

HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>到期管家</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#f5f6f8;color:#222;max-width:900px;margin:0 auto;padding:16px}
h1{font-size:22px;margin-bottom:4px}
.sub{color:#888;font-size:13px;margin-bottom:16px}
.stats{display:flex;gap:10px;margin-bottom:16px}
.stat{flex:1;background:#fff;border-radius:10px;padding:12px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.stat .n{font-size:24px;font-weight:700}
.stat .l{font-size:12px;color:#888}
.stat.red .n{color:#e5484d}.stat.amber .n{color:#f5a623}.stat.green .n{color:#2da44e}
.card{background:#fff;border-radius:10px;padding:10px 14px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid #ccc}
.card.expired{border-color:#e5484d}.card.critical{border-color:#e5484d}.card.approaching{border-color:#f5a623}.card.upcoming{border-color:#2da44e}
.card .line1{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.card .name{font-weight:600;font-size:15px}
.card .cat{font-size:12px;background:#eef;color:#448;padding:2px 8px;border-radius:10px;white-space:nowrap}
.card .date{font-size:13px;color:#666;white-space:nowrap}
.card .days{font-weight:700;font-size:13px;white-space:nowrap}
.card .days.expired,.card .days.critical{color:#e5484d}
.card .days.approaching{color:#d48806}
.card .days.upcoming{color:#2da44e}
.card .url{font-size:13px;color:#1688d4;text-decoration:none;white-space:nowrap}
.card .url:hover{text-decoration:underline}
.card .line2{display:flex;align-items:baseline;gap:8px;margin-top:4px}
.card .notes{font-size:13px;color:#666;flex:1;white-space:pre-wrap}
.card .del{font-size:12px;color:#aaa;text-decoration:none;white-space:nowrap}
.card .del:hover{color:#e5484d}
.card .price{font-size:12px;color:#b26a00;background:#fff7e6;border-radius:6px;padding:2px 8px;white-space:nowrap}
.card .autobadge{font-size:13px;white-space:nowrap;cursor:default}
.card .autotoggle{font-size:12px;color:#1688d4;text-decoration:none;white-space:nowrap;margin-right:10px}
.cats{margin-bottom:12px;display:flex;gap:8px;flex-wrap:wrap}
.cats a{font-size:13px;color:#666;background:#fff;border-radius:16px;padding:5px 14px;text-decoration:none;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.cats a.on{background:#1688d4;color:#fff}
form.add{background:#fff;border-radius:10px;padding:16px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
form.add h3{margin-bottom:10px;font-size:15px}
form.add .row{display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap}
form.add input,form.add select,form.add textarea{padding:8px;border:1px solid #ddd;border-radius:6px;font-size:14px}
form.add input[name=name]{flex:2;min-width:150px}
form.add select{flex:1;min-width:100px}
form.add input[type=date]{flex:1;min-width:130px}
form.add input[name=url]{width:100%}
form.add textarea{width:100%;height:56px;resize:vertical}
form.add button{background:#1688d4;color:#fff;border:0;padding:9px 20px;border-radius:6px;font-size:14px;cursor:pointer}
.empty{text-align:center;color:#999;padding:30px}
</style>
</head>
<body>
<h1>📅 到期管家</h1>
<div class="sub">域名 · 信用卡 · 会员 · 证书，一个地方看全</div>

<div class="stats">
<div class="stat red"><div class="n">{{counts.expired}}</div><div class="l">已过期</div></div>
<div class="stat amber"><div class="n">{{counts.critical + counts.approaching}}</div><div class="l">30天内到期</div></div>
<div class="stat green"><div class="n">{{counts.upcoming}}</div><div class="l">安全</div></div>
</div>

<div class="cats">
<a href="/" class="{% if not cat %}on{% endif %}">全部</a>
{% for k,v in categories.items() %}<a href="/?cat={{k}}" class="{% if cat==k %}on{% endif %}">{{v}}</a>{% endfor %}
</div>

<form class="add" method="post" action="/add">
<h3>➕ 添加事项</h3>
<div class="row">
<input name="name" placeholder="名称，如 example.com" required>
<select name="category">
{% for k,v in categories.items() %}<option value="{{k}}">{{v}}</option>{% endfor %}
</select>
<input type="date" name="expiry_date" required>
<input name="price" placeholder="价格，如 60/年" style="flex:1;min-width:90px">
</div>
<div class="row">
<input name="url" placeholder="管理网址，如 https://example.com/admin（选填，卡片上可直接点进去）">
</div>
<div class="row">
<textarea name="notes" placeholder="备注：去哪里续、注意事项…"></textarea>
</div>
<button type="submit">添加</button>
</form>

{% for it in items %}
<div class="card {{it.status}}">
<div class="line1">
<span class="name">{{it.name}}</span><span class="cat">{{categories[it.category]}}</span>
<span class="date">到期 {{it.expiry_date}}</span>
<span class="days {{it.status}}">{{it.days_text}}</span>
{% if it.price %}<span class="price">{{it.price}}</span>{% endif %}
{% if it.auto_task %}<span class="autobadge" title="已设置自动任务">🤖</span>{% endif %}
{% if it.url %}<a class="url" href="{{it.url}}" target="_blank" rel="noopener">🌐 {{it.url_host}}</a>{% endif %}
</div>
<div class="line2">
{% if it.notes %}<span class="notes">{{it.notes}}</span>{% else %}<span class="notes"></span>{% endif %}
<a class="autotoggle" href="/toggle_auto/{{it.id}}">{% if it.auto_task %}🤖自动任务·开{% else %}设自动任务{% endif %}</a>
<a class="del" href="/delete/{{it.id}}" onclick="return confirm('删除 {{it.name}}？')">删除</a>
</div>
</div>
{% endfor %}
{% if not items %}<div class="empty">还没有事项，从上面添加第一个吧</div>{% endif %}
</body>
</html>
"""

@app.route("/")
def index():
    conn = get_db()
    cat = request.args.get("cat", "")
    if cat in CATEGORIES:
        rows = conn.execute("SELECT * FROM items WHERE category=? ORDER BY expiry_date", (cat,)).fetchall()
    else:
        cat = ""
        rows = conn.execute("SELECT * FROM items ORDER BY expiry_date").fetchall()
    conn.close()
    items = []
    counts = {"expired": 0, "critical": 0, "approaching": 0, "upcoming": 0}
    for r in rows:
        status, delta = get_status(r["expiry_date"], r["reminder_days"] or 30)
        counts[status] += 1
        if delta < 0:
            days_text = f"已过期 {-delta} 天"
        elif delta == 0:
            days_text = "今天到期！"
        else:
            days_text = f"剩 {delta} 天"
        url = (r["url"] or "").strip() if "url" in r.keys() else ""
        items.append({
            "id": r["id"], "name": r["name"], "category": r["category"],
            "expiry_date": r["expiry_date"], "notes": r["notes"] or "",
            "url": url, "url_host": urlparse(url).netloc if url else "",
            "price": (r["price"] or "").strip() if "price" in r.keys() else "",
            "auto_task": r["auto_task"] if "auto_task" in r.keys() and r["auto_task"] else 0,
            "status": status, "days_text": days_text,
        })
    # 排序：过期和临期在前
    order = {"expired": 0, "critical": 1, "approaching": 2, "upcoming": 3}
    items.sort(key=lambda x: order[x["status"]])
    return render_template_string(HTML, items=items, counts=counts, categories=CATEGORIES, cat=cat)

@app.route("/add", methods=["POST"])
def add():
    conn = get_db()
    conn.execute(
        "INSERT INTO items (name, category, expiry_date, notes, url, price) VALUES (?,?,?,?,?,?)",
        (request.form["name"], request.form.get("category", "other"),
         request.form["expiry_date"], request.form.get("notes", ""),
         request.form.get("url", "").strip(), request.form.get("price", "").strip()),
    )
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/delete/<int:item_id>")
def delete(item_id):
    conn = get_db()
    conn.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/toggle_auto/<int:item_id>")
def toggle_auto(item_id):
    conn = get_db()
    conn.execute("UPDATE items SET auto_task = 1 - COALESCE(auto_task, 0) WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer or "/")

@app.route("/api/items")
def api_items():
    conn = get_db()
    rows = conn.execute("SELECT * FROM items ORDER BY expiry_date").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8283)
