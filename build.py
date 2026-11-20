"""把 docs/ 与 README 编译成单页 ``book.html``。

做三件事：

1. 把 Markdown 的一个子集转成 HTML（标题、段落、列表、表格、代码、引用、图）；
2. 把 SVG 插图内联进页面，PNG 转成 data URI——产物不依赖外部文件与网络；
3. 生成侧边目录与锚点，并处理跨文档链接（``xxx.md`` → 页内锚点）。

不追求完整 Markdown 兼容：本库用不到的语法一律不实现，出错时宁可原样输出。
"""

from __future__ import annotations

import base64
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DOCS = [
    ("index", "封面与导航", None),
    ("00-preface", "00 · 导论", "docs/00-preface.md"),
    ("01-agent-loop", "01 · 定义与最小闭环", "docs/01-agent-loop.md"),
    ("02-context", "02 · 上下文工程", "docs/02-context.md"),
    ("03-tools", "03 · 工具调用", "docs/03-tools.md"),
    ("04-memory", "04 · 记忆系统", "docs/04-memory.md"),
    ("05-planning", "05 · 规划与路由", "docs/05-planning.md"),
    ("06-reflection", "06 · 反思与自我修正", "docs/06-reflection.md"),
    ("07-rag", "07 · 检索增强", "docs/07-rag.md"),
    ("08-multiagent", "08 · 多智能体", "docs/08-multiagent.md"),
    ("09-orchestration", "09 · 图编排", "docs/09-orchestration.md"),
    ("10-evaluation", "10 · 评估与可观测", "docs/10-evaluation.md"),
    ("11-case-research", "11 · 案例：研究助手", "docs/11-case-research.md"),
    ("12-case-ticket", "12 · 案例：工单处理", "docs/12-case-ticket.md"),
    ("13-production", "13 · 从原型到产品", "docs/13-production.md"),
    ("A-glossary", "A · 术语表", "docs/A-glossary.md"),
    ("B-upstream-map", "B · 上游教程映射", "docs/B-upstream-map.md"),
    ("C-references", "C · 参考与许可", "docs/C-references.md"),
]

CSS = """
:root{--ink:#0f172a;--muted:#475569;--line:#e2e8f0;--accent:#4338ca;--bg:#fff;--soft:#f8fafc}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Microsoft YaHei","PingFang SC","Noto Sans CJK SC",system-ui,sans-serif;line-height:1.75}
#layout{display:grid;grid-template-columns:280px minmax(0,1fr);gap:0;max-width:1500px;margin:0 auto}
nav#toc{position:sticky;top:0;height:100vh;overflow:auto;padding:28px 18px 60px;border-right:1px solid var(--line);font-size:14px}
nav#toc h2{font-size:15px;margin:0 0 12px;color:var(--muted);letter-spacing:.05em}
nav#toc a{display:block;color:var(--ink);text-decoration:none;padding:3px 6px;border-radius:6px}
nav#toc a:hover{background:var(--soft);color:var(--accent)}
nav#toc a.sub{font-size:12.5px;color:var(--muted);padding-left:16px}
main{padding:40px 56px 120px;max-width:980px}
h1{font-size:30px;line-height:1.3;margin:0 0 18px;padding-bottom:12px;border-bottom:2px solid var(--ink)}
h2{font-size:22px;margin:40px 0 14px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:17px;margin:26px 0 10px}
p{margin:12px 0}
blockquote{margin:18px 0;padding:12px 18px;border-left:4px solid var(--accent);background:var(--soft);color:var(--muted)}
code{font-family:"Cascadia Mono",Consolas,"Courier New",monospace;font-size:.9em;background:#f1f5f9;padding:2px 5px;border-radius:4px}
pre{background:#0f172a;color:#e2e8f0;padding:16px 18px;border-radius:10px;overflow:auto;line-height:1.55}
pre code{background:none;color:inherit;padding:0;font-size:13px}
table{border-collapse:collapse;width:100%;margin:18px 0;font-size:14.5px;display:block;overflow:auto}
th,td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
th{background:var(--soft);font-weight:700}
tr:nth-child(even) td{background:#fcfdff}
ul,ol{padding-left:24px}
li{margin:6px 0}
figure{margin:26px 0;text-align:center}
figure svg,figure img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:8px;background:#fff}
figcaption{font-size:13.5px;color:var(--muted);margin-top:8px}
hr{border:none;border-top:1px solid var(--line);margin:36px 0}
a{color:var(--accent);text-decoration:none;border-bottom:1px solid rgba(67,56,202,.25)}
a:hover{border-bottom-color:var(--accent)}
.mermaid-src{border:1px dashed var(--line);border-radius:8px;padding:10px 12px;background:var(--soft)}
.mermaid-src .hint{font-size:12px;color:var(--muted);margin-bottom:6px}
.cover{padding:10px 0 26px}
.cover .kicker{color:var(--accent);font-weight:700;letter-spacing:.12em;font-size:13px}
.cover h1{border:none;font-size:40px;margin:8px 0 10px}
.cover .lead{font-size:17px;color:var(--muted);max-width:760px}
.meta{display:flex;gap:18px;flex-wrap:wrap;margin-top:18px;font-size:13px;color:var(--muted)}
.meta span{background:var(--soft);border:1px solid var(--line);border-radius:999px;padding:4px 12px}
footer{padding:30px 56px 60px;color:var(--muted);font-size:13px;border-top:1px solid var(--line)}
@media(max-width:900px){#layout{grid-template-columns:1fr}nav#toc{position:relative;height:auto;border-right:none;border-bottom:1px solid var(--line)}main{padding:24px 20px 80px}}
@media print{nav#toc{display:none}#layout{display:block}main{max-width:none;padding:0}pre{white-space:pre-wrap}}
"""


