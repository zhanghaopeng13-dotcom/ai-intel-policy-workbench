#!/usr/bin/env python3
"""Send a concise failure notification to a Feishu/Lark custom bot."""
import argparse
import json
import os
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", default="AI 产业情报看板更新失败")
    parser.add_argument("--detail", default="请查看自动化运行日志。")
    args = parser.parse_args()
    webhook = os.environ.get("DAILY_INTEL_ALERT_WEBHOOK") or os.environ.get("DAILY_INTEL_LARK_WEBHOOK")
    if not webhook:
        print("[alert] webhook not configured; skipping")
        return 0
    context = os.environ.get("GITHUB_SERVER_URL", "") + "/" + os.environ.get("GITHUB_REPOSITORY", "") + "/actions/runs/" + os.environ.get("GITHUB_RUN_ID", "")
    body = {"msg_type": "text", "content": {"text": f"{args.title}\n{args.detail}\n{context}"}}
    req = urllib.request.Request(webhook, data=json.dumps(body, ensure_ascii=False).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as response:
        print("[alert] sent", response.status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
