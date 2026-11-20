"""本书全部插图：一份布局，输出 PNG 与 SVG。

坐标是手工排的。改图时先看 ``build.py`` 渲染出的 PNG，再微调数字。
"""

from __future__ import annotations

from pathlib import Path

from scene import BG, FAINT, INK, MUTED, Diagram


def fig_agent_loop() -> Diagram:
    d = Diagram(1120, 680, "图 1-1  智能体的最小闭环",
                "循环的每一圈都在重写上下文；终止条件与轨迹是工程化的两根支柱")
    d.header()

    d.panel(40, 100, 1040, 300, "① 控制循环：从任务到答复", tone="white")
    a = d.node("task", 60, 175, 170, 92, "任务输入", "用户目标 + 初始上下文", tone="slate")
    b = d.node("ctx", 300, 175, 200, 92, "上下文装配", "系统提示·历史·记忆·工具说明", tone="sky")
    c = d.node("llm", 570, 175, 170, 92, "模型决策", "继续调用 / 收尾", tone="indigo")
    e = d.node("tool", 810, 175, 200, 92, "工具执行", "校验 → 调用 → 截断", tone="amber")
    f = d.node("final", 570, 330, 170, 62, "最终答复", "结论 + 引用", tone="emerald")

    d.edge("task", "ctx", "user")
    d.edge("ctx", "llm", "prompt")
    d.edge("llm", "tool", "tool_call")
    d.edge("llm", "final", "无工具调用", sides=("bottom", "top"))

    # 观察回灌
    d.scene.polyline([(910, 267), (910, 305), (400, 305), (400, 267)],
                     color="#f59e0b", width=2.2, arrow=True)
    d.scene.label(520, 305, "观察回灌（结果 / 错误 / 截断标记）", size=12, color="#b45309")

    d.panel(40, 420, 500, 220, "② 状态层：上下文就是状态", tone="white")
    d.node("wm", 70, 470, 200, 70, "工作记忆", "最近若干轮", tone="sky")
    d.node("lm", 300, 470, 200, 70, "长期记忆", "事实 / 偏好 / 情景", tone="violet")
    d.node("tr", 70, 560, 430, 54, "轨迹（trace）", "每一步输入摘要、工具调用、耗时、错误", tone="slate")
    d.scene.line(170, 540, 170, 560, arrow=True)
    d.scene.line(400, 540, 400, 560, arrow=True)

    d.panel(560, 420, 520, 220, "③ 控制层：什么时候必须停", tone="white")
    d.node("budget", 590, 470, 210, 70, "预算", "token / 步数 / 时间", tone="rose")
    d.node("dup", 820, 470, 230, 70, "重复检测", "同工具同参数 ≥ N 次", tone="rose")
    d.node("guard", 590, 560, 460, 54, "审批门与白名单：副作用工具的执行许可", tone="amber")
    d.scene.line(695, 540, 695, 560, arrow=True)
    return d


def fig_context_budget() -> Diagram:
    d = Diagram(1120, 620, "图 2-1  上下文预算的分配与压缩",
                "把 128k 的窗口当成一张预算表：谁占位、谁可压缩、压缩后损失什么")
    d.header()

    x0, y0, total, h = 80, 150, 960, 86
    segments = [
        ("系统提示", 0.14, "#c7d2fe"),
        ("工具说明", 0.11, "#bae6fd"),
        ("长期记忆", 0.15, "#ddd6fe"),
        ("历史对话", 0.28, "#fde68a"),
        ("当前任务", 0.09, "#bbf7d0"),
        ("预留输出", 0.23, "#fecdd3"),
    ]
    x = x0
    for name, ratio, color in segments:
        w = total * ratio
        d.scene.rect(x, y0, w, h, fill=color, stroke="#ffffff", width=2, radius=4)
        d.scene.text(x + w / 2, y0 + h / 2 + 5, name, size=15, color=INK, anchor="middle", bold=True)
        d.scene.text(x + w / 2, y0 + h + 24, f"{ratio:.0%}", size=12, color=MUTED, anchor="middle")
        x += w
    d.scene.text(x0, y0 - 18, "128k 上下文窗口（示意比例）", size=13, color=MUTED)

    d.panel(80, 300, 460, 250, "可压缩区：按代价从低到高", tone="white")
    items = [("① 截断旧对话", "零成本，丢细节", "emerald"),
             ("② 工具输出摘要", "一次小模型调用", "emerald"),
             ("③ 历史滚动摘要", "需要重写，可能丢数字", "amber"),
             ("④ 检索替代全量", "引入召回失败风险", "rose")]
    y = 340
    for title, cost, tone in items:
        fill, stroke, ink = {"emerald": ("#dcfce7", "#4ade80", "#14532d"),
                             "amber": ("#fef3c7", "#fbbf24", "#78350f"),
                             "rose": ("#ffe4e6", "#fb7185", "#881337")}[tone]
        d.scene.rect(105, y, 410, 44, fill=fill, stroke=stroke, radius=8)
        d.scene.text(120, y + 28, title, size=14, color=ink, bold=True)
        d.scene.text(290, y + 28, cost, size=12, color=MUTED)
        y += 50

    d.panel(580, 300, 460, 250, "不可压缩区：必须预留", tone="white")
    d.note(605, 348, "输出预留：模型答复本身也要占窗口。把上限写进 Budget，比事后截断安全。",
           size=12.5, width_chars=31)
    d.note(605, 412, "工具 schema：可精简描述，但不能删参数约束——删掉等于把校验"
                     "责任交给模型。", size=12.5, width_chars=31)
    d.note(605, 476, "系统提示：稳定规则应前置且少改，改一次前缀缓存全失效。",
           size=12.5, width_chars=33)

    d.scene.text(80, 590, "经验值：历史对话超过窗口的 30% 时，回答质量开始明显下降；"
                          "此时应触发摘要而不是继续追加。", size=13, color=MUTED)
    return d


