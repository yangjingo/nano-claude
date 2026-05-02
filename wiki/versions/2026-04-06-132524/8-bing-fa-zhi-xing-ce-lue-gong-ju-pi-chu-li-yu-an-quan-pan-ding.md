Claude Code 的工具执行系统采用了精细的**并发控制机制**，在确保系统安全性的同时最大化执行效率。核心设计理念是通过 **`isConcurrencySafe()` 判定方法**将工具分为两类：**并发安全工具**（如只读操作）可以同时执行多个实例，而**非并发安全工具**（如文件编辑、Shell 命令）必须独占执行。这种策略既避免了竞态条件和资源冲突，又充分利用了现代异步 I/O 的性能优势，在典型的代码探索场景中可以将多个文件读取、搜索操作并行化，显著减少用户等待时间。

## 一、并发安全的核心判定机制

### Tool 接口的 isConcurrencySafe 方法

每个工具都必须实现 `isConcurrencySafe(input)` 方法，该方法接收工具的输入参数，返回布尔值表示该次调用是否可以与其他工具并发执行。这个设计允许工具根据**具体的输入内容**动态判定安全性，而非简单地基于工具类型。默认情况下，`buildTool()` 工厂函数为所有工具提供 `false` 的保守默认值，确保未明确声明安全性的工具按串行方式执行。

```typescript
export type Tool<
  Input extends AnyObject = AnyObject,
  Output = unknown,
  P extends ToolProgressData = ToolProgressData,
> = {
  // ... 其他方法
  isConcurrencySafe(input: z.infer<Input>): boolean
  // ...
}
```

工具定义时通过 `buildTool()` 函数获得默认实现，未显式覆盖 `isConcurrencySafe` 的工具将继承 `false` 的默认值，这种 **fail-close 策略**确保了系统的保守安全性。当工具被标记为并发安全时，系统会将其与同一批次中的其他并发安全工具并行执行，而非安全工具则会阻塞后续工具的启动直到其完成。

