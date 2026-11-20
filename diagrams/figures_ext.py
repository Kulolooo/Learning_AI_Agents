"""插图（续）：规划、反思、拓扑、编排、评估、路线图与两个综合案例。"""

from __future__ import annotations

from scene import BG, FAINT, INK, MUTED, Diagram


def fig_plan_execute() -> Diagram:
    d = Diagram(1160, 640, "图 6-1  计划-执行-重规划",
                "计划是承诺，重规划是纠错；没有重规划的计划系统等于把错误放大 N 倍")
    d.header()

    goal = d.node("goal", 50, 200, 150, 90, "目标", "多步任务", tone="slate")
    planner = d.node("planner", 240, 200, 170, 90, "规划器", "拆成 2-5 步", tone="indigo")
    d.edge("goal", "planner", "task")

    d.panel(450, 120, 250, 300, "计划（可编辑的状态机）", tone="white")
    s1 = d.node("s1", 475, 165, 200, 56, "s1 确认口径", "done", tone="emerald")
    s2 = d.node("s2", 475, 235, 200, 56, "s2 拉取数据", "running", tone="amber")
    s3 = d.node("s3", 475, 305, 200, 56, "s3 生成报告", "pending", tone="slate")
    d.scene.line(575, 221, 575, 235, arrow=True, color="#94a3b8")
    d.scene.line(575, 291, 575, 305, arrow=True, color="#94a3b8", dash="4 4")
    d.edge("planner", "s1", "plan")

    ex = d.node("exec", 750, 200, 160, 90, "执行器", "工具 / 子智能体", tone="sky")
    out = d.node("out", 970, 200, 150, 90, "汇总", "结果 + 失败原因", tone="emerald")
    d.edge("s2", "exec", "取下一步")
    d.edge("exec", "out", "done")

    rep = d.node("rep", 600, 430, 200, 80, "重规划器", "改写剩余步骤 / 降级", tone="rose")
    d.scene.polyline([(830, 290), (830, 430)], color="#fb7185", width=2.2, arrow=True)
    d.scene.label(920, 360, "第 n 步失败（超时 / 校验失败）", size=12, color="#be123c")
    d.scene.polyline([(600, 470), (430, 470), (430, 333), (475, 333)],
                     color="#fb7185", width=2.2, arrow=True)
    d.scene.label(505, 470, "回到待执行队列（有次数上限）", size=12, color="#be123c")

    d.note(50, 585, "关键设计：步骤状态必须显式落盘（done / running / failed），"
                    "否则重规划时无法判断哪些工作可复用。", size=13, width_chars=62)
    return d


def fig_reflection() -> Diagram:
    d = Diagram(1200, 680, "图 7-1  反思循环与终止条件",
                "反思是用评审换质量；评审标准必须是外部的、可重复的")
    d.header()

    gen = d.node("gen", 60, 215, 150, 88, "初稿", "生成器", tone="slate")
    crit = d.node("crit", 260, 215, 170, 88, "评审", "规则 / rubric / 测试", tone="amber")
    dec = d.node("dec", 480, 220, 150, 78, "达到标准？", "分数 ≥ 阈值", tone="indigo")
    fin = d.node("fin", 680, 215, 150, 88, "定稿", "输出 + 评分记录", tone="emerald")
    rev = d.node("rev", 480, 390, 150, 88, "修订", "带着问题清单重写", tone="sky")

    d.edge("gen", "crit", "draft")
    d.edge("crit", "dec", "score")
    d.edge("dec", "fin", "通过", sides=("right", "left"))
    d.edge("dec", "rev", "未通过", sides=("bottom", "top"))
    d.scene.polyline([(480, 434), (380, 434), (380, 303)],
                     color="#0ea5e9", width=2.2, arrow=True)
    d.scene.label(405, 414, "重写后回评审（≤ N 轮）", size=12, color="#0369a1")

    d.panel(680, 370, 480, 260, "三条终止条件，缺一不可", tone="white")
    d.note(705, 412, "① 分数达标：rubric 全项通过，而不是感觉更好。", size=12.5, width_chars=36)
    d.note(705, 452, "② 轮数触顶：反思会过拟合评审，3 轮之后收益通常趋零。", size=12.5, width_chars=36)
    d.note(705, 492, "③ 收益递减：新稿分数低于上一稿，立即回退到最佳版本。", size=12.5, width_chars=36)
    d.note(705, 548, "反模式：让模型再检查一遍却没有评分标准——它只会换一种说法。",
           size=12, color="#be123c", width_chars=38)
    return d


