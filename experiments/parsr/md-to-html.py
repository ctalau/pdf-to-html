#!/usr/bin/env python3
"""Convert markdown to HTML with multiple fallbacks."""
from __future__ import annotations
import html
import re
import subprocess
import sys
from pathlib import Path


def convert_with_python_markdown(md: str) -> str | None:
    try:
        import markdown  # type: ignore
        return markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"])
    except Exception:
        return None


def convert_with_markdown2(md: str) -> str | None:
    try:
        import markdown2  # type: ignore
        return markdown2.markdown(md, extras=["tables", "fenced-code-blocks", "strike", "cuddled-lists"])
    except Exception:
        return None


def convert_with_pandoc(md: str) -> str | None:
    try:
        proc = subprocess.run(
            ["pandoc", "-f", "markdown", "-t", "html"],
            input=md,
            text=True,
            capture_output=True,
            check=True,
        )
        return proc.stdout
    except Exception:
        return None


def convert_with_basic_fallback(md: str) -> str:
    lines = md.splitlines()
    out = []
    in_list = False
    for raw in lines:
        line = raw.rstrip()
        if not line:
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        if line.startswith("#"):
            if in_list:
                out.append("</ul>")
                in_list = False
            lvl = min(6, len(line) - len(line.lstrip("#")))
            text = html.escape(line[lvl:].strip())
            out.append(f"<h{lvl}>{text}</h{lvl}>")
        elif re.match(r"^[-*+]\s+", line):
            if not in_list:
                out.append("<ul>")
                in_list = True
            text = html.escape(re.sub(r"^[-*+]\s+", "", line))
            out.append(f"<li>{text}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def markdown_to_html(md: str, title: str) -> tuple[str, str]:
    for name, fn in [
        ("python-markdown", convert_with_python_markdown),
        ("markdown2", convert_with_markdown2),
        ("pandoc", convert_with_pandoc),
    ]:
        result = fn(md)
        if result:
            return result, name
    return convert_with_basic_fallback(md), "basic-fallback"


def main() -> int:
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input.md> <output.html> [title]", file=sys.stderr)
        return 1
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    title = sys.argv[3] if len(sys.argv) > 3 else in_path.stem

    md = in_path.read_text(encoding="utf-8", errors="replace")
    body, engine = markdown_to_html(md, title)
    html_doc = f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\">\n<title>{html.escape(title)}</title>\n</head>\n<body>\n{body}\n</body>\n</html>\n"
    out_path.write_text(html_doc, encoding="utf-8")
    print(engine)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
