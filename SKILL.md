# Open-ADBLLM Skill

Open-ADBLLM 是一个 ADB 命令 HTTP API，为上位 Agent 提供手机底层操控能力。截图、点击、滑动、打字等操作全部封装为 REST 端点。

> ⚠️ Open-ADBLLM **不做决策**——只负责执行 ADB 指令。需要上位 Agent 有视觉能力，看图后决定每一步操作。

## ⚠️ 地址配置

| 上位 Agent 在哪 | 用的地址 |
|---|---|
| Docker 同宿主机 | `172.17.0.1:8000`（默认 bridge 网关） |
| 非 Docker / 同机 | `localhost:8000` |
| 远程 | 宿主机内网 IP |

## API 文档

### 🟢 基础操作（始终开放）

#### 截图

```bash
GET /screenshot
→ {"image": "base64...", "width": 720, "height": 1602}
```

截图已压缩为 720p JPEG，可直接 base64 decode 后送给视觉模型。

#### 屏幕信息

```bash
GET /screen/info
→ {"width": 1080, "height": 2400, "dpi": 420}
```

#### 触控

```bash
POST /tap         {"x": 500, "y": 800}
POST /swipe       {"start": [500,800], "end": [500,200], "duration": 300}
POST /long-press  {"x": 500, "y": 800, "duration": 1000}
```

坐标：像素坐标，以 `/screen/info` 返回的分辨率为准。

#### 输入

```bash
POST /type  {"text": "hello"}   # 需 ADB Keyboard
POST /key   {"key": "home"}     # back/home/recent/power/volume_up/volume_down/enter
```

#### 应用

```bash
POST /app/launch  {"package": "com.android.settings"}
GET  /app/current  → {"package": "com.android.settings"}
GET  /app/list     → {"packages": [...]}
```

#### 设备

```bash
GET /device/info  → {"model": "...", "android_version": "...", "battery": "..."}
GET /health       → {"status":"ok", "adb_available":true}
```

### 🟡 高级操作（需控制台开关，否则 403）

```bash
POST /device/wake        # 唤醒
POST /device/sleep       # 熄屏
POST /device/reboot      # 重启
POST /device/brightness  {"level": 128}
POST /wifi/toggle        # WiFi 开关
POST /app/uninstall      {"package": "xxx"}
POST /app/clear          {"package": "xxx"}
POST /shell              {"command": "ls /sdcard"}
```

### 🔴 危险操作（需一次性密钥）

1. 到控制台生成密钥
2. `Authorization: Bearer <密钥>`

```bash
POST /device/factory-reset
POST /oem/unlock
POST /root/enable
```

## Python 调用示例

```python
import requests, base64
from io import BytesIO
from PIL import Image

BASE = os.getenv("ADBLLM_URL", "http://172.17.0.1:8000")

def screenshot():
    r = requests.get(f"{BASE}/screenshot", timeout=10)
    r.raise_for_status()
    data = r.json()
    img = Image.open(BytesIO(base64.b64decode(data["image"])))
    return img, data["width"], data["height"]

def tap(x, y):
    requests.post(f"{BASE}/tap", json={"x": x, "y": y}, timeout=5)

def swipe(start, end, duration=300):
    requests.post(f"{BASE}/swipe", json={"start": start, "end": end, "duration": duration}, timeout=5)

def key(k):
    requests.post(f"{BASE}/key", json={"key": k}, timeout=5)

def type_text(text):
    requests.post(f"{BASE}/type", json={"text": text}, timeout=5)

# 示例：打开设置
img, w, h = screenshot()        # 截图
# ... 上位 Agent 看图，分析坐标 ...
tap(125, 560)                    # 点设置图标
key("home")                      # 回到桌面
```

## 典型工作流

```
1. screenshot() → 拿到手机截图，送给视觉模型
2. 视觉模型分析："需点击设置图标，坐标 [125,560]"
3. tap(125, 560) → 点击
4. screenshot() → 确认页面已变化
5. 继续下一步或结束
```

## 注意事项

1. 坐标以像素为单位，调用 `/screen/info` 获取当前分辨率
2. `/type` 需要 ADB Keyboard 已安装并启用
3. 上位 Agent **必须有视觉能力**——本服务只负责执行，不负责看图
4. 黄色操作需要去控制台 `http://<host>:8000/` 手动开启开关
5. 红色操作需要到控制台生成一次性 32 位密钥