def fig_topologies() -> Diagram:
    d = Diagram(1160, 720, "图 8-1  四种多智能体拓扑",
                "拓扑决定通信成本与错误传播路径；先问是否真的需要多智能体")
    d.header()

    # (a) pipeline
    d.panel(40, 100, 540, 280, "(a) 流水线：线性、无协商", tone="white")
    a1 = d.node("a1", 70, 165, 140, 70, "抽取", "结构化", tone="slate")
    a2 = d.node("a2", 250, 165, 140, 70, "撰写", "长文本", tone="sky")
    a3 = d.node("a3", 430, 165, 120, 70, "校对", "一致性", tone="emerald")
    d.edge("a1", "a2", "facts")
    d.edge("a2", "a3", "draft")
    d.note(70, 280, "优点：可调试、可插入人工节点。缺点：上游错误会原样传到下游，"
                    "且总延迟等于各段之和。", size=12, width_chars=44)

    # (b) supervisor
    d.panel(600, 100, 520, 280, "(b) 主管：星型、集中决策", tone="white")
    sup = d.node("sup", 790, 145, 150, 64, "主管", "拆解 / 分派 / 合并", tone="indigo")
    w1 = d.node("w1", 630, 265, 130, 64, "专家 A", "检索", tone="sky")
    w2 = d.node("w2", 790, 265, 130, 64, "专家 B", "计算", tone="amber")
    w3 = d.node("w3", 950, 265, 130, 64, "专家 C", "写作", tone="emerald")
    d.edge("sup", "w1", sides=("bottom", "top"))
    d.edge("sup", "w2", sides=("bottom", "top"))
    d.edge("sup", "w3", sides=("bottom", "top"))
    d.note(620, 350, "优点：职责清晰、易加人。风险：主管成为瓶颈与单点，"
                     "合并阶段容易丢信息。", size=12, width_chars=44)

    # (c) debate
    d.panel(40, 400, 540, 290, "(c) 辩论：对抗、裁判裁决", tone="white")
    pro = d.node("pro", 90, 470, 150, 70, "正方", "主张 + 证据", tone="emerald")
    con = d.node("con", 350, 470, 150, 70, "反方", "反驳 + 反例", tone="rose")
    jud = d.node("jud", 220, 590, 150, 64, "裁判", "按 rubric 取舍", tone="indigo")
    d.scene.line(240, 492, 350, 492, arrow=True, color="#16a34a")
    d.scene.label(295, 480, "第 1 轮", size=11, color="#15803d")
    d.scene.line(350, 518, 240, 518, arrow=True, color="#e11d48")
    d.scene.label(295, 534, "第 2 轮", size=11, color="#be123c")
    d.scene.line(165, 540, 240, 590, arrow=True, color="#64748b")
    d.scene.line(425, 540, 350, 590, arrow=True, color="#64748b")

    # (d) blackboard
    d.panel(600, 400, 520, 290, "(d) 黑板：共享状态、事件驱动", tone="white")
    board = d.node("board", 730, 460, 190, 70, "黑板", "带版本的共享事实", tone="violet")
    b1 = d.node("b1", 640, 580, 120, 64, "感知", "", tone="sky")
    b2 = d.node("b2", 780, 580, 120, 64, "推理", "", tone="amber")
    b3 = d.node("b3", 920, 580, 120, 64, "行动", "", tone="emerald")
    for nid in ("b1", "b2", "b3"):
        d.edge(nid, "board", "", sides=("top", "bottom"))
    d.note(620, 672, "适合长任务与异步协作；难点在冲突解决与收敛判定。",
           size=11.5, width_chars=42)
    return d


