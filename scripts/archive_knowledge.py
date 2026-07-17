#!/usr/bin/env python3
"""Create weekly/monthly Markdown archives suitable for Obsidian or Notion import."""
import argparse
import datetime as dt
import json
import re
from pathlib import Path

from common import ROOT, read_text, write_text


def payloads(start, end):
    for path in sorted((ROOT / "data").glob("*/*/*/digest.js")):
        match = re.search(r'window\.__DAILY__\[[^]]+\]\s*=\s*(\{.*\})\s*;?\s*$', read_text(path), re.S)
        if not match:
            continue
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            print("[archive] skipped legacy non-JSON digest", path)
            continue
        day = dt.date.fromisoformat(data["date"])
        if start <= day <= end:
            yield data


def period_range(kind, value):
    if kind == "month":
        year, month = map(int, value.split("-"))
        start = dt.date(year, month, 1)
        end = (dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1))
    else:
        year, week = map(int, value.split("-W"))
        start = dt.date.fromisocalendar(year, week, 1)
        end = start + dt.timedelta(days=6)
    return start, end


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", choices=("week", "month"), required=True)
    parser.add_argument("--value", help="YYYY-Www or YYYY-MM; defaults to current period")
    parser.add_argument("--output-dir", default="knowledge-base")
    args = parser.parse_args()
    today = dt.date.today()
    if args.value:
        value = args.value
    elif args.period == "month":
        completed = today.replace(day=1) - dt.timedelta(days=1)
        value = completed.strftime("%Y-%m")
    else:
        completed = today - dt.timedelta(days=7)
        value = f"{completed.isocalendar().year}-W{completed.isocalendar().week:02d}"
    start, end = period_range(args.period, value)
    days = list(payloads(start, end))
    items = [item for day in days for item in day.get("items", [])]
    policy = [item for item in items if item.get("content_type") == "policy" or item.get("policy")]
    sectors = {}
    for item in policy:
        for sector in (item.get("policy") or {}).get("affected_industries", []) or ["待分类"]:
            sectors.setdefault(sector, []).append(item)
    lines = ["---", f"period: {value}", f"generated: {today.isoformat()}", "tags: [产业情报, 政策演进]", "---", "", f"# {value} 软件与互联网产业情报归档", "", f"> 覆盖 {len(days)} 天、{len(items)} 条情报，其中政策 {len(policy)} 条。", "", "## 政策演进脉络", ""]
    for sector, rows in sorted(sectors.items()):
        lines += [f"### {sector}", ""]
        for item in sorted(rows, key=lambda x: x.get("date", "")):
            p = item.get("policy") or {}
            lines.append(f"- **{item.get('date', '')} · [{item.get('title', '')}]({p.get('original_url') or item.get('url', '')})** — {item.get('impact_summary') or item.get('why') or item.get('summary', '')}（{item.get('impact_sentiment', '中性')}；生效：{p.get('effective_date', '待明确')}）")
        lines.append("")
    lines += ["## 重点信号", ""]
    for item in items:
        if item.get("heat") in ("high", "rising"):
            lines.append(f"- [{item.get('title', '')}]({item.get('url', '')})：{item.get('impact_summary') or item.get('summary', '')}")
    lines += ["", "## 关注词命中", ""]
    for item in items:
        if item.get("watchword_hits"):
            lines.append(f"- **{', '.join(item['watchword_hits'])}** — [{item.get('title', '')}]({item.get('url', '')})")
    out = ROOT / args.output_dir / args.period / f"{value}.md"
    write_text(out, "\n".join(lines) + "\n")
    print("[archive] wrote", out)


if __name__ == "__main__":
    main()
