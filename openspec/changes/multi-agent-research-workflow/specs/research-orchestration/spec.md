# Spec Delta

## Purpose

主 agent 根据用户的原始问题和各子 agent 的最新结果决定下一步调用或结束本轮，并向调用方按实际发生顺序报告调度过程。

## ADDED Requirements

### Requirement: 主 agent 独占用户交互
系统 SHALL 只允许主 agent 接收用户发言并产生给用户的最终回答。子 agent MUST NOT 直接向用户输出最终回答。

#### Scenario: 子 agent 返回后仍由主 agent 作答
- **WHEN** 检索子 agent 完成一次调用
- **THEN** 控制权回到主 agent，该子 agent 的返回不直接成为给用户的最终回答

### Requirement: 每次只发出一条命令
主 agent 每次获得控制权时 SHALL 发出且只发出一条命令。命令 MUST 是检索、分析、研究方向或结束本轮之一，并带有本次调用参数。

#### Scenario: 检索之后可以再次检索
- **WHEN** 主 agent 已经发出过检索命令并收到返回
- **THEN** 主 agent 可以再次发出检索命令，并附带新的调用参数

#### Scenario: 一次控制权只执行一条命令
- **WHEN** 主 agent 获得一次控制权并发出一条命令
- **THEN** 系统在主 agent 下次获得控制权之前只执行这一条命令

### Requirement: 子 agent 互不调用
检索、分析和研究方向子 agent MUST NOT 调用另一个子 agent。

#### Scenario: 分析不触发检索
- **WHEN** 主 agent 发出分析命令且已有可用的检索结果
- **THEN** 只有分析子 agent 执行，检索子 agent 不会被分析子 agent 调用

### Requirement: 检索子 agent 调用检索工具
检索子 agent SHALL 把检索命令中的查询参数交给检索工具，并用工具的成功结果替换已保存的检索结果。工具失败时 MUST 把失败交给主 agent，且 MUST NOT 把它写成新的成功检索结果。

#### Scenario: 工具成功后更新检索结果
- **WHEN** 主 agent 发出带查询参数的检索命令，且检索工具返回成功
- **THEN** 已保存的检索结果变为该成功结果

#### Scenario: 工具失败不写成成功结果
- **WHEN** 检索工具返回失败
- **THEN** 主 agent 收到失败，该失败不成为新的成功检索结果

### Requirement: 状态只保留各子 agent 的最新成功结果
系统 SHALL 为检索、分析、研究方向各保留一份最新成功结果，并在会话中保留用户问题。主 agent MUST NOT 直接改写子 agent 的结果正文。

#### Scenario: 新的成功结果覆盖旧结果
- **WHEN** 同一子 agent 第二次成功返回
- **THEN** 状态中该子 agent 只保留第二次成功结果

### Requirement: 缺少前置结果时拒绝命令
分析命令在没有可用检索结果时 MUST NOT 执行。研究方向命令在没有可用检索结果或没有可用分析结果时 MUST NOT 执行。被拒绝的命令 MUST 把控制权交回主 agent，说明缺少的前置结果，且不得改写已有结果。

#### Scenario: 没有检索结果时拒绝分析
- **WHEN** 没有可用检索结果且主 agent 发出分析命令
- **THEN** 分析子 agent 不执行，控制权回到主 agent，并标明缺少检索结果

#### Scenario: 没有分析结果时拒绝研究方向
- **WHEN** 已有可用检索结果、没有可用分析结果，且主 agent 发出研究方向命令
- **THEN** 研究方向子 agent 不执行，控制权回到主 agent，并标明缺少分析结果

### Requirement: 失败结果不能充当前置结果
子 agent 的失败结果 MUST NOT 满足下游命令的前置条件，也 MUST NOT 覆盖该子 agent 上一次成功结果。主 agent SHALL 收到这次失败。

#### Scenario: 分析失败后不能做研究方向
- **WHEN** 最近一次分析失败，且此前没有可用的分析结果
- **THEN** 研究方向命令不执行，控制权回到主 agent，并标明缺少可用的分析结果

#### Scenario: 再次检索失败时保留原结果
- **WHEN** 已有成功的检索、分析和研究方向结果，且一次新的检索失败
- **THEN** 主 agent 收到这次失败，三份成功结果都保持不变

### Requirement: 新的检索成功后作废下游结果
成功写入新的检索结果后，系统 MUST 清除分析和研究方向的已有结果。

#### Scenario: 再次检索成功后下游结果不可用
- **WHEN** 状态中已有分析和研究方向结果，且一次新的检索成功写入
- **THEN** 检索结果变为新结果，分析结果和研究方向结果变为不可用

### Requirement: 子 agent 失败不结束本轮
子 agent 执行失败时，系统 SHALL 把控制权交回主 agent，且 MUST NOT 因此结束本轮。

#### Scenario: 分析失败后本轮仍继续
- **WHEN** 分析子 agent 执行失败
- **THEN** 主 agent 重新获得控制权，本轮尚未结束

### Requirement: 达到循环上限后只能结束
系统 SHALL 限制一轮用户发言中的子 agent 调用次数。达到上限后，主 agent MUST 只能结束本轮。最终回答 MUST 说明本轮因达到上限而停止。

#### Scenario: 上限之后不再执行检索
- **WHEN** 本轮子 agent 调用次数已经达到上限，主 agent 仍发出检索命令
- **THEN** 检索不执行，本轮以最终回答结束，且回答说明已达到上限

### Requirement: 最终回答只使用仍然有效的结果
主 agent 结束本轮时 SHALL 用中文回答用户的原始问题。回答中的论文事实、论文解释、研究空白、技术路线和创新点 MUST 来自当前仍可用的对应结果。已作废的结果 MUST NOT 被写成当前结论。

#### Scenario: 已作废的研究方向不进入当前结论
- **WHEN** 研究方向结果已因新的检索成功被清除，且主 agent 在没有新的研究方向结果时结束本轮
- **THEN** 最终回答不把已清除的研究方向内容作为当前结论

### Requirement: 同一会话可以接着使用已有结果
系统 SHALL 让同一会话的后续用户发言看到上一轮留下的检索结果、分析结果和研究方向结果。新的一轮 MUST 可以只调用其中一个子 agent。

#### Scenario: 下一轮只做分析
- **WHEN** 同一会话的上一轮留下了可用检索结果，用户发出新的发言，且主 agent 只发出分析命令
- **THEN** 分析使用该检索结果，系统不要求先再执行一次检索

#### Scenario: 重启后下一轮仍能使用检索结果
- **WHEN** 检索结果已经写入会话存储，进程重新启动后用户再次发言，且主 agent 只发出分析命令
- **THEN** 分析使用重启前保存的检索结果

### Requirement: 不同会话互相隔离
系统 MUST NOT 把一个会话已保存的检索结果、分析结果或研究方向结果提供给另一个会话。

#### Scenario: 新会话看不到其他会话的论文
- **WHEN** 会话 A 已有检索结果，会话 B 尚未执行检索
- **THEN** 会话 B 没有可用的检索结果

### Requirement: 调度过程按顺序可见
系统 SHALL 按实际发生顺序输出事件。事件 MUST 包含命令已发出、子 agent 已返回、下游结果已作废和本轮已结束，并使调用方能够区分命令类型、成功或失败，以及哪些已保存的结果被清除。

#### Scenario: 作废事件早于下一条命令
- **WHEN** 一次新的检索成功并清除了下游结果，然后主 agent 发出下一条命令
- **THEN** 事件流中，该次检索返回和下游结果作废都早于下一条命令已发出