def fig_orchestration() -> Diagram:
    d = Diagram(1160, 660, "图 9-1  图编排：状态、条件边与人工中断",
                "把 Agent 从一个函数变成一张可暂停、可恢复、可回放的状态图")
    d.header()

    start = d.node("start", 50, 200, 110, 70, "入口", "input", tone="slate")
    plan = d.node("plan", 210, 200, 140, 70, "规划", "state", tone="indigo")
    act = d.node("act", 400, 200, 140, 70, "执行", "tool / llm", tone="sky")
    chk = d.node("chk", 590, 200, 150, 70, "校验", "schema / test", tone="amber")
    hitl = d.node("hitl", 590, 360, 150, 70, "人工审批", "interrupt", tone="rose")
    end = d.node("end", 800, 200, 120, 70, "出口", "output", tone="emerald")

    d.edge("start", "plan", "edges")
    d.edge("plan", "act", "next")
    d.edge("act", "chk", "result")
    d.edge("chk", "end", "pass")
    d.edge("chk", "hitl", "需确认", sides=("bottom", "top"))
    d.edge("hitl", "act", "批准后重入", sides=("left", "bottom"))
    d.scene.polyline([(650, 200), (650, 150), (280, 150), (280, 200)],
                     color="#f59e0b", width=2.2, arrow=True)
    d.scene.label(470, 150, "fail → 重规划（带上失败原因）", size=12, color="#b45309")

    d.panel(50, 480, 1080, 130, "持久化：每一步之后写检查点", tone="white")
    d.note(75, 525, "检查点 = 完整状态快照（消息、计划、工具结果、预算计数）+ 版本号。"
                    "有了它，中断可恢复、失败可重放、评测可复现。", size=13, width_chars=64)
    d.note(75, 567, "代价：状态必须可序列化——把数据库连接、文件句柄这类东西挡在状态之外。",
           size=12, color=MUTED, width_chars=64)

    d.scene.text(1020, 182, "每个节点的护栏", size=12, color=MUTED, anchor="middle")
    d.tag(960, 200, "幂等键", "amber")
    d.tag(960, 236, "超时", "rose")
    d.tag(960, 272, "重试上限", "indigo")
    return d


def fig_eval_loop() -> Diagram:
    d = Diagram(1120, 700, "图 10-1  评估驱动的开发闭环",
                "先有度量，再谈优化；每次改动都要能回答更好还是更差")
    d.header()

    ds = d.node("ds", 80, 120, 190, 80, "固定用例集", "任务 + 期望行为", tone="slate")
    run = d.node("run", 360, 120, 190, 80, "批量运行", "模型 + 工具 + 预算", tone="sky")
    tr = d.node("tr", 640, 120, 190, 80, "轨迹", "JSONL / span 树", tone="violet")
    chk = d.node("chk", 640, 300, 190, 80, "断言与指标", "工具/步数/引用/时延", tone="amber")
    gate = d.node("gate", 360, 300, 190, 80, "发布门禁", "通过率 ≥ 基线", tone="emerald")
    fix = d.node("fix", 80, 300, 190, 80, "归因与修改", "提示 / 工具 / 检索", tone="rose")

    d.edge("ds", "run", "cases")
    d.edge("run", "tr", "emit")
    d.edge("tr", "chk", "load", sides=("bottom", "top"))
    d.edge("chk", "gate", "report", sides=("left", "right"))
    d.edge("gate", "fix", "不达标", sides=("left", "right"))
    d.edge("fix", "ds", "更新用例", sides=("top", "left"))

    d.panel(80, 440, 960, 210, "三层评估：成本与置信度的权衡", tone="white")
    rows = [("L1 规则断言", "毫秒级 · 每次提交", "是否调用工具、是否超步、是否含关键词", "emerald"),
            ("L2 轨迹指标", "毫秒级 · 每次提交", "步数分布、错误率、token、P95 时延", "sky"),
            ("L3 模型评审", "秒级 · 按发布节奏", "rubric 逐项打分、成对比较（A/B）", "violet")]
    y = 485
    for name, freq, desc, tone in rows:
        fill, stroke, ink = {"emerald": ("#dcfce7", "#4ade80", "#14532d"),
                             "sky": ("#e0f2fe", "#38bdf8", "#0c4a6e"),
                             "violet": ("#ede9fe", "#a78bfa", "#4c1d95")}[tone]
        d.scene.rect(105, y, 200, 46, fill=fill, stroke=stroke, radius=8)
        d.scene.text(125, y + 29, name, size=14, color=ink, bold=True)
        d.scene.text(320, y + 22, freq, size=12, color=MUTED)
        d.scene.text(320, y + 40, desc, size=12, color=MUTED)
        y += 54
    return d


