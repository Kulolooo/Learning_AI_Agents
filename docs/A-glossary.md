# 附录 A · 术语表（中英对照）

## A.1 术语对照

| 中文 | 英文 | 本库用法 |
|---|---|---|
| 智能体 | agent | 具备目标、工具与反馈回路的系统；本库默认指 LLM 驱动的循环 |
| 循环 | loop / agent loop | 模型决策 → 工具执行 → 观察回灌的重复过程 |
| 轨迹 | trace | 一次运行的结构化事件序列，可落盘、可回放 |
| 步 | step | 一次模型调用（含其触发的工具执行） |
| 观察 | observation | 工具返回值或错误文本，作为消息回灌给模型 |
| 上下文窗口 | context window | 模型单次可见的 token 上限 |
| 上下文工程 | context engineering | 在窗口内做信息选择、排序与压缩 |
| 前缀缓存 | prefix caching | 相同前缀复用计算，降低延迟与成本 |
| 工具 schema | tool schema | 工具名、描述、参数的机器可读声明 |
| 函数调用 | function calling | 模型输出结构化工具调用请求的机制 |
| 幂等键 | idempotency key | 由工具名与参数派生的哈希，用于副作用去重 |
| 护栏 | guardrail | 预算、审批、白名单、校验等控制点 |
| 人在环 | human-in-the-loop (HITL) | 高风险动作前的人工确认 |
| 工作记忆 | working memory | 当前会话的短期上下文 |
| 情景记忆 | episodic memory | 历史任务的过程与结果 |
| 语义记忆 | semantic memory | 稳定事实与偏好 |
| 检索增强 | RAG | 先检索资料、再据此生成 |
| 切分 | chunking | 把长文档切成可检索的片段 |
| 稀疏检索 | sparse retrieval | 基于词频的检索，如 BM25 |
| 稠密检索 | dense retrieval | 基于向量的语义检索 |
| 倒数排名融合 | reciprocal rank fusion (RRF) | 按排名合并多路检索结果 |
| 重排 | reranking | 对候选片段做更精细的打分 |
| 忠实度 | faithfulness | 答案是否只使用给定资料 |
| 引用覆盖率 | citation coverage | 被引用片段占召回片段的比例 |
| 规划 | planning | 把目标拆成可执行步骤 |
| 重规划 | replanning | 失败后改写剩余步骤 |
| 路由 | routing | 一步决策，把请求分给处理器 |
| 反思 | reflection | 依据评审意见修订产出 |
| 自一致性 | self-consistency | 多次采样后投票 |
| 多智能体 | multi-agent | 多个角色按协议协作 |
| 主管 | supervisor | 拆解、分派、合并的协调角色 |
| 黑板 | blackboard | 带版本的共享状态 |
| 编排 | orchestration | 用图描述节点、边与状态 |
| 检查点 | checkpoint | 状态快照，用于恢复与回放 |
| 条件边 | conditional edge | 依据状态决定下一节点 |
| 评估集 | eval set | 固定的任务与期望行为集合 |
| 断言 | assertion | 可自动判定的检查项 |
| 评分量表 | rubric | 逐项打分的质量标准 |
| 通过率 | pass rate | 通过全部断言的用例比例 |
| 门禁 | release gate | 合并/发布前必须满足的条件 |
| 影子模式 | shadow mode | 只给建议不执行，用于对照 |
| 灰度 | canary | 小流量先上线 |
| 回滚开关 | kill switch | 按路径关闭能力的开关 |
