"""极简矢量场景描述层：一份布局，同时输出 SVG 与 PNG。

为什么不直接用 Mermaid / Graphviz：本机没有它们，且书籍插图需要完全可控的
排版（中文换行、色彩语义、箭头标签不压线）。这里只实现本书用得到的图元，
两种后端共享同一份布局，避免"文档里的图"和"能编辑的源"漂移。
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]
FONT_SVG = "'Microsoft YaHei','PingFang SC','Noto Sans CJK SC','Source Han Sans SC',sans-serif"

INK = "#0f172a"
MUTED = "#475569"
FAINT = "#94a3b8"
BG = "#ffffff"

TONES: dict[str, tuple[str, str, str]] = {
    # name: (fill, stroke, title color)
    "slate": ("#f8fafc", "#cbd5e1", INK),
    "indigo": ("#eef2ff", "#818cf8", "#312e81"),
    "sky": ("#e0f2fe", "#38bdf8", "#0c4a6e"),
    "emerald": ("#dcfce7", "#4ade80", "#14532d"),
    "amber": ("#fef3c7", "#fbbf24", "#78350f"),
    "rose": ("#ffe4e6", "#fb7185", "#881337"),
    "violet": ("#ede9fe", "#a78bfa", "#4c1d95"),
    "white": ("#ffffff", "#cbd5e1", INK),
}


@dataclass
class Prim:
    kind: str
    args: dict[str, Any]


@dataclass
class Scene:
    width: int
    height: int
    title: str = ""
    caption: str = ""
    prims: list[Prim] = field(default_factory=list)

    # ------------------------------------------------------------------ 图元
    def rect(self, x: float, y: float, w: float, h: float, fill: str = "#fff",
             stroke: str = "#cbd5e1", width: float = 2, radius: float = 10,
             dash: str = "", opacity: float = 1.0) -> None:
        self.prims.append(Prim("rect", dict(x=x, y=y, w=w, h=h, fill=fill, stroke=stroke,
                                            width=width, radius=radius, dash=dash,
                                            opacity=opacity)))

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = FAINT,
             width: float = 2, dash: str = "", arrow: bool = False) -> None:
        self.prims.append(Prim("line", dict(x1=x1, y1=y1, x2=x2, y2=y2, color=color,
                                            width=width, dash=dash, arrow=arrow)))

    def polyline(self, points: Sequence[tuple[float, float]], color: str = FAINT,
                 width: float = 2, dash: str = "", arrow: bool = True) -> None:
        self.prims.append(Prim("polyline", dict(points=list(points), color=color,
                                                width=width, dash=dash, arrow=arrow)))

    def text(self, x: float, y: float, value: str, size: float = 16, color: str = INK,
             anchor: str = "start", bold: bool = False, mono: bool = False,
             opacity: float = 1.0) -> None:
        self.prims.append(Prim("text", dict(x=x, y=y, s=value, size=size, color=color,
                                            anchor=anchor, bold=bold, mono=mono,
                                            opacity=opacity)))

    def circle(self, cx: float, cy: float, r: float, fill: str = "#fff",
               stroke: str = FAINT, width: float = 2) -> None:
        self.prims.append(Prim("circle", dict(cx=cx, cy=cy, r=r, fill=fill,
                                              stroke=stroke, width=width)))

    def path(self, d: str, color: str = FAINT, width: float = 2, dash: str = "",
             arrow: bool = False, fill: str = "none") -> None:
        self.prims.append(Prim("path", dict(d=d, color=color, width=width, dash=dash,
                                            arrow=arrow, fill=fill)))

    def label(self, x: float, y: float, value: str, size: float = 13,
              color: str = MUTED) -> None:
        """箭头标签：带白色底，避免压线。"""
        pad = 4
        w = _text_width(value, size) + pad * 2
        h = size + pad * 2
        self.rect(x - w / 2, y - h / 2, w, h, fill=BG, stroke="none", width=0, radius=4)
        self.text(x, y + size * 0.35, value, size=size, color=color, anchor="middle")


# ---------------------------------------------------------------------- 布局辅助
@dataclass
class Node:
    id: str
    x: float
    y: float
    w: float
    h: float
    title: str
    sub: str = ""
    tone: str = "slate"

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    def anchor(self, side: str) -> tuple[float, float]:
        return {
            "left": (self.x, self.cy),
            "right": (self.x + self.w, self.cy),
            "top": (self.cx, self.y),
            "bottom": (self.cx, self.y + self.h),
        }[side]


class Diagram:
    """在 Scene 之上提供"节点 + 边"的便捷 API。"""

    def __init__(self, width: int = 1120, height: int = 620, title: str = "",
                 subtitle: str = "") -> None:
        self.scene = Scene(width, height)
        self.nodes: dict[str, Node] = {}
        self.title = title
        self.subtitle = subtitle

    # ------------------------------------------------------------------ 节点
    def node(self, nid: str, x: float, y: float, w: float, h: float, title: str,
             sub: str = "", tone: str = "slate") -> Node:
        node = Node(nid, x, y, w, h, title, sub, tone)
        self.nodes[nid] = node
        fill, stroke, ink = TONES[tone]
        self.scene.rect(x, y, w, h, fill=fill, stroke=stroke, width=2, radius=12)
        has_sub = bool(sub)
        title_y = y + h / 2 - (9 if has_sub else 0)
        self.scene.text(node.cx, title_y, title, size=16, color=ink, anchor="middle", bold=True)
        if has_sub:
            lines = wrap_text(sub, max(int(w / 12.5), 6))[:3]
            for i, line in enumerate(lines):
                self.scene.text(node.cx, y + h / 2 + 13 + i * 17, line, size=12.5,
                                color=MUTED, anchor="middle")
        return node

    def panel(self, x: float, y: float, w: float, h: float, title: str = "",
              tone: str = "white", dash: str = "6 4") -> None:
        fill, stroke, ink = TONES[tone]
        self.scene.rect(x, y, w, h, fill=fill, stroke=stroke, width=1.5, radius=14,
                        dash=dash, opacity=0.55 if tone == "white" else 1.0)
        if title:
            self.scene.text(x + 16, y + 26, title, size=14, color=ink, bold=True)

    def band(self, x: float, y: float, w: float, h: float, label: str,
             color: str = "#6366f1") -> None:
        self.scene.rect(x, y, w, h, fill=color, stroke=color, width=0, radius=8, opacity=0.10)
        self.scene.text(x + w / 2, y + h - 10, label, size=13, color=color, anchor="middle")

    # ------------------------------------------------------------------ 边
    def edge(self, src: str, dst: str, label: str = "", *, sides: tuple[str, str] | None = None,
             color: str = "#64748b", dash: str = "", width: float = 2.2, offset: float = 0) -> None:
        a, b = self.nodes[src], self.nodes[dst]
        s_side, d_side = sides or _pick_sides(a, b)
        x1, y1 = a.anchor(s_side)
        x2, y2 = b.anchor(d_side)
        if offset:
            if s_side in ("left", "right"):
                y1 += offset
                y2 += offset
            else:
                x1 += offset
                x2 += offset
        self._route((x1, y1), (x2, y2), s_side, d_side, label, color, dash, width)

    def _route(self, p1, p2, s_side: str, d_side: str, label: str, color: str,
               dash: str, width: float) -> None:
        horizontal = s_side in ("left", "right") and d_side in ("left", "right")
        vertical = s_side in ("top", "bottom") and d_side in ("top", "bottom")
        if horizontal and abs(p1[1] - p2[1]) < 1:
            self.scene.line(*p1, *p2, color=color, width=width, dash=dash, arrow=True)
            mid = ((p1[0] + p2[0]) / 2, p1[1] - 14)
        elif vertical and abs(p1[0] - p2[0]) < 1:
            self.scene.line(*p1, *p2, color=color, width=width, dash=dash, arrow=True)
            mid = (p1[0], (p1[1] + p2[1]) / 2)
        else:
            if s_side in ("left", "right"):
                mx = (p1[0] + p2[0]) / 2
                points = [p1, (mx, p1[1]), (mx, p2[1]), p2]
            else:
                my = (p1[1] + p2[1]) / 2
                points = [p1, (p1[0], my), (p2[0], my), p2]
            self.scene.polyline(points, color=color, width=width, dash=dash, arrow=True)
            mid = (points[1][0], (points[1][1] + points[2][1]) / 2) if s_side in ("left", "right") \
                else (points[2][0], points[1][1])
        if label:
            self.scene.label(mid[0], mid[1], label)

    def loop(self, nid: str, label: str, *, side: str = "left", drop: float = 40,
             color: str = "#f59e0b") -> None:
        """自环：用于"重试 / 反思 / 重规划"。"""
        node = self.nodes[nid]
        if side == "left":
            x = node.x
            points = [(x, node.cy - 18), (x - drop, node.cy - 18), (x - drop, node.cy + 18),
                      (x, node.cy + 18)]
        else:
            x = node.x + node.w
            points = [(x, node.cy - 18), (x + drop, node.cy - 18), (x + drop, node.cy + 18),
                      (x, node.cy + 18)]
        self.scene.polyline(points, color=color, width=2.2, arrow=True)
        self.scene.label(x + (drop if side == "right" else -drop) / 2,
                         node.cy - 10, label, size=12, color=color)

    # ------------------------------------------------------------------ 装饰
    def note(self, x: float, y: float, text: str, size: float = 13,
             color: str = MUTED, width_chars: int = 46) -> None:
        for i, line in enumerate(wrap_text(text, width_chars)):
            self.scene.text(x, y + i * (size + 6), line, size=size, color=color)

    def tag(self, x: float, y: float, text: str, tone: str = "indigo") -> None:
        fill, stroke, ink = TONES[tone]
        w = _text_width(text, 12) + 18
        self.scene.rect(x, y, w, 24, fill=fill, stroke=stroke, width=1.5, radius=12)
        self.scene.text(x + w / 2, y + 16.5, text, size=12, color=ink, anchor="middle", bold=True)

    # ------------------------------------------------------------------ 输出
    def header(self) -> None:
        if self.title:
            self.scene.text(40, 44, self.title, size=23, color=INK, bold=True)
        if self.subtitle:
            self.scene.text(40, 70, self.subtitle, size=14, color=MUTED)

    def render_png(self, path: str | Path, scale: int = 2) -> Path:
        return render_png(self, path, scale)

    def render_svg(self, path: str | Path) -> Path:
        return render_svg(self, path)


def _pick_sides(a: Node, b: Node) -> tuple[str, str]:
    if abs(b.cx - a.cx) >= abs(b.cy - a.cy):
        return ("right", "left") if b.cx > a.cx else ("left", "right")
    return ("bottom", "top") if b.cy > a.cy else ("top", "bottom")


def wrap_text(text: str, width: int) -> list[str]:
    """按显示宽度折行：CJK 记 1，ASCII 记 0.6。"""
    lines: list[str] = []
    current, used = "", 0.0
    for ch in text:
        step = 1.0 if "\u4e00" <= ch <= "\u9fff" else 0.55
        if used + step > width and current:
            lines.append(current)
            current, used = "", 0.0
        current += ch
        used += step
    if current:
        lines.append(current)
    return lines


def _text_width(text: str, size: float) -> float:
    """按字符计数一次乘出来，避免逐字符累加在 .x5 边界上出现浮点抖动。"""
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    ascii_count = len(text) - cjk
    return round(size * (cjk + 0.55 * ascii_count), 1)


# ---------------------------------------------------------------------- PNG 后端
def render_png(diagram: Diagram, path: str | Path, scale: int = 2) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    scene = diagram.scene
    img = Image.new("RGB", (scene.width * scale, scene.height * scale), BG)
    draw = ImageDraw.Draw(img)
    fonts: dict[tuple[bool, int], Any] = {}

    def font(size: int, bold: bool) -> Any:
        key = (bold, size)
        if key not in fonts:
            path_ = "C:/Windows/Fonts/msyhbd.ttc" if bold else FONT_CANDIDATES[0]
            fonts[key] = ImageFont.truetype(path_, int(size * scale))
        return fonts[key]

    def sc(v: float) -> float:
        return v * scale

    for prim in scene.prims:
        a = prim.args
        if prim.kind == "rect":
            if a["width"] == 0:
                draw.rectangle([sc(a["x"]), sc(a["y"]), sc(a["x"] + a["w"]), sc(a["y"] + a["h"])],
                               fill=a["fill"])
            else:
                draw.rounded_rectangle(
                    [sc(a["x"]), sc(a["y"]), sc(a["x"] + a["w"]), sc(a["y"] + a["h"])],
                    radius=sc(a["radius"]), fill=a["fill"], outline=a["stroke"],
                    width=max(int(sc(a["width"])), 1))
        elif prim.kind == "line":
            draw.line([sc(a["x1"]), sc(a["y1"]), sc(a["x2"]), sc(a["y2"])],
                      fill=a["color"], width=max(int(sc(a["width"])), 1))
            if a["arrow"]:
                _arrow_png(draw, (a["x1"], a["y1"]), (a["x2"], a["y2"]), a["color"], sc, scale)
        elif prim.kind == "polyline":
            pts = [(sc(x), sc(y)) for x, y in a["points"]]
            draw.line(pts, fill=a["color"], width=max(int(sc(a["width"])), 1), joint="curve")
            if a["arrow"]:
                _arrow_png(draw, a["points"][-2], a["points"][-1], a["color"], sc, scale)
        elif prim.kind == "text":
            f = font(a["size"], a["bold"])
            xy = (sc(a["x"]), sc(a["y"]))
            draw.text(xy, a["s"], font=f, fill=a["color"], anchor=_pil_anchor(a["anchor"]))
        elif prim.kind == "circle":
            draw.ellipse([sc(a["cx"] - a["r"]), sc(a["cy"] - a["r"]),
                          sc(a["cx"] + a["r"]), sc(a["cy"] + a["r"])],
                         fill=a["fill"], outline=a["stroke"], width=max(int(sc(a["width"])), 1))
        elif prim.kind == "path":
            continue  # PNG 后端不支持贝塞尔，本书的图不使用 path

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def _pil_anchor(anchor: str) -> str:
    return {"start": "lm", "middle": "mm", "end": "rm"}[anchor]


def _arrow_png(draw: Any, p1, p2, color: str, sc: Any, scale: int) -> None:
    angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    length, width = 11, 6
    tip = (sc(p2[0]), sc(p2[1]))
    base = (tip[0] - length * scale * math.cos(angle),
            tip[1] - length * scale * math.sin(angle))
    left = (base[0] - width * scale * math.sin(angle), base[1] + width * scale * math.cos(angle))
    right = (base[0] + width * scale * math.sin(angle), base[1] - width * scale * math.cos(angle))
    draw.polygon([tip, left, right], fill=color)


# ---------------------------------------------------------------------- SVG 后端
def render_svg(diagram: Diagram, path: str | Path) -> Path:
    scene = diagram.scene
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {scene.width} {scene.height}" '
        f'width="{scene.width}" height="{scene.height}" role="img">',
        f'<rect width="{scene.width}" height="{scene.height}" fill="{BG}"/>',
        "<style>text{font-family:" + FONT_SVG + ";}</style>",
    ]
    for prim in scene.prims:
        a = prim.args
        if prim.kind == "rect":
            parts.append(
                f'<rect x="{a["x"]:.1f}" y="{a["y"]:.1f}" width="{a["w"]:.1f}" '
                f'height="{a["h"]:.1f}" rx="{a["radius"]:.1f}" fill="{a["fill"]}" '
                f'fill-opacity="{a["opacity"]}" stroke="{a["stroke"]}" '
                f'stroke-width="{a["width"]:.1f}"'
                + (f' stroke-dasharray="{a["dash"]}"' if a["dash"] else "") + "/>")
        elif prim.kind == "line":
            parts.append(
                f'<line x1="{a["x1"]:.1f}" y1="{a["y1"]:.1f}" x2="{a["x2"]:.1f}" '
                f'y2="{a["y2"]:.1f}" stroke="{a["color"]}" stroke-width="{a["width"]:.1f}"'
                + (f' stroke-dasharray="{a["dash"]}"' if a["dash"] else "") + "/>")
            if a["arrow"]:
                parts.append(_arrow_svg((a["x1"], a["y1"]), (a["x2"], a["y2"]), a["color"]))
        elif prim.kind == "polyline":
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in a["points"])
            parts.append(
                f'<polyline points="{pts}" fill="none" stroke="{a["color"]}" '
                f'stroke-width="{a["width"]:.1f}" stroke-linejoin="round"'
                + (f' stroke-dasharray="{a["dash"]}"' if a["dash"] else "") + "/>")
            if a["arrow"]:
                parts.append(_arrow_svg(a["points"][-2], a["points"][-1], a["color"]))
        elif prim.kind == "text":
            weight = ' font-weight="700"' if a["bold"] else ""
            escape = _esc(a["s"])
            parts.append(
                f'<text x="{a["x"]:.1f}" y="{a["y"]:.1f}" font-size="{a["size"]:.1f}" '
                f'fill="{a["color"]}" text-anchor="{a["anchor"]}"{weight} '
                f'dominant-baseline="middle">{escape}</text>')
        elif prim.kind == "circle":
            parts.append(
                f'<circle cx="{a["cx"]:.1f}" cy="{a["cy"]:.1f}" r="{a["r"]:.1f}" '
                f'fill="{a["fill"]}" stroke="{a["stroke"]}" stroke-width="{a["width"]:.1f}"/>')
    parts.append("</svg>")
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts), encoding="utf-8")
    return out


def _arrow_svg(p1, p2, color: str) -> str:
    angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    length, width = 11.0, 6.0
    tip = p2
    base = (tip[0] - length * math.cos(angle), tip[1] - length * math.sin(angle))
    left = (base[0] - width * math.sin(angle), base[1] + width * math.cos(angle))
    right = (base[0] + width * math.sin(angle), base[1] - width * math.cos(angle))
    return (f'<polygon points="{tip[0]:.1f},{tip[1]:.1f} {left[0]:.1f},{left[1]:.1f} '
            f'{right[0]:.1f},{right[1]:.1f}" fill="{color}"/>')


def _esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
