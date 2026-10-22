# 到期管家 Expiry Tracker

一个极简的到期事项跟踪小工具：域名、信用卡、会员、订阅、证书……把所有会过期的东西放在一个页面里看全。

单文件 Flask 应用 + SQLite，无前端框架、无构建步骤，打开就能用。

## 功能

- 📅 按到期日自动排序，过期 / 7 天内 / 提醒期内 / 安全，四种状态一目了然
- 🏷️ 分类筛选：域名、信用卡、会员、订阅、证书、其他
- 💰 可记录价格（如 `60/年`）、管理网址（卡片上可直接点进去续费）、备注（去哪续、注意事项）
- 🤖 每条事项可标记「自动任务」（适合配合定时任务/机器人做自动续费或提醒）
- 🔌 提供 `GET /api/items` JSON 接口，方便接自己的提醒脚本
- 📊 顶部统计：已过期数、30 天内到期数、安全数

## 快速开始

### 本地运行

```bash
pip install -r requirements.txt
DB_PATH=./expiry.db python app.py
```

打开 http://127.0.0.1:8283 即可使用。数据保存在 SQLite 文件里（`DB_PATH` 指定，默认 `/data/expiry.db`）。

### Docker 运行

```bash
docker build -t expiry-tracker .
docker run -d --name expiry-tracker -p 8283:8283 -v expiry-data:/data expiry-tracker
```

## 配置

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DB_PATH` | `/data/expiry.db` | SQLite 数据库文件路径 |

端口固定为 `8283`（在 `app.py` 末尾可改）。

## 说明

- 无登录鉴权，设计定位是跑在内网 / NAS / 个人服务器上自用；如需公网访问，请自行加一层反向代理鉴权。
- 删除和自动任务开关是页面上的直接链接，点前会有确认（删除）。

## License

MIT
