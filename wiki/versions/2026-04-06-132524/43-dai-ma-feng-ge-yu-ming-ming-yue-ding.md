Claude Code 项目遵循一套系统化的命名约定和代码组织原则，确保在超过 2000 个文件的大型 TypeScript 代码库中保持一致性与可维护性。本文档从文件命名、类型系统、标识符约定、导入规范等多个维度，解析项目采用的工程化实践，为开发者提供代码考古与静态分析的认知框架。

## 文件命名约定

项目采用**混合命名策略**，根据文件类型和功能域选择不同的命名模式。核心原则是：**单文件模块使用 camelCase，React 组件使用 PascalCase，命令目录使用 kebab-case，工具集合使用 PascalCase 目录**。

### TypeScript 模块文件

纯 TypeScript 文件（非 React 组件）统一使用 **camelCase** 命名，包括核心模块、工具函数、服务类等。例如：

- **核心引擎**：`queryEngine.ts`、`query.ts`、`task.ts`、`tool.ts`
- **桥接系统**：`bridgeApi.ts`、`bridgeConfig.ts`、`bridgeMain.ts`、`replBridge.ts`
- **工具函数**：`format.ts`、`file.ts`、`path.ts`、`hash.ts`
- **服务层**：`claude.ts`、`bootstrap.ts`、`index.ts`（入口文件）

这种约定使得通过文件名即可快速识别模块用途，例如 `bridgeApi.ts` 明确表示桥接 API 客户端，`formatFileSize` 函数位于 `format.ts` 模块中。