def fig_curriculum() -> Diagram:
    d = Diagram(1160, 760, "图 0-1  学习路线：四个阶段，十三个章节",
                "从最小闭环到综合案例，每一章都可以独立运行、独立验证")
    d.header()

    bands = [
        ("第一阶段 · 基础", 110, "indigo",
         [("01", "定义与闭环"), ("02", "上下文工程"), ("03", "工具调用"), ("04", "记忆系统")]),
        ("第二阶段 · 单智能体能力", 260, "sky",
         [("05", "规划与路由"), ("06", "反思与修正"), ("07", "检索增强")]),
        ("第三阶段 · 协作与工程", 410, "emerald",
         [("08", "多智能体"), ("09", "图编排"), ("10", "评估与可观测")]),
        ("第四阶段 · 综合实践", 560, "amber",
         [("11", "研究助手"), ("12", "工单处理"), ("13", "从原型到产品")]),
    ]
    for label, y, tone, chapters in bands:
        d.panel(60, y, 1040, 120, label, tone="white")
        x = 90
        for num, name in chapters:
            fill, stroke, ink = {"indigo": ("#eef2ff", "#818cf8", "#312e81"),
                                 "sky": ("#e0f2fe", "#38bdf8", "#0c4a6e"),
                                 "emerald": ("#dcfce7", "#4ade80", "#14532d"),
                                 "amber": ("#fef3c7", "#fbbf24", "#78350f")}[tone]
            d.scene.rect(x, y + 45, 220, 56, fill=fill, stroke=stroke, radius=10)
            d.scene.text(x + 18, y + 79, num, size=18, color=ink, bold=True)
            d.scene.text(x + 52, y + 79, name, size=14, color=ink)
            x += 240

    d.scene.line(110, 230, 110, 260, arrow=True, color=FAINT)
    d.scene.line(110, 380, 110, 410, arrow=True, color=FAINT)
    d.scene.line(110, 530, 110, 560, arrow=True, color=FAINT)
    d.scene.text(90, 710, "配套：learning_agents 包（可直接运行）· 14 张架构图 · 41 个单元测试 · "
                          "上游 64 篇教程映射表", size=13, color=MUTED)
    return d


def fig_research_agent() -> Diagram:
    d = Diagram(1160, 680, "图 11-1  深度研究助手：并行取证 + 强制引用",
                "研究类任务的核心不是写得好，而是每条结论都能追到来源")
    d.header()

    q = d.node("q", 50, 160, 160, 76, "研究问题", "开放式 / 多跳", tone="slate")
    plan = d.node("plan", 250, 160, 170, 76, "问题分解", "3-5 个子问题", tone="indigo")
    d.edge("q", "plan", "task")

    d.panel(470, 100, 300, 300, "并行取证", tone="white")
    s1 = d.node("s1", 495, 140, 250, 64, "检索 A · 网页", "官方文档 / 综述", tone="sky")
    s2 = d.node("s2", 495, 216, 250, 64, "检索 B · 论文", "摘要 + 方法段", tone="violet")
    s3 = d.node("s3", 495, 292, 250, 64, "检索 C · 本地库", "内部资料 / 历史结论", tone="amber")
    d.edge("plan", "s1")
    d.edge("plan", "s2")
    d.edge("plan", "s3")

    read = d.node("read", 810, 160, 150, 76, "抽取证据", "主张 + 出处 + 原文", tone="sky")
    table = d.node("table", 810, 270, 150, 76, "证据表", "去重 / 冲突标注", tone="violet")
    d.edge("s1", "read")
    d.edge("s2", "read")
    d.edge("s3", "read")
    d.edge("read", "table", "claims")

    draft = d.node("draft", 700, 470, 160, 76, "写作", "按证据组织", tone="emerald")
    check = d.node("check", 500, 470, 160, 76, "引用核查", "每条主张有编号", tone="rose")
    final = d.node("final", 300, 470, 160, 76, "交付", "报告 + 参考列表", tone="emerald")
    d.edge("table", "draft", sides=("bottom", "top"))
    d.edge("draft", "check", "draft", sides=("left", "right"))
    d.edge("check", "final", "pass", sides=("left", "right"))
    d.scene.polyline([(580, 470), (580, 424), (500, 424), (500, 402)],
                     color="#fb7185", width=2.2, arrow=True)
    d.scene.label(655, 396, "缺失引用 → 回到取证（≤ 2 次）", size=12, color="#be123c")

    d.note(50, 590, "失败模式：子问题互相重复导致证据同质化；检索结果相互矛盾时不标注冲突；"
                    "把摘要当原文引用。", size=13, width_chars=58)
    return d


