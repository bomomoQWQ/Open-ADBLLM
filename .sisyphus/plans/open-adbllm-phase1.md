# Open-ADBLLM Phase 1 Work Plan

## TL;DR

> **目标**：搭建项目骨架 + Dockerfile + 🟢 绿色 API（17 个端点），使上游 Agent 能通过 HTTP 操控手机。
> **交付物**：可运行的 Docker 镜像，`GET /health` 和 `GET /screenshot` 可用。
> **预估**：中等工作量，6-8 个任务，可并行。

---

## Context

### 原始需求
用户需要一个**独立于 Open-AutoGLM** 的 ADB 命令 HTTP API 项目。与 Open-AutoGLM 不同，不做 VLM 决策，只做 ADB 执行层，交给有视觉能力的上级 Agent（如 GPT-4V）来决策。

### 技术决策
- 复用 `F:/Open-AutoGLM/Open-AutoGLM/phone_agent/adb/` 的 ADB 模块（已验证生产可用）
- FastAPI + uvicorn，和 Open-AutoGLM 一样
- Docker `--network host`，和 Open-AutoGLM 一样
- 截图使用同一套压缩方案（720p JPEG 80 + RGBA→RGB）

### 项目位置
`F:\Open-AutoGLM\Open-ADBLLM\`

---

## Work Objectives

### Core Objective
搭建 Open-ADBLLM Phase 1：Docker 化 HTTP 服务，包含全部 🟢 绿色 API。

### Concrete Deliverables
- 可运行的 `Dockerfile`
- `server.py` 包含 17 个绿色 API 端点
- `requirements.txt`
- 复用并正确导入 `phone_agent/adb/` 模块
- `README.md`（需求文档已在，可能需要微调）

---

## Verification Strategy

- **Agent-Executed QA**：每个 API 用 curl 调用验证返回值
- **截图端点**：手动确认返回 base64 可解码为有效 JPEG
- **触控/按键**：在真机上验证点击/滑动/返回实际生效
- **Build**：`docker build` 成功，镜像 < 300MB

---

## Execution Strategy

### Parallel Waves

```
Wave 1 (基础骨架，全部并行):
├── Task 1: 项目骨架（目录结构、requirements.txt、.gitignore）[quick]
├── Task 2: Dockerfile [quick]
├── Task 3: 复用 adb 模块（从 Open-AutoGLM 复制 phone_agent/adb/）[quick]
└── Task 4: server.py 骨架（FastAPI app、配置加载、health 端点）[quick]

Wave 2 (绿色 API，全部并行):
├── Task 5: 屏幕 API（screenshot, screen/info）[quick]
├── Task 6: 触控 API（tap, swipe, long-press）[quick]
├── Task 7: 输入 + 按键 API（type, key）[quick]
├── Task 8: 应用 + 设备 API（app/launch, app/current, app/list, device/info）[quick]
```

---

## TODOs

- [ ] 1. 项目骨架

  **What to do**:
  - 创建 `requirements.txt`（FastAPI, uvicorn, Pillow, openai? 只取需要的）
  - 创建 `.gitignore`（__pycache__, .venv, *.pyc）
  - 确认 `README.md` 需求文档完整

  **QA Scenarios**:
  - `pip install -r requirements.txt` 无报错

  **Commit**: `chore: project skeleton`

- [ ] 2. Dockerfile

  **What to do**:
  - 基于 `python:3.11-slim`
  - `apt install adb`
  - 安装依赖 + 复制代码
  - CMD: `uvicorn server:app --host 0.0.0.0 --port ${ADBLLM_PORT:-8000}`

  **QA Scenarios**:
  - `docker build -t open-adbllm .` 成功
  - 镜像大小 < 300MB

  **Commit**: `feat: Dockerfile`

- [ ] 3. 复用 ADB 模块

  **What to do**:
  - 从 `F:\Open-AutoGLM\Open-AutoGLM\phone_agent\adb\` 复制以下文件到本项目 `phone_agent/adb/`：
    - `__init__.py`, `screenshot.py`, `device.py`, `input.py`, `connection.py`
  - 移除不必要的依赖（`config/timing.py` 等，硬编码替代或直接删依赖）
  - 确保 `import` 路径正确

  **Must NOT do**:
  - 不要引入 Open-AutoGLM 的 `config/`、`model/`、`actions/` 模块

  **QA Scenarios**:
  - `python -c "from phone_agent.adb import get_screenshot, tap, swipe, type_text, back, home; print('imports OK')"` 无报错

  **Commit**: `feat: port ADB module from Open-AutoGLM`

- [ ] 4. server.py 骨架

  **What to do**:
  - FastAPI app 初始化
  - 环境变量加载（ADBLLM_PORT, ADBLLM_TOKEN 等）
  - `GET /health`：检查 ADB 可用性 + 设备连接状态
  - CORS 允许所有来源（同一内网）

  **QA Scenarios**:
  - `curl http://localhost:8000/health` → `{"status":"ok","adb_available":true,"device_connected":true}`

  **Commit**: `feat: server skeleton with health endpoint`

