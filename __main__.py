"""Smart-Web-Scraper CLI。

子命令：
    fetch <url>                       原始 HTML 抓取（保留 v1 行为）
    text <url>                        清洗后纯文本
    extract <url> --schema "..."      LLM 智能字段提取（v2 新增）
    list-backends                     列 LLM backend

示例：

    python __main__.py fetch https://example.com -o page.html
    python __main__.py text https://example.com -o text.txt
    python __main__.py extract https://example.com/product/123 \\
        --schema "提取商品名、价格、库存状态、评分" -o data.json
    python __main__.py extract https://news.site/article/xyz \\
        --schema '{"title":"str","author":"str","publish_date":"str","summary":"str"}'
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scraper import SmartScraper  # noqa: E402
from llm_extractor import LLMClient, LLMExtractor, LLMNotAvailable  # noqa: E402


def cmd_fetch(args) -> int:
    scraper = SmartScraper()
    html = scraper.fetch_page(args.url, timeout=args.timeout)
    if html is None:
        sys.stderr.write(f"[error] 拉取失败 {args.url}\n")
        return 1
    if args.output:
        Path(args.output).write_text(html, encoding="utf-8")
        sys.stderr.write(f"[ok] {len(html)} 字符已写入 {args.output}\n")
    else:
        sys.stdout.write(html)
    return 0


def cmd_text(args) -> int:
    scraper = SmartScraper()
    html = scraper.fetch_page(args.url, timeout=args.timeout)
    if html is None:
        return 1
    text = scraper.extract_text(html)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        sys.stderr.write(f"[ok] {len(text)} 字符已写入 {args.output}\n")
    else:
        print(text)
    return 0


def cmd_extract(args) -> int:
    """LLM 智能字段提取。"""
    # schema 可以是 JSON 字符串或自然语言
    schema = args.schema
    if schema.lstrip().startswith("{"):
        try:
            schema = json.loads(schema)
        except json.JSONDecodeError:
            pass  # 解析失败就当作自然语言

    extractor = LLMExtractor(LLMClient(backend=args.backend))
    try:
        result = extractor.extract_from_url(args.url, schema, timeout=args.timeout)
    except LLMNotAvailable as e:
        sys.stderr.write(f"[error] {e}\n")
        return 2
    except Exception as e:
        sys.stderr.write(f"[error] 抽取失败: {type(e).__name__}: {e}\n")
        return 3

    payload = {"url": args.url, "schema": args.schema, **result.to_dict()}
    out = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        sys.stderr.write(f"[ok] 提取完成，已写入 {args.output}\n")
    else:
        print(out)
    return 0


def cmd_list_backends(args) -> int:
    import os as _os
    rows = [
        ("openai",    "gpt-4o-mini",                "OPENAI_API_KEY"),
        ("anthropic", "claude-3-5-haiku-20241022",  "ANTHROPIC_API_KEY"),
        ("deepseek",  "deepseek-chat",              "DEEPSEEK_API_KEY"),
    ]
    print(f"{'backend':<12} {'default model':<32} {'env var'}")
    print("-" * 70)
    for b, m, e in rows:
        cfg = "yes" if _os.getenv(e) else "no"
        print(f"{b:<12} {m:<32} {e}  (configured: {cfg})")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="smart_scraper", description="Smart-Web-Scraper CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    common_backends = ["openai", "anthropic", "deepseek"]

    sp = sub.add_parser("fetch", help="拉原始 HTML")
    sp.add_argument("url")
    sp.add_argument("--timeout", type=int, default=15)
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_fetch)

    sp = sub.add_parser("text", help="拉清洗后纯文本")
    sp.add_argument("url")
    sp.add_argument("--timeout", type=int, default=15)
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_text)

    sp = sub.add_parser("extract", help="LLM 智能字段提取")
    sp.add_argument("url")
    sp.add_argument("--schema", required=True,
                    help="自然语言描述（'提取商品名和价格'）或 JSON schema 字符串")
    sp.add_argument("--backend", default="deepseek", choices=common_backends)
    sp.add_argument("--timeout", type=int, default=20)
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_extract)

    sp = sub.add_parser("list-backends")
    sp.set_defaults(func=cmd_list_backends)

    return p


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
