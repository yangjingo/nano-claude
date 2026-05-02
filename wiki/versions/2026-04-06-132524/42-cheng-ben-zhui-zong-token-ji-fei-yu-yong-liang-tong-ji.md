Claude Code 的成本追踪系统是一套完整的 token 用量监控与计费统计机制，贯穿了从 API 响应处理、实时成本累加、到历史数据分析的全链路。该系统为高级开发者提供了透明的成本可见性，支持按模型分组的用量统计、会话恢复时的成本累积、以及历史会话的统计可视化。

## 系统架构概览

成本追踪系统由三层架构组成：**数据采集层**负责从 API 响应中提取 Usage 数据；**状态管理层**维护全局成本状态并支持会话持久化；**展示层**通过命令行和 UI 组件呈现成本信息。系统通过 OpenTelemetry 指标导出机制，将成本数据接入监控体系，同时将细粒度的 token 统计保存到项目配置文件，实现跨会话的成本追踪。

```mermaid
graph TB
    A[API Response] -->|Usage Object| B[calculateUSDCost]
    B --> C[addToTotalSessionCost]
    C --> D[STATE.modelUsage]
    C --> E[STATE.totalCostUSD]
    C --> F[OpenTelemetry Counters]
    
    D --> G[getTotalInputTokens]
    D --> H[getTotalOutputTokens]
    D --> I[getModelUsage]
    
    E --> J[getTotalCostUSD]
    
    G --> K[formatTotalCost]
    H --> K
    J --> K
    
    K --> L[/cost command]
    K --> M[Usage.tsx Component]
    
    N[saveCurrentSessionCosts] --> O[Project Config]
    O --> P[restoreCostStateForSession]
    P --> D
    P --> E
    
    style B fill:#e1f5ff
    style C fill:#e1f5ff
    style D fill:#fff4e6
    style E fill:#fff4e6
    style F fill:#f3e5f5
```

