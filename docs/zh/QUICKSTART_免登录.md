# 快速启动指南 - 免登录用户系统

## 🚀 5分钟快速开始

### 第一步：启动服务器

```bash
# 在终端中执行（确保在项目根目录）
cd /Users/ericren/projects/chat/voice-assistant
uvicorn app.server:app --reload
```

看到这样的输出表示成功：
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process...
INFO:     Started server process...
```

### 第二步：打开前端界面

在浏览器中打开 `chat-ui.html` 文件：
```
file:///Users/ericren/projects/chat/voice-assistant/chat-ui.html
```

或者直接在 Finder 中双击 `chat-ui.html` 文件。

### 第三步：开始使用

1. 页面会自动创建你的匿名用户账号
2. 尝试说："Add coffee to my collection"（添加咖啡到我的集合）
3. 然后说："I consumed 2 coffees"（我喝了2杯咖啡）
4. 查看统计："How much coffee have I consumed?"（我喝了多少咖啡？）

### 第四步：验证数据持久化

1. 关闭浏览器
2. 重新打开 `chat-ui.html`
3. 你会看到之前添加的所有数据还在！

## 🎯 核心特性演示

### 功能1：多用户数据隔离

**测试步骤：**
1. 在 Chrome 正常模式下：添加 "coffee" 和 "tea"
2. 在 Chrome 隐身模式下：添加 "milk" 和 "juice"
3. 观察：两个窗口显示完全不同的数据

### 功能2：数据持久化

**测试步骤：**
1. 添加一些collections和transactions
2. 完全关闭浏览器
3. 重新打开，数据依然存在

### 功能3：自动用户识别

**测试步骤：**
1. 打开浏览器开发者工具（F12）
2. 查看 Application > Cookies
3. 找到 `device_id` cookie
4. 这就是你的用户标识

## 📱 API 测试

### 查看当前用户信息

```bash
curl -X GET http://localhost:8000/api/user/me \
  -H "Cookie: device_id=YOUR_DEVICE_ID" \
  | jq
```

### 获取collections

```bash
curl -X GET http://localhost:8000/collections \
  -H "Cookie: device_id=YOUR_DEVICE_ID" \
  | jq
```

### 发送聊天消息

```bash
curl -X POST 'http://localhost:8000/chat?message=Add%20coffee&lang=en' \
  -H "Cookie: device_id=YOUR_DEVICE_ID" \
  | jq
```

## 🗄️ 查看数据库

### 使用SQLite命令行

```bash
# 打开数据库
sqlite3 data/users.db

# 查看所有用户
SELECT device_id, created_at, last_seen, session_count FROM anonymous_users;

# 查看所有collections
SELECT * FROM collections;

# 查看所有transactions
SELECT * FROM transactions;

# 退出
.quit
```

### 使用图形界面（可选）

推荐工具：
- [DB Browser for SQLite](https://sqlitebrowser.org/) （免费）
- [TablePlus](https://tableplus.com/) （免费版）

直接打开 `data/users.db` 文件即可查看和编辑数据。

## 🌍 支持的语言

### 英文示例
```
"Add coffee to my collection"
"I consumed 2 coffees"
"How much coffee did I consume?"
"Show me statistics"
```

### 中文示例
```
"添加咖啡到我的集合"
"我喝了2杯咖啡"
"我喝了多少咖啡？"
"显示统计数据"
```

## 📊 查看实时状态

### 服务器健康检查
```bash
curl http://localhost:8000/health
```

### 用户统计（所有用户）
访问：http://localhost:8000/api/analytics/dashboard

或使用 curl：
```bash
curl http://localhost:8000/api/analytics/dashboard | jq
```

## 🔧 常见问题

### Q1: 浏览器显示连接失败
**A:** 确保后端服务器正在运行（执行步骤一）

### Q2: 数据没有保存
**A:** 检查浏览器是否允许Cookie，查看开发者工具的控制台是否有错误

### Q3: 如何重置所有数据
**A:** 删除 `data/users.db` 文件，重启服务器即可

### Q4: 如何清除我自己的数据
**A:** 在聊天界面说 "clear all data" 或 "清除所有数据"

### Q5: 可以在多个浏览器中使用吗？
**A:** 可以！每个浏览器会被识别为不同的用户，数据完全独立

## 🎨 自定义配置

### 修改Cookie过期时间

编辑 `app/user_session.py`：
```python
class UserSessionManager:
    def __init__(self):
        # ...
        self.cookie_max_age = 30 * 24 * 60 * 60  # 改为你想要的秒数
```

### 修改数据库位置

编辑 `app/database.py`：
```python
class Database:
    def __init__(self, db_path: str = "data/users.db"):  # 改为你想要的路径
```

### 修改API端口

启动服务器时指定：
```bash
uvicorn app.server:app --reload --port 8080
```

## 📖 下一步

- 查看 `免登录系统使用说明.md` 了解详细功能
- 查看 `更新说明.md` 了解技术细节
- 访问 http://localhost:8000/docs 查看完整API文档

## 🆘 需要帮助？

如果遇到问题：
1. 查看服务器终端的错误日志
2. 查看浏览器开发者工具的控制台
3. 检查 `data/` 目录是否有写入权限
4. 确认Python版本 >= 3.8

---

**提示**: 这是一个开发环境的快速启动指南。生产环境部署请参考 `免登录系统使用说明.md` 中的部署章节。
