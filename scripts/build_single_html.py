#!/usr/bin/env python3
"""Build a self-contained dashboard HTML with manifest and digest data embedded."""
import argparse
import re
from pathlib import Path

from common import ROOT, digest_path_for, extract_latest_from_manifest, normalize_date, read_text, write_text


DATA_SCRIPT_RE = re.compile(
    r'<script\s+src=["\']data/(?:manifest\.js|\d{4}/\d{2}/\d{2}/digest(?:\.en)?\.js)["\']\s*>\s*</script>\s*',
    re.I,
)


def safe_inline_javascript(text):
    return re.sub(r"</script", r"<\\/script", text, flags=re.I)


def build(date_value, output):
    if date_value == "latest":
        latest = extract_latest_from_manifest()
        if not latest:
            raise SystemExit("[bundle] manifest.js 未找到 latest")
        date_value = latest
    date_iso = normalize_date(date_value)
    digest = digest_path_for(date_iso)
    if not digest.exists():
        raise SystemExit("[bundle] 未找到 digest: %s" % digest)

    html = read_text(ROOT / "index.html")
    html = DATA_SCRIPT_RE.sub("", html)
    embedded = "\n".join([
        "<script id=\"embedded-dashboard-data\">",
        safe_inline_javascript(read_text(ROOT / "data" / "manifest.js")),
        safe_inline_javascript(read_text(digest)),
        "</script>",
    ])
    head_end = html.lower().find("</head>")
    if head_end < 0:
        raise SystemExit("[bundle] index.html 缺少 </head>")
    html = html[:head_end] + embedded + "\n" + html[head_end:]
    html = html.replace("<title>", "<title>离线分享版 · ", 1)
    html = "<!-- 单文件离线分享版：数据已内嵌，可直接双击打开。生成日期 %s -->\n" % date_iso + html
    out = ROOT / output
    write_text(out, html)
    print("[bundle] wrote", out)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="latest", help="latest, YYYY-MM-DD, or YYYY/MM/DD")
    parser.add_argument("--output", default="share/ai-intel-dashboard-latest.html")
    args = parser.parse_args()
    build(args.date, args.output)


if __name__ == "__main__":
    main()