- [ ] 5. 屏幕 API

  **What to do**:
  - `GET /screenshot`：调用 `phone_agent.adb.get_screenshot()`，返回 `{"image": "base64...", "width": N, "height": N}`
  - `GET /screen/info`：返回分辨率、DPI（通过 `adb shell wm size` 和 `adb shell wm density`）

  **QA Scenarios**:
  - `curl http://localhost:8000/screenshot` → 200，image 字段可 base64 decode 为有效 JPEG
  - `curl http://localhost:8000/screen/info` → `{"width":1080,"height":2400,"dpi":420}`

  **Commit**: `feat: screenshot and screen info APIs`

- [ ] 6. 触控 API

  **What to do**:
  - `POST /tap` `{x, y}` → 调 `device.tap(x, y)`
  - `POST /swipe` `{start: [x1,y1], end: [x2,y2], duration?: 300}` → 调 `device.swipe(...)`
  - `POST /long-press` `{x, y, duration?: 1000}` → 用 swipe 同坐标实现长按

  **QA Scenarios**:
  - 在手机上打开计算器 → `POST /tap {x,y}` 点击数字按钮 → 屏幕上出现对应数字
  - `POST /swipe` → 页面滑动

  **Commit**: `feat: touch input APIs`

- [ ] 7. 输入 + 按键 API

  **What to do**:
  - `POST /type` `{text}` → 调 `input.type_text(text)`（需 ADB Keyboard）
  - `POST /key` `{key}` → 映射 keycode 表：back→4, home→3, recent→187, power→26, volume_up→24, volume_down→25, enter→66

  **QA Scenarios**:
  - 打开某个输入框 → `POST /type {text: "hello"}` → 输入框出现 "hello"
  - `POST /key {key: "home"}` → 回到桌面

  **Commit**: `feat: text input and key APIs`

- [ ] 8. 应用 + 设备 API

  **What to do**:
  - `POST /app/launch` `{package}` → `adb shell am start -n`
  - `GET /app/current` → `device.get_current_app()`
  - `GET /app/list` → `adb shell pm list packages`
  - `GET /device/info` → 型号(`ro.product.model`)、版本(`ro.build.version.release`)、电量(`dumpsys battery`)

  **QA Scenarios**:
  - `POST /app/launch {package: "com.android.settings"}` → 手机打开设置
  - `GET /device/info` → 返回型号、版本、电量等信息

  **Commit**: `feat: app and device info APIs`

---

## Final Verification Wave

- [ ] F1. 构建镜像：`docker build -t open-adbllm .` 成功
- [ ] F2. 启动容器 + `curl /health` 通过
- [ ] F3. `curl /screenshot` 返回有效截图
- [ ] F4. `POST /tap` 实测点击生效
- [ ] F5. `POST /key {key: "home"}` 实测回到桌面
- [ ] F6. 提交到 GitHub `bomomoQWQ/Open-ADBLLM`

---

## Commit Strategy

- Task 1-8 各自独立 commit
- Final verification 后打 tag `v0.1.0`

## Success Criteria

- [ ] `docker build` 成功，镜像可运行
- [ ] 所有 17 个绿色 API 可访问
- [ ] 截图为有效 720p JPEG
- [ ] 触控在实际手机上生效
- [ ] 已推送到 GitHub + Docker Hub
