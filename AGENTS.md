# 项目开发规则

本文件适用于本项目全部代码、数据库变更、来源采集适配器、接口变更，以及前端 UI 风格约束，与全局开发规则共同生效。

## 应用边界（改代码前必读）

本仓库按应用分目录维护，**三套应用并存，改动必须进入对应应用包**：

| 应用 | 形态 | 唯一业务代码位置 | 启动命令 |
| --- | --- | --- | --- |
| 团队工作台 2.0 | 本地 Web（默认 8765） | `apps/workbench/bidmonitor_workbench` | `.venv/bin/python run_workbench.py` |
| 桌面维护版 | Tkinter GUI | `apps/desktop/bidmonitor_desktop` | `.venv/bin/python run_original.py` |
| 历史 Web 后台 | 兼容保留（8080） | `apps/legacy_web/bidmonitor_legacy_web` | `.venv/bin/python server/app.py` |

- `server/app.py`、`server/workbench_app.py` 仅保留兼容导出，**不作为修改入口**；`legacy_web/core/` 是冻结实现，不当作桌面维护版或工作台的修改入口。
- 各应用私有数据位于 `runtime/`（工作台/桌面/历史 Web 各自目录），兼容旧目录；`BIDMONITOR_*_HOME` 环境变量可覆盖。`runtime/`、私人配置、数据库与日志不提交 Git。
- 详细架构见 [docs/TECH_STACK.md](docs/TECH_STACK.md)，应用导航见 [README.md](README.md)。

## 前端 UI 风格规范（团队工作台）

- 工作台前端（`apps/workbench/bidmonitor_workbench/web/`）为**原生 HTML + CSS + JavaScript 单页应用**：无框架、无构建工具，hash 路由，`fetch` 调 JSON API。
- **新增页面/组件必须先读完整 `web/assets/app.css` 并严格复用其 CSS 变量与类名模板**；禁止自创色值、禁止引入第三方组件库或构建工具。
- 核心变量速查（`app.css` `:root`）：
  - 背景 `--bg:#f5f7fb`；侧栏白 `#ffffff`；卡片白
  - 文字 `--ink:#172338`；次要 `--muted:#7b8799`
  - 主色 `--blue:#3168e8`（主按钮/激活/链接）；浅底 `--light:#edf3ff`；强调绿 `--green:#159374`
  - 边框 `--line:#e7ebf2`；圆角 `--radius:12px`；输入聚焦 `outline:#c4d6ff` + `border-color:var(--blue)`
- 图标用文本符号（如 ⌕ ▤ ⚙），不引入图标库。
- 桌面版为 Tkinter 原生控件，遵循既有窗口/控件风格，不做框架级改动。

## 技能使用限制

- 本项目默认技能按各自触发条件正常使用；**superpowers 工作流技能（`brainstorming`、`writing-plans`、`executing-plans`、`tdd`、`test-driven-development`）视为本项目默认启用且为必经环节**，不要求用户逐次点名。
- 技能与当前任务无关或用户未点名时，不主动加载不相关技能。

## 简单提示词触发功能

- 用户常以一句话触发本项目功能（如"采集公告""搜标讯""启动工作台"）。Agent 默认按 **`docs/quick-triggers.md`** 的触发词映射表路由到对应页面 / API / 操作，命中触发词即按该表"默认行为"执行。
- **未命中映射表的简单提示词**：先向用户确认意图（AskUserQuestion），不得自行猜测。
- **新功能上线时**：将触发词补进 `docs/quick-triggers.md`（提交 body / 交付记录同步注明"已登记触发词"）。
- 改默认行为/产物时，同步更新触发词表与对应应用源码/README，保持两处一致。

## 开发流程（强制 superpowers 工作流）

- **任何功能新增、行为修改、Bug 修复（非纯对话/咨询）都必须走 superpowers 工作流**，不允许跳过需求梳理与设计评审直接写代码：
  1. `brainstorming`：探索需求，逐个澄清问题，与用户核对需求，提出方案并取得用户对设计的确认。
  2. 撰写设计文档：保存到 `docs/superpowers/specs/YYYY-MM-DD-<功能名>-design.md`，完成后必须请用户评审该文档；用户批准前不得进入实现。
  3. `writing-plans`：将已批准的设计拆解为实现计划，保存到 `docs/superpowers/plans/`。
  4. `executing-plans` + `tdd`：按计划实现并用测试验证。
  5. 交付记录：写 `docs/superpowers/notes/YYYY-MM-DD-<功能名>.md`（如适用）。

