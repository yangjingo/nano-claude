# Claude Code 逆向 Wiki

这是一份独立的 Claude Code 源码逆向 Wiki。它的目标是把源码快照中的关键结构、运行链路、权限机制、扩展系统和交互界面拆开讲清楚，方便阅读、检索和发布。

## 当前版本

- 版本号：`2026-04-06-132524`
- 生成时间：`2026-04-06T05:25:24.8642112Z`
- 语言：`zh`
- 当前指针：[`wiki/current`](current)

## 如何阅读

推荐按下面顺序看：

1. 先看项目概览和目录导航，建立整体模型。
2. 再看启动流程、查询循环和工具系统，理解主执行链路。
3. 然后看权限、MCP、Bridge、Task 和扩展机制。
4. 最后看 REPL/UI 相关页面，把交互层和运行层串起来。

快速路径：

- `1 -> 2 -> 3 -> 5 -> 6 -> 9 -> 15 -> 18 -> 28 -> 37`

## 发布结构

这个 Wiki 采用版本化目录：

- `wiki/README.md` 作为首页
- `wiki/current` 作为当前版本指针
- `wiki/versions/<version>/` 作为每个快照版本目录
- `wiki/versions/<version>/wiki.json` 作为该版本的文章索引

如果后续新增版本，只需要新增一个 `versions/<version>/` 目录，并更新 `wiki/current` 即可。

## 版本索引

### 1. 入门与总览

| 编号 | 文章 | 难度 |
|---|---|---|
| 1 | [项目概览：Claude Code 源码快照的价值与定位](versions/2026-04-06-132524/1-xiang-mu-gai-lan-claude-code-yuan-ma-kuai-zhao-de-jie-zhi-yu-ding-wei.md) | Beginner |
| 2 | [代码仓库导航：目录结构与核心模块地图](versions/2026-04-06-132524/2-dai-ma-cang-ku-dao-hang-mu-lu-jie-gou-yu-he-xin-mo-kuai-di-tu.md) | Beginner |
| 3 | [从 main.tsx 开始：CLI 启动流程与初始化](versions/2026-04-06-132524/3-cong-main-tsx-kai-shi-cli-qi-dong-liu-cheng-yu-chu-shi-hua.md) | Intermediate |
| 4 | [快照分析环境搭建与常用命令](versions/2026-04-06-132524/4-kuai-zhao-fen-xi-huan-jing-da-jian-yu-chang-yong-ming-ling.md) | Intermediate |

### 2. 查询与工具

| 编号 | 文章 | 难度 |
|---|---|---|
| 5 | [QueryEngine：LLM 查询循环与工具调度核心](versions/2026-04-06-132524/5-queryengine-llm-cha-xun-xun-huan-yu-gong-ju-diao-du-he-xin.md) | Advanced |
| 6 | [工具系统架构：从 Tool 接口到 40+ 工具实现](versions/2026-04-06-132524/6-gong-ju-xi-tong-jia-gou-cong-tool-jie-kou-dao-40-gong-ju-shi-xian.md) | Advanced |
| 7 | [命令系统设计：50+ 捷径命令的组织与注册](versions/2026-04-06-132524/7-ming-ling-xi-tong-she-ji-50-xie-gang-ming-ling-de-zu-zhi-yu-zhu-ce.md) | Advanced |
| 8 | [并发执行策略：工具批处理与安全判断](versions/2026-04-06-132524/8-bing-fa-zhi-xing-ce-lue-gong-ju-pi-chu-li-yu-an-quan-pan-ding.md) | Advanced |
| 9 | [权限模式系统：default / plan / auto / bypass 等模式解析](versions/2026-04-06-132524/9-quan-xian-mo-shi-xi-tong-default-plan-auto-bypass-deng-mo-shi-jie-xi.md) | Advanced |
| 10 | [Bash 工具安全制度：后台执行策略](versions/2026-04-06-132524/10-bash-gong-ju-an-quan-zhi-du-pan-ding-yu-hou-tai-zhi-xing-ce-lue.md) | Advanced |
| 11 | [权限请求流程：用户交互与决策传播](versions/2026-04-06-132524/11-quan-xian-qing-qiu-liu-cheng-yong-hu-jiao-hu-yu-jue-ce-chuan-bo.md) | Intermediate |
| 12 | [AppState 设计：React 状态管理与订阅机制](versions/2026-04-06-132524/12-appstate-she-ji-react-zhuang-tai-guan-li-yu-ding-yue-ji-zhi.md) | Intermediate |
| 13 | [文件缓存与读取优化：FileStateCache 实现](versions/2026-04-06-132524/13-wen-jian-huan-cun-yu-du-qu-you-hua-filestatecache-shi-xian.md) | Intermediate |
| 14 | [会话持久化：sessionStorage 与对话恢复](versions/2026-04-06-132524/14-hui-hua-chi-jiu-hua-sessionstorage-yu-dui-hua-hui-fu.md) | Intermediate |

