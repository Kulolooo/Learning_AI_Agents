"""文风审计：按 research-writing 技能的禁用清单统计"AI 味"指标。

    python tools/style_audit.py            # 全部文档
    python tools/style_audit.py docs/01-agent-loop.md

统计口径与技能里的 style_check.ps1 对齐，另加几项中文技术写作的高频套话
（"不是A而是B""真正""本质上""这意味着"）。代码块与表格内的文本不计入，
否则示例代码里的 `**kwargs` 会污染结果。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PATTERNS = {
    "机械过渡": r"首先|其次|最后|此外|另外|接下来|总之",
    "空壳强调": r"值得注意的是|需要指出的是|重要的是|必须强调的是|显而易见",
    "不是A而是B": r"不是[^。；\n]{1,14}而是",
    "拔高词": r"真正的|本质上|从根本上|恰恰|正是",
    "解释套话": r"换句话说|也就是说|这意味着|一句话",
    "破折号": r"——",
}


def prose_only(text: str) -> str:
    """去掉代码块、行内代码、表格与图片链接。"""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"`[^`]*`", "", text)
    text = "\n".join(line for line in text.splitlines() if not line.strip().startswith("|"))
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    return text


def audit(path: Path) -> dict[str, int]:
    text = prose_only(path.read_text(encoding="utf-8"))
    stats = {name: len(re.findall(pattern, text)) for name, pattern in PATTERNS.items()}
    stats["加粗"] = len(re.findall(r"\*\*[^*\n]+\*\*", text))
    stats["列表行"] = len(re.findall(r"^\s*(?:[-*+]|\d+\.)\s+", text, flags=re.M))
    stats["字数"] = len(re.findall(r"[\u4e00-\u9fff]", text))
    return stats


def main(argv: list[str]) -> int:
    targets = [Path(a) for a in argv] if argv else sorted(ROOT.glob("docs/*.md")) + [ROOT / "README.md"]
    header = ["文件", *PATTERNS, "加粗", "列表行", "字数"]
    rows = []
    totals = {k: 0 for k in header[1:]}
    for path in targets:
        if not path.exists():
            print(f"跳过不存在的文件：{path}")
            continue
        stats = audit(path)
        rows.append([path.name, *[stats[k] for k in header[1:]]])
        for k in header[1:]:
            totals[k] += stats[k]

    widths = [max(len(str(r[i])) for r in [header, *rows]) for i in range(len(header))]
    for row in [header, *rows]:
        print("  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))
    print("-" * (sum(widths) + 2 * len(widths)))
    totals_row = ["合计".ljust(widths[0])]
    totals_row += [str(totals[k]).ljust(widths[i]) for i, k in enumerate(header[1:], start=1)]
    print("  ".join(totals_row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
