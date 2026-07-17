---
name: daily-intelligence-workbench
description: Run and configure a daily China national and regional policy, current-affairs, AI, autonomous-driving, agent, foundation-model, software, and internet industry intelligence dashboard. Use when the user asks to collect or search policies, filter by region, trace originals and effective dates, explain sector impact, schedule updates, archive knowledge, send alerts, or package the completed dashboard and data into one offline HTML file that can be directly shared and opened.
---

# Daily Intelligence Workbench

Operate the local policy and technology intelligence workbench. Turn official policy sources, current affairs, industry anchors, optional X/Twitter providers, and an agent-assisted research loop into a structured `digest.js`, a local HTML dashboard, Markdown knowledge-base archives, and optional Feishu pushes.

## Natural Language Setup Mode

When the user asks in natural language, do the setup rather than only listing commands. Examples:

- "Set this up for AI + crypto and AI + finance, English output, no push, and run it every morning."
- "帮我初始化每日资讯工作台，关注 AI+加密和 AI+金融，每天 8:30 自动生成。"
- "Use this repo as your daily task and push the digest to Lark when configured."

Translate the request into this decision set:

1. Industry anchors: infer from the request, otherwise default to `ai-crypto,ai-finance`.
2. Output language: infer from the user's language, otherwise use `zh`; support `zh`, `en`, and `bilingual`.
3. Push behavior: only enable push when the user explicitly wants it and a webhook is already configured or provided locally.
4. Schedule time: infer from the request, otherwise use `08:30`.
5. Agent execution mode: if the user wants the agent itself to run daily and the current agent host has native recurring tasks/automations, create that agent-native daily task. Otherwise install the local OS schedule with `scripts/install_schedule.py`.

For agent-native schedules, the recurring task should open this repository, read this skill, run `python3 scripts/run_daily.py --date today` plus `--push` only when push is configured, then run `python3 scripts/validate_digest.py --date latest`. Do not store secrets in the task definition.

For local OS schedules, run:

```bash
python3 scripts/install_schedule.py install --time HH:MM
python3 scripts/install_schedule.py install --time HH:MM --push
```

Use the second command only when push is configured. After setup, report the exact anchors, language, push mode, schedule mode, schedule time, and the command or native task that will run.

## Core Workflow

1. Inspect the repository root. Confirm these paths exist:
   - `index.html`
   - `config/`
   - `data/manifest.js`
   - `scripts/`
2. Initialize local configuration when needed:
   - `python3 scripts/init.py`
   - Use `--anchors ai-crypto,ai-finance` or another comma-separated list for non-interactive setup.
   - Use `--language zh`, `--language en`, or `--language bilingual` to choose digest output language.
3. Generate or validate a daily digest:
   - `python3 scripts/run_daily.py --date today`
   - If an agent command is configured, the script creates a research prompt and invokes that command.
   - If no agent command is configured, the script writes a handoff prompt under `.daily-intel/runs/<date>/research_prompt.md`.
   - After successful validation, the runner automatically creates `share/ai-intel-dashboard-latest.html` with all current data embedded.
4. Validate the generated output:
   - `python3 scripts/validate_digest.py --date latest`
5. Start the local dashboard:
   - `python3 scripts/serve.py --port 4318`
6. Push the digest only when the user has configured a webhook:
   - `python3 scripts/push_lark.py`
7. Install or inspect schedules:
   - `python3 scripts/install_schedule.py install --time 08:30 --push`
   - `python3 scripts/install_schedule.py status`
   - `python3 scripts/install_schedule.py uninstall`
8. Generate knowledge-base archives:
   - `python3 scripts/archive_knowledge.py --period week`
   - `python3 scripts/archive_knowledge.py --period month`

## Single-File Sharing

Build the shareable dashboard after every successful daily run:

```bash
python3 scripts/build_single_html.py --date latest
```

