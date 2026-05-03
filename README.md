# Open-ADBLLM

> ADB 命令 HTTP API + 网页控制台，为上游 AI Agent 提供手机底层操控能力。

```
上位 Agent (视觉模型) ── HTTP ──► Open-ADBLLM ── ADB ──► 📱
                                  │
                                  └── 网页控制台 (开关/密钥/日志)
```

## 项目介绍

Open-ADBLLM 是一个轻量级 ADB 命令 HTTP 服务。与Open_AutoGLM不同，它**不做 VLM 决策**——只负责执行 ADB 指令。截图、点击、滑动、打字等操作全部封装为 REST API，交给有视觉能力的上游 AI Agent 来决策。(原理上来说，你似乎可以让你的Agent帮你root？🤔)

> **本人没有多模态模型测试此 Skill（悲），欢迎测试提交 PR 喵~**

**典型工作流**：

```
1. 上位 Agent: GET /screenshot          → 拿到手机截图
2. 上位 Agent: 看图，决定点"设置"图标  → 坐标 [125, 560]
3. 上位 Agent: POST /tap {x:125,y:560} → 点击
4. 上位 Agent: GET /screenshot          → 确认进入设置页
5. 上位 Agent: 任务完成
```

## 懒人版快速安装

使用 AI 编程助手（如 Claude Code）：

```
访问文档，为我安装 Open-ADBLLM
https://raw.githubusercontent.com/bomomoQWQ/Open-ADBLLM/refs/heads/main/README.md
```

## 宿主机准备

```bash
# Linux: 安装 ADB
sudo apt install adb -y

# 启动 ADB server
adb start-server

# 手机 USB 连接后确认
adb devices
# → 应看到设备:  xxxxxx   device
```

手机上需要开启 **USB 调试** 和 **USB 调试（安全设置）**。文本输入需要安装 [ADB Keyboard](https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk)。

## Docker 部署（推荐 🐳）

```bash
docker pull bomomo/open-adbllm:latest

docker run -d --network host \
  --name adbllm \
  --restart unless-stopped \
  -e ADBLLM_PORT=8000 \
  -e ADBLLM_CONSOLE_USER=admin \
  -e ADBLLM_CONSOLE_PASS=<密码> \
  bomomo/open-adbllm:latest
```

`--network host` 使容器内 adb 客户端直连宿主机 adb server（127.0.0.1:5037）。

### 验证

```bash
curl http://localhost:8000/health
# → {"status":"ok","adb_available":true,"device_connected":true}
```

浏览器访问 `http://<宿主机IP>:8000/` 进入网页控制台。

---

## API 文档

### 🟢 基础操作（始终开放，无需认证）

#### 屏幕

**截图**

```bash
GET /screenshot
```

```json
{"image": "/9j/4AAQSkZJRg...", "width": 720, "height": 1602}
```

截图自动压缩为 720p JPEG（约 ~160 token），与原图视觉无差异。

**屏幕信息**

```bash
GET /screen/info
```

```json
{"width": 1080, "height": 2400, "dpi": 420}
```

#### 触控

```bash
POST /tap         {"x": 500, "y": 800}
POST /swipe       {"start": [500, 800], "end": [500, 200], "duration": 300}
POST /long-press  {"x": 500, "y": 800, "duration": 1000}
```

坐标：像素坐标，以原始屏幕分辨率（从 `/screen/info` 获取）为准。

#### 输入

```bash
POST /type  {"text": "hello"}    # 需已点击输入框聚焦，需 ADB Keyboard
POST /key   {"key": "home"}      # back/home/recent/power/volume_up/volume_down/enter
```

#### 应用

```bash
POST /app/launch  {"package": "com.android.settings"}    # 启动应用
GET  /app/current                                        # 当前前台 App
GET  /app/list                                           # 已安装应用列表
```

#### 设备

```bash
GET /device/info    # 型号、安卓版本、电量
GET /health         # ADB 状态
```

### 🟡 高级操作（需控制台开启黄级权限）

所有黄色 API 需先在控制台打开 🟡 开关，否则返回 `403`。

```bash
POST /device/wake        # 唤醒屏幕
POST /device/sleep       # 熄屏
POST /device/reboot      # 重启
POST /device/brightness  {"level": 128}           # 调亮度 (0-255)
POST /wifi/toggle                                 # WiFi 开关
POST /app/uninstall      {"package": "xxx"}       # 卸载
POST /app/clear          {"package": "xxx"}       # 清除数据
POST /shell              {"command": "ls /sdcard"} # 执行 shell
```

