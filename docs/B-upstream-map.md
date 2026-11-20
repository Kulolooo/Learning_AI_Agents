# 附录 B · 上游 65 篇教程的阅读映射

本表把 NirDiamant/GenAI_Agents 的 notebook 按主题归并，标注与本库章节的对应关系和阅读建议。阅读建议分三档：标注"精读"的教程与本库某章互补，值得逐格运行；标注"对照"的是同一机制的不同抽象层，扫读即可；标注"选读"的是行业应用，只读其中的状态设计与工具层。

> 上游仓库采用自定义非商业许可，本库与其无代码或文字复用关系。链接指向原始 notebook。

## B.1 基础与循环

| 上游教程 | 主题 | 本库章节 | 建议 |
|---|---|---|---|
| [agent_while_loop_from_scratch](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/agent_while_loop_from_scratch.ipynb) | 不用框架的 while 循环 | 01 | 精读 |
| [simple_conversational_agent](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/simple_conversational_agent.ipynb) | 带记忆的对话 | 01、04 | 对照 |
| [simple_conversational_agent-pydanticai](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/simple_conversational_agent-pydanticai.ipynb) | 同上，PydanticAI 实现 | 01 | 选读 |
| [simple_question_answering_agent](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/simple_question_answering_agent.ipynb) | 单轮问答 | 01 | 选读 |
| [task_oriented_agent](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/task_oriented_agent.ipynb) | 以目标驱动的任务型智能体 | 01、05 | 对照 |
| [workflows_first_from_scratch](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/workflows_first_from_scratch.ipynb) | 先工作流、后自主 | 05、13 | 精读 |
| [one_step_decision_router](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/one_step_decision_router.ipynb) | 一步路由 | 05 | 精读 |
| [langgraph-tutorial](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/langgraph-tutorial.ipynb) | 图编排入门 | 09 | 精读 |
| [mcp-tutorial](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/mcp-tutorial.ipynb) | 工具协议 | 03 | 精读 |

## B.2 工具、上下文与技能

| 上游教程 | 主题 | 本库章节 | 建议 |
|---|---|---|---|
| [designing_tools_for_agents](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/designing_tools_for_agents.ipynb) | 工具设计 | 03 | 精读 |
| [context_engineering_from_scratch](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/context_engineering_from_scratch.ipynb) | 上下文装配 | 02 | 精读 |
| [read_vs_write_cost](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/read_vs_write_cost.ipynb) | 读写成本权衡 | 04 | 精读 |
| [thinking_budgets_from_scratch](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/thinking_budgets_from_scratch.ipynb) | 推理预算 | 01、02 | 对照 |
| [skills_from_scratch](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/skills_from_scratch.ipynb) | 技能封装与复用 | 03、09 | 对照 |

## B.3 记忆

| 上游教程 | 主题 | 本库章节 | 建议 |
|---|---|---|---|
| [memory-agent-tutorial](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/memory-agent-tutorial.ipynb) | 记忆模式 | 04 | 精读 |
| [memory_enhanced_conversational_agent](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/memory_enhanced_conversational_agent.ipynb) | 短期 + 长期记忆 | 04 | 对照 |

## B.4 推理、反思与规划

| 上游教程 | 主题 | 本库章节 | 建议 |
|---|---|---|---|
| [reflection_from_scratch](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/reflection_from_scratch.ipynb) | 反思循环 | 06 | 精读 |
| [plan_then_execute_from_scratch](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/plan_then_execute_from_scratch.ipynb) | 计划-执行 | 05 | 精读 |
| [self_improving_agent](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/self_improving_agent.ipynb) | 从历史运行中学习 | 06、10 | 对照 |
| [self_healing_code](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/self_healing_code.ipynb) | 代码自愈 | 06 | 精读 |
| [e2e_testing_agent](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/e2e_testing_agent.ipynb) | 自动生成端到端测试 | 06、10 | 选读 |

## B.5 检索与内容分析

| 上游教程 | 主题 | 本库章节 | 建议 |
|---|---|---|---|
| [search_the_internet_and_summarize](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/search_the_internet_and_summarize.ipynb) | 检索 + 摘要 | 07、11 | 对照 |
| [news_tldr_langgraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/news_tldr_langgraph.ipynb) | 新闻浓缩 | 07、11 | 选读 |
| [scientific_paper_agent_langgraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/scientific_paper_agent_langgraph.ipynb) | 论文检索与总结 | 07、11 | 选读 |
| [systematic_review_of_scientific_articles](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/systematic_review_of_scientific_articles.ipynb) | 系统性文献综述 | 11 | 选读 |
| [contextual_quoting_agentic_system](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/contextual_quoting_agentic_system.ipynb) | 带上下文的引用 | 07、11 | 精读 |
| [ContentIntelligence](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/ContentIntelligence.ipynb) | 内容分类与分析 | 07 | 选读 |
| [ainsight_langgraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/ainsight_langgraph.ipynb) | 洞察生成管道 | 07 | 选读 |

## B.6 多智能体与协作

| 上游教程 | 主题 | 本库章节 | 建议 |
|---|---|---|---|
| [multi_agent_collaboration_system](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/multi_agent_collaboration_system.ipynb) | 多角色协作 | 08 | 精读 |
| [research_team_autogen](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/research_team_autogen.ipynb) | AutoGen 研究小组 | 08 | 对照 |
| [blog_writer_swarm](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/blog_writer_swarm.ipynb) | 规划-撰稿-编辑 | 08 | 对照 |
| [database_discovery_fleet](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/database_discovery_fleet.ipynb) | 数据库探查舰队 | 08 | 选读 |
| [grocery_management_agents_system](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/grocery_management_agents_system.ipynb) | 生活域多智能体 | 08 | 选读 |