- Write the default output to `share/ai-intel-dashboard-latest.html` and overwrite it on the next run.
- Embed `data/manifest.js` and the selected `digest.js`; remove all `data/...` script dependencies from the generated HTML.
- Keep the source `index.html` modular. Do not replace it with the bundled output.
- Treat a bundle failure as a daily-run failure so the configured Feishu alert fires.
- Verify the output contains `window.__MANIFEST__`, `window.__DAILY__`, and no `<script src="data/...">`. The recipient must be able to open it by double-clicking without a local server.

## China Policy Intelligence Contract

Read `config/policy.yaml` and `config/watchwords.yaml` before research.

1. Use exactly five dashboard sectors: `lab=AI 与大模型`, `kol=智能体与软件`, `paper=自动驾驶`, `oss=数据要素与安全`, and `fin=互联网与数字产业`. Treat labs, KOLs, papers, open source, and finance as source/content attributes, never as dashboard dimensions. Target 15–25 high-signal items per day and normally at least 3 per sector.
2. Discover policies through media or search, but verify them at the issuing authority. Prefer the State Council and ministry or regulator pages listed in `config/policy.yaml`.
3. Set policy entries to `content_type: policy`. Record `policy.original_url`, `issuer`, `published_date`, `effective_date`, and `affected_industries`. Use `待明确` only when the original text does not specify an effective date.
4. Write `impact_sentiment` as `利好`, `利空`, or `中性`. Write `impact_summary` as one concrete sentence naming the affected track and mechanism, such as “对自动驾驶意味着 L3 准入的合规与测试门槛抬高”。Do not write generic market commentary.
5. Preserve uncertainty. Separate publication, public-comment, adoption, and effective dates. Do not imply that a draft or consultation is effective law.
6. Prioritize candidates matching `config/watchwords.yaml`; the deterministic writer adds `watchword_hits`, and the dashboard highlights them.
7. Populate `hot_topics_today` only from the current run. The dashboard's “今日最新热点” view must render those topics and their related items without mixing historical digests.
8. Scan every portal in `config/policy.yaml` `local_government_portals` on each daily run. For local policies, set `policy.region` to the configured region, keep the government original URL, and prefer policies published today or within the last seven days. The “各地最新政策” view aggregates these items independently of their five-sector classification.

## Archival and Alert Workflow

- Run weekly and monthly archives with `scripts/archive_knowledge.py`. Markdown under `knowledge-base/` is directly usable as an Obsidian vault folder and importable into Notion.
- For a true LLM-written monthly narrative, configure the scheduled agent to read that month's digests and revise the generated “政策演进脉络” section; preserve all original links.
- Configure `DAILY_INTEL_ALERT_WEBHOOK` as a repository secret. The GitHub Actions workflows call `scripts/notify_failure.py` only on failure.
- Keep all webhooks, Notion tokens, and agent credentials in environment variables or repository secrets, never committed files.
- Use `.github/workflows/daily-policy-intelligence.yml` for the daily run and `.github/workflows/archive-knowledge.yml` for weekly/monthly archives. GitHub schedules use UTC.
- Commit `share/ai-intel-dashboard-latest.html` in the daily workflow so the latest transferable file is always available from the repository.

## X/Twitter Provider Discipline

Treat X/Twitter collection as a provider, not a hard dependency.

- Use public web/status/profile reads as the default. Public status pages and public profiles can often be read without login, while X search often requires login.
- Use Chrome login state, browser extensions, X API, or third-party providers only when the user explicitly configures them locally.
- Never inspect, copy, export, or store cookies, session storage, passwords, or tokens.
- Do not describe the workflow as "anti-ban" or guaranteed to avoid rate limits. Prefer "low-frequency, read-only, user-owned provider".
- Record provider limitations in digest notes when a source could not be verified directly.

For detailed provider strategy, read `references/source-providers.md`.

## Digest Contract

Write each daily output to `data/YYYY/MM/DD/digest.js` and update `data/manifest.js`. The frontend expects:

- `date`, `date_cn`, `generated_at`
- `dimensions`: five or more dimension summaries
- `hot_topics_today`: cross-dimensional topics
- `items`: structured intelligence entries
- Optional: `kol_list`, `practice_list`, `market_mood`