# --------------------------------------------------------------------------- 行内
def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: _link(m.group(1), m.group(2)), text)
    return text


def _link(label: str, target: str) -> str:
    if target.startswith(("http://", "https://", "#")):
        return f'<a href="{target}" target="_blank" rel="noreferrer">{label}</a>'
    stem = Path(target).stem
    anchor = "#doc-" + stem if stem in {d[0] for d in DOCS} else "#"
    return f'<a href="{anchor}">{label}</a>'


# --------------------------------------------------------------------------- 块级
def convert(md: str, base: Path | None = None) -> str:
    base = base or ROOT
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            i += 1
            buf: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            code = "\n".join(buf)
            if lang == "mermaid":
                out.append('<div class="mermaid-src"><div class="hint">'
                           "Mermaid 流程图源码（GitHub / Typora / VS Code 可直接渲染）</div>"
                           f"<pre><code>{html.escape(code)}</code></pre></div>")
            else:
                out.append(f'<pre><code class="lang-{lang}">{html.escape(code)}</code></pre>')
            continue

        if stripped.startswith("<") and stripped.endswith(">"):
            out.append(line)          # 允许内嵌 HTML
            i += 1
            continue

        if not stripped:
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].strip()) <= set("|-: "):
            rows, i = _table(lines, i)
            out.append(rows)
            continue

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped[level:].strip()
            anchor = _slug(title)
            out.append(f'<h{min(level, 4)} id="{anchor}">{inline(title)}</h{min(level, 4)}>')
            i += 1
            continue

        if stripped.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            out.append(f"<blockquote>{inline(' '.join(buf))}</blockquote>")
            continue

        if re.match(r"^\s*[-*]\s+", line):
            items, i = _list(lines, i, ordered=False)
            out.append(items)
            continue

        if re.match(r"^\s*\d+\.\s+", line):
            items, i = _list(lines, i, ordered=True)
            out.append(items)
            continue

        if stripped.startswith("![") and "(" in stripped:
            out.append(_figure(stripped, base))
            i += 1
            continue

        # 段落：连续非空行合并
        buf = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not _block_start(lines[i]):
            buf.append(lines[i].strip())
            i += 1
        out.append(f"<p>{inline(' '.join(buf))}</p>")

    return "\n".join(out)


def _block_start(line: str) -> bool:
    s = line.strip()
    return (s.startswith(("#", "```", "|", ">", "![", "<"))
            or bool(re.match(r"^[-*]\s+", s)) or bool(re.match(r"^\d+\.\s+", s)))


def _table(lines: list[str], start: int) -> tuple[str, int]:
    def cells(row: str) -> list[str]:
        return [c.strip() for c in row.strip().strip("|").split("|")]

    header = cells(lines[start])
    align = cells(lines[start + 1])
    body: list[list[str]] = []
    i = start + 2
    while i < len(lines) and lines[i].strip().startswith("|"):
        body.append(cells(lines[i]))
        i += 1
    head_html = "".join(f"<th>{inline(c)}</th>" for c in header)
    rows = []
    for row in body:
        tds = []
        for idx, cell in enumerate(row):
            style = ""
            if idx < len(align):
                if align[idx].endswith(":") and align[idx].startswith(":"):
                    style = ' style="text-align:center"'
                elif align[idx].endswith(":"):
                    style = ' style="text-align:right"'
            tds.append(f"<td{style}>{inline(cell)}</td>")
        rows.append("<tr>" + "".join(tds) + "</tr>")
    return f"<table><thead><tr>{head_html}</tr></thead><tbody>{''.join(rows)}</tbody></table>", i