## 行业与来源配置化规范

- **来源目录统一维护**：工作台来源在 `collectors/sources.py`（跨行业来源）与 `collectors/extra_sources.json`（来源扩充，每条保留网址出处）；行业与来源细分标签映射统一维护在 `collectors/sectors.py`，前端和接口共用。
- **新增来源/行业禁止在业务代码里新建硬编码词表**：行业映射、来源目录、站点发现规则统一进上述文件；正则边界、匹配优先级、去重/停用等**逻辑**留在代码，配置文件只存词条/定义。
- 核验脚本只访问公开页面，不执行下载的 JavaScript；核验结果 JSON 报告位于 `runtime/workbench/`，脚本与页面采集避免同时执行。

## 提交消息规范

为便于按提交记录整理迭代文档（`weekly-iteration-report`），提交消息统一采用以下格式，**summary 必填、body 三要素建议填写**：

```
type(scope): 一句话做了什么

- 原因：为什么改（背景/问题）
- 改动：改了什么（关键要点：新增表/字段、接口、核心逻辑）
- 影响：测试结果 / 是否动表/接口/前端 / 兼容性
```

- summary 用 Conventional Commits 类型（`feat`/`fix`/`perf`/`docs`/`refactor`/`test`/`chore`）+ 作用域（如 `workbench-collector`/`desktop-notifier`/`source-census`），一眼可归类。
- body 三要素（原因/改动/影响）用于关键提交（功能、性能、修复、接口/表变更）；**纯文档/测试/小修类可从简**（一句原因即可）。
- 详细设计、数字、验收仍放 `docs/superpowers/notes/`；提交 body 写要点，不重复长文。

## 变更验证

- 涉及数据库、来源采集、接口的变更，必须检查完整依赖链（采集→入库→搜索/线索→导出），不能只检查当前报错的位置。
- 数据库与接口变更必须提供与影响范围相符的回归验证。测试统一放 `tests/`（pytest），运行方式：`PYTHONPATH=. .venv/bin/python -m pytest tests/`。
- 不得直接删除用户实际业务数据或清空数据库来验证变更。使用隔离测试数据；实际数据核对采用只读方式。
- SQLite 无 ORM、无迁移框架，**改表结构需新增兼容处理或初始化逻辑**，不得靠破坏既有数据绕过。
- 默认不擅自启动开发服务器。**用户明确要求"启动工作台 / 启动桌面版 / 启动历史Web"时**，按下文「服务启动规范」执行，不自行另起其他启动方式。

## 服务启动规范

- **启动工作台** → `.venv/bin/python run_workbench.py`（默认 http://127.0.0.1:8765，自动开浏览器；`--no-browser --port` 可改）
- **启动桌面版** → `.venv/bin/python run_original.py`（Tkinter GUI）
- **启动历史Web** → `.venv/bin/python server/app.py`（0.0.0.0:8080）
- 依赖安装：`.venv/bin/python -m pip install -r requirements.txt -r server/requirements.txt`（来源核验脚本另需 `scripts/requirements.txt`）。
- 收到"启动项目 / 启动服务"等指令时，先确认本项目自有启动文档（`docs/quick-triggers.md` 第四节），**按项目自有约定执行，不套用通用启动流程**；若入口缺失或异常，报告用户而不是自行摸索。

## 新接手项目变更提醒

- 本项目为迭代基线，任何改动都应尽量不破坏既有功能（三应用并存、既有接口、历史数据、既有测试）。
- 改动一旦可能影响既有功能（既有采集行为、已发布接口、历史数据、前端已有页面、既有测试），必须在动手前向用户明确说明：影响范围、涉及文件、风险与验证方式，取得用户确认后再实施；不得等到改动完成后才提示。
- 不得以"顺手优化""重构顺便"为由，悄悄改动与当前任务无关的既有代码；确需改动时，先说明原因并取得确认。
- 开发过程中若发现既有功能存在缺陷或隐患，可记录并提示用户，但不在未授权的情况下自行修改。
