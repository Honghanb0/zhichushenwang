# 直触深网 · 网络安全周报生成器

![Logo](icon.png)

直触深网是一款基于 Electron + Python 的网络安全周报自动生成工具，能够自动抓取全球 76 个主流安全媒体的 RSS 源，按时间范围筛选热点新闻并提取正文，随后调用大模型（支持任意 OpenAI 兼容 API，默认 DeepSeek）生成包含搜集时期、态势总览、详细内容、阅读思考四大板块的结构化周报，每条事件自动打上安全资讯、漏洞研究、政策合规等标签，最终支持导出 Markdown 与 Word 两种格式。软件为绿色单文件分发，无需配置 Python/Node 环境，双击即可运行。

---

## 一、简介

自动抓取全球主流安全媒体的 RSS 热点新闻，提取正文，调用大模型（支持任意 OpenAI 兼容 API）生成结构化《网络安全周报》，包含搜集时期 / 态势总览 / 详细内容 / 阅读思考四大板块。每条事件自动打标签（安全资讯 / 漏洞研究 / 政策合规 / 漏洞预警 / AI 安全 / 攻防对抗），支持导出 **Markdown** 与 **Word(.docx)** 两种格式。

无需安装 Python/Node 环境，所有依赖已内置于安装包中。

---

## 二、安装

| 形式 | 文件 | 说明 |
|---|---|---|
| 安装版 | `electron/dist-electron/直触深网-Setup-1.0.0.exe` | 向导安装，可自定义目录，自动创建桌面与开始菜单快捷方式 |
| 便携版 | `electron/dist-electron/直触深网-Portable-1.0.0.exe` | 无需安装，直接运行，适合 U 盘/临时使用 |

> 系统要求：Windows 10 及以上；需联网（RSS 采集 + 大模型 API）。

---

## 三、启动

1. 双击「直触深网」快捷方式或可执行文件。
2. 程序自动拉起内嵌 Python 后端（`CyberSecBackend.exe`，监听 `127.0.0.1:8029`），就绪后显示主界面。
3. 关闭窗口即退出，后端进程随之终止。

> 若 `8029` 端口被占用，后端自动顺延至 `8030` 等后续端口。

---

## 四、配置

界面「配置参数」区域：

| 配置项 | 默认值 | 说明 |
|---|---|---|
| API Key | 空 | 不填进入**离线模式**（仅 RSS，无大模型）。可通过环境变量 `DEEPSEEK_API_KEY` 传入 |
| API Base URL | `https://api.deepseek.com/v1` | 任意 OpenAI 兼容端点（DeepSeek / 通义 / 本地 Ollama 等） |
| 模型名称 | `deepseek-v4-flash` | 可改为其他可用模型 |
| 时间范围 | 近一周 | 支持自定义起止日期 |
| 最大事件数 | 20 | 纳入周报的事件上限 |
| 抓取全文条数 | 20 | 对排名前 N 条新闻抓取原文正文 |
| 自定义 RSS | 空 | 每行一个 `名称,URL`，留空使用内置 76 个默认源 |

**高级（端口）**：修改 `app.py` 中的 `PORT` 与 `electron/main.js` 中的 `PORT_DEFAULT` 后重新打包；或以后端参数启动：`CyberSecBackend.exe --port 9000`。

---

## 五、功能使用

### 5.1 时间范围
- 快捷按钮「近一天 / 近一周 / 近一月」一键设置（结束日期=今天）。
- 自定义：手动选择起止日期（`YYYY-MM-DD`）。
- 校验：开始不得晚于结束、结束不得晚于今天、区间不超过 365 天。

### 5.2 生成周报
- 点击「生成周报」，左下角实时显示进度日志（RSS 采集 → 抓取全文 → 大模型生成）。
- 完成后右侧预览 Markdown 周报，出现三个按钮：**下载 Markdown / 下载 Word / 复制全文**。

### 5.3 报告完整性保证
四大板块（搜集时期 / 态势总览 / 详细内容 / 阅读思考）分段独立生成，缺失或截断自动续写补全，不受单次 token 上限影响。

### 5.4 离线模式
不填 API Key 也能运行，基于 RSS 摘要生成资讯汇总。

### 5.5 本地大模型
将「API Base URL」改为 `http://127.0.0.1:11434/v1`（Ollama），「模型名称」改为对应本地模型名，并确保 Ollama 服务已启动。

---

## 六、常见问题

**Q1：启动后白屏？**
- 检查 `8029` 端口：`netstat -ano | findstr 8029`
- 确认网络可访问 RSS 源（企业内网可能拦截外网）

**Q2：提示「未找到后端」或启动超时？**
- 安装版确认 `resources/backend/CyberSecBackend.exe` 完整
- 杀毒软件可能拦截，建议将程序目录加入白名单

**Q3：周报板块不全？**
- 已内置续写机制；检查网络是否正常，或适当降低「最大事件数」后重试

**Q4：部分新闻只有摘要？**
- 受目标站点限制时自动回退到 RSS 摘要，不影响周报生成

**Q5：API 报错 4xx/5xx？**
- 核对 Key、Base URL、模型名；DeepSeek 需账户有可用余额

**Q6：Word 导出打不开 / 错乱？**
- 由 `python-docx` 生成，需 Microsoft Word 或兼容软件；确认生成未被中断后重试

---

## 七、版权声明

软件界面底部中央固定显示：**【网安周报agent软件】版权所有：洪声越Jeff 联系邮箱：[HongshengyueJeff@163.com](mailto:HongshengyueJeff@163.com)**，导出的 Word 页脚亦附同样声明。

---

## 八、目录结构

```
zhichushenwang/
├─ app.py                          # Flask 后端（端口 8029）
├─ cybersecurity_weekly_agent.py   # 核心：采集 / 全文抓取 / 大模型 / 报告生成 / 标签 / Word 导出
├─ electron/
│  ├─ main.js                     # Electron 主进程
│  ├─ preload.js                  # 渲染进程桥接
│  ├─ package.json                 # 依赖与打包配置
│  ├─ backend.spec                 # PyInstaller 规格文件
│  ├─ build/icon.{ico,png}        # 应用图标
│  ├─ resources/backend/          # 打包内置的 CyberSecBackend.exe
│  └─ dist-electron/              # 构建产物（安装版 + 便携版）
└─ README.md
```

---

## 九、开发构建

```bash
# 1. 构建 Python 后端 exe
cd electron
python -m PyInstaller --noconfirm backend.spec

# 2. 将后端 exe 同步到 Electron 资源目录
Copy-Item dist/CyberSecBackend/* resources/backend/ -Recurse -Force

# 3. 构建 Electron 应用
npm install
npm run dist        # 输出至 electron/dist-electron/
```
