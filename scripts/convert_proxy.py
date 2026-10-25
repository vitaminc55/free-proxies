#!/usr/bin/env python3
"""把 proxy.txt 转换为 protocol://@ip:port#国家 格式。"""

import re
import sys
import time
import urllib.request

SOURCE_URL = "https://raw.githubusercontent.com/watchttvv/free-proxy-list/refs/heads/main/proxy.txt"
OUTPUT_FILE = "proxy_converted.txt"

# 形如：socks5://1.2.3.4:1080 <其余信息>
LINE_RE = re.compile(
    r"^(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*)://"
    r"(?P<ip>[^\s:]+):(?P<port>\d+)\s+(?P<rest>.*)$"
)
IPV4_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$"
)
TAG_RE = re.compile(r"\[[^\]]*\]")
ENTRY_TIME_RE = re.compile(r"入库时间[：:]\s*\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}")


def fetch(url: str) -> str:
    request = urllib.request.Request(
        f"{url}?t={int(time.time())}",
        headers={"User-Agent": "free-proxy-list-bot/1.0", "Cache-Control": "no-cache"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8-sig")


def country_from(rest: str) -> str:
    """从 '入库时间：10-25 08:09 [机房] 拉脱维亚 里加 里加 — veesp.com' 提取国家。"""
    text = ENTRY_TIME_RE.sub(" ", rest)
    text = TAG_RE.sub(" ", text)
    parts = text.split()
    return parts[0] if parts else "未知"


def convert(content: str) -> tuple[list[str], int, int]:
    lines: list[str] = []
    seen: set[str] = set()
    skipped = 0

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        match = LINE_RE.match(line)
        if not match:
            skipped += 1
            continue

        ip = match.group("ip")
        # 源列表中有部分 IP 被遮挡成 89.219.X.46，这种节点不可用，直接丢弃。
        if not IPV4_RE.match(ip):
            skipped += 1
            continue

        name = country_from(match.group("rest"))
        converted = f"{match.group('scheme')}://@{ip}:{match.group('port')}#{name}"
        if converted not in seen:
            seen.add(converted)
            lines.append(converted)

    return lines, skipped, len(seen)


def main() -> int:
    try:
        content = fetch(SOURCE_URL)
    except Exception as exc:  # 网络异常时让 workflow 失败，保留上一次的产物
        print(f"拉取源文件失败: {exc}", file=sys.stderr)
        return 1

    lines, skipped, total = convert(content)
    if not lines:
        print("没有解析出任何有效节点，保留原文件。", file=sys.stderr)
        return 1

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"已写入 {OUTPUT_FILE}: {total} 个节点，跳过 {skipped} 行无效数据")
    return 0


if __name__ == "__main__":
    sys.exit(main())