## B.7 评估、可观测与治理

| 上游教程 | 主题 | 本库章节 | 建议 |
|---|---|---|---|
| [trace_based_agent_evaluation](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/trace_based_agent_evaluation.ipynb) | 基于轨迹的评估 | 10 | 精读 |
| [human_in_the_loop_approval_agent](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/human_in_the_loop_approval_agent.ipynb) | 人工审批 | 09、12 | 精读 |
| [graph_inspector_system_langgraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/graph_inspector_system_langgraph.ipynb) | 图结构与调试 | 09、10 | 对照 |
| [essay_grading_system_langgraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/essay_grading_system_langgraph.ipynb) | rubric 评分 | 10 | 对照 |

## B.8 行业应用（按需选读）

| 上游教程 | 场景 | 本库章节 |
|---|---|---|
| [customer_support_agent_langgraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/customer_support_agent_langgraph.ipynb) | 客服工单 | 12 |
| [ClauseAI](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/ClauseAI.ipynb) | 合同条款分析 | 07、12 |
| [document_intake_agent_langgraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/document_intake_agent_langgraph.ipynb) | 单据入库与路由 | 05、12 |
| [HR_AI-Assistant](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/HR_AI-Assistant.ipynb) | 招聘流水线 | 05 |
| [project_manager_assistant_agent](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/project_manager_assistant_agent.ipynb) | 项目计划 | 05、07 |
| [sales_call_analyzer_agent](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/sales_call_analyzer_agent.ipynb) | 通话分析 | 07 |
| [car_buyer_agent_langgraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/car_buyer_agent_langgraph.ipynb) | 比价与推荐 | 08 |
| [ShopGenie](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/ShopGenie.ipynb) | 购物研究 | 08 |
| [EU_Green_Compliance_FAQ_Bot](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/EU_Green_Compliance_FAQ_Bot.ipynb) | 合规问答 | 07 |
| [Weather_Disaster_Management_AI_AGENT](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/Weather_Disaster_Management_AI_AGENT.ipynb) | 灾害决策支持 | 08 |
| [taskifier](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/taskifier.ipynb) | 自由文本转任务 | 05 |
| [ai_driven_ml_and_datascience_assistant](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/ai_driven_ml_and_datascience_assistant.ipynb) | 建模流程助手 | 06 |
| [simple_data_analysis_agent_notebook](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/simple_data_analysis_agent_notebook.ipynb) | 数据分析 | 03 |
| [simple_data_analysis_agent_notebook-pydanticai](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/simple_data_analysis_agent_notebook-pydanticai.ipynb) | 同上 | 03 |
| [Gutenbergs_Sage](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/Gutenbergs_Sage.ipynb) | 语料库检索 | 07 |
| [Academic_Task_Learning_Agent_LangGraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/Academic_Task_Learning_Agent_LangGraph.ipynb) | 学习型助教 | 06 |
| [chiron_learning_agent_langgraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/chiron_learning_agent_langgraph.ipynb) | 辅导智能体 | 05 |
| [journalism_focused_ai_assistant_langgraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/journalism_focused_ai_assistant_langgraph.ipynb) | 新闻工作流 | 11 |
| [agent_hackathon_genAI_career_assistant](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/agent_hackathon_genAI_career_assistant.ipynb) | 职业规划 | 08 |
| [social_media_publishing_agent_publora_langgraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/social_media_publishing_agent_publora_langgraph.ipynb) | 社媒发布 | 12 |
| [simple_travel_planner_langgraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/simple_travel_planner_langgraph.ipynb) | 约束规划 | 05 |

## B.9 创意与多模态（了解即可）

| 上游教程 | 场景 | 本库章节 |
|---|---|---|
| [art_agent](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/art_agent.ipynb) | 视觉艺术 | 03 |
| [music_compositor_agent_langgraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/music_compositor_agent_langgraph.ipynb) | 音乐生成 | 03 |
| [generate_podcast_agent_langgraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/generate_podcast_agent_langgraph.ipynb) | 播客生产 | 09 |
| [tts_poem_generator_agent_langgraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/tts_poem_generator_agent_langgraph.ipynb) | 诗 + 语音 | 09 |
| [gif_animation_generator_langgraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/gif_animation_generator_langgraph.ipynb) | 动画生成 | 09 |
| [business_meme_generator](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/business_meme_generator.ipynb) | 梗图生成 | 03 |
| [murder_mystery_agent_langgraph](https://github.com/NirDiamant/GenAI_Agents/blob/main/all_agents_tutorials/murder_mystery_agent_langgraph.ipynb) | 互动叙事 | 09 |

## B.10 阅读顺序建议

若目标是"把本库的机制落到框架里"，推荐这条路径（每篇 1—2 小时）：

1. `agent_while_loop_from_scratch` → 对照 01 章，确认自己写的循环与开源实现一致；
2. `designing_tools_for_agents` → 对照 03 章，收集工具描述的写法；
3. `reflection_from_scratch` → 对照 06 章，看反思的终止条件如何实现；
4. `plan_then_execute_from_scratch` → 对照 05 章；
5. `memory-agent-tutorial` + `read_vs_write_cost` → 对照 04 章；
6. `langgraph-tutorial` + `human_in_the_loop_approval_agent` → 对照 09 章；
7. `trace_based_agent_evaluation` → 对照 10 章；
8. 任选一个行业案例，只读状态与工具层。