### 🔴 危险操作（需一次性 32 位密钥）

1. 到控制台点击"生成一次性密钥"
2. 带密钥调用：`Authorization: Bearer <密钥>`
3. 密钥使用一次后立即销毁，60s 未使用自动过期

```bash
POST /device/factory-reset    # 恢复出厂
POST /oem/unlock              # OEM 解锁
POST /root/enable             # 开启 root
```

被拒时返回 `423 Locked`。

---

## 权限模型

```
🟢 绿色: 无需认证，始终开放
🟡 黄色: 控制台滑块开关（_yellow_enabled 内存变量）
🔴 红色: Header Authorization: Bearer <一次性32位密钥>
```

| 权限级别 | 控制方式 | 有效期 |
|---|---|---|
| 绿 | 无 | 永久 |
| 黄 | 网页控制台开关 | 直到手动关闭 |
| 红 | 控制台生成密钥 + API Header | 一次性，60s 过期 |

---

## 网页控制台

访问 `http://<host>:8000/`：

- 🎨 暗色主题，中英文双语切换
- 📜 实时 SSE 日志流 + 时间戳
- 🟡 黄色权限：滑块开关
- 🔴 红色密钥：一键生成 → 32 位密钥 → 60s 倒计时 → 自动清除
- 🔒 Basic Auth 保护（通过 `ADBLLM_CONSOLE_USER` / `ADBLLM_CONSOLE_PASS` 设置）

---

## 环境变量

| 变量 | 必填 | 说明 | 默认值 |
|---|---|---|---|
| `ADBLLM_PORT` | 否 | HTTP 监听端口 | `8000` |
| `ADBLLM_CONSOLE_USER` | 否 | 控制台用户名 | 空（无认证） |
| `ADBLLM_CONSOLE_PASS` | 否 | 控制台密码 | 空（无认证） |

---

## Python 调用示例

> 📦 上位 Agent 集成用 Skill 包：`Open-ADBLLM_Skill.zip`（含 SKILL.md）。可直接导入 AstrBot 等平台使用。

```python
import requests, base64
from io import BytesIO
from PIL import Image

BASE = "http://localhost:8000"

# 截图
r = requests.get(f"{BASE}/screenshot")
data = r.json()
img = Image.open(BytesIO(base64.b64decode(data["image"])))
print(f"Screenshot: {data['width']}x{data['height']}")

# 点击
requests.post(f"{BASE}/tap", json={"x": 500, "y": 800})

# 按键
requests.post(f"{BASE}/key", json={"key": "home"})

# 唤醒（需黄色权限开启）
requests.post(f"{BASE}/device/wake")

# 危险操作（需红色密钥）
requests.post(f"{BASE}/oem/unlock",
    headers={"Authorization": "Bearer <one-time-key>"})
```

---

## 项目结构

```
Open-ADBLLM/
├── server.py               # FastAPI 入口（全部逻辑）
├── Dockerfile               # Docker 构建
├── requirements.txt         # 依赖
├── phone_agent/
│   ├── adb/                 # ADB 模块（截图/触控/输入/连接）
│   │   ├── screenshot.py    # 截图 → 720p JPEG
│   │   ├── device.py        # 点击/滑动/返回/Home
│   │   ├── input.py         # 文本输入/ADB Keyboard
│   │   └── connection.py    # ADB 连接管理
│   └── config/              # 应用包名映射 + 时序配置
├── .sisyphus/               # 工作规划
│   ├── drafts/              # 需求草稿
│   └── plans/               # 完整版工作计划
└── README.md
```

---

## 常见问题

### 设备未找到

```bash
adb kill-server && adb start-server
adb devices
```

检查 USB 调试开启、数据线支持数据传输、手机上已授权。

### 文本输入不工作

安装 ADB Keyboard 并启用：

```bash
adb shell ime enable com.android.adbkeyboard/.AdbIME
```

### 截图黑屏

支付/银行等敏感页面会自动返回黑屏。正常现象。

### 与传统 Phone Agent 的区别

| | 传统 Phone Agent | Open-ADBLLM |
|---|---|---|
| 谁做决策 | 内置 VLM | 上位 Agent |
| 使用方法 | 发自然语言任务 | 逐步调用 API |
| 适用模型 | 任意 VLM | 任意带视觉的模型 |
| 复杂度 | 高（prompt/解析/循环检测） | 低（纯透传） |

---

## 构建镜像

```bash
docker build -t open-adbllm .
```

## License

[MIT License](LICENSE)
