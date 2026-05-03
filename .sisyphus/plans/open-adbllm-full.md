# Open-ADBLLM 完整版 Work Plan

## TL;DR

> **目标**：完整 ADB HTTP API + 网页控制台，含 🟢🟡🔴 三级权限、SSE 实时日志、一次性密钥机制、Docker 镜像。
> **交付物**：可运行的完整项目，推送到 GitHub + Docker Hub。
> **预估**：大任务，12-14 个任务，4 波并行。
> **并行执行**：YES，Wave 1-3 内高度并行。

---

## Context

### 原始需求
独立于 Open-AutoGLM 的 ADB HTTP API 项目。不做 VLM 决策，纯 ADB 执行层 + 网页控制台。

### 权限模型（已简化）
- 🟢 绿色: 始终开放，无需认证
- 🟡 黄色: 控制台一键开关控制（`_yellow_enabled` boolean 内存变量）
- 🔴 红色: 一次性 32 位密钥（UUID hex），用一次销毁，60s 过期

### 技术决策
- 复用 `F:/Open-AutoGLM/Open-AutoGLM/phone_agent/adb/` 模块
- FastAPI + uvicorn + Pillow + SSE
- 控制台用 FastAPI serve 静态 HTML + SSE
- Docker `--network host`

### 项目位置
`F:\Open-AutoGLM\Open-ADBLLM\`，仓库 `https://github.com/bomomoQWQ/Open-ADBLLM`

---

## Work Objectives

### Core Objective
完整可用的 ADB HTTP API 服务 + 网页控制台，含三级权限。

### Concrete Deliverables
- `Dockerfile` + `server.py` + `requirements.txt`
- 17 🟢 + 9 🟡 + 3 🔴 API 端点
- 权限装饰器（绿/黄/红）
- 一次性密钥生成/验证/销毁
- 网页控制台：SSE 日志 + 密钥管理 + 黄权限开关 + Basic Auth
- `SKILL.md` 集成文档
- Docker Hub 镜像 `bomomo/open-adbllm`
- GitHub 推送

---

## Verification Strategy

- **Agent-Executed QA**：所有端点 curl 验证
- **截图**：base64 可解码为有效 JPEG
- **触控/按键**：真机实测
- **权限**：无 token → 403，正确 token → 200
- **红色密钥**：无密钥 → 423，控制台生成密钥 → 带密钥重试 → 200 → 密钥作废
- **控制台**：浏览器访问 `/` → Basic Auth → 日志流 + 密钥面板

---

## Execution Strategy

### Parallel Waves

```
Wave 1 (基础，4并行):
├── 1. 骨架 + requirements + .gitignore
├── 2. Dockerfile
├── 3. ADB 模块复用
└── 4. server.py 基础骨架（FastAPI + health + 配置）

Wave 2 (核心 API，4并行):
├── 5. 屏幕 API（screenshot, screen/info）
├── 6. 触控 API（tap, swipe, long-press）
├── 7. 输入 + 按键 API（type, key）
└── 8. 应用 + 设备 API（app/launch, app/current, app/list, device/info）

Wave 3 (权限 + 高级 API，3并行):
├── 9. 权限装饰器（require_level）
├── 10. 🟡 高级 API（reboot, wake, sleep, brightness, wifi, install, uninstall, clear, shell）
└── 11. 🔴 危险 API + 一次性密钥（factory-reset, oem-unlock, root-enable + 密钥生成/验证/销毁）

Wave 4 (控制台 + 文档，2并行):
├── 12. 网页控制台（HTML + SSE日志流 + 黄开关 + 红密钥面板 + Basic Auth）
└── 13. SKILL.md 文档

Wave FINAL (验证):
├── F1. docker build + run + health check
├── F2. 全 API curl 测试
├── F3. 控制台浏览器访问测试
└── F4. GitHub + Docker Hub 推送
```

---

## TODOs

- [ ] 1. 项目骨架

  **What to do**: 创建 `requirements.txt`（FastAPI, uvicorn, Pillow）、`.gitignore`、确认 README.md 需求文档。

  **QA**: `pip install -r requirements.txt` 无报错

  **Parallel**: Wave 1, 与 2/3/4 并行 | **Blocks**: 无 | **Blocked By**: 无
  **Commit**: `chore: project skeleton`

- [ ] 2. Dockerfile

  **What to do**: `FROM python:3.11-slim`, `apt install adb`, 安装依赖 + 复制代码, CMD uvicorn。参考 `F:\Open-AutoGLM\Open-AutoGLM\Dockerfile`。

  **QA**: `docker build` 成功，镜像 < 300MB

  **Parallel**: Wave 1 | **Commit**: `feat: Dockerfile`