def fig_tool_call() -> Diagram:
    d = Diagram(1120, 660, "图 3-1  一次工具调用的完整时序",
                "模型的输出只是「意图」；真正的执行发生在运行时，且每一步都可能失败")
    d.header()

    lanes = [("用户 / 上游", 130, "slate"), ("智能体循环", 390, "indigo"),
             ("工具注册表", 660, "amber"), ("外部世界", 930, "emerald")]
    for name, x, tone in lanes:
        fill, stroke, ink = {"slate": ("#f8fafc", "#cbd5e1", INK),
                             "indigo": ("#eef2ff", "#818cf8", "#312e81"),
                             "amber": ("#fef3c7", "#fbbf24", "#78350f"),
                             "emerald": ("#dcfce7", "#4ade80", "#14532d")}[tone]
        d.scene.rect(x - 110, 100, 220, 52, fill=fill, stroke=stroke, radius=10)
        d.scene.text(x, 132, name, size=15, color=ink, anchor="middle", bold=True)
        d.scene.line(x, 152, x, 600, color="#cbd5e1", width=1.6, dash="5 5")

    steps = [
        (170, "用户", "智能体", "① 提出任务", "#64748b"),
        (225, "智能体", "工具注册表", "② 组装 tools schema 随请求发送", "#4f46e5"),
        (290, "智能体", "智能体", "③ 模型返回 tool_call（名字 + 参数 JSON）", "#4f46e5"),
        (350, "智能体", "工具注册表", "④ 参数校验：缺参 / 类型错 / 未声明字段", "#b45309"),
        (415, "工具注册表", "外部世界", "⑤ 执行：副作用工具先过审批门", "#047857"),
        (480, "工具注册表", "智能体", "⑥ 结果或错误，统一转成观察文本", "#b45309"),
        (545, "智能体", "智能体", "⑦ 观察写回消息列表，进入下一轮决策", "#4f46e5"),
    ]
    xs = {"用户": 130, "智能体": 390, "工具注册表": 660, "外部世界": 930}
    for y, src, dst, label, color in steps:
        x1, x2 = xs[src], xs[dst]
        if src == dst:
            d.scene.polyline([(x1, y - 16), (x1 + 64, y - 16), (x1 + 64, y + 16), (x1, y + 16)],
                             color=color, width=2, arrow=True)
            d.scene.text((x1 + x2) / 2 if src != dst else x1 + 32, y - 30, label,
                         size=12, color=color, anchor="middle")
        else:
            d.scene.line(x1, y, x2, y, color=color, width=2, arrow=True)
            d.scene.text((x1 + x2) / 2, y - 12, label, size=12, color=color, anchor="middle")

    d.scene.rect(80, 610, 960, 34, fill="#f8fafc", stroke="#e2e8f0", radius=8)
    d.scene.text(96, 632, "失败路径：④ 校验失败 → 结构化错误；⑤ 抛异常 / 超时 → ERROR 文本；"
                          "两种情况都不终止循环，而是交给模型决策。", size=12, color=MUTED)
    return d