def fig_ticket_agent() -> Diagram:
    d = Diagram(1160, 680, "图 12-1  客服工单处理：路由 + 工具 + 升级",
                "高频问题走确定性路径，长尾问题才交给自主循环；不可逆动作必须审批")
    d.header()

    msg = d.node("msg", 50, 240, 150, 80, "工单", "文本 + 订单号", tone="slate")
    route = d.node("route", 240, 240, 150, 80, "路由", "意图 + 紧急度", tone="indigo")
    d.edge("msg", "route", "normalize")

    d.panel(440, 110, 310, 330, "三条确定性路径", tone="white")
    b1 = d.node("b1", 465, 150, 260, 66, "退款 / 发票", "查政策 → 校验资格", tone="emerald")
    b2 = d.node("b2", 465, 236, 260, 66, "物流异常", "查轨迹 → 生成解释", tone="sky")
    b3 = d.node("b3", 465, 322, 260, 66, "投诉 / 复杂", "升级人工 + 摘要", tone="rose")
    d.edge("route", "b1", "票据")
    d.edge("route", "b2", "物流")
    d.edge("route", "b3", "升级")

    tools = d.node("tools", 780, 150, 160, 80, "工具层", "订单 / 政策 / 物流", tone="amber")
    policy = d.node("policy", 780, 260, 160, 80, "策略校验", "金额 / 时效 / 权限", tone="violet")
    appr = d.node("appr", 780, 370, 160, 80, "审批门", "退款金额 > 阈值", tone="rose")
    d.edge("b1", "tools", "query")
    d.edge("tools", "policy", "facts")
    d.edge("policy", "appr", "高风险")

    reply = d.node("reply", 985, 240, 150, 80, "回复", "结论 + 依据", tone="emerald")
    d.edge("policy", "reply", "通过", sides=("right", "left"))
    d.edge("appr", "reply", "批准", sides=("right", "left"))

    d.scene.polyline([(1060, 320), (1060, 500), (330, 500), (330, 320)],
                     color="#94a3b8", width=2, dash="5 4", arrow=True)
    d.scene.label(680, 500, "未解决 → 回到路由，并把失败原因写进工单", size=12, color=MUTED)

    d.note(50, 560, "评估用例：退款金额边界、政策版本过期、用户情绪升级、工具超时。"
                    "每条用例都断言调用了哪个工具、是否停在审批门。", size=13, width_chars=62)
    return d


def fig_autonomy() -> Diagram:
    d = Diagram(1120, 680, "图 13-1  自主度与任务不确定性的取舍",
                "越往右上，能力越强、成本越高、越需要护栏")
    d.header()

    x0, y0, w, h = 150, 120, 810, 460
    d.scene.rect(x0, y0, w, h, fill="#ffffff", stroke="#cbd5e1", radius=12)
    d.scene.line(x0 + w / 2, y0, x0 + w / 2, y0 + h, color="#e2e8f0")
    d.scene.line(x0, y0 + h / 2, x0 + w, y0 + h / 2, color="#e2e8f0")
    d.scene.text(x0 + w / 2, y0 + h + 36, "任务不确定性 →", size=13, color=MUTED, anchor="middle")
    for i, ch in enumerate("自主度"):
        d.scene.text(x0 - 26, y0 + h / 2 - 22 + i * 20, ch, size=12, color=MUTED, anchor="middle")
    d.scene.text(x0 - 26, y0 + 22, "高", size=12, color=MUTED, anchor="middle")
    d.scene.text(x0 - 26, y0 + h - 20, "低", size=12, color=MUTED, anchor="middle")

    d.node("react", 175, 165, 240, 84, "ReAct 循环", "高自主 · 中不确定", tone="amber")
    d.node("multi", 610, 165, 240, 84, "多智能体", "高自主 · 高不确定", tone="rose")
    d.node("wf", 175, 400, 240, 84, "固定工作流", "低自主 · 低不确定", tone="emerald")
    d.node("rt", 610, 400, 240, 84, "路由 + 模板", "低自主 · 中不确定", tone="sky")

    d.note(175, 292, "工具充分时最优：失败可回灌。", size=12, width_chars=30)
    d.note(610, 292, "仅当角色确实异质、且能承担通信成本。", size=12, width_chars=30)
    d.note(175, 530, "确定性优先：可预测、可审计、延迟最低。", size=12, width_chars=30)
    d.note(610, 530, "分类清晰时最优：意图可枚举。", size=12, width_chars=30)

    d.scene.text(70, 640, "选择顺序：能工作流就工作流 → 能路由就路由 → 单智能体 → 多智能体。"
                          "每升一级，先补齐对应的评估与护栏。", size=13, color=INK)
    return d