**数据采集层**的核心入口是 `calculateUSDCost` 函数，它接收模型标识符和 Anthropic SDK 的 `BetaUsage` 对象，根据预设的价格表计算美元成本。该函数首先通过 `getCanonicalName` 将模型别名标准化为短名称（如 `claude-3-5-sonnet`），然后从 `MODEL_COSTS` 映射表中获取价格配置，最后应用 `tokensToUSDCost` 公式将各类 token 数量转换为成本。Sources: [src/utils/modelCost.ts](src/utils/modelCost.ts#L131-L180)

**状态管理层**位于 `bootstrap/state.ts`，维护一个全局单例 `STATE` 对象，其中包含 `totalCostUSD`（累计成本）、`modelUsage`（按模型分组的用量统计）等字段。`addToTotalCostState` 函数负责原子性地更新这两个字段，而 `getTotalInputTokens`、`getTotalOutputTokens` 等辅助函数则通过 `sumBy` 聚合所有模型的用量。状态管理模块还提供会话恢复机制：`saveCurrentSessionCosts` 在进程退出前将成本快照持久化到项目配置，`restoreCostStateForSession` 在会话恢复时将历史成本重新加载到全局状态。Sources: [src/bootstrap/state.ts](src/bootstrap/state.ts#L557-L569), [src/cost-tracker.ts](src/cost-tracker.ts#L143-L175)

**展示层**包含三个主要组件：`/cost` 命令直接调用 `formatTotalCost` 输出当前会话的成本摘要；`Usage.tsx` 组件通过 `fetchUtilization` API 获取速率限制和配额使用情况，以进度条形式展示；`Stats.tsx` 组件读取历史会话日志，聚合生成活跃天数、最长会话、token 总量等统计数据，并支持按日期范围过滤。Sources: [src/commands/cost/cost.ts](src/commands/cost/cost.ts#L1-L25), [src/components/Settings/Usage.tsx](src/components/Settings/Usage.tsx#L1-L100), [src/components/Stats.tsx](src/components/Stats.tsx#L400-L577)

## 模型定价机制

Claude Code 内置了 Anthropic 官方定价表，通过 `ModelCosts` 类型定义了五种计费维度：`inputTokens`（输入 token）、`outputTokens`（输出 token）、`promptCacheWriteTokens`（缓存写入）、`promptCacheReadTokens`（缓存读取）、`webSearchRequests`（网页搜索请求）。系统预定义了多个价格层级（`COST_TIER_3_15`、`COST_TIER_15_75` 等），不同模型根据其市场定价映射到相应层级。

```typescript
// 价格层级示例（美元/百万 token）
export const COST_TIER_3_15 = {
  inputTokens: 3,              // $3/M input
  outputTokens: 15,            // $15/M output
  promptCacheWriteTokens: 3.75, // 1.25x base
  promptCacheReadTokens: 0.3,   // 0.1x base
  webSearchRequests: 0.01,      // $0.01/request
} as const
```

**价格计算公式**在 `tokensToUSDCost` 函数中实现：将各类 token 数量除以 1,000,000（百万），乘以对应的单价，最后求和。缓存 token 的价格分别是基准价格的 1.25 倍（写入）和 0.1 倍（读取），这反映了 Anthropic 的 prompt caching 机制的成本优化特性。Sources: [src/utils/modelCost.ts](src/utils/modelCost.ts#L36-L142)

**动态定价**针对 Opus 4.6 模型的 fast mode 特性：当检测到 `usage.speed === 'fast'` 时，系统自动切换到 `COST_TIER_30_150` 价格表（$30/$150），而非标准的 `COST_TIER_5_25`（$5/$25）。这种设计允许系统在运行时根据 API 响应中的元数据动态调整计费逻辑。Sources: [src/utils/modelCost.ts](src/utils/modelCost.ts#L94-L99)

**未知模型处理**通过 `trackUnknownModelCost` 函数记录遥测事件，并设置 `hasUnknownModelCost` 标志。系统在格式化成本输出时会提示"costs may be inaccurate"，避免误导用户。回退策略使用默认模型的价格表（通常是 Sonnet 系列的 `COST_TIER_3_15`）。Sources: [src/utils/modelCost.ts](src/utils/modelCost.ts#L166-L173)

## 成本累加与聚合流程

每次 API 调用完成后，`addToTotalSessionCost` 函数被触发，它执行以下四个关键步骤：**第一步**，调用 `addToTotalModelUsage` 为当前模型累加 token 统计（包括输入、输出、缓存读写、网页搜索）；**第二步**，调用 `addToTotalCostState` 将计算出的成本和更新后的模型用量写入全局状态；**第三步**，更新 OpenTelemetry 指标（`costCounter` 和 `tokenCounter`），附加模型名称和 token 类型作为属性；**第四步**，递归处理 advisor 工具的用量（如果存在），将辅助模型的成本也纳入总计。Sources: [src/cost-tracker.ts](src/cost-tracker.ts#L250-L324)

**按模型聚合**的实现通过 `getModelUsage` 函数获取完整的 `modelUsage` 映射表，其中每个模型的 `ModelUsage` 对象包含独立的 token 统计和成本。`formatModelUsage` 函数进一步将完整模型名称标准化为短名称（如 `claude-3-5-sonnet-v2` → `sonnet-3.5`），并合并同一短名称下不同版本的用量。这种设计允许用户在报告中看到聚合后的模型级别统计，而非细粒度的版本级别统计。Sources: [src/cost-tracker.ts](src/cost-tracker.ts#L181-L226)

**跨模型汇总**通过 `getTotalInputTokens`、`getTotalOutputTokens` 等函数实现，它们使用 `sumBy` 对 `modelUsage` 映射表的所有值求和。这些汇总函数被 `formatTotalCost` 调用，生成包含总成本、API 耗时、代码行变更的完整报告。Sources: [src/bootstrap/state.ts](src/bootstrap/state.ts#L704-L722)

## 会话持久化与恢复机制

成本追踪系统设计了会话级别的持久化机制，确保用户在切换会话或重启 CLI 后不会丢失历史成本数据。**持久化触发**通过 `costHook.ts` 中的 `useCostSummary` Hook 实现：它在组件挂载时注册 `process.on('exit')` 事件监听器，在进程退出前调用 `saveCurrentSessionCosts`，将当前成本快照写入项目配置文件的 `lastCost`、`lastModelUsage` 等字段。Sources: [src/costHook.ts](src/costHook.ts#L1-L23)

**恢复流程**在会话启动时由 `restoreCostStateForSession` 函数驱动：它首先通过 `getStoredSessionCosts` 读取项目配置，检查 `lastSessionId` 是否与当前会话 ID 匹配（防止恢复错误会话的成本）；如果匹配，则调用 `setCostStateForRestore` 将持久化的成本数据重新加载到全局状态，并调整 `startTime` 以使 wall duration 正确累积。Sources: [src/cost-tracker.ts](src/cost-tracker.ts#L87-L137)

**持久化数据结构**由 `StoredCostState` 类型定义，包含 `totalCostUSD`、`totalAPIDuration`、`totalLinesAdded`、`totalLinesRemoved` 以及 `modelUsage` 映射表。其中 `modelUsage` 在持久化时会剥离 `contextWindow` 和 `maxOutputTokens` 字段（这些是运行时动态计算的），在恢复时重新通过 `getContextWindowForModel` 和 `getModelMaxOutputTokens` 注入。Sources: [src/cost-tracker.ts](src/cost-tracker.ts#L71-L123)

## 命令系统与用户交互

成本追踪系统暴露了三个用户命令：**`/cost`** 输出当前会话的成本摘要，包括总成本、按模型分组的 token 统计、API 耗时和代码变更行数；对于 Claude.ai 订阅用户，该命令会提示当前使用订阅配额还是超额配额。**`/usage`** 打开 Settings 对话框的 Usage 标签页，展示速率限制使用情况（5 小时窗口、7 天窗口）和配额重置时间，通过进度条可视化消耗比例。**`/stats`** 显示历史统计面板，包括活跃天数、会话总数、token 总量、最长会话等指标，并支持按日期范围（7 天、30 天、全部时间）过滤。Sources: [src/commands/cost/cost.ts](src/commands/cost/cost.ts#L1-L25), [src/commands/usage/usage.tsx](src/commands/usage/usage.tsx#L1-L7), [src/commands/stats/stats.tsx](src/commands/stats/stats.tsx#L1-L7)

**权限控制**由 `hasConsoleBillingAccess` 和 `hasClaudeAiBillingAccess` 两个函数实现。Console 用户（使用 API key 登录）需要具备组织或工作区的 `admin`/`billing` 角色才能查看成本；Claude.ai 订阅用户中，Max/Pro 个人用户始终有权限，而 Team/Enterprise 用户需要组织级别的 `admin`/`billing`/`owner` 角色。系统还支持通过 `DISABLE_COST_WARNINGS` 环境变量全局禁用成本警告。Sources: [src/utils/billing.ts](src/utils/billing.ts#L10-L78)

**输出格式化**由 `formatTotalCost` 函数控制，它使用 `chalk` 库应用 dim 颜色，生成多行文本报告。`formatCost` 辅助函数处理成本数字的精度：成本大于 $0.5 时显示两位小数，否则显示四位小数（例如 `$0.0034`）。模型级别的统计通过 `formatModelUsage` 格式化为缩进列表，每个模型一行，包含 token 数量（使用 `formatNumber` 添加千分位分隔符）和成本。Sources: [src/cost-tracker.ts](src/cost-tracker.ts#L177-L244)

## UI 组件与可视化

**Usage 组件**（`Usage.tsx`）通过 `fetchUtilization` API 获取实时配额数据，返回的 `Utilization` 对象包含 `five_hour`、`seven_day`、`seven_day_opus`、`seven_day_sonnet` 等多个速率限制窗口。每个 `RateLimit` 对象包含 `utilization`（0-100 的百分比）和 `resets_at`（ISO 8601 时间戳）。组件使用 `ProgressBar` 子组件可视化消耗比例，并调用 `formatResetText` 生成友好的重置时间描述（如 "Resets in 2 hours"）。Sources: [src/components/Settings/Usage.tsx](src/components/Settings/Usage.tsx#L1-L100), [src/services/api/usage.ts](src/services/api/usage.ts#L12-L63)

**Stats 组件**（`Stats.tsx`）采用 React 19 的 `use()` Hook 处理异步数据加载：在组件首次渲染时通过 `createAllTimeStatsPromise` 启动全时间范围统计查询，然后 Suspense 等待结果；加载完成后，用户可以通过 Date Range Selector 切换到 7 天或 30 天视图，此时组件通过 `useEffect` 触发新的查询并缓存结果。这种设计避免了每次切换日期范围时的 Suspense 阻塞。Sources: [src/components/Stats.tsx](src/components/Stats.tsx#L59-L179)

**统计聚合**由 `aggregateClaudeCodeStatsForRange` 函数实现（位于 `utils/stats.ts`），它扫描会话日志目录（`.claude/projects/<project-id>/`），按日期范围过滤 JSONL 文件，解析每条 `TranscriptMessage` 提取 token 统计和元数据。聚合过程计算每日活跃度（`DailyActivity`）、按模型的每日 token 分布（`DailyModelTokens`）、会话时长统计（`SessionStats`）、连续活跃天数（`StreakInfo`）等指标。结果通过 `statsCache` 机制缓存到磁盘，避免重复计算。Sources: [src/utils/stats.ts](src/utils/stats.ts#L53-L150)

## OpenTelemetry 指标集成

成本追踪系统与 OpenTelemetry 指标体系深度集成，支持将成本和 token 数据导出到外部监控系统。**指标注册**在 `setMeter` 函数中完成：它接收一个 `Meter` 实例和一个计数器工厂函数，创建 `costCounter`（`claude_code.cost.usage`，单位 USD）和 `tokenCounter`（`claude_code.token.usage`，单位 tokens）两个计数器。Sources: [src/bootstrap/state.ts](src/bootstrap/state.ts#L948-L987)

**指标更新**在 `addToTotalSessionCost` 中触发：每次成本累加时，系统调用 `costCounter.add(cost, { model, speed? })` 记录成本，并调用 `tokenCounter.add` 四次分别记录输入、输出、缓存读取、缓存写入的 token 数量。这些指标带有模型名称、token 类型等属性，支持在监控后端进行多维度聚合分析。Sources: [src/cost-tracker.ts](src/cost-tracker.ts#L291-L301)

**StatsStore 机制**提供了一套轻量级的直方图统计能力：`StatsContext` 通过 `createStatsStore` 创建一个内存统计存储，支持 `increment`（计数器）、`set`（仪表）、`observe`（直方图）三种操作。直方图使用蓄水池采样算法维护固定大小的样本集（1024 个），计算 p50、p95、p99 等百分位数。进程退出前，`StatsProvider` 自动调用 `store.getAll()` 获取所有指标，并通过 `saveCurrentProjectConfig` 持久化到 `lastSessionMetrics` 字段。Sources: [src/context/stats.tsx](src/context/stats.tsx#L28-L98)

## 与其他系统的协作

**QueryEngine 集成**在每次 API 调用完成后触发成本累加：`QueryEngine` 解析 API 响应中的 `usage` 字段，调用 `addToTotalSessionCost` 更新全局状态。这种设计确保了成本追踪的实时性——用户可以在任意时刻通过 `/cost` 命令查看当前累计成本。Sources: [src/cost-tracker.ts](src/cost-tracker.ts#L278-L324)

**Compact 服务集成**在对话压缩时保存成本快照：`compact` 服务在调用 `saveCurrentSessionCosts` 之前，会收集 FPS 性能指标（`FpsMetrics`），将其一并持久化到项目配置。这允许系统在统计报告中展示性能与成本的关联性。Sources: [src/costHook.ts](src/costHook.ts#L10-L16)

**Advisor 工具集成**递归处理辅助模型的成本：当 API 响应中包含 advisor 工具的用量时，`addToTotalSessionCost` 通过 `getAdvisorUsage` 提取这些用量，对每个 advisor 模型递归调用自身，将成本累加到主会话总计中。这种设计确保了多模型协作场景下的成本完整性。Sources: [src/cost-tracker.ts](src/cost-tracker.ts#L304-L322)

**Token Budget 集成**通过 `snapshotOutputTokensForTurn` 和 `getTurnOutputTokens` 函数实现：系统在每个对话轮次开始时快照当前输出 token 数量，在轮次进行中通过差值计算本轮消耗的 token。这与 token budget 机制配合，当输出 token 接近预算上限时触发警告或停止生成。Sources: [src/bootstrap/state.ts](src/bootstrap/state.ts#L724-L743)

## 高级特性与边界情况

**Fast Mode 动态定价**针对 Opus 4.6 模型的特殊计费场景：系统在 `getModelCosts` 函数中检测 `usage.speed === 'fast'` 标志，动态返回 `COST_TIER_30_150` 价格表（$30/$150 per Mtok），而非标准的 `COST_TIER_5_25`（$5/$25）。这种设计允许 Anthropic 在推出新特性时灵活调整计费策略，而无需修改核心成本计算逻辑。Sources: [src/utils/modelCost.ts](src/utils/modelCost.ts#L147-L153)

**未知模型容错**通过 `DEFAULT_UNKNOWN_MODEL_COST` 和 `hasUnknownModelCost` 标志实现：当遇到未在 `MODEL_COSTS` 映射表中定义的模型时，系统使用默认价格表（当前是 `COST_TIER_5_25`）计算成本，同时记录遥测事件并设置警告标志。`formatTotalCost` 在输出时检查该标志，如果为 true 则附加提示信息"costs may be inaccurate due to usage of unknown models"。Sources: [src/utils/modelCost.ts](src/utils/modelCost.ts#L89-L173), [src/cost-tracker.ts](src/cost-tracker.ts#L228-L244)

**会话切换保护**通过 `sessionSwitched` 信号和 `lastSessionId` 校验实现：`saveCurrentSessionCosts` 在持久化时会记录当前会话 ID；`restoreCostStateForSession` 在恢复时验证持久化的会话 ID 是否匹配，防止在多会话场景下恢复错误的历史成本。Sources: [src/cost-tracker.ts](src/cost-tracker.ts#L92-L95)

**历史统计缓存**通过 `statsCache` 机制优化性能：`aggregateClaudeCodeStatsForRange` 首先尝试从 `.claude/stats-cache.json` 加载缓存，如果缓存的日期范围覆盖请求范围，则直接返回缓存结果；否则扫描会话日志重新计算，并更新缓存文件。缓存使用文件锁（`withStatsCacheLock`）保护，避免并发写入冲突。Sources: [src/utils/stats.ts](src/utils/stats.ts#L14-L24)

**成本计算精度**通过 `formatCost` 函数控制显示格式：成本大于 $0.5 时使用 `toFixed(2)` 显示两位小数（如 `$1.23`），否则使用 `toFixed(4)` 显示四位小数（如 `$0.0034`）。这种设计在保持精度的同时提供友好的阅读体验。Sources: [src/cost-tracker.ts](src/cost-tracker.ts#L177-L179)

系统通过上述机制的组合，为 Claude Code 用户提供了透明、精确、实时的成本可见性，同时保持了架构的可扩展性和可维护性。开发者可以通过扩展 `MODEL_COSTS` 映射表支持新模型，通过 OpenTelemetry 指标接入企业监控系统，或通过 StatsStore 机制实现自定义的统计维度。