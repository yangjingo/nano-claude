Claude Code 的计划模式是一个强大的架构设计阶段，允许 AI 在编写代码之前先探索代码库、理解现有模式并设计实现方案。本文档深入分析 EnterPlanMode 和 ExitPlanMode 工具的交互机制、状态管理和用户确认流程。

## 架构概览

计划模式切换涉及工具层、权限系统、UI 组件和全局状态的协同工作。核心组件包括 **EnterPlanModeTool** 和 **ExitPlanModeV2Tool**（负责工具调用逻辑）、**EnterPlanModePermissionRequest** 和 **ExitPlanModePermissionRequest**（处理用户交互对话框），以及 **handlePlanModeTransition**（管理全局状态转换）。

Sources: [EnterPlanModeTool.ts](src/tools/EnterPlanModeTool/EnterPlanModeTool.ts#L1-L127), [ExitPlanModeV2Tool.ts](src/tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts#L1-L494), [EnterPlanModePermissionRequest.tsx](src/components/permissions/EnterPlanModePermissionRequest/EnterPlanModePermissionRequest.tsx#L1-L122), [ExitPlanModePermissionRequest.tsx](src/components/permissions/ExitPlanModePermissionRequest/ExitPlanModePermissionRequest.tsx#L1-L768)

## EnterPlanMode：进入计划模式

### 工具触发条件

EnterPlanMode 工具通过智能判断是否需要进入计划模式来避免不必要的规划开销。该工具会在以下场景主动触发：**新功能实现**（如添加认证系统）、**多种可行方案**（如选择缓存策略）、**代码修改**（如重构组件）、**架构决策**（如选择状态管理方案）、**多文件变更**（超过 2-3 个文件）、**需求不明确**（需要先探索理解范围），以及**用户偏好重要**（实现路径有多种合理选择）。

工具会跳过计划模式的情况包括：单行或少量行的修复、添加明确需求的单个函数、用户给出非常具体详细指令的任务、纯研究/探索任务（应使用 Agent 工具），以及用户明确表示"让我们开始做 X"的场景。

Sources: [prompt.ts](src/tools/EnterPlanModeTool/prompt.ts#L28-L171)

### 权限请求流程

当 AI 调用 EnterPlanMode 时，系统会触发权限请求对话框，要求用户确认是否进入计划模式。对话框展示清晰的信息："Claude 想要进入计划模式来探索和设计实现方案"，并说明在计划模式中 AI 将：彻底探索代码库、识别现有模式、设计实现策略。关键提示是：**在用户批准计划之前不会进行任何代码更改**。

用户有两个选择：**"是的，进入计划模式"** 或 **"不，现在开始实现"**。如果选择"是"，系统会记录 `tengu_plan_enter` 事件，调用 `handlePlanModeTransition` 函数更新全局状态，并通过 `toolUseConfirm.onAllow` 设置权限模式为 'plan'。如果选择"不"，对话框关闭并拒绝工具调用，AI 将直接开始实现。

Sources: [EnterPlanModePermissionRequest.tsx](src/components/permissions/EnterPlanModePermissionRequest/EnterPlanModePermissionRequest.tsx#L23-L52), [EnterPlanModeTool.ts](src/tools/EnterPlanModeTool/EnterPlanModeTool.ts#L79-L103)

### 状态转换机制

`handlePlanModeTransition` 函数负责管理计划模式的状态转换逻辑。当切换**到**计划模式时（`toMode === 'plan'` 且 `fromMode !== 'plan'`），函数会清除任何待处理的退出附件标志 `needsPlanModeExitAttachment = false`，防止用户快速切换时同时发送 `plan_mode` 和 `plan_mode_exit` 附件。

进入计划模式时，`EnterPlanModeTool.call()` 方法会更新 AppState，将 `toolPermissionContext.mode` 设置为 'plan'，并通过 `prepareContextForPlanMode` 函数运行分类器激活副作用（当用户的 `defaultMode` 为 'auto' 时）。这确保了即使在计划模式中，如果用户之前启用了自动模式，系统也能正确处理权限上下文。

Sources: [state.ts](src/bootstrap/state.ts#L1322-L1350), [EnterPlanModeTool.ts](src/tools/EnterPlanModeTool/EnterPlanModeTool.ts#L85-L103)

## ExitPlanMode：退出计划模式

### 计划文件管理

退出计划模式时，系统会读取计划文件内容并将其呈现给用户审批。计划文件路径由 `getPlanFilePath()` 生成，主会话使用 `{planSlug}.md` 格式，子代理使用 `{planSlug}-agent-{agentId}.md` 格式。`planSlug` 是通过 `generateWordSlug()` 生成的随机词组，在会话首次访问时缓存，确保整个会话期间使用同一个计划文件。

如果用户通过 Ctrl+G 在外部编辑器中编辑了计划文件，ExitPlanModePermissionRequest 会检测到内容变化并设置 `planEditedLocally` 标志。这个标志用于确保工具结果中包含编辑后的计划内容，使 AI 能够看到用户的修改。

Sources: [plans.ts](src/utils/plans.ts#L63-L165), [ExitPlanModePermissionRequest.tsx](src/components/permissions/ExitPlanModePermissionRequest/ExitPlanModePermissionRequest.tsx#L209-L238)

### 多维度审批选项

ExitPlanMode 对话框提供了丰富的审批选项，根据会话状态和用户权限动态生成。核心选项包括：

**清空上下文选项**（`showClearContextOnPlanAccept = true` 时显示）：**`yes-bypass-permissions`**（绕过所有权限检查）、**`yes-accept-edits`**（自动接受文件编辑）、**`yes-auto-clear-context`**（恢复自动模式并清空上下文，仅当自动模式可用时）。这些选项会设置 `initialMessage` 触发 REPL 清空对话上下文并启动新查询。

**保留上下文选项**：**`yes-accept-edits-keep-context`**（保持当前对话，自动接受编辑）、**`yes-default-keep-context`**（保持当前对话，使用默认权限模式）、**`yes-resume-auto-mode`**（保持当前对话，恢复自动模式，仅当自动模式可用时）。这些选项通过 `buildPermissionUpdates` 构建权限更新并直接应用到当前会话。

**特殊选项**：**`ultraplan`**（将计划传送到 CCR 进行多代理细化，仅当 `feature('ULTRAPLAN')` 启用且没有活跃会话时显示）、**`no`**（拒绝计划，保持在计划模式中）。当用户选择"no"时，如果提供了反馈文本或粘贴了图片，系统会将这些反馈发送给 AI 以帮助改进计划。

Sources: [ExitPlanModePermissionRequest.tsx](src/components/permissions/ExitPlanModePermissionRequest/ExitPlanModePermissionRequest.tsx#L211-L398), [ExitPlanModeV2Tool.ts](src/tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts#L232-L389)

### 团队成员审批流程

对于团队成员（teammate），计划模式的行为有所不同。如果 `isPlanModeRequired()` 返回 true（表示该成员被配置为必须使用计划模式），ExitPlanMode 不会显示本地对话框，而是将计划审批请求发送给团队负责人。

审批请求包含以下信息：`type: 'plan_approval_request'`、`from`（代理名称）、`timestamp`、`planFilePath`、`planContent` 和 `requestId`（唯一标识符）。请求通过 `writeToMailbox('team-lead', ...)` 发送到团队负责人的邮箱。

团队成员的工具结果会显示："您的计划已提交给团队负责人审批。计划文件：{filePath}。接下来会发生什么：1. 等待团队负责人审查您的计划 2. 您将在收件箱中收到批准/拒绝消息 3. 如果批准，您可以继续实施 4. 如果拒绝，根据反馈完善您的计划。**重要提示**：在收到批准之前不要继续。检查您的收件箱以获取响应。请求 ID：{requestId}"。

Sources: [ExitPlanModeV2Tool.ts](src/tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts#L256-L292), [ExitPlanModeV2Tool.ts](src/tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts#L395-L435)

### 自动模式集成

当 `feature('TRANSCRIPT_CLASSIFIER')` 启用时，计划模式与自动模式有深度集成。如果用户在计划模式期间使用了自动模式（通过 `isAutoModeActive()` 检测），退出计划模式时会根据目标模式决定是否停用自动模式：

如果**不**恢复到自动模式（例如选择 `yes-accept-edits` 或 `yes-default-keep-context`），系统会调用 `setAutoModeActive(false)`、设置 `needsAutoModeExitAttachment = true`，并通过 `restoreDangerousPermissions` 恢复之前为自动模式剥离的危险权限。

如果恢复到自动模式（选择 `yes-resume-auto-mode` 或 `yes-auto-clear-context`），系统保持 `autoModeActive = true` 并继续使用剥离后的权限上下文。这确保了自动模式的安全边界在整个计划模式生命周期中保持一致。

Sources: [ExitPlanModeV2Tool.ts](src/tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts#L298-L340), [ExitPlanModePermissionRequest.tsx](src/components/permissions/ExitPlanModePermissionRequest/ExitPlanModePermissionRequest.tsx#L283-L328)

### 会话自动命名

当用户批准计划时（选择任何"yes"选项），系统会自动从计划内容生成会话名称，除非用户已经通过 `/rename` 或 `--name` 设置了自定义名称。自动命名通过 `generateSessionName()` 实现，该函数使用 Haiku 模型分析计划的前 1000 个字符（计划通常在开头总结目标，结尾是测试步骤）生成简洁的 kebab-case 名称。

生成的名称会保存到会话元数据（`saveCustomTitle` 和 `saveAgentName`，来源标记为 'auto'），并更新 `AppState.standaloneAgentContext.name` 以在提示边框徽章中显示。对于清空上下文的选项，命名应用于**新生成的**会话 ID（`regenerateSessionId()` 在 `setInitialMessage` 之前调用），确保命名的是执行会话而不是被放弃的规划会话。

Sources: [ExitPlanModePermissionRequest.tsx](src/components/permissions/ExitPlanModePermissionRequest/ExitPlanModePermissionRequest.tsx#L102-L139), [ExitPlanModePermissionRequest.tsx](src/components/permissions/ExitPlanModePermissionRequest/ExitPlanModePermissionRequest.tsx#L332-L336)

## UI 渲染与交互

### EnterPlanMode 渲染

EnterPlanMode 工具的 UI 渲染非常简洁。`renderToolUseMessage()` 返回 null（不在工具调用时显示任何内容），`renderToolResultMessage()` 显示一个带有计划模式颜色（通过 `getModeColor('plan')` 获取）的黑色圆点和"已进入计划模式"文本，下方有灰色说明："Claude 现在正在探索和设计实现方案"。

`renderToolUseRejectedMessage()` 显示"用户拒绝进入计划模式"，使用默认模式颜色。这种简洁的渲染避免了视觉噪音，同时清晰地传达了状态变化。

Sources: [UI.tsx](src/tools/EnterPlanModeTool/UI.tsx#L1-L33)

### ExitPlanMode 渲染

ExitPlanMode 的渲染更加复杂，根据输出状态显示不同内容。**空计划**时显示简单的"已退出计划模式"。**等待团队负责人审批**时显示"计划已提交给团队负责人审批"，下方显示计划文件路径和"等待团队负责人审查和批准..."。

**用户批准**时显示"用户批准了 Claude 的计划"，在 MessageResponse 组件中渲染计划内容（使用 Markdown 组件），并显示"计划保存到：{displayPath} · /plan 编辑"提示。**用户拒绝**时调用 `RejectedPlanMessage` 组件，显示"用户拒绝了 Claude 的计划："并在带边框的框中显示计划内容。

Sources: [UI.tsx](src/tools/ExitPlanModeTool/UI.tsx#L1-L82), [RejectedPlanMessage.tsx](src/components/messages/UserToolResultMessage/RejectedPlanMessage.tsx#L1-L31)

### 外部编辑器集成

ExitPlanModePermissionRequest 支持 **Ctrl+G** 快捷键在外部编辑器中编辑计划文件。按下 Ctrl+G 时，系统调用 `editFileInEditor(planFilePath)`（V2 工具）或 `editPromptInEditor(currentPlan)`（V1 工具），在用户的 `$EDITOR` 中打开计划文件。

编辑完成后，如果内容发生变化，系统更新 `currentPlan` 状态、设置 `planEditedLocally = true`、显示"✓ 计划已保存！"消息（5 秒后自动隐藏）。外部编辑器名称通过 `toIDEDisplayName(getExternalEditor())` 获取并显示在对话框底部："ctrl-g 在 {editorName} 中编辑 · {displayPath}"。

**Shift+Tab** 快捷键提供快速审批路径，立即选择"auto-accept edits"选项（根据 `showClearContext` 选择 `yes-accept-edits` 或 `yes-accept-edits-keep-context`），加快工作流程。

Sources: [ExitPlanModePermissionRequest.tsx](src/components/permissions/ExitPlanModePermissionRequest/ExitPlanModePermissionRequest.tsx#L284-L308)

### 粘性底部栏

对于非空计划，ExitPlanModePermissionRequest 使用粘性底部栏（sticky footer）渲染选项列表，确保用户在滚动长计划时选项始终可见。`setStickyFooter` 回调在 `useLayoutEffect` 中设置，渲染一个带计划模式边框的框，包含"您想继续吗？"提示和 Select 组件。

Select 组件支持图片粘贴（通过 `onImagePaste` 回调），用户可以粘贴截图作为反馈。粘贴的图片通过 `storeImage` 和 `cacheImagePath` 存储，并在选择"no"时转换为 `ImageBlockParam[]`（经过 `maybeResizeAndDownsampleImageBlock` 处理）附加到拒绝消息中。

Sources: [ExitPlanModePermissionRequest.tsx](src/components/permissions/ExitPlanModePermissionRequest/ExitPlanModePermissionRequest.tsx#L494-L547)

## 工具提示与行为指导

### EnterPlanMode 提示词

EnterPlanMode 工具的提示词根据用户类型（`USER_TYPE === 'ant'` vs 外部用户）提供不同指导。**外部用户**版本强调"主动使用此工具进行非平凡实现任务"，列出了 7 种应该使用计划模式的场景（新功能、多种方案、代码修改、架构决策、多文件变更、需求不明确、用户偏好重要），并提供了大量正反面示例。

**Ant 用户**版本更加克制，强调"当任务对正确方法有真正的歧义时使用此工具"，列出了 3 种核心场景（重大架构歧义、需求不明确、高影响重构），并明确指出应该跳过计划模式的情况：任务即使涉及多个文件也很直接、用户请求足够具体、添加具有明显实现模式的功能、bug 修复、研究任务、用户说"让我们开始做 X"。

两个版本都强调"此工具需要用户批准"，但外部版本更倾向于"如有疑问，选择规划"，而 Ant 版本倾向于"如有疑问，开始工作并使用 AskUserQuestion 处理具体问题"。

Sources: [prompt.ts](src/tools/EnterPlanModeTool/prompt.ts#L28-L171)

### ExitPlanMode 提示词

ExitPlanMode 提示词简洁明了："当您在计划模式中并已完成计划编写到计划文件，准备好让用户审批时使用此工具。"提示词强调：**工具不接受计划内容作为参数**——它会从您写入的文件中读取计划；此工具只是信号您已完成规划并准备好让用户审查和批准。

重要指导包括：仅当任务需要规划**实现步骤**时使用此工具（对于研究任务不要使用）；如果在需求或方法上有未解决的问题，先使用 AskUserQuestion；一旦计划最终确定，使用**此工具**请求批准——**不要**使用 AskUserQuestion 问"这个计划可以吗？"或"我应该继续吗？"，因为那正是此工具的功能。

Sources: [prompt.ts](src/tools/ExitPlanModeTool/prompt.ts#L1-L30)

## 面板禁用与通道限制

当 `--channels` 标志激活时（用户可能在 Telegram/Discord 上，不在 TUI 前），EnterPlanMode 和 ExitPlanMode 都会被禁用。这是通过 `getAllowedChannels().length > 0` 检查实现的。禁用的原因是计划审批对话框需要终端交互，在通道模式下会挂起。两个工具配对禁用，防止计划模式成为"可以进入但永远无法离开的陷阱"。

Sources: [EnterPlanModeTool.ts](src/tools/EnterPlanModeTool/EnterPlanModeTool.ts#L46-L56), [ExitPlanModeV2Tool.ts](src/tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts#L84-L95)

## 实现细节与最佳实践

### 计划文件持久化

计划文件存储在 `getPlansDirectory()` 返回的目录中，默认是 `~/.claude/plans`，但可以通过 `settings.plansDirectory` 自定义（相对于项目根目录）。目录在首次访问时通过 `mkdirSync` 创建（`recursive: true` 使其在已存在时成为无操作）。路径验证确保自定义目录在项目根目录内，防止路径遍历攻击。

`copyPlanForResume` 函数处理会话恢复时的计划文件恢复。如果计划文件丢失（ENOENT），系统尝试从文件快照（`findFileSnapshotEntry`）或消息历史中恢复计划内容，然后写入磁盘。这确保了即使在远程会话（CCR）中文件不持久，恢复后也能继续使用之前的计划。

Sources: [plans.ts](src/utils/plans.ts#L84-L239)

### 验证输入与模式检查

ExitPlanMode 的 `validateInput` 方法在非队友上下文中检查当前模式。如果 `mode !== 'plan'`，验证失败并返回错误消息："您不在计划模式中。此工具仅用于在编写计划后退出计划模式。如果您的计划已被批准，继续实施。"这防止了在非计划模式中误调用工具。

`checkPermissions` 方法对队友返回 `{ behavior: 'allow' }` 以绕过权限 UI（由 `call()` 方法处理适当的行为），对非队友返回 `{ behavior: 'ask', message: '退出计划模式？' }` 触发对话框。

Sources: [ExitPlanModeV2Tool.ts](src/tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts#L162-L202)

### 工具结果映射

`mapToolResultToToolResultBlockParam` 方法根据输出状态生成不同的工具结果内容。对于**等待团队负责人审批**，返回详细的等待指令。对于**代理**（`isAgent === true`），返回简单的"用户已批准计划。现在您不需要做任何其他事情。请回复'ok'"。

对于**非代理用户批准**，工具结果包含完整的计划内容（即使是通过 Ctrl+G 编辑的），并标记为"批准的计划（用户编辑）"或"批准的计划"。如果计划为空，返回简单的"用户已批准退出计划模式。您现在可以继续。"如果 `hasTaskTool` 为 true（Agent 工具可用），附加提示建议使用 `TeamCreateTool` 并行化工作。

Sources: [ExitPlanModeV2Tool.ts](src/tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts#L395-L494)

## 相关主题

- 了解权限模式系统的整体架构，参见 [权限模式系统：default、plan、auto、bypass 等模式解析](9-quan-xian-mo-shi-xi-tong-default-plan-auto-bypass-deng-mo-shi-jie-xi)
- 深入权限请求流程与用户交互，参见 [权限请求流程：用户交互与决策传播](11-quan-xian-qing-qiu-liu-cheng-yong-hu-jiao-hu-yu-jue-ce-chuan-bo)
- 探索其他权限对话框实现，参见 [权限请求对话框：PermissionRequest 组件](34-quan-xian-qing-qiu-dui-hua-kuang-permissionrequest-zu-jian) 和 [MCP 服务器审批流程：MCPServerApprovalDialog](35-mcp-fu-wu-qi-shen-pi-liu-cheng-mcpserverapprovaldialog)