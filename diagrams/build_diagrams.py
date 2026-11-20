"""渲染全部插图：``python diagrams/build_diagrams.py``

输出到 ``diagrams/out/``：同名 ``.svg``（放进书里）与 ``.png``（便于预览、
也用于 GitHub 渲染不支持的场景）。
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import figures_core  # noqa: E402
import figures_ext  # noqa: E402

OUT = HERE / "out"

FIGURES = {
    "fig-01-agent-loop": figures_core.fig_agent_loop,
    "fig-02-context-budget": figures_core.fig_context_budget,
    "fig-03-tool-call": figures_core.fig_tool_call,
    "fig-04-memory-layers": figures_core.fig_memory_layers,
    "fig-05-rag-pipeline": figures_core.fig_rag_pipeline,
    "fig-06-plan-execute": figures_ext.fig_plan_execute,
    "fig-07-reflection": figures_ext.fig_reflection,
    "fig-08-topologies": figures_ext.fig_topologies,
    "fig-09-orchestration": figures_ext.fig_orchestration,
    "fig-10-eval-loop": figures_ext.fig_eval_loop,
    "fig-11-curriculum": figures_ext.fig_curriculum,
    "fig-12-research-agent": figures_ext.fig_research_agent,
    "fig-13-ticket-agent": figures_ext.fig_ticket_agent,
    "fig-14-autonomy": figures_ext.fig_autonomy,
}


def main(argv: list[str] | None = None) -> int:
    only = set(argv or [])
    OUT.mkdir(parents=True, exist_ok=True)
    for name, factory in FIGURES.items():
        if only and name not in only:
            continue
        diagram = factory()
        png = diagram.render_png(OUT / f"{name}.png", scale=2)
        svg = diagram.render_svg(OUT / f"{name}.svg")
        print(f"{name:<24} {png.stat().st_size // 1024:>5} KB  {svg.stat().st_size // 1024:>4} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