Honor `config/runtime.yaml` `output_language` when creating user-facing fields. Supported values are:

- `zh`: Simplified Chinese output with technical terms and URLs preserved.
- `en`: English output with source names, project names, tickers, and URLs preserved.
- `bilingual`: Simplified Chinese first, with concise English equivalents for titles and key summaries where useful.

For the complete schema and validation expectations, read `references/data-schema.md`.

## Agent Research Procedure

When no structured JSON has been provided, run the research loop manually in the current agent:

1. Read `config/industry.yaml`, `config/sources.yaml`, `config/keywords.yaml`, `config/kol.yaml`, `config/research_radar.yaml`, `config/policy.yaml`, and `config/watchwords.yaml`.
2. Before generic search, run the research-radar pass:
   - Researcher longform / X Articles: especially Anthropic Claude Code and OpenAI/alignment researchers.
   - Official research pages: Anthropic Research, OpenAI Research, OpenAI Alignment, Google DeepMind Research.
   - Chinese frontier labs: DeepSeek, Kimi/Moonshot, Z.ai/GLM, Qwen. Check official pages, Hugging Face model cards, and GitHub technical reports.
   - Open-source finance/quant agents: discover from X discussion plus GitHub topics, not GitHub stars alone.
3. Build the five sector tracks defined above. Assign every policy, current-affairs item, company release, paper, or open-source project to the sector it affects.
4. Search with English keywords first, then use Chinese sources for local context when configured.
5. For the KOL views track, run an X-first pass before newsletters: use the handles in `config/kol.yaml`, query `site:x.com/<handle>/status`, `site:x.com/<handle>/article`, public X status/profile pages, configured Gate-News `news_feed_search_x`, X API, or local browser providers, and prefer public X status/profile/article URLs as `items[].url` or `items[].x_src`.
6. Target at least 60% of KOL-view items with X evidence. If the public/provider path cannot reach that ratio, document the limitation in `dimensions[].notes` and only then fall back to AINews, Latent Space, Interconnects, blogs, or media summaries.
7. Prefer primary sources: official blogs, research pages, arXiv, GitHub, Hugging Face model cards, project docs, public X status/profile/article pages, reputable media.
8. Filter aggressively: remove marketing, duplicated reposts, job posts, unverifiable claims, and stale content. Do not drop a high-signal researcher article merely because it is not viral yet.
9. For longform or research items, set `content_type` and usually `depth: deep`. Include `detail`, `key_points`, `examples`, `product_implications`, and `limitations` so the dashboard is useful without opening the source.
10. Write a temporary canonical JSON file matching `references/data-schema.md`.
    Run `python3 scripts/enrich_policy.py <canonical-json-path>` when inspecting the normalized JSON before import.
11. Convert it into dashboard format:
   - `python3 scripts/run_daily.py --date YYYY-MM-DD --from-json /path/to/digest.json --push`
12. Validate and serve locally.

## Scheduling

Use `scripts/install_schedule.py` for local schedules. On macOS it writes a LaunchAgent. On Linux it writes a marked crontab line. The scheduled script is intentionally local-first and reads configuration from `config/runtime.yaml` plus environment variables.

Keep schedule setup separate from account setup. A schedule may run without X login, API keys, or push bots; it should create a research prompt or validate existing data rather than failing destructively.

## Push Safety

Push only after the user configures `config/push.yaml` or passes a webhook override. Do not commit real webhook URLs. For Lark/Feishu, `scripts/push_lark.py` uses only the Python standard library and sends an interactive card.

## Useful Resources

- `references/data-schema.md` - Digest schema and canonical JSON format.
- `references/source-providers.md` - Public web, Chrome, extension, API, and fallback provider strategy.
- `config/research_radar.yaml` - Researcher longform, lab research, Chinese frontier lab, and finance/quant agent radar.
- `docs/调研方法论与Loop设计.md` - Product and research methodology.