- [ ] 3. ADB 模块复用

  **What to do**: 从 `F:\Open-AutoGLM\Open-AutoGLM\phone_agent\adb\` 复制 `__init__.py`, `screenshot.py`, `device.py`, `input.py`, `connection.py`。移除 `config/` 依赖，硬编码 timing 值。

  **Must NOT**: 引入 `model/`, `actions/`, `config/` 模块

  **QA**: `from phone_agent.adb import get_screenshot, tap, swipe, type_text` 无 import error

  **Parallel**: Wave 1 | **Commit**: `feat: port ADB module`

- [ ] 4. server.py 基础骨架

  **What to do**: FastAPI app, 环境变量加载（ADBLLM_PORT, ADBLLM_CONSOLE_USER, ADBLLM_CONSOLE_PASS），`GET /health` 检查 ADB + 设备，CORS 全开。

  **QA**: `curl /health` → `{"status":"ok","adb_available":true,"device_connected":true}`

  **Parallel**: Wave 1 | **Commit**: `feat: server skeleton + health`

- [ ] 5. 屏幕 API

  **What to do**: `GET /screenshot` 调 `get_screenshot()` 返回 `{image, width, height}`。`GET /screen/info` 调 `adb shell wm size/density`。

  **QA**: `/screenshot` → 200 + 有效 JPEG base64。`/screen/info` → `{width, height, dpi}`

  **Parallel**: Wave 2 | **Commit**: `feat: screenshot + screen info`

- [ ] 6. 触控 API

  **What to do**: `POST /tap {x,y}`, `POST /swipe {start,end,duration?}`, `POST /long-press {x,y,duration?}`。用原始屏幕尺寸做坐标映射。

  **QA**: 真机 tap 计算器数字键 → 显示数字；swipe → 页面滑动

  **Parallel**: Wave 2 | **Commit**: `feat: touch APIs`

- [ ] 7. 输入 + 按键 API

  **What to do**: `POST /type {text}` → `type_text(text)`（需 ADB Keyboard）。`POST /key {key}` → 映射 keycode 表。

  **QA**: type "hello" → 输入框出现；key "home" → 回桌面

  **Parallel**: Wave 2 | **Commit**: `feat: input + key APIs`

- [ ] 8. 应用 + 设备 API

  **What to do**: `POST /app/launch {package}`, `GET /app/current`, `GET /app/list`, `GET /device/info`（型号/版本/电量）。

  **QA**: launch 设置 → 手机打开设置；device/info → 返回真实信息

  **Parallel**: Wave 2 | **Commit**: `feat: app + device info APIs`

- [ ] 9. 权限控制

  **What to do**:
  - 黄色开关：`_yellow_enabled = True` 内存变量，控制台可切换
  - 黄色 API 加 `@require_yellow` 装饰器，关闭时返回 403
  - 红色密钥：`_red_keys: dict[str, float]`（key → expiry）
  - `POST /admin/gen-key` → 生成 `uuid4().hex`，60s 有效期，返回密钥
  - 红色 API 加 `@require_red`，验证后立即销毁密钥

  **QA**: 黄色关闭 → 黄色 API 403；黄色开启 → 200。红色无密钥 → 423；正确密钥 → 200 → 再调 → 403

  **Parallel**: Wave 3 | **Commit**: `feat: permission system (yellow toggle + red one-time key)`

- [ ] 10. 🟡 高级 API

  **What to do**: 所有黄色 API 加 `@require_yellow`。
  - reboot/wake/sleep → `input keyevent 26/223/224`
  - brightness → `settings put system screen_brightness`
  - wifi toggle → `svc wifi enable/disable`
  - install/uninstall/clear → `adb install/uninstall/pm clear`
  - shell → `subprocess.run(adb_prefix + ["shell"] + cmd)`

  **QA**: 控制台关黄色 → 403；开黄色 → 正常执行

  **Parallel**: Wave 3 | **Commit**: `feat: advanced (yellow) APIs`

- [ ] 11. 🔴 危险 API + 一次性密钥

  **What to do**:
  - 密钥存储：`_red_keys: dict[str, float]` （key → expiry timestamp, 60s 过期）
  - `POST /admin/gen-key`：生成 `uuid4().hex`，存内存，返回密钥
  - 红色 API 加 `@require_level("red")`
  - 验证通过后立即 `del _red_keys[key]`（一次性）
  - 密钥过期后自动清理

  **QA**: 无密钥调红色 API → 423；控制台生成密钥 → 带密钥重试 → 200 → 再次调 → 403

  **Parallel**: Wave 3 | **Commit**: `feat: danger (red) APIs + one-time key`

- [ ] 12. 网页控制台

  **What to do**:
  - `GET /` 返回静态 HTML 控制台页面
  - Basic Auth：如果设了 CONSOLE_USER/PASS，FastAPI middleware 鉴权
  - SSE `/stream`：`asyncio.Queue` 收集所有 `print()` → 推送到前端
  - HTML 内嵌：左侧日志流、右侧黄权限开关 + 红色密钥面板
  - 密钥面板：一键生成 → 显示密钥 → 复制按钮 → 60s 倒计时

  **QA**: 浏览器访问 `/` → Basic Auth → 看到日志流 → 点击生成密钥 → 显示 32 位密钥

  **Parallel**: Wave 4 | **Commit**: `feat: web console with SSE + key management`

- [ ] 13. SKILL.md 文档

  **What to do**: 参照 `F:\Open-AutoGLM\Open-AutoGLM\SKILL.md` 格式，写 Open-ADBLLM 的 skill 集成文档。包含 API 列表、Python 调用示例、权限说明。

  **QA**: 文档可读，所有端点有使用示例

  **Parallel**: Wave 4 | **Commit**: `docs: SKILL.md`

---

## Final Verification Wave

- [ ] F1. `docker build -t open-adbllm .` → 成功
- [ ] F2. `docker run` + `curl /health` → ok
- [ ] F3. 全 API 功能测试（curl 脚本批量）
- [ ] F4. 控制台浏览器测试（截图）
- [ ] F5. `docker push bomomo/open-adbllm:latest`
- [ ] F6. `git push` → GitHub

---

## Commit Strategy

每个 task 独立 commit，final 后打 tag `v1.0.0`。

## Success Criteria

- [ ] 所有 29 个 API 可访问且功能正常
- [ ] 黄权限开关正确控制（关闭→403，开启→200）
- [ ] 红色密钥生成→使用→销毁完整闭环
- [ ] 一次性密钥 60s 过期自动失效
- [ ] 控制台可登录、可看日志、可管理权限和密钥
- [ ] Docker 镜像已推送
- [ ] GitHub 仓库已更新
