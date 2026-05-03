# Open-ADBLLM

ADB 命令 HTTP API，为上游 AI Agent 提供手机底层操控能力。

## 项目目标

将 ADB 命令（截图/点击/滑动/输入/启动应用等）封装为 REST API，让任何支持 HTTP 的 AI Agent 直接控制手机，不依赖内置 VLM。

```
上级 Agent (有视觉能力) ── HTTP ──► Open-ADBLLM ── ADB ──► 📱
```

## 计划

- [ ] ADB 截图 API
- [ ] ADB 点击 API
- [ ] ADB 滑动 API
- [ ] ADB 输入 API
- [ ] ADB 应用管理 API
- [ ] Docker 部署
