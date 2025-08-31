#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pandas-based CSV -> normalized DataFrame -> Notion properties CSV
Supports multi-column / multi-keyword filtering.

Usage:
  python pandas_batch_convert.py \
    --input <in.csv> \
    --outdir <dir> \
    [--uuid-map <uuid_to_pageid.json>] \
    [--filter-cols title,tags,author] \
    [--filter-keys 盛世天下,古风] \
    [--keyword-mode any|all] \
    [--col-mode any|all] \
    [--case-sensitive] \
    [--regex]
"""
from __future__ import annotations
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone, timedelta
import hashlib, re, argparse
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
    "platform",
    "share_url",
    "title",
    "pubdate",
    "view",
    "like",
    "reply",
    "share",
    "favorite",
    "cover_url",
    "tags",
    "bgm",
    "co_operators",
    "author",
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
    # Keep only CJK characters and ·
    return re.sub(r'[^\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u00B7]+', '', s)

# ---- Core transforms (vectorized via Series.apply) ----
def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # 1) Ensure expected columns exist; missing ones are created as empty
    expected_cols: List[str] = list(COLUMN_ALIASES.keys())
    for c in expected_cols:
        if c not in df.columns:
            df[c] = ""

    # 2) Rename columns using aliases (keep others untouched)
    rename_map = {c: COLUMN_ALIASES.get(c, c) for c in df.columns}
    print(f"Renaming columns: {rename_map}")
    df = df[expected_cols].rename(columns=rename_map)

    # 3) Compute target fields
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

    # 4) Reorder columns
    out = out[TARGET_FIELDS_ORDER]
    return out

# ---- Filtering ----
def build_filter_mask(
    df: pd.DataFrame,
    cols: List[str],
    keys: List[str],
    keyword_mode: str = "any",
    col_mode: str = "any",
    case_sensitive: bool = False,
    use_regex: bool = False,
) -> pd.Series:
    """
    Returns a boolean mask for df based on text containment across columns and keywords.
    - keyword_mode: 'any' = match if any keyword matches within a column; 'all' = all keywords must match within the column
    - col_mode: 'any' = any of the specified columns may satisfy; 'all' = all specified columns must satisfy
    """
    if not cols or not keys:
        return pd.Series([True] * len(df), index=df.index)

    # Only keep existing columns
    cols = [c for c in cols if c in df.columns]
    if not cols:
        print("[Filter] None of the specified columns exist in the normalized DataFrame; skipping filter.")
        return pd.Series([True] * len(df), index=df.index)

    # Prepare per-column masks according to keyword_mode
    per_col_masks: List[pd.Series] = []

    if use_regex:
        patterns = keys  # treat as regex
        def contains_any(series: pd.Series) -> pd.Series:
            mask = pd.Series(False, index=series.index)
            for pat in patterns:
                mask = mask | series.astype(str).str.contains(pat, case=case_sensitive, regex=True, na=False)
            return mask
        def contains_all(series: pd.Series) -> pd.Series:
            mask = pd.Series(True, index=series.index)
            for pat in patterns:
                mask = mask & series.astype(str).str.contains(pat, case=case_sensitive, regex=True, na=False)
            return mask
    else:
        # escape keywords to literal matches
        escaped = [re.escape(k) for k in keys]
        # compile once as OR for "any" path
        or_pattern = "|".join(escaped)
        def contains_any(series: pd.Series) -> pd.Series:
            return series.astype(str).str.contains(or_pattern, case=case_sensitive, regex=True, na=False)
        def contains_all(series: pd.Series) -> pd.Series:
            # all keywords must appear (as literals)
            mask = pd.Series(True, index=series.index)
            for pat in escaped:
                mask = mask & series.astype(str).str.contains(pat, case=case_sensitive, regex=True, na=False)
            return mask

    per_col_func = contains_any if keyword_mode.lower() == "any" else contains_all

    for c in cols:
        per_col_masks.append(per_col_func(df[c]))

    if col_mode.lower() == "all":
        final_mask = per_col_masks[0]
        for m in per_col_masks[1:]:
            final_mask = final_mask & m
    else:  # any
        final_mask = per_col_masks[0]
        for m in per_col_masks[1:]:
            final_mask = final_mask | m

    return final_mask

# ---- CLI / Main ----
def main(input_csv: Path, outdir: Path, uuid_map: Optional[Path],
         filter_cols: Optional[str], filter_keys: Optional[str],
         keyword_mode: str, col_mode: str,
         case_sensitive: bool, use_regex: bool) -> None:

    outdir.mkdir(parents=True, exist_ok=True)
    df_raw = pd.read_csv(input_csv, dtype=str).fillna("")
    norm = normalize_dataframe(df_raw)

    # Apply filtering (on normalized columns)
    cols_list = [c.strip() for c in (filter_cols or "").split(",") if c.strip()] if filter_cols else []
    keys_list = [k.strip() for k in (filter_keys or "").split(",") if k.strip()] if filter_keys else []

    if cols_list and keys_list:
        mask = build_filter_mask(
            norm, cols_list, keys_list,
            keyword_mode=keyword_mode, col_mode=col_mode,
            case_sensitive=case_sensitive, use_regex=use_regex
        )
        before, after = len(norm), int(mask.sum())
        print(f"[Filter] Rows before: {before}, after: {after} (kept {after}/{before})")
        norm = norm[mask].copy()
    else:
        print("[Filter] No filter applied (missing --filter-cols or --filter-keys).")

    date_str = datetime.now().strftime("%Y%m%d")
    norm_csv = outdir / f"platform_links_{date_str}.csv"
    norm.to_csv(norm_csv, index=False, encoding="utf-8")
    print(f"Saved: {norm_csv} (rows={len(norm)})")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--outdir", required=True, type=Path)
    ap.add_argument("--uuid-map", type=Path, default=None)

    # filtering options
    ap.add_argument("--filter-cols", type=str, default="title,tags",
                    help="Comma-separated normalized column names to search (default: title,tags)")
    ap.add_argument("--filter-keys", type=str, default="圻夏夏,东栏学,长公主在上",
                    help="Comma-separated keywords (default: 圻夏夏)")
    ap.add_argument("--keyword-mode", choices=["any", "all"], default="any",
                    help="'any' = any keyword matches; 'all' = all keywords must match")
    ap.add_argument("--col-mode", choices=["any", "all"], default="any",
                    help="'any' = any column may satisfy; 'all' = every specified column must satisfy")
    ap.add_argument("--case-sensitive", action="store_true",
                    help="Enable case-sensitive matching")
    ap.add_argument("--regex", action="store_true",
                    help="Treat keywords as regex patterns")

    args = ap.parse_args()
    main(
        args.input, args.outdir, args.uuid_map,
        args.filter_cols,
        args.filter_keys,
        args.keyword_mode,
        args.col_mode,
        args.case_sensitive,
        args.regex,
    )
