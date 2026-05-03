# Draft: Open-ADBLLM 需求规格

## 核心定位
ADB 命令 HTTP API + 网页控制台，为上游 AI Agent 提供手机底层操控能力。不做决策，只做执行。

## 功能模块
### 🟢 基础（17 API，始终开放）
截屏/信息、点击/滑动/长按、打字、按键(back/home/recent等)、启动/当前App/应用列表、设备信息、健康检查

### 🟡 高级（9 API，需控制台开关开启）
重启/唤醒/熄屏/亮度、WiFi开关、安装/卸载/清数据 APK、执行 shell

### 🔴 危险（3 API，需一次性密钥）
恢复出厂、OEM解锁、Root

## 权限
- 🟢 绿: 无需认证，始终开放
- 🟡 黄: 控制台一键开关，关闭时黄色 API 返回 403
- 🔴 红: Header Bearer <一次性32位UUID>，只能用一次

## 网页控制台
- / → 单页，Basic Auth (ADBLLM_CONSOLE_USER/PASS)
- SSE实时日志流
- 🟡 黄色权限：一键开关按钮
- 🔴 红色密钥面板：生成密钥 → 复制 → 到期倒计时

## 技术
- Python 3.11 + FastAPI + uvicorn
- 复用 F:/Open-AutoGLM/Open-AutoGLM/phone_agent/adb/ 的截图/触控/输入模块
- Docker --network host

## 环境变量
- ADBLLM_PORT - HTTP端口(默认8000)
- ADBLLM_CONSOLE_USER / ADBLLM_CONSOLE_PASS - 控制台凭证