Sources: [queryEngine.ts](src/QueryEngine.ts#L1-L60), [bridgeApi.ts](src/bridge/bridgeApi.ts#L1-L80), [format.ts](src/utils/format.ts#L1-L80), [file.ts](src/utils/file.ts#L1-L50)

### React 组件文件

所有 React 组件文件（`.tsx` 扩展名）使用 **PascalCase** 命名，组件名与文件名保持一致。命名模式通常以功能类型后缀结尾：

- **Provider 组件**：`App.tsx`、`AppState.tsx`、`AppStateStore.tsx`
- **对话框组件**：`MCPServerApprovalDialog.tsx`、`RemoteEnvironmentDialog.tsx`
- **消息组件**：`Message.tsx`、`MessageRow.tsx`、`Messages.tsx`
- **状态组件**：`StatusLine.tsx`、`StatusNotice.tsx`

Sources: [App.tsx](src/components/App.tsx#L1-L56), [AppState.tsx](src/state/AppState.tsx#L1-L80)

### 命令目录与斜杠命令

`commands/` 目录下的子目录使用 **kebab-case** 命名，对应 CLI 中的 `/` 斜杠命令。这种命名在文件系统层面保持可读性，同时与命令行习惯一致：

```
commands/
├── add-dir/           → /add-dir
├── backfill-sessions/ → /backfill-sessions
├── commit-push-pr/    → /commit-push-pr
├── good-claude/       → /good-claude
├── install-github-app/ → /install-github-app
├── mcp/               → /mcp
├── pr_comments/       → /pr_comments (特殊：下划线)
```

命令入口文件通常为 `index.js` 或直接以命令名命名的单文件（如 `commit.ts`）。Sources: [commands.ts](src/commands.ts#L1-L60)

### 工具集合目录

`tools/` 目录下的工具使用 **PascalCase** 目录名，每个工具是一个独立的功能单元，内部包含主文件、UI 组件、限制配置等：

```
tools/
├── FileReadTool/
│   ├── FileReadTool.ts     (主逻辑)
│   ├── UI.tsx              (UI 组件)
│   ├── imageProcessor.ts   (图像处理)
│   ├── limits.ts           (限制配置)
│   └── prompt.ts           (提示词)
├── BashTool/
├── AgentTool/
├── WebFetchTool/
```

这种组织方式将相关功能聚合在同一目录，避免单个文件过大（`FileReadTool.ts` 超过 1100 行），同时保持清晰的职责边界。Sources: [FileReadTool.ts](src/tools/FileReadTool/FileReadTool.ts#L1-L80)

## 类型系统命名约定

TypeScript 类型系统是 Claude Code 架构的核心，项目采用**语义化类型命名**策略，通过类型名即可推断其用途和约束。

### 基础类型别名

**类型别名**使用 **PascalCase**，命名遵循"名词+类型后缀"模式：

- **实体类型**：`SessionId`、`AgentId`、`TaskId`（带 branded type 标记）
- **状态类型**：`TaskStatus`、`TaskType`、`PermissionMode`
- **配置类型**：`AppState`、`ToolUseContext`、`BridgeConfig`
- **结果类型**：`LocalCommandResult`、`PermissionResult`、`CompactionResult`

Sources: [ids.ts](src/types/ids.ts#L1-L45), [Task.ts](src/Task.ts#L1-L100), [permissions.ts](src/types/permissions.ts#L1-L80)

### Branded Types（品牌类型）

项目大量使用 **Branded Types** 技术防止类型混淆，通过交叉类型添加编译时标记：

```typescript
export type SessionId = string & { readonly __brand: 'SessionId' }
export type AgentId = string & { readonly __brand: 'AgentId' }

// 转换函数使用 as 类型断言
export function asSessionId(id: string): SessionId {
  return id as SessionId
}

// 验证函数返回 null 或 branded type
export function toAgentId(s: string): AgentId | null {
  return AGENT_ID_PATTERN.test(s) ? (s as AgentId) : null
}
```

这种模式确保 `SessionId` 和 `AgentId` 不能互换使用，即使底层都是 `string`。命名约定为：**实体名 + Id**（如 `SessionId`），转换函数为 **as + 类型名** 或 **to + 类型名**。Sources: [ids.ts](src/types/ids.ts#L1-L45)

### 联合类型与字面量类型

**联合类型**用于表示有限状态集合，类型名为 **PascalCase**，值使用 **camelCase**：

```typescript
export type TaskStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'killed'

export type TaskType =
  | 'local_bash'
  | 'local_agent'
  | 'remote_agent'
  | 'in_process_teammate'
  | 'local_workflow'
  | 'monitor_mcp'
  | 'dream'

export type PermissionBehavior = 'allow' | 'deny' | 'ask'
```

常量数组使用 **UPPER_SNAKE_CASE** 配合 `as const` 断言：

```typescript
export const EXTERNAL_PERMISSION_MODES = [
  'acceptEdits',
  'bypassPermissions',
  'default',
  'dontAsk',
  'plan',
] as const

export type ExternalPermissionMode = (typeof EXTERNAL_PERMISSION_MODES)[number]
```

Sources: [Task.ts](src/Task.ts#L6-L29), [permissions.ts](src/types/permissions.ts#L16-L44)

### 接口与对象类型

**对象类型**使用 **PascalCase**，属性名使用 **camelCase**。类型定义优先使用 `type` 而非 `interface`：

```typescript
export type TaskStateBase = {
  id: string
  type: TaskType
  status: TaskStatus
  description: string
  toolUseId?: string
  startTime: number
  endTime?: number
  outputFile: string
  outputOffset: number
  notified: boolean
}

export type PermissionRule = {
  source: PermissionRuleSource
  ruleBehavior: PermissionBehavior
  ruleValue: PermissionRuleValue
}
```

可选属性使用 `?` 标记，函数类型属性使用箭头函数语法。Sources: [Task.ts](src/Task.ts#L45-L57), [permissions.ts](src/types/permissions.ts#L75-L79)

## 标识符命名约定

### 变量与参数

**局部变量**和**函数参数**使用 **camelCase**，遵循"名词或名词短语"原则：

```typescript
const taskId = generateTaskId(type)
const bytes = randomBytes(8)
const baseUrl = deps.baseUrl
const accessToken = deps.getAccessToken()
```

布尔变量使用 **is/has/can/should** 前缀：

```typescript
const isTerminalTaskStatus = (status: TaskStatus): boolean => { ... }
const hasGrowthBookEnvOverride = ...
const canUserConfigureAdvisor = ...
```

Sources: [Task.ts](src/Task.ts#L27-L100), [format.ts](src/utils/format.ts#L9-L23)

### 函数命名

**函数**使用 **camelCase**，命名遵循"动词+名词"模式，清晰表达函数行为：

- **获取类**：`getSessionId`、`getAppState`、`getCwd`、`getModelUsage`
- **验证类**：`validateBridgeId`、`isTerminalTaskStatus`、`isPolicyAllowed`
- **转换类**：`formatFileSize`、`formatDuration`、`asSessionId`、`toAgentId`
- **创建类**：`createBridgeApiClient`、`createStore`、`generateTaskId`
- **检查类**：`pathExists`、`fileHistoryEnabled`、`isBypassPermissionsModeDisabled`

异步函数名不加 `Async` 后缀（TypeScript 类型系统已明确返回 `Promise`）。Sources: [format.ts](src/utils/format.ts#L9-L80), [bridgeApi.ts](src/bridge/bridgeApi.ts#L48-L68), [file.ts](src/utils/file.ts#L39-L46)

### 常量命名

**模块级常量**使用 **UPPER_SNAKE_CASE**，常量名应具有描述性：

```typescript
// API 限制常量
export const API_IMAGE_MAX_BASE64_SIZE = 5 * 1024 * 1024  // 5 MB
export const IMAGE_TARGET_RAW_SIZE = (API_IMAGE_MAX_BASE64_SIZE * 3) / 4
export const IMAGE_MAX_WIDTH = 2000
export const IMAGE_MAX_HEIGHT = 2000

// PDF 限制
export const PDF_TARGET_RAW_SIZE = 20 * 1024 * 1024  // 20 MB
export const API_PDF_MAX_PAGES = 100
export const PDF_EXTRACT_SIZE_THRESHOLD = 3 * 1024 * 1024

// 配置常量
export const MAX_OUTPUT_SIZE = 0.25 * 1024 * 1024  // 0.25MB
const BETA_HEADER = 'environments-2025-11-01'
const EMPTY_POLL_LOG_INTERVAL = 100
```

**枚举式常量对象**使用 **PascalCase** 作为对象名：

```typescript
const TASK_ID_PREFIXES: Record<string, string> = {
  local_bash: 'b',
  local_agent: 'a',
  remote_agent: 'r',
  in_process_teammate: 't',
  local_workflow: 'w',
  monitor_mcp: 'd',
}
```

Sources: [apiLimits.ts](src/constants/apiLimits.ts#L1-L80), [Task.ts](src/Task.ts#L79-L92), [bridgeApi.ts](src/bridge/bridgeApi.ts#L38-L74)

### 类与错误类型

**类名**使用 **PascalCase**，错误类以 `Error` 结尾：

```typescript
export class BridgeFatalError extends Error {
  readonly status: number
  readonly errorType: string | undefined
  
  constructor(message: string, status: number, errorType?: string) {
    super(message)
    this.name = 'BridgeFatalError'
    this.status = status
    this.errorType = errorType
  }
}
```

React 组件类遵循相同约定，但通常使用函数组件+ hooks 模式而非 class 组件。Sources: [bridgeApi.ts](src/bridge/bridgeApi.ts#L56-L66)

## 导入路径与模块组织

### 导入路径约定

项目统一使用 **`.js` 扩展名**的导入路径，即使源文件是 `.ts` 或 `.tsx`。这是 TypeScript 的 ESM 模块解析要求：

```typescript
// 正确：使用 .js 扩展名
import { formatFileSize } from './utils/format.js'
import { getSessionId } from './bootstrap/state.js'
import type { AppState } from './state/AppState.js'

// 错误：不使用扩展名或使用 .ts
import { formatFileSize } from './utils/format'  // ❌
import { getSessionId } from './bootstrap/state.ts'  // ❌
```

路径形式包括：
- **相对路径**：`./file.js`、`../file.js`、`../../services/api/file.js`
- **绝对路径**：`src/path/to/file.js`（使用 `src` 前缀）

Sources: [main.tsx](src/main.tsx#L1-L50), [format.ts](src/utils/format.ts#L3), [QueryEngine.ts](src/QueryEngine.ts#L1-L60)

### 导入顺序与分组

导入语句按以下顺序组织，组间用空行分隔：

1. **外部依赖**（Node.js 内置模块、npm 包）
2. **内部绝对路径导入**（`src/` 前缀）
3. **相对路径导入**（`./`、`../`）
4. **类型导入**（使用 `import type`）

```typescript
// 1. 外部依赖
import { feature } from 'bun:bundle'
import { Command as CommanderCommand } from '@commander-js/extra-typings'
import chalk from 'chalk'
import { readFileSync } from 'fs'
import React from 'react'

// 2. 内部绝对路径
import { getOauthConfig } from './constants/oauth.js'
import { getRemoteSessionUrl } from './constants/product.js'

// 3. 相对路径
import { formatFileSize } from './utils/format.js'
import { getCwd } from './utils/cwd.js'

// 4. 类型导入
import type { Root } from './ink.js'
import type { AppState } from './state/AppState.js'
```

Sources: [main.tsx](src/main.tsx#L1-L50), [claude.ts](src/services/api/claude.ts#L1-L60)

### 重新导出模式

为避免循环依赖和提供清晰 API，项目使用**桶文件**模式：

```typescript
// types/permissions.ts - 纯类型定义文件
import type { 
  PermissionAllowDecision,
  PermissionAskDecision,
  // ...
} from '../../types/permissions.js'

// 重新导出以保持向后兼容
export type {
  PermissionAllowDecision,
  PermissionAskDecision,
  PermissionDecision,
  // ...
}
```

```typescript
// AppState.tsx - 从 Store 文件重新导出
export { 
  type AppState, 
  type AppStateStore, 
  getDefaultAppState 
} from './AppStateStore.js'
```

Sources: [PermissionResult.ts](src/utils/permissions/PermissionResult.ts#L1-L21), [AppState.tsx](src/state/AppState.tsx#L23-L26)

## 代码组织原则

### 目录结构模式

项目按**功能域**组织目录，而非技术分层（controller/service/dao）。每个目录代表一个独立的子系统：

```
src/
├── bridge/          # IDE 桥接系统（15+ 文件）
├── commands/        # 斜杠命令（50+ 目录）
├── components/      # React UI 组件（100+ 文件）
├── constants/       # 全局常量配置
├── services/        # 外部服务集成（API、MCP、OAuth）
├── tools/           # 工具实现（40+ 工具）
├── types/           # 类型定义（共享类型）
├── utils/           # 工具函数（150+ 文件）
├── hooks/           # React Hooks（80+ 文件）
└── state/           # 状态管理
```

这种组织方式使得相关功能内聚，例如 `bridge/` 目录包含所有与 IDE 双向通信相关的代码，从 API 客户端到会话管理、认证逻辑。Sources: [目录结构](.)

### 单一职责文件

每个文件聚焦单一职责，通过文件名即可推断内容：

- **`format.ts`**：纯格式化函数（`formatFileSize`、`formatDuration`、`formatSecondsShort`）
- **`file.ts`**：文件系统操作（`pathExists`、`readFileSafe`、`addLineNumbers`）
- **`ids.ts`**：ID 类型定义（`SessionId`、`AgentId`、`toAgentId`）
- **`apiLimits.ts`**：API 限制常量（无运行时依赖，避免循环导入）

Sources: [format.ts](src/utils/format.ts#L1-L80), [ids.ts](src/types/ids.ts#L1-L45), [apiLimits.ts](src/constants/apiLimits.ts#L1-L80)

### 注释与文档

项目采用 **JSDoc 风格注释**，强调"为何而非如何"：

```typescript
/**
 * Formats a byte count to a human-readable string (KB, MB, GB).
 * @example formatFileSize(1536) → "1.5KB"
 */
export function formatFileSize(sizeInBytes: number): string { ... }

/**
 * Marker type for verifying analytics metadata doesn't contain sensitive data
 * 
 * This type forces explicit verification that string values being logged
 * don't contain code snippets, file paths, or other sensitive information.
 * 
 * Usage: `myString as AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS`
 */
export type AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS = never
```

关键设计决策使用**块注释**解释背景：

```typescript
// DCE: voice context is ant-only. External builds get a passthrough.
const VoiceProvider = feature('VOICE_MODE') 
  ? require('../context/voice.js').VoiceProvider 
  : ({ children }) => children
```

Sources: [format.ts](src/utils/format.ts#L6-L23), [index.ts](src/services/analytics/index.ts#L12-L33), [AppState.tsx](src/state/AppState.tsx#L13-L20)

## 特殊命名模式

### 私有/内部标识符

模块内部使用的辅助函数可能使用下划线前缀（但项目中较少使用）：

```typescript
// React compiler 内部变量（自动生成）
const $ = _c(9)
let t1, t2, t3

// 临时变量
const _temp = (state) => { ... }
```

Sources: [App.tsx](src/components/App.tsx#L20-L54)

### 类型断言标记

使用 **`_VERIFIED_`** 或 **`_PROTO_`** 前缀标记特殊类型：

```typescript
// 验证标记类型
export type AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS = never
export type AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS = never

// PII 标记类型（带权限访问控制）
export type AnalyticsMetadata_I_VERIFIED_THIS_IS_PII_TAGGED = never
```

Sources: [index.ts](src/services/analytics/index.ts#L19-L33)

### 常量验证函数

类型守卫函数使用 **`is`** 前缀：

```typescript
export function isTerminalTaskStatus(status: TaskStatus): boolean {
  return status === 'completed' || status === 'failed' || status === 'killed'
}
```

Sources: [Task.ts](src/Task.ts#L27-L29)

## 命名约定速查表

| 类别 | 约定 | 示例 | 文件位置示例 |
|------|------|------|-------------|
| TypeScript 模块文件 | camelCase | `bridgeApi.ts`、`format.ts` | `src/bridge/`, `src/utils/` |
| React 组件文件 | PascalCase | `App.tsx`、`Message.tsx` | `src/components/` |
| 命令目录 | kebab-case | `add-dir/`, `commit-push-pr/` | `src/commands/` |
| 工具目录 | PascalCase | `FileReadTool/`, `BashTool/` | `src/tools/` |
| 类型别名 | PascalCase | `SessionId`, `TaskStatus` | `src/types/ids.ts` |
| 类名 | PascalCase | `BridgeFatalError` | `src/bridge/bridgeApi.ts` |
| 函数 | camelCase | `formatFileSize`, `getSessionId` | `src/utils/format.ts` |
| 变量 | camelCase | `taskId`, `baseUrl` | 所有文件 |
| 常量 | UPPER_SNAKE_CASE | `API_IMAGE_MAX_BASE64_SIZE` | `src/constants/apiLimits.ts` |
| 布尔变量/函数 | is/has/can 前缀 | `isTerminalTaskStatus` | `src/Task.ts` |
| 导入路径 | .js 扩展名 | `from './utils/format.js'` | 所有导入语句 |

## 架构影响与最佳实践

这套命名约定不仅是风格指南，更是**架构决策的体现**：

1. **类型安全优先**：Branded Types 防止 ID 混淆，联合类型约束状态空间
2. **模块边界清晰**：功能域目录+单一职责文件降低耦合
3. **可追溯性**：文件名→模块功能→导出 API 的清晰映射
4. **静态分析友好**：一致的命名模式支持 IDE 智能提示和代码导航

开发者在进行代码考古时，可通过以下策略快速定位：

- **查找类型定义**：从 `src/types/` 开始，文件名即类型用途
- **理解命令实现**：`src/commands/<command-name>/` 目录
- **追踪工具逻辑**：`src/tools/<ToolName>/` 目录
- **定位工具函数**：`src/utils/<function-purpose>.ts` 文件

下一步建议阅读 [调试技巧：日志、诊断与性能分析](44-diao-shi-ji-qiao-ri-zhi-zhen-duan-yu-xing-neng-fen-xi)，了解如何利用日志系统和诊断工具进行动态分析，结合静态命名约定快速定位问题根源。