Sources: [Tool.ts](src/Tool.ts#L362-L402), [Tool.ts](src/Tool.ts#L757-L769)

### 典型工具的并发安全实现策略

**BashTool** 展示了最复杂的判定逻辑，它通过 `isReadOnly()` 方法检查命令是否为只读操作，只有读取类命令（如 `ls`、`cat`、`grep`）才被允许并发执行，而写入类命令（如 `rm`、`mv`、`git commit`）则必须独占执行。这种基于命令语义的细粒度判定避免了多个 Shell 命令同时修改文件系统导致的竞态条件。

```typescript
export const BashTool = buildTool({
  // ...
  isConcurrencySafe(input) {
    return this.isReadOnly?.(input) ?? false;
  },
  isReadOnly(input) {
    const compoundCommandHasCd = commandHasAnyCd(input.command);
    const result = checkReadOnlyConstraints(input, compoundCommandHasCd);
    return result.behavior === 'allow';
  },
  // ...
})
```

**FileReadTool**、**GrepTool** 和 **GlobTool** 等只读工具则简单地将 `isConcurrencySafe()` 设为 `true`，因为它们不会修改任何状态，天然适合并发执行。这种设计使得 Claude 可以同时读取多个文件、搜索多个模式而无需等待每个操作顺序完成，在大型代码库探索场景中显著提升响应速度。

```typescript
export const FileReadTool = buildTool({
  // ...
  isConcurrencySafe() {
    return true
  },
  isReadOnly() {
    return true
  },
  // ...
})

export const GrepTool = buildTool({
  // ...
  isConcurrencySafe() {
    return true
  },
  isReadOnly() {
    return true
  },
  // ...
})
```

**FileEditTool** 和 **FileWriteTool** 等写入工具则依赖默认的 `false` 值，因为文件修改操作必须严格串行化以避免覆盖冲突。系统会在这些工具执行期间阻塞其他工具的启动，确保文件系统状态的确定性。

Sources: [BashTool.tsx](src/tools/BashTool/BashTool.tsx#L434-L441), [FileReadTool.ts](src/tools/FileReadTool/FileReadTool.ts#L373-L378), [GrepTool.ts](src/tools/GrepTool/GrepTool.ts#L183-L188)

## 二、工具批处理与执行编排

### partitionToolCalls 分批算法

当 LLM 返回包含多个 `tool_use` 块的响应时，系统通过 `partitionToolCalls()` 函数将这些工具调用**分组批处理**。该算法按照工具出现的顺序，将连续的并发安全工具归为同一批次，遇到非安全工具时则开启新批次。这种设计既保持了工具调用的原始顺序（对于依赖链很重要），又最大化了并发度。

```typescript
function partitionToolCalls(
  toolUseMessages: ToolUseBlock[],
  toolUseContext: ToolUseContext,
): Batch[] {
  return toolUseMessages.reduce((acc: Batch[], toolUse) => {
    const tool = findToolByName(toolUseContext.options.tools, toolUse.name)
    const parsedInput = tool?.inputSchema.safeParse(toolUse.input)
    const isConcurrencySafe = parsedInput?.success
      ? (() => {
          try {
            return Boolean(tool?.isConcurrencySafe(parsedInput.data))
          } catch {
            // 如果 isConcurrencySafe 抛出异常（如 shell-quote 解析失败），
            // 保守地将其视为非并发安全
            return false
          }
        })()
      : false
    // 如果当前工具和前一批次都是并发安全的，则合并到同一批次
    if (isConcurrencySafe && acc[acc.length - 1]?.isConcurrencySafe) {
      acc[acc.length - 1]!.blocks.push(toolUse)
    } else {
      // 否则开启新批次
      acc.push({ isConcurrencySafe, blocks: [toolUse] })
    }
    return acc
  }, [])
}
```

分批算法的关键特性是**保持原始顺序**：即使多个工具可以并发执行，它们的完成顺序可能不同，但结果会按照工具在 LLM 响应中的出现顺序依次提交给下一轮对话。这种设计确保了工具执行的**确定性语义**，使得用户可以预测和理解工具调用的行为。

Sources: [toolOrchestration.ts](src/services/tools/toolOrchestration.ts#L91-L116)

### 并发执行的协调机制

**runTools()** 函数作为批处理的顶层协调器，遍历每个批次并根据其安全属性选择执行策略。对于并发安全批次，它调用 `runToolsConcurrently()` 使用 `all()` 辅助函数同时启动所有工具，并通过 `Promise.race()` 机制在任意工具完成时立即 yield 结果。对于非安全批次，则通过 `runToolsSerially()` 严格串行执行，确保前一个工具完全结束后才启动下一个。

```typescript
export async function* runTools(
  toolUseMessages: ToolUseBlock[],
  assistantMessages: AssistantMessage[],
  canUseTool: CanUseToolFn,
  toolUseContext: ToolUseContext,
): AsyncGenerator<MessageUpdate, void> {
  let currentContext = toolUseContext
  for (const { isConcurrencySafe, blocks } of partitionToolCalls(
    toolUseMessages,
    currentContext,
  )) {
    if (isConcurrencySafe) {
      // 并发安全批次：并行执行
      for await (const update of runToolsConcurrently(
        blocks,
        assistantMessages,
        canUseTool,
        currentContext,
      )) {
        yield {
          message: update.message,
          newContext: currentContext,
        }
      }
    } else {
      // 非安全批次：串行执行
      for await (const update of runToolsSerially(
        blocks,
        assistantMessages,
        canUseTool,
        currentContext,
      )) {
        yield {
          message: update.message,
          newContext: currentContext,
        }
      }
    }
  }
}
```

并发执行通过 `getMaxToolUseConcurrency()` 函数控制最大并发数，默认值为 10，可通过环境变量 `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` 调整。这个限制防止了系统在处理大量并发工具调用时过度消耗资源（如文件描述符、网络连接），同时也为未来的动态资源管理预留了配置接口。

```typescript
function getMaxToolUseConcurrency(): number {
  return (
    parseInt(process.env.CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY || '', 10) || 10
  )
}
```

Sources: [toolOrchestration.ts](src/services/tools/toolOrchestration.ts#L19-L82), [toolOrchestration.ts](src/services/tools/toolOrchestration.ts#L8-L12)

## 三、StreamingToolExecutor 的流式执行架构

### 流式场景下的并发控制

**StreamingToolExecutor** 类专门处理 LLM **流式响应**场景下的工具执行，它在 `tool_use` 块逐步到达时就立即启动工具执行，而非等待整个响应完成。这种设计显著降低了**首字节延迟**，用户可以在 LLM 仍在生成后续工具调用时就看到第一批工具的执行结果。执行器通过 `TrackedTool` 数据结构跟踪每个工具的状态、安全属性和执行结果。

```typescript
type TrackedTool = {
  id: string
  block: ToolUseBlock
  assistantMessage: AssistantMessage
  status: ToolStatus
  isConcurrencySafe: boolean
  promise?: Promise<void>
  results?: Message[]
  pendingProgress: Message[]
  contextModifiers?: Array<(context: ToolUseContext) => ToolUseContext>
}
```

`addTool()` 方法在每个 `tool_use` 块到达时被调用，它会解析工具输入并调用 `isConcurrencySafe()` 判定安全性，然后立即调用 `processQueue()` 尝试启动执行。`canExecuteTool()` 方法检查当前并发状态，只有当**没有工具正在执行**，或**所有正在执行的工具都是并发安全且新工具也是并发安全**时，才允许启动新工具。

```typescript
private canExecuteTool(isConcurrencySafe: boolean): boolean {
  const executingTools = this.tools.filter(t => t.status === 'executing')
  return (
    executingTools.length === 0 ||
    (isConcurrencySafe && executingTools.every(t => t.isConcurrencySafe))
  )
}
```

`processQueue()` 方法遍历队列中的所有工具，对满足执行条件的工具调用 `executeTool()` 启动异步执行。当遇到无法执行的非安全工具时，处理会停止（因为必须保持顺序），但后续的安全工具如果条件允许仍可启动。这种**动态调度策略**在保证安全性的同时最大化了并行度。

Sources: [StreamingToolExecutor.ts](src/services/tools/StreamingToolExecutor.ts#L21-L32), [StreamingToolExecutor.ts](src/services/tools/StreamingToolExecutor.ts#L76-L124), [StreamingToolExecutor.ts](src/services/tools/StreamingToolExecutor.ts#L129-L135)

### 错误级联与兄弟进程取消

StreamingToolExecutor 实现了**错误级联机制**：当 BashTool 执行失败时，它会通过 `siblingAbortController` 取消所有正在执行的其他 BashTool 实例。这种设计基于 Shell 命令通常存在**隐式依赖链**的假设（例如 `mkdir dir && cd dir`），一个命令失败通常意味着后续命令也会失败或产生错误结果。取消兄弟进程可以快速失败，避免浪费计算资源和用户等待时间。

```typescript
if (isErrorResult) {
  thisToolErrored = true
  // 只有 Bash 错误会取消兄弟进程。Bash 命令通常有隐式依赖链
  // （例如 mkdir 失败 → 后续命令无意义）。
  // Read/WebFetch 等是独立的 — 一个失败不应影响其他。
  if (tool.block.name === BASH_TOOL_NAME) {
    this.hasErrored = true
    this.erroredToolDescription = this.getToolDescription(tool)
    this.siblingAbortController.abort('sibling_error')
  }
}
```

被取消的工具会收到合成错误消息，说明取消原因（`sibling_error`、`user_interrupted` 或 `streaming_fallback`）。对于用户中断（按 ESC 拒绝），系统使用 `REJECT_MESSAGE` 生成友好的错误提示，而非原始的技术错误信息。这种**错误分类与传播机制**确保了用户能够理解工具失败的上下文。

```typescript
private createSyntheticErrorMessage(
  toolUseId: string,
  reason: 'sibling_error' | 'user_interrupted' | 'streaming_fallback',
  assistantMessage: AssistantMessage,
): Message {
  if (reason === 'user_interrupted') {
    return createUserMessage({
      content: [{
        type: 'tool_result',
        content: withMemoryCorrectionHint(REJECT_MESSAGE),
        is_error: true,
        tool_use_id: toolUseId,
      }],
      toolUseResult: 'User rejected tool use',
      sourceToolAssistantUUID: assistantMessage.uuid,
    })
  }
  // ... 其他错误类型的处理
}
```

Sources: [StreamingToolExecutor.ts](src/services/tools/StreamingToolExecutor.ts#L354-L364), [StreamingToolExecutor.ts](src/services/tools/StreamingToolExecutor.ts#L153-L205)

## 四、上下文修改器的串行化约束

### contextModifier 的执行时机

工具执行可以通过返回 `contextModifier` 来修改后续工具的执行上下文，例如更新文件缓存状态、添加新的工作目录等。然而，**并发执行的工具不支持上下文修改器**，因为多个工具同时修改上下文会导致竞态条件和不确定性行为。系统通过类型系统和运行时检查强制这一约束：只有非并发安全的工具（必然串行执行）才能应用上下文修改器。

```typescript
// 注意：当前不支持并发工具的上下文修改器。
// 目前没有工具在使用，但如果要在并发工具中使用，
// 需要在这里实现支持逻辑。
if (!tool.isConcurrencySafe && contextModifiers.length > 0) {
  for (const modifier of contextModifiers) {
    this.toolUseContext = modifier(this.toolUseContext)
  }
}
```

在 `runTools()` 的批处理逻辑中，并发安全批次的上下文修改器会被**延迟应用**：首先收集所有修改器到队列中，待整个批次完成后才依次应用。这种**批量应用策略**避免了修改器应用顺序对结果的影响，确保了并发执行的**确定性语义**。

```typescript
if (isConcurrencySafe) {
  const queuedContextModifiers: Record<
    string,
    ((context: ToolUseContext) => ToolUseContext)[]
  > = {}
  // 运行只读批次并发执行
  for await (const update of runToolsConcurrently(...)) {
    if (update.contextModifier) {
      const { toolUseID, modifyContext } = update.contextModifier
      if (!queuedContextModifiers[toolUseID]) {
        queuedContextModifiers[toolUseID] = []
      }
      queuedContextModifiers[toolUseID].push(modifyContext)
    }
    yield { message: update.message, newContext: currentContext }
  }
  // 批次完成后统一应用修改器
  for (const block of blocks) {
    const modifiers = queuedContextModifiers[block.id]
    if (!modifiers) continue
    for (const modifier of modifiers) {
      currentContext = modifier(currentContext)
    }
  }
  yield { newContext: currentContext }
}
```

Sources: [StreamingToolExecutor.ts](src/services/tools/StreamingToolExecutor.ts#L388-L395), [toolOrchestration.ts](src/services/tools/toolOrchestration.ts#L30-L63)

## 五、中断行为的精细化控制

### interruptBehavior 的两种模式

工具可以通过 `interruptBehavior()` 方法声明当用户在工具执行期间提交新消息时的行为：**`'cancel'`** 模式会立即停止工具并丢弃结果，**`'block'`** 模式则让工具继续执行，新消息在队列中等待。默认行为是 `'block'`，确保长时间运行的操作（如大文件读取、网络请求）不会被用户误操作中断。

```typescript
export type Tool<
  Input extends AnyObject = AnyObject,
  Output = unknown,
  P extends ToolProgressData = ToolProgressData,
> = {
  // ...
  /**
   * 当用户在工具运行时提交新消息应该发生什么。
   *
   * - `'cancel'` — 停止工具并丢弃其结果
   * - `'block'`  — 继续运行；新消息等待
   *
   * 未实现时默认为 `'block'`。
   */
  interruptBehavior?(): 'cancel' | 'block'
  // ...
}
```

`StreamingToolExecutor` 通过 `updateInterruptibleState()` 方法动态计算当前是否有可中断的工具在执行。只有当**所有正在执行的工具都声明为 `'cancel'` 模式**时，系统才认为当前状态可中断，并向 UI 层传递该状态。这种**全或无的策略**简化了状态管理，避免了部分工具可中断、部分不可中断的复杂交互场景。

```typescript
private updateInterruptibleState(): void {
  const executing = this.tools.filter(t => t.status === 'executing')
  this.toolUseContext.setHasInterruptibleToolInProgress?.(
    executing.length > 0 &&
      executing.every(t => this.getToolInterruptBehavior(t) === 'cancel'),
  )
}

private getToolInterruptBehavior(tool: TrackedTool): 'cancel' | 'block' {
  const definition = findToolByName(this.toolDefinitions, tool.block.name)
  if (!definition?.interruptBehavior) return 'block'
  try {
    return definition.interruptBehavior()
  } catch {
    return 'block'
  }
}
```

Sources: [Tool.ts](src/Tool.ts#L410-L416), [StreamingToolExecutor.ts](src/services/tools/StreamingToolExecutor.ts#L254-L260), [StreamingToolExecutor.ts](src/services/tools/StreamingToolExecutor.ts#L233-L241)

## 六、安全判定的实际应用场景

### 场景一：代码库探索

当 Claude 需要理解一个新代码库时，通常会发起多个并发操作：读取 `package.json`、搜索特定模式、列出目录结构等。由于这些都是只读操作，`partitionToolCalls()` 会将它们归为同一批次，`runToolsConcurrently()` 同时启动所有工具，显著缩短探索时间。如果其中混入了 `git log` 命令（通过 BashTool 执行），系统会自动将其分为新批次，因为 BashTool 需要根据命令内容判定是否只读。

**分批示例**：
```
批次 1（并发安全）:
  - Read package.json
  - Grep "function.*export"
  - Glob "**/*.ts"

批次 2（非安全，串行）:
  - Bash "git log --oneline -10"

批次 3（并发安全）:
  - Read README.md
  - Read tsconfig.json
```

### 场景二：代码重构

在重构场景中，Claude 可能先并发读取多个相关文件，然后串行执行编辑操作。`partitionToolCalls()` 会自动创建清晰的分界：所有 Read 操作在同一批次并发执行，后续的 Edit 操作各自独占一个批次。这种**自然的批处理边界**既保证了读取的高效性，又确保了编辑的安全性。

**分批示例**：
```
批次 1（并发安全）:
  - Read src/utils/helper.ts
  - Read src/utils/parser.ts
  - Read src/types/index.ts

批次 2（非安全，串行）:
  - Edit src/utils/helper.ts

批次 3（非安全，串行）:
  - Edit src/utils/parser.ts

批次 4（非安全，串行）:
  - Edit src/types/index.ts
```

### 场景三：测试与部署

在测试和部署流程中，BashTool 的**错误级联机制**特别有价值。如果 `npm test` 失败，系统会立即取消后续的 `npm run build` 和部署命令，避免浪费时间和资源。对于独立的只读检查（如 `git status`、`docker ps`），它们可以与测试命令并发执行，提供实时的环境状态信息。

Sources: [toolOrchestration.ts](src/services/tools/toolOrchestration.ts#L91-L116)

## 七、性能优化与资源管理

### 并发数的动态调整

默认的 10 个并发工具限制在大多数场景下提供了良好的性能平衡，但在特定场景下可能需要调整。对于**I/O 密集型操作**（如大量文件读取、网络请求），可以适当提高并发数以充分利用系统资源；对于**CPU 密集型操作**（如大文件解析、复杂计算），降低并发数可以避免过度竞争 CPU 时间。通过环境变量 `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` 的配置，高级用户可以根据工作负载特性优化性能。

```bash
# 提高并发数以加速大量文件读取
export CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY=20

# 降低并发数以减少 CPU 竞争
export CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY=5
```

### 进度消息的即时反馈

StreamingToolExecutor 通过 `pendingProgress` 数组和 `progressAvailableResolve` 信号机制，实现了**进度消息的即时反馈**。工具在执行过程中可以发送进度更新（如 "正在读取文件 1/10"），这些消息会被立即 yield 给 UI 层显示，而非等待工具完全结束。这种设计显著提升了用户体验，让用户在长时间操作期间能够看到实时进展。

```typescript
if (update.message) {
  // 进度消息立即 yield
  if (update.message.type === 'progress') {
    tool.pendingProgress.push(update.message)
    // 通知有进度可用
    if (this.progressAvailableResolve) {
      this.progressAvailableResolve()
      this.progressAvailableResolve = undefined
    }
  } else {
    messages.push(update.message)
  }
}
```

Sources: [toolOrchestration.ts](src/services/tools/toolOrchestration.ts#L8-L12), [StreamingToolExecutor.ts](src/services/tools/StreamingToolExecutor.ts#L366-L378)

## 八、最佳实践与设计原则

### 工具开发者的并发安全声明

开发新工具时，应遵循以下原则声明并发安全性：

1. **只读工具应显式声明 `isConcurrencySafe() => true`**，即使默认值是 `false`，显式声明能提高代码可读性和意图清晰度
2. **写入工具无需显式声明**，默认的 `false` 值已提供正确的保守行为
3. **条件性安全工具应实现动态判定**，如 BashTool 根据命令内容判断是否只读
4. **避免在并发安全工具中使用 `contextModifier`**，当前架构不支持，会导致未定义行为

### 系统架构的演进方向

当前的并发执行系统为未来的优化预留了多个扩展点：

1. **动态并发数调整**：基于系统负载、工具类型、历史执行时间等因素动态计算最优并发数
2. **优先级调度**：为不同类型的工具分配优先级，确保关键路径上的操作优先执行
3. **依赖图分析**：通过静态分析工具输入参数，自动识别依赖关系并优化执行顺序
4. **资源感知调度**：考虑文件描述符、网络连接、内存等资源限制，避免过度并发导致的资源枯竭

这些演进方向都建立在当前 `isConcurrencySafe()` 判定机制和批处理架构的基础之上，展示了该设计的**可扩展性和前瞻性**。