### 3. MCP / Bridge / Auth

| 编号 | 文章 | 难度 |
|---|---|---|
| 15 | [MCP 客户端实现：连接管理与工具发现](versions/2026-04-06-132524/15-mcp-ke-hu-duan-shi-xian-lian-jie-guan-li-yu-gong-ju-fa-xian.md) | Advanced |
| 16 | [MCP 工具调用：MCPTool 与资源访问](versions/2026-04-06-132524/16-mcp-gong-ju-diao-yong-mcptool-yu-zi-yuan-fang-wen.md) | Intermediate |
| 17 | [MCP 服务端配置与认证流程](versions/2026-04-06-132524/17-mcp-fu-wu-qi-pei-zhi-yu-ren-zheng-liu-cheng.md) | Intermediate |
| 18 | [Bridge 事件循环：IDE 双向通信协议](versions/2026-04-06-132524/18-bridge-zhu-xun-huan-ide-shuang-xiang-tong-xin-xie-yi.md) | Advanced |
| 19 | [会话管理：sessionRunner 与多环境支持](versions/2026-04-06-132524/19-hui-hua-guan-li-sessionrunner-yu-duo-huan-jing-zhi-chi.md) | Intermediate |
| 20 | [JWT 认证与受信任设备机制](versions/2026-04-06-132524/20-jwt-ren-zheng-yu-shou-xin-ren-she-bei-ji-zhi.md) | Intermediate |

### 4. 插件 / Skills / Hooks / API

| 编号 | 文章 | 难度 |
|---|---|---|
| 21 | [内置插件注册机制](versions/2026-04-06-132524/21-nei-zhi-cha-jian-zhu-ce-builtinplugin-ji-zhi.md) | Intermediate |
| 22 | [BundledSkill 与命令注册](versions/2026-04-06-132524/22-ji-neng-xi-tong-bundledskill-yu-ming-ling-zhu-ce.md) | Intermediate |
| 23 | [Hooks 配置与执行时机](versions/2026-04-06-132524/23-gou-zi-xi-tong-hooks-pei-zhi-yu-zhi-xing-shi-ji.md) | Advanced |
| 24 | [Anthropic API 客户端封装与错误处理](versions/2026-04-06-132524/24-api-ke-hu-duan-anthropic-api-feng-zhuang-yu-cuo-wu-chu-li.md) | Intermediate |
| 25 | [OAuth 2.0 流程认证与令牌刷新](versions/2026-04-06-132524/25-oauth-2-0-liu-cheng-ren-zheng-yu-ling-pai-shua-xin.md) | Intermediate |
| 26 | [上下文压缩：compact 与对话摘要](versions/2026-04-06-132524/26-shang-xia-wen-ya-suo-compact-fu-wu-yu-dui-hua-zhai-yao.md) | Intermediate |
| 27 | [内存抽取：extractMemories 与持久化](versions/2026-04-06-132524/27-nei-cun-zi-dong-ti-qu-extractmemories-yu-chi-jiu-hua.md) | Advanced |

### 5. REPL / UI

| 编号 | 文章 | 难度 |
|---|---|---|
| 28 | [REPL 主界面：屏幕组织与消息渲染](versions/2026-04-06-132524/28-repl-zhu-jie-mian-ping-mu-zu-zhi-yu-xiao-xi-xuan-ran.md) | Intermediate |
| 29 | [Ink 框架集成：React 终端渲染引擎](versions/2026-04-06-132524/29-ink-kuang-jia-ji-cheng-react-zhong-duan-xuan-ran-yin-qing.md) | Intermediate |
| 30 | [消息组件：Message / MessageRow 与虚拟滚动](versions/2026-04-06-132524/30-xiao-xi-zu-jian-message-messagerow-yu-xu-ni-gun-dong.md) | Intermediate |
| 31 | [PromptInput：用户输入处理与模式切换](versions/2026-04-06-132524/31-promptinput-yong-hu-shu-ru-chu-li-yu-mo-shi-qie-huan.md) | Intermediate |
| 32 | [键盘绑定系统：快捷键配置与匹配](versions/2026-04-06-132524/32-jian-pan-bang-ding-xi-tong-kuai-jie-jian-pei-zhi-yu-pi-pei.md) | Intermediate |
| 33 | [Vim 模式实现：motion / operator / text objects](versions/2026-04-06-132524/33-vim-mo-shi-shi-xian-motion-operator-yu-text-objects.md) | Intermediate |
| 34 | [权限请求对话框：PermissionRequest 组件](versions/2026-04-06-132524/34-quan-xian-qing-qiu-dui-hua-kuang-permissionrequest-zu-jian.md) | Intermediate |
| 35 | [MCP 服务器审批流程：MCPServerApprovalDialog](versions/2026-04-06-132524/35-mcp-fu-wu-qi-shen-pi-liu-cheng-mcpserverapprovaldialog.md) | Intermediate |
| 36 | [计划模式切换：EnterPlanMode / ExitPlanMode 交互](versions/2026-04-06-132524/36-ji-hua-mo-shi-qie-huan-enterplanmode-exitplanmode-jiao-hu.md) | Intermediate |

### 6. 协作与运行时

| 编号 | 文章 | 难度 |
|---|---|---|
| 37 | [多代理协调：Coordinator 模式与团队协作](versions/2026-04-06-132524/37-duo-dai-li-xie-diao-coordinator-mo-shi-yu-tuan-dui-xie-zuo.md) | Advanced |
| 38 | [自代理工具：AgentTool 与任务委派](versions/2026-04-06-132524/38-zi-dai-li-gong-ju-agenttool-yu-ren-wu-wei-pai.md) | Advanced |
| 39 | [远程会话：RemoteSessionManager 与 WebSocket 通信](versions/2026-04-06-132524/39-yuan-cheng-hui-hua-remotesessionmanager-yu-websocket-tong-xin.md) | Advanced |
| 40 | [Git Worktree 集成：隔离工作树管理](versions/2026-04-06-132524/40-git-worktree-ji-cheng-ge-chi-gong-zuo-shu-guan-li.md) | Advanced |
| 41 | [LSP 集成：语言服务协议客户端实现](versions/2026-04-06-132524/41-lsp-ji-cheng-yu-yan-fu-wu-qi-xie-yi-ke-hu-duan-shi-xian.md) | Advanced |
| 42 | [成本追踪：token 计费与用量统计](versions/2026-04-06-132524/42-cheng-ben-zhui-zong-token-ji-fei-yu-yong-liang-tong-ji.md) | Advanced |
| 43 | [代码风格与命名约定](versions/2026-04-06-132524/43-dai-ma-feng-ge-yu-ming-ming-yue-ding.md) | Intermediate |
| 44 | [调试技巧：日志诊断与性能分析](versions/2026-04-06-132524/44-diao-shi-ji-qiao-ri-zhi-zhen-duan-yu-xing-neng-fen-xi.md) | Intermediate |
| 45 | [特性开关：Bun bundle feature flags 机制](versions/2026-04-06-132524/45-te-xing-kai-guan-bun-bundle-feature-flags-ji-zhi.md) | Advanced |
| 46 | [静态分析方法：无构建环境下的代码探索](versions/2026-04-06-132524/46-jing-tai-fen-xi-fang-fa-wu-gou-jian-huan-jing-xia-de-dai-ma-tan-suo.md) | Intermediate |

## 参考来源

- [6551Team/claude-code-design-guide](https://github.com/6551Team/claude-code-design-guide/tree/main)
- [openedclaude.github.io/claude-reviews-claude](https://openedclaude.github.io/claude-reviews-claude/)

## 说明

- 这是独立 Wiki，不依赖仓库其他文档作为入口。
- 后续如果增加新版本，只需要更新 `wiki/current` 和新增版本目录。
- 如果你要把它发布成静态站点，`wiki/README.md` 可以直接作为首页。
