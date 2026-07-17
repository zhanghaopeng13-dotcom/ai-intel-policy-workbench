#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate a generated digest.js and manifest.js using lightweight checks."""

import argparse
import json
import re
import sys

from common import ROOT, digest_path_for, extract_latest_from_manifest, read_text, slash_date


DEEP_TYPES = {"x_article", "official_research", "paper", "technical_report", "model_card", "long_blog"}
RESEARCH_DOMAINS = (
    "anthropic.com/research",
    "openai.com/research",
    "alignment.openai.com",
    "moonshotai.github.io",
    "huggingface.co/moonshotai",
    "huggingface.co/deepseek-ai",
    "github.com/deepseek-ai",
    "z.ai/blog",
    "github.com/zai-org",
    "huggingface.co/zai-org",
)


def active_industry_anchors():
    path = ROOT / "config" / "industry.yaml"
    if not path.exists():
        return []
    txt = read_text(path)
    m = re.search(r'(?m)^anchors:\n((?:\s*-\s*[\w-]+\s*\n)+)', txt)
    if not m:
        return []
    return re.findall(r'-\s*([\w-]+)', m.group(1))


def load_strict_payload(raw):
    m = re.search(r'window\.__DAILY__\[[^\]]+\]\s*=\s*(\{.*\})\s*;?\s*$', raw, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def prop(name):
    return r'(?:"%s"|%s)\s*:\s*' % (re.escape(name), re.escape(name))


def validate_digest(date_value):
    if date_value == "latest":
        latest = extract_latest_from_manifest()
        if not latest:
            raise SystemExit("[validate] manifest.js 未找到 latest")
        date_value = latest
    key = slash_date(date_value)
    path = digest_path_for(key)
    if not path.exists():
        raise SystemExit("[validate] 未找到 digest: %s" % path)

    raw = read_text(path)
    errors = []
    warnings = []

    if 'window.__DAILY__' not in raw:
        errors.append("缺少 window.__DAILY__ 赋值")
    if key not in raw:
        errors.append("digest 中未包含日期 key %s" % key)
    if not re.search(r'\bdate\s*:\s*"%s"' % re.escape(key.replace("/", "-")), raw) and key.replace("/", "-") not in raw:
        warnings.append("未显式找到 date=%s" % key.replace("/", "-"))

    payload = load_strict_payload(raw)
    if payload:
        item_ids = [item.get("id", "") for item in payload.get("items", [])]
        dims = [dim.get("key", "") for dim in payload.get("dimensions", [])]
        hot_topics = [topic.get("title", "") for topic in payload.get("hot_topics_today", [])]
        urls = [item.get("url", "") for item in payload.get("items", []) if item.get("url")]
    else:
        item_ids = re.findall(prop("id") + r'"([^"]+)"', raw)
        dims = re.findall(prop("key") + r'"([^"]+)"', raw)
        hot_topics = re.findall(prop("title") + r'"([^"]+)"[^{}\n]*' + prop("heat"), raw)
        urls = re.findall(prop("url") + r'"([^"]+)"', raw)

    if len(item_ids) < 1:
        errors.append("items 里未识别到 id")
    if len(dims) < 1:
        errors.append("dimensions 里未识别到 key")
    if len(urls) < max(1, len(item_ids) // 2):
        warnings.append("URL 数量偏少：%d urls / %d items" % (len(urls), len(item_ids)))
    if payload:
        policy_items = [
            item for item in payload.get("items", [])
            if item.get("content_type") == "policy" or item.get("policy")
        ]
        for item in policy_items:
            policy = item.get("policy") or {}
            missing = [key for key in ("original_url", "issuer", "region", "published_date", "effective_date", "affected_industries") if not policy.get(key)]
            if missing:
                errors.append("政策条目 %s 缺少字段：%s" % (item.get("id", "(no-id)"), ", ".join(missing)))
            if item.get("impact_sentiment") not in ("利好", "利空", "中性"):
                errors.append("政策条目 %s impact_sentiment 必须为利好/利空/中性" % item.get("id", "(no-id)"))
            if not item.get("impact_summary"):
                errors.append("政策条目 %s 缺少 impact_summary" % item.get("id", "(no-id)"))
        print("[validate] policy_items=%d" % len(policy_items))

        policy_mode = len(policy_items) >= max(1, len(payload.get("items", [])) // 3)
        kol_items = [] if policy_mode else [item for item in payload.get("items", []) if item.get("dim") == "kol"]
        x_kol = [
            item for item in kol_items
            if "x.com/" in (item.get("url", "") + " " + " ".join(item.get("x_src") or []))
            or str(item.get("source", "")).lower().startswith(("x", "twitter"))
        ]
        if kol_items:
            ratio = len(x_kol) / float(len(kol_items))
            print("[validate] kol_x_sources=%d/%d (%.0f%%)" % (len(x_kol), len(kol_items), ratio * 100))
            if ratio < 0.5:
                warnings.append("KOL 维度 X 来源占比偏低：%d/%d；请优先补公开 X status/profile 或 x_src" % (len(x_kol), len(kol_items)))

        deep_items = [
            item for item in payload.get("items", [])
            if item.get("depth") == "deep" or item.get("content_type") in DEEP_TYPES
        ]
        short_deep = [
            item for item in deep_items
            if len(str(item.get("detail") or "")) < 500
        ]
        if deep_items:
            print("[validate] deep_items=%d short_detail=%d" % (len(deep_items), len(short_deep)))
        for item in short_deep[:5]:
            warnings.append("深度/长文条目 detail 偏短：%s；请补充 key_points/examples/product_implications/limitations" % item.get("id", "(no-id)"))

        radar_hits = [
            item for item in payload.get("items", [])
            if item.get("content_type") in DEEP_TYPES
            or any(domain in (item.get("url", "") + " " + " ".join(item.get("x_src") or [])) for domain in RESEARCH_DOMAINS)
        ]
        print("[validate] research_radar_hits=%d" % len(radar_hits))
        if not radar_hits and not policy_mode:
            warnings.append("未发现研究雷达命中项：请确认已扫描 config/research_radar.yaml（研究员长文/官方研究页/国产模型论文）")

        anchors = active_industry_anchors()
        if ("ai-finance" in anchors or "ai-crypto" in anchors) and not policy_mode:
            finance_oss = []
            for item in payload.get("items", []):
                if item.get("dim") != "oss":
                    continue
                blob = " ".join(str(item.get(k, "")) for k in ("title", "summary", "detail", "why", "buzz")).lower()
                blob += " " + " ".join(str(x).lower() for x in item.get("tags") or [])
                if any(term in blob for term in ("trading", "quant", "financial", "finance", "stock", "backtest", "broker", "exchange", "量化", "投研", "交易", "回测")):
                    finance_oss.append(item)
            print("[validate] finance_quant_oss=%d" % len(finance_oss))
            if len(finance_oss) < 2:
                warnings.append("当前锚定 AI+金融/加密，但开源项目中金融/量化 Agent 少于 2 条；请补充 X/GitHub 热议项目")

    manifest = read_text(ROOT / "data" / "manifest.js")
    if 'latest: "%s"' % key not in manifest and '"%s"' % key not in manifest:
        warnings.append("manifest.js 未显式标记 latest=%s" % key)
    if path.name not in "digest.js":
        warnings.append("digest 文件名异常")

    print("[validate] date=%s items=%d dimensions=%d hot_topics~=%d urls=%d" % (
        key, len(item_ids), len(set(dims)), len(hot_topics), len(urls)
    ))
    for w in warnings:
        print("[validate][warn]", w)
    if errors:
        for e in errors:
            print("[validate][error]", e)
        return 1
    print("[validate] OK", path)
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="latest", help="YYYY-MM-DD, YYYY/MM/DD, today, or latest")
    args = parser.parse_args()
    sys.exit(validate_digest(args.date))


if __name__ == "__main__":
    main()
