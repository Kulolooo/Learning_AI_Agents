# 附录 C · 参考、许可与写作说明

## C.1 论文与规范

| 主题 | 文献 |
|---|---|
| ReAct 循环 | Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models*, ICLR 2023. <https://arxiv.org/abs/2210.03629> |
| 工具学习 | Schick et al., *Toolformer: Language Models Can Teach Themselves to Use Tools*, 2023. <https://arxiv.org/abs/2302.04761> |
| 检索增强 | Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*, NeurIPS 2020. <https://arxiv.org/abs/2005.11401> |
| 排名融合 | Cormack et al., *Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods*, SIGIR 2009. |
| 位置效应 | Liu et al., *Lost in the Middle: How Language Models Use Long Contexts*, 2023. <https://arxiv.org/abs/2307.03172> |
| 反思 | Madaan et al., *Self-Refine*, 2023. <https://arxiv.org/abs/2303.17651> |
| 反思（强化） | Shinn et al., *Reflexion*, 2023. <https://arxiv.org/abs/2303.11366> |
| 自一致性 | Wang et al., *Self-Consistency Improves Chain of Thought Reasoning in Language Models*, 2022. <https://arxiv.org/abs/2203.11171> |
| 记忆 | Packer et al., *MemGPT: Towards LLMs as Operating Systems*, 2023. <https://arxiv.org/abs/2310.08560> |
| 多智能体 | Wu et al., *AutoGen*, 2023. <https://arxiv.org/abs/2308.08155> |
| 多智能体辩论 | Du et al., *Improving Factuality and Reasoning in Language Models through Multiagent Debate*, 2023. <https://arxiv.org/abs/2305.14325> |
| 代码评估 | Chen et al., *Evaluating Large Language Models Trained on Code*, 2021. <https://arxiv.org/abs/2107.03374> |
| 工具协议 | Anthropic, *Model Context Protocol*. <https://modelcontextprotocol.io> |
| 工程实践 | Anthropic, *Building effective agents*, 2024. <https://www.anthropic.com/research/building-effective-agents> |

## C.2 与上游仓库的关系

本库的选题结构参考 NirDiamant/GenAI_Agents（65 篇 notebook 的开源教程集），逐篇映射放在附录 B。本库不包含上游的代码、notebook 文本、图片或数据集；`learning_agents` 包的实现为独立编写，没有参考上游的代码结构；术语与主题选择属于公共领域的一般性知识，不构成对上游的复制。上游仓库采用自定义的非商业许可，若计划商业使用上游材料，请先阅读其 `LICENSE`。

> 上游地址：<https://github.com/NirDiamant/GenAI_Agents>

## C.3 本库许可

| 部分 | 许可 | 说明 |
|---|---|---|
| 代码（`learning_agents/`、`examples/`、`tests/`、`diagrams/*.py`） | MIT | 可自由使用、修改、商用，保留版权声明 |
| 文档（`docs/`、`README.md`、`book.html`） | CC BY 4.0 | 可转载与改编，需署名并注明来源 |
| 插图（`diagrams/out/*.svg`、`*.png`） | CC BY 4.0 | 与文档一致 |

许可条款属于发布者的选择，技术上并不构成限制。若计划以其他条款发布（例如非商业许可），修改本节与 `LICENSE` 即可。

## C.4 写作与表述说明

为便于在不同平台发布与长期维护，本库在写作上遵循以下约定：

1. 原创表述：所有章节为独立撰写，不逐句翻译任何来源；引用他人观点时给出链接。
2. 术语统一：同一概念只用一个中文译名，首次出现时附英文，见附录 A。
3. 可验证优先：涉及数字、阈值、公式的地方给出推导或来源；经验值明确标注为"起点"。
4. 不含敏感内容：不涉及个人隐私、内部系统地址、凭据、真实客户数据；示例中的订单号、门店名均为构造。
5. 厂商中立：不以任何框架或云服务作为默认前提；示例仅依赖 Python 标准库。
6. 可复现：所有图由 `diagrams/` 下的脚本生成，所有代码可离线运行，测试覆盖核心行为。

## C.5 如何贡献

1. 新增或修改实现：补单元测试，`python -m unittest discover -s tests` 必须全绿；
2. 新增插图：在 `diagrams/figures_*.py` 中添加函数，并在 `build_diagrams.py` 注册；
3. 修改文档：保持每章结构（学习目标 → 机制 → 图 → 工程要点 → 失败模式 → 练习 → 参考）；
4. 提交前运行 `python build.py`，确保 `book.html` 与插图同步。

## C.6 版本

- `0.1.0` — 初版：13 章 + 3 附录、14 张插图、可运行包与 41 个单元测试。
