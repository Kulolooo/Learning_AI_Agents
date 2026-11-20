"""仓库自检：链接、图片、章节结构、book.html 完整性。

    python tools/check_links.py

CI 里跑这一条即可发现"文档引用了不存在的图"这类低级但高频的问题。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = sorted((ROOT / "docs").glob("*.md")) + [ROOT / "README.md"]
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def check_links() -> list[str]:
    problems: list[str] = []
    for doc in DOCS:
        for target in LINK.findall(doc.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            path = (doc.parent / target.split("#")[0]).resolve()
            if not path.exists():
                problems.append(f"{doc.relative_to(ROOT)} -> 缺失 {target}")
    return problems


def check_structure() -> list[str]:
    problems: list[str] = []
    for doc in sorted((ROOT / "docs").glob("*.md")):
        text = doc.read_text(encoding="utf-8")
        if not text.startswith("# "):
            problems.append(f"{doc.name}: 缺少一级标题")
        if "## " not in text:
            problems.append(f"{doc.name}: 没有二级标题")
        numbered = doc.name[0].isdigit() and not doc.name.startswith("00")
        if numbered and not re.search(r"^## (\d+\.|学习目标)", text, flags=re.M):
            problems.append(f"{doc.name}: 缺少学习目标或编号小节")
        if text.count("```") % 2:
            problems.append(f"{doc.name}: 代码围栏未闭合")
    return problems


def check_book() -> list[str]:
    book = ROOT / "book.html"
    if not book.exists():
        return ["book.html 不存在，请先运行 python build.py"]
    text = book.read_text(encoding="utf-8")
    problems = []
    if "缺图" in text:
        problems.append("book.html 存在缺图占位，检查图片路径")
    if text.count("<svg") < 14:
        problems.append(f"book.html 只内联了 {text.count('<svg')} 张图（期望 14）")
    ids = set(re.findall(r'id="([^"]+)"', text))
    missing = sorted({h for h in re.findall(r'href="#([^"]+)"', text) if h not in ids})
    if missing:
        problems.append(f"book.html 有 {len(missing)} 个锚点未命中：{missing[:5]}")
    return problems


def main() -> int:
    groups = {
        "链接": check_links(),
        "章节结构": check_structure(),
        "book.html": check_book(),
    }
    failed = False
    for name, problems in groups.items():
        if problems:
            failed = True
            print(f"[{name}] {len(problems)} 个问题")
            for item in problems:
                print("  -", item)
        else:
            print(f"[{name}] 通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
