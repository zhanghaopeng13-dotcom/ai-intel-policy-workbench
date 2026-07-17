#!/usr/bin/env python3
"""Normalize policy fields and mark configured watchword hits in canonical JSON."""
import argparse
import json
import re
from pathlib import Path

from common import ROOT, read_text, write_text


def watchwords():
    path = ROOT / "config" / "watchwords.yaml"
    if not path.exists():
        return []
    words = []
    for line in read_text(path).splitlines():
        match = re.match(r'^\s*-\s*["\']?(.+?)["\']?\s*$', line)
        if match:
            words.append(match.group(1))
    return words


def enrich(payload):
    words = watchwords()
    for item in payload.get("items", []):
        blob = " ".join(str(item.get(k) or "") for k in ("title", "summary", "detail", "why", "impact_summary"))
        blob += " " + " ".join(str(v) for v in item.get("tags") or [])
        item["watchword_hits"] = [word for word in words if word.lower() in blob.lower()]
        if item.get("content_type") == "policy" or item.get("policy"):
            policy = item.setdefault("policy", {})
            policy.setdefault("original_url", item.get("url", ""))
            policy.setdefault("published_date", item.get("date", ""))
            policy.setdefault("effective_date", "待明确")
            policy.setdefault("issuer", item.get("source", ""))
            issuer = str(policy.get("issuer") or "")
            inferred_region = next((name for name in ("北京", "上海", "广东", "深圳", "浙江", "江苏", "四川", "湖北", "安徽", "福建") if name in issuer), "全国")
            policy.setdefault("region", inferred_region)
            policy.setdefault("affected_industries", [])
            item.setdefault("impact_sentiment", "中性")
            item.setdefault("impact_summary", item.get("why", ""))
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path")
    args = parser.parse_args()
    path = Path(args.json_path)
    payload = enrich(json.loads(read_text(path)))
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print("[enrich] normalized", path)


if __name__ == "__main__":
    main()
