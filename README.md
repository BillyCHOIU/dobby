# 🏠 Dobby AI — 你的全屋智能管家

<p align="center">
  <strong>基于 Hermes Agent 打造的个人 AI 助手</strong>
</p>
<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="#"><img src="https://img.shields.io/badge/Built%20by-BillyCHOIU-blueviolet?style=for-the-badge" alt="Built by BillyCHOIU"></a>
  <a href="#"><img src="https://img.shields.io/badge/Platform-Windows%2010%2B-blue?style=for-the-badge" alt="Windows"></a>
</p>

**Dobby** 是一个定位为全屋智能管家的 AI 助手，基于 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 二次开发。

### 核心能力

| 能力 | 说明 |
|------|------|
| **智能家居控制** | 通过 MQTT/Home Assistant 控制局域网内任意品牌设备 |
| **摄像头监控** | 集成 RTSP/ONVIF 摄像头，实时画面分析 |
| **健康监测** | 对接 BLE 健康监测设备，跟踪体征数据 |
| **语音交互** | 手机端语音控制（Telegram/WhatsApp），TTS 语音播报 |
| **7×24 运行** | Windows 服务化运行，后期可移植到路由器（OpenWrt） |
| **完整的 AI Agent** | 代码编辑、文件操作、网络搜索、计划任务、长短期记忆 |

## 快速开始

### 环境要求

- Windows 10+（原生命令行 / PowerShell / Git Bash）
- Python 3.11~3.13
- 推荐安装 [uv](https://docs.astral.sh/uv/)（替代 pip）

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/BillyCHOIU/dobby.git
cd dobby

# 2. 安装依赖
pip install -e .

# 3. 初始化配置
dobby setup

# 4. 启动
dobby
```

### CLI 命令

```bash
dobby                    # 交互式对话
dobby chat -q "..."     # 单次查询
dobby setup             # 配置向导
dobby doctor            # 健康检查
dobby gateway start     # 启动消息网关
dobby cron list         # 查看定时任务
```

## 文档

完整文档请查看 [Hermes Agent 文档](https://hermes-agent.nousresearch.com/docs/)（核心架构与 Hermes 一致）。

## 与 Hermes Agent 的关系

Dobby 是 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 的一个定制化 fork，保留了完整的底层能力（skills、memory、gateway、cron、MCP 等），在此之上：

- 重新定义了默认身份（智能家居管家）
- 修改了默认提示词和服务端特性
- 后续会加入智能家居专属插件和技能包

## 许可证

MIT License — 与 Hermes Agent 一致。