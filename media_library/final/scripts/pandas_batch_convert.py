#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pandas-based CSV -> normalized DataFrame -> Notion properties JSONL

Usage:
  python pandas_batch_convert.py --input <in.csv> --outdir <dir> [--uuid-map <uuid_to_pageid.json>]
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Callable
from datetime import datetime, timezone, timedelta
import hashlib, re, json, argparse
from urllib.parse import urlparse, urlunparse
from pathlib import Path
import pandas as pd

# ---- Configs ----
COLUMN_ALIASES: Dict[str, str] = {
    "uuid": "uuid",
    "source_id": "source_id",
    "视频原标题": "title",
    "发布者": "author",
    "发布平台": "platform",
    "发布日期": "pubdate",
    "视频时长": "duration",
    "分辨率": "resolution",
    "视频比例": "aspect_ratio",
    "内容类型": "content_type",
    "时代背景": "era",
    "内容主题": "topic",
    "简介": "desc",
    "合作信息": "co_operators",
    "BGM": "bgm",
    "分享链接": "share_url",
    "下载链接": "download_url",
    "所属合集": "related_series",
    "播放量/浏览数": "view",
    "点赞数": "like",
    "评论数": "reply",
    "转发数": "share",
    "收藏数": "favorite",
    "封面图": "cover_url",
    "关键词": "tags",
}

PLATFORM_MAP: Dict[str, str] = {
    "bilibili": "B站",
    "douyin": "抖音",
    "xhs": "小红书",
    "kuaishou": "快手"
}

# TODO: Read from platform_links_final.json
TARGET_FIELDS_ORDER = [
    "link_id",
    # "video_uuid",
    "platform",
    # "source_id",
    "share_url",
    "title",
    "pubdate",
    # "is_primary",
    "view",
    "like",
    "reply",
    "share",
    "favorite",
    "cover_url",
    # "download_url",
    "tags",
    "bgm",
    "co_operators",
    "related_series",
]

TZ_BEIJING = timezone(timedelta(hours=8))
_NUM_CJK = {"万": 10_000, "千": 1_000}

# ---- Helpers ----
def _none_if_blank(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None

def _normalize_platform(v: Any) -> Optional[str]:
    s = (str(v) if v is not None else "").strip().lower()
    s = re.sub(r"\s+", "", s)
    return PLATFORM_MAP.get(s, s or None)

def _normalize_url(v: Any) -> Optional[str]:
    s = _none_if_blank(v)
    if not s:
        return None
    try:
        parts = urlparse(s)
        if not parts.scheme:
            parts = parts._replace(scheme="http")
        return urlunparse(parts)
    except Exception:
        return s

def _parse_count(v: Any) -> Optional[int]:
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    s = s.replace(",", "").replace("，", "")
    for unit, mul in _NUM_CJK.items():
        if s.endswith(unit):
            try:
                return int(float(s[:-1]) * mul)
            except ValueError:
                return None
    try:
        return int(float(s))
    except ValueError:
        return None

def _parse_related_series(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    # Keep only CJK characters
    return re.sub(r'[^\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u00B7]+', '', s)

_DATE_PATTERNS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y.%m.%d %H:%M:%S",
]

def _parse_human_date(s: str) -> Optional[str]:
    s = s.strip()
    s = re.sub(r"年|\.|/", "-", s)
    s = s.replace("月", "-").replace("日", "")
    s = re.sub(r"\s+", " ", s).strip()
    for pat in _DATE_PATTERNS:
        try:
            dt = datetime.strptime(s, pat.replace("/", "-").replace(".", "-"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TZ_BEIJING)
            return dt.astimezone(TZ_BEIJING).isoformat()
        except ValueError:
            continue
    return None

def _parse_pubdate(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    if re.fullmatch(r"-?\d+", s):
        try:
            n = int(s)
            if n >= 10**18:
                dt = datetime.fromtimestamp(n / 1_000_000_000, TZ_BEIJING)
            elif n > 10**13:
                dt = datetime.fromtimestamp(n / 1_000_000, TZ_BEIJING)
            elif n > 10**11:
                dt = datetime.fromtimestamp(n / 1000, TZ_BEIJING)
            else:
                dt = datetime.fromtimestamp(n, TZ_BEIJING)
            return dt.isoformat()
        except Exception:
            pass
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ_BEIJING)
        return dt.astimezone(TZ_BEIJING).isoformat()
    except Exception:
        pass
    return _parse_human_date(s)

def _build_link_id(platform: Optional[str], source_id: Optional[str], share_url: Optional[str]) -> Optional[str]:
    platform = (platform or "").strip()
    source_id = (source_id or "").strip()
    if platform and source_id:
        return f"{platform}:{source_id}"
    if platform and share_url:
        h = hashlib.sha1(share_url.encode("utf-8")).hexdigest()[:12]
        return f"{platform}:u:{h}"
    return None

# ---- Core transforms (vectorized via Series.apply) ----
def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # 1) Rename columns using aliases (keep others untouched)
    rename_map = {c: COLUMN_ALIASES.get(c, c) for c in df.columns}
    print(f"Renaming columns: {rename_map}")
    df = df[COLUMN_ALIASES.keys()]

    df = df.rename(columns=rename_map)

    # 2) Compute target fields
    out = pd.DataFrame(index=df.index)
    out["link_id"] = df.get("uuid").apply(_none_if_blank)
    out["platform"] = df.get("platform").apply(_normalize_platform)
    out["share_url"] = df.get("share_url").apply(_normalize_url)
    out["title"] = df.get("title").apply(_none_if_blank)
    out["pubdate"] = df.get("pubdate")
    out["view"] = df.get("view").apply(_parse_count)
    out["like"] = df.get("like").apply(_parse_count)
    out["reply"] = df.get("reply").apply(_parse_count)
    out["share"] = df.get("share").apply(_parse_count)
    out["favorite"] = df.get("favorite").apply(_parse_count)
    out["cover_url"] = df.get("cover_url").apply(_normalize_url)
    out["tags"] = df.get("tags").apply(_none_if_blank)
    out["bgm"] = df.get("bgm").apply(_normalize_url)
    out["co_operators"] = df.get("co_operators").apply(_none_if_blank)
    out["author"] = df.get("author").apply(_none_if_blank)
    out["related_series"] = df.get("related_series").apply(_parse_related_series)
    # out["download_url"] = df.get("download_url").apply(_normalize_url)
    # out["is_primary"] = False

    # 3) Reorder columns
    out = out[TARGET_FIELDS_ORDER]
    return out

# def notion_properties_row(record: Dict[str, Any],
#                           uuid_to_pageid: Callable[[Optional[str]], Optional[str]] | None = None) -> Dict[str, Any]:
#     props: Dict[str, Any] = {}
#     if record.get("link_id"):
#         props["链接ID"] = {"title": [{"text": {"content": str(record["link_id"])}}]}
#     if uuid_to_pageid:
#         pid = uuid_to_pageid(record.get("video_uuid"))
#         if pid:
#             props["视频UUID"] = {"relation": [{"id": pid}]}
#     if record.get("platform"):
#         props["发布平台"] = {"select": {"name": record["platform"]}}

#     def rt(name, val):
#         if val:
#             props[name] = {"rich_text": [{"text": {"content": str(val)}}]}
#     def url(name, val):
#         if val:
#             props[name] = {"url": val}
#     def num(name, val):
#         if val is not None:
#             props[name] = {"number": float(val)}
#     def date(name, val_iso):
#         if val_iso:
#             props[name] = {"date": {"start": val_iso}}
#     def cb(name, val_bool):
#         if val_bool is not None:
#             props[name] = {"checkbox": bool(val_bool)}

#     rt("source_id", record.get("source_id"))
#     url("分享链接", record.get("share_url"))
#     rt("视频原标题", record.get("title"))
#     date("发布日期", record.get("pubdate"))
#     cb("主平台", record.get("is_primary"))
#     num("播放", record.get("views"))
#     num("点赞", record.get("likes"))
#     num("评论", record.get("comments"))
#     num("转发", record.get("shares"))
#     num("收藏", record.get("favorites"))
#     url("平台封面", record.get("cover_url_platform"))
#     url("下载链接", record.get("download_url"))
#     return props

# def load_uuid_map(path: Optional[Path]) -> Callable[[Optional[str]], Optional[str]]:
#     if path and path.exists():
#         mapping = json.loads(Path(path).read_text(encoding="utf-8"))
#         def _map(u: Optional[str]) -> Optional[str]:
#             if not u:
#                 return None
#             return mapping.get(u)
#         return _map
#     return lambda _u: None

def main(input_csv: Path, outdir: Path, uuid_map: Optional[Path]) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(input_csv, dtype=str).fillna("")
    norm = normalize_dataframe(df)

    # Save normalized JSONL
    # norm_path = outdir / "normalized.jsonl"
    # with norm_path.open("w", encoding="utf-8") as f:
    #     for _, row in norm.iterrows():
    #         f.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\n")

    # # Save notion properties JSONL
    # uuid_mapper = load_uuid_map(uuid_map)
    # props_path = outdir / "notion_properties.jsonl"
    # with props_path.open("w", encoding="utf-8") as f:
    #     for _, row in norm.iterrows():
    #         props = notion_properties_row(row.to_dict(), uuid_to_pageid=uuid_mapper)
    #         f.write(json.dumps(props, ensure_ascii=False) + "\n")

    # Optional: also save a CSV preview of normalized
    norm_csv = outdir / "platform_links.csv"
    norm.to_csv(norm_csv, index=False, encoding="utf-8")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--outdir", required=True, type=Path)
    ap.add_argument("--uuid-map", type=Path, default=None)
    args = ap.parse_args()
    main(args.input, args.outdir, args.uuid_map)