def fig_memory_layers() -> Diagram:
    d = Diagram(1120, 640, "图 4-1  三层记忆的读写与淘汰",
                "写入决定成本，读取决定质量；遗忘不是缺陷，是必要的维护")
    d.header()

    d.scene.rect(60, 110, 1000, 90, fill="#e0f2fe", stroke="#38bdf8", radius=12)
    d.scene.text(90, 145, "工作记忆（working）", size=16, color="#0c4a6e", bold=True)
    d.scene.text(90, 172, "最近 N 轮对话 / 当前子任务状态 · 滑动窗口淘汰", size=13, color=MUTED)
    d.scene.text(1010, 155, "读: 每轮注入", size=12, color="#0369a1", anchor="end")

    d.scene.rect(60, 240, 1000, 100, fill="#ede9fe", stroke="#a78bfa", radius=12)
    d.scene.text(90, 275, "情景记忆（episodic）", size=16, color="#4c1d95", bold=True)
    d.scene.text(90, 302, "任务 → 步骤 → 结果的完整经历，按任务相似度召回", size=13, color=MUTED)
    d.scene.text(1010, 290, "读: top-k 相似任务", size=12, color="#6d28d9", anchor="end")

    d.scene.rect(60, 380, 1000, 100, fill="#dcfce7", stroke="#4ade80", radius=12)
    d.scene.text(90, 415, "语义记忆（semantic）", size=16, color="#14532d", bold=True)
    d.scene.text(90, 442, "稳定事实 / 用户偏好 / 领域知识，带时间戳与置信度", size=13, color=MUTED)
    d.scene.text(1010, 430, "读: 向量召回 + 重排", size=12, color="#15803d", anchor="end")

    # 写路径
    d.scene.line(240, 200, 240, 240, arrow=True, color="#0ea5e9", width=2)
    d.scene.label(330, 222, "压缩/提炼", size=12)
    d.scene.line(240, 340, 240, 380, arrow=True, color="#8b5cf6", width=2)
    d.scene.label(330, 362, "去重 / 冲突合并", size=12)

    # 读路径
    d.scene.line(860, 380, 860, 340, arrow=True, color="#22c55e", width=2)
    d.scene.line(860, 240, 860, 200, arrow=True, color="#22c55e", width=2)

    # 维护
    d.panel(60, 510, 470, 100, "淘汰策略", tone="white")
    d.note(85, 555, "工作：按轮数；情景：按时间 + 成功率；语义：按重要度 × 新近度。",
           size=12, width_chars=44)
    d.panel(590, 510, 470, 100, "失效信号", tone="white")
    d.note(615, 555, "同一事实出现两个版本、召回内容与当前任务无关、用户明确更正。",
           size=12, width_chars=44)
    return d


def fig_rag_pipeline() -> Diagram:
    d = Diagram(1160, 640, "图 5-1  检索增强的完整链路",
                "离线建索引，在线做融合与重排；每一段都可以单独评测")
    d.header()

    d.panel(40, 100, 1080, 210, "离线：建索引", tone="white")
    a = d.node("doc", 70, 160, 150, 84, "原始文档", "Markdown / PDF / 网页", tone="slate")
    b = d.node("chunk", 260, 160, 150, 84, "切分", "句边界 + 重叠", tone="sky")
    c1 = d.node("bm25", 460, 120, 170, 70, "BM25 索引", "精确词 / 型号 / 错误码", tone="amber")
    c2 = d.node("vec", 460, 214, 170, 70, "向量索引", "语义近似 / 同义改写", tone="violet")
    d.edge("doc", "chunk", "解析")
    d.edge("chunk", "bm25")
    d.edge("chunk", "vec")
    d.note(760, 180, "索引物化落盘，支持增量重建；\nembedding 模型版本必须与索引\n一起记录，否则召回会静默漂移。",
           size=12, width_chars=22)

    d.panel(40, 340, 1080, 210, "在线：检索与生成", tone="white")
    q = d.node("q", 70, 400, 150, 84, "用户问题", "可能含多跳意图", tone="slate")
    r1 = d.node("s1", 260, 360, 150, 64, "稀疏召回", "top-k", tone="amber")
    r2 = d.node("s2", 260, 444, 150, 64, "稠密召回", "top-k", tone="violet")
    fuse = d.node("rrf", 450, 400, 160, 84, "RRF 融合", "按排名而非分数", tone="indigo")
    rr = d.node("rerank", 650, 400, 160, 84, "重排", "词项覆盖 / 交叉编码", tone="sky")
    gen = d.node("gen", 850, 400, 180, 84, "带引用生成", "只依据资料作答", tone="emerald")
    d.edge("q", "s1", "query")
    d.edge("q", "s2")
    d.edge("s1", "rrf")
    d.edge("s2", "rrf")
    d.edge("rrf", "rerank", "top-20")
    d.edge("rerank", "gen", "top-3")

    d.panel(40, 570, 1080, 60, "", tone="white", dash="4 4")
    d.scene.text(60, 606, "评测锚点：召回率（该找到的找到了吗）· 引用覆盖率（答案标了来源吗）"
                          "· 忠实度（是否只用资料里的话）", size=13, color=MUTED)
    return d