def _list(lines: list[str], start: int, ordered: bool) -> tuple[str, int]:
    pattern = r"^\s*\d+\.\s+" if ordered else r"^\s*[-*]\s+"
    items = []
    i = start
    while i < len(lines):
        s = lines[i]
        if re.match(pattern, s):
            items.append(re.sub(pattern, "", s).strip())
            i += 1
        elif s.startswith("  ") and items:
            items[-1] += " " + s.strip()
            i += 1
        else:
            break
    tag = "ol" if ordered else "ul"
    body = "".join(f"<li>{inline(item)}</li>" for item in items)
    return f"<{tag}>{body}</{tag}>", i


_IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def _figure(raw: str, base: Path = ROOT) -> str:
    m = _IMG.search(raw)
    if not m:
        return f"<p>{inline(raw)}</p>"
    alt, src = m.group(1), m.group(2)
    path = (base / src).resolve()
    if not path.exists():
        return f'<figure><figcaption>{inline(alt)}（缺图：{src}）</figcaption></figure>'
    if path.suffix.lower() == ".svg":
        svg = path.read_text(encoding="utf-8")
        svg = re.sub(r"<\?xml[^>]*\?>", "", svg).strip()
        return f"<figure>{svg}<figcaption>{inline(alt)}</figcaption></figure>"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return (f'<figure><img src="data:{mime};base64,{data}" alt="{html.escape(alt)}">'
            f"<figcaption>{inline(alt)}</figcaption></figure>")


_SLUG_MAP: dict[str, str] = {}


def _slug(title: str) -> str:
    base = re.sub(r"[^\w\u4e00-\u9fff]+", "-", title).strip("-").lower() or "section"
    count = _SLUG_MAP.get(base, 0) + 1
    _SLUG_MAP[base] = count
    return base if count == 1 else f"{base}-{count}"


# --------------------------------------------------------------------------- 页面
def cover() -> str:
    return f"""
<section id="doc-index" class="cover">
  <div class="kicker">LEARNING AI AGENTS</div>
  <h1>把智能体拆开看</h1>
  <p class="lead">一个偏探讨性质的中文智能体工程笔记库：十三个章节、十四张架构图、
  一个零依赖实现。讲清楚循环、上下文、工具、记忆、规划、检索、协作与评估，
  以及它们各自的代价。</p>
  <div class="meta"><span>13 章 · 3 附录</span><span>14 张矢量插图</span>
  <span>42 个单元测试</span><span>零运行时依赖</span></div>
</section>
"""


def build() -> Path:
    sections = [cover()]
    toc: list[str] = []
    for doc_id, title, path in DOCS:
        if path is None:
            continue
        md = (ROOT / path).read_text(encoding="utf-8")
        body = convert(md, (ROOT / path).parent)
        sections.append(f'<section id="doc-{doc_id}">\n{body}\n</section>')
        toc.append(f'<a href="#doc-{doc_id}">{html.escape(title)}</a>')
        # 目录直接复用正文里已生成的 id，避免二次 slug 产生 -2 之类的重名
        for level, anchor, text in re.findall(
                r'<h([23]) id="([^"]+)">(.+?)</h\1>', body):
            plain = re.sub(r"<[^>]+>", "", text)
            toc.append(f'<a class="sub" href="#{anchor}">{html.escape(plain)}</a>')

    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Learning_AI_Agents · 把智能体拆开看</title>
<style>{CSS}</style>
</head>
<body>
<div id="layout">
<nav id="toc">
  <h2>目录</h2>
  {''.join(toc)}
</nav>
<main>
{''.join(sections)}
</main>
</div>
<footer>
  Learning_AI_Agents · 由 build.py 生成 · 代码 MIT，文档 CC BY 4.0
</footer>
</body>
</html>
"""
    out = ROOT / "book.html"
    out.write_text(page, encoding="utf-8")
    return out


if __name__ == "__main__":
    path = build()
    size = path.stat().st_size / 1024
    print(f"book.html 已生成：{size:.0f} KB")
