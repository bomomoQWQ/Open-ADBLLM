# Open-ADBLLM

ADB 命令 HTTP API + 网页控制台，为上游 AI Agent 提供手机底层操控能力。

```
上级 Agent ── HTTP ──► Open-ADBLLM ── ADB ──► 📱
                        │
                        └── 网页控制台 (开关/密钥/日志)
```

## 功能模块

### 🟢 基础操作（始终开放）

| 模块 | API | 说明 |
|---|---|---|
| 屏幕 | `GET /screenshot` | 返回 base64 JPEG（720p） |
| 屏幕 | `GET /screen/info` | 分辨率、DPI |
| 触控 | `POST /tap` | `{x, y}` |
| 触控 | `POST /swipe` | `{start, end, duration?}` |
| 触控 | `POST /long-press` | `{x, y, duration?}` |
| 输入 | `POST /type` | `{text}` 文本输入 |
| 按键 | `POST /key` | `{key: "back"/"home"/"recent"/"power"/"volume_up"/"volume_down"/"enter"}` |
| 应用 | `POST /app/launch` | `{package}` 启动 |
| 应用 | `GET /app/current` | 当前前台 App |
| 应用 | `GET /app/list` | 已安装应用列表 |
| 设备 | `GET /device/info` | 型号、安卓版本、电量 |
| 系统 | `GET /health` | ADB 连接状态 + 设备信息 |

### 🟡 高级操作（控制台开关控制）

| 模块 | API | 说明 |
|---|---|---|
| 设备 | `POST /device/reboot` | 重启 |
| 设备 | `POST /device/wake` | 唤醒 |
| 设备 | `POST /device/sleep` | 熄屏 |
| 设备 | `POST /device/brightness` | `{level: 0-255}` |
| 网络 | `POST /wifi/toggle` | WiFi 开关 |
| 应用 | `POST /app/install` | 安装 APK |
| 应用 | `POST /app/uninstall` | 卸载 `{package}` |
| 应用 | `POST /app/clear` | 清除数据 `{package}` |
| 系统 | `POST /shell` | 执行 adb shell（沙箱范围） |

### 🔴 危险操作（需一次性 32 位密钥）

| 模块 | API | 说明 |
|---|---|---|
| 设备 | `POST /device/factory-reset` | 恢复出厂 |
| 系统 | `POST /oem/unlock` | OEM 解锁 |
| 系统 | `POST /root/enable` | 开启 root |

---

## 权限模型

```
🟢 绿色: 无需认证，始终开放
🟡 黄色: 控制台一键开关，关闭时返回 403
🔴 红色: Header Authorization: Bearer <一次性32位密钥>
```

> **红色密钥**：由控制台实时生成（`uuid4().hex`），60 秒有效，用一次即销毁。

## 网页控制台

- `/` — 单页控制台，Basic Auth 保护
- 实时 SSE 日志流
- 🟡 黄色权限：一键开关按钮
- 🔴 红色密钥区：生成密钥 + 复制 + 60s 倒计时

## 环境变量

| 变量 | 必填 | 说明 |
|---|---|---|
| `ADBLLM_PORT` | 否 | HTTP 端口（默认 8000） |
| `ADBLLM_CONSOLE_USER` | 否 | 控制台用户名（不设则无认证） |
| `ADBLLM_CONSOLE_PASS` | 否 | 控制台密码 |

## 技术栈

- Python 3.11 + FastAPI + uvicorn
- Pillow（截图压缩）
- ADB 层复用 `phone_agent/adb/`
- Docker 部署，`--network host`

## 部署

```bash
docker run -d --network host \
  --name adbllm \
  -e ADBLLM_PORT=8000 \
  -e ADBLLM_CONSOLE_USER=admin \
  -e ADBLLM_CONSOLE_PASS=<密码> \
  bomomo/open-adbllm:latest
```

## 开发

```bash
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
docker build -t open-adbllm .
```
