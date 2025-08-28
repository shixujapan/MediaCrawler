#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate works & series JSON/CSV from schemas, records and link-groups JSON.

- Works表：
  * 只保留 is_displayed=true 且 type!='rollup' 的字段
  * work_id = MD5(首个link_id + pubdate(Asia/Shanghai 00:00:00)的Unix秒) 前8位
  * title/author/co_operators/share_url 取首条
  * tags 合并去重后按字母排序，带 `#`
  * link_list 为该组 link_id 用逗号拼接
- Series表：
  * 只保留 is_displayed=true 且 type!='rollup'
  * series_id = MD5(series_name) 前8位
  * tags、co_operators 合并（去重、字母排序）
  * work_id_list 按 group_id 升序排序
- 输出：
  * works_output.json / series_output.json
  * works_output.csv  / series_output.csv
"""

import json, hashlib, datetime, pytz, argparse, re, csv
from typing import List, Dict, Any, Tuple, Iterable
from collections import OrderedDict as OD


# ----------------- schema helpers -----------------

def filter_schema_keys(schema: List[Dict[str, Any]]) -> List[str]:
    filtered = [s for s in schema if s.get("is_displayed") and s.get("type") != "rollup"]
    filtered.sort(key=lambda x: x.get("order", 0))
    return [s["name"] for s in filtered]


# ----------------- basic utils -----------------

def parse_pubdate_to_unix(pubdate_str: str) -> int:
    s = (pubdate_str or "").replace("-", "/")
    dt = datetime.datetime.strptime(s, "%Y/%m/%d")
    tz = pytz.timezone("Asia/Shanghai")
    dt_tz = tz.localize(datetime.datetime(dt.year, dt.month, dt.day, 0, 0, 0))
    return int(dt_tz.timestamp())


def md5_8(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:8]


# ----------------- token join helpers -----------------

_TOKEN_SPLIT_RE = re.compile(r"[#,\s/;；，、|]+")

def _split_tokens(raw: str) -> List[str]:
    if not raw:
        return []
    parts = [p.strip() for p in _TOKEN_SPLIT_RE.split(str(raw)) if p.strip()]
    return parts

def _merge_tokens_sorted(seqs: Iterable[Iterable[str]]) -> List[str]:
    seen = set()
    for seq in seqs:
        for t in seq:
            if t:
                seen.add(t)
    return sorted(seen, key=lambda x: x.lower())

def merge_tags_alpha(tags_list: List[str]) -> str:
    tokens = []
    for raw in tags_list:
        tokens.extend(_split_tokens(raw))
    merged = _merge_tokens_sorted([tokens])
    return "" if not merged else "#" + "#".join(merged)

def merge_coops_alpha(coops_list: List[str]) -> str:
    tokens = []
    for raw in coops_list:
        tokens.extend(_split_tokens(raw))
    merged = _merge_tokens_sorted([tokens])
    return "、".join(merged) if merged else ""


# ----------------- works generation -----------------

def build_work_row(schema_keys: List[str],
                   records_index: Dict[str, Dict[str, Any]],
                   link_ids: List[str]) -> Dict[str, Any]:
    out = OD((k, "") for k in schema_keys)
    selected = [records_index[lid] for lid in link_ids if lid in records_index]
    if not selected:
        return out
    first = selected[0]
    unix = parse_pubdate_to_unix(first.get("pubdate", ""))
    out["work_id"] = md5_8(f"{first['link_id']}{unix}")
    if "title" in out: out["title"] = first.get("title", "") or ""
    if "author" in out: out["author"] = first.get("author", "") or ""
    if "co_operators" in out: out["co_operators"] = first.get("co_operators") or ""
    if "share_url" in out: out["share_url"] = first.get("share_url", "") or ""
    if "tags" in out:
        out["tags"] = merge_tags_alpha([r.get("tags") for r in selected])
    if "link_list" in out:
        out["link_list"] = ",".join(link_ids)
    return out


def parse_link_groups(link_groups: Any) -> List[Dict[str, Any]]:
    if isinstance(link_groups, dict):
        if "series_name" in link_groups:
            link_groups = [link_groups]
        else:
            candidates = []
            for v in link_groups.values():
                if isinstance(v, dict) and ("series_name" in v or "duplicated_id_list" in json.dumps(v, ensure_ascii=False)):
                    candidates.append(v)
            link_groups = candidates or [link_groups]
    if not isinstance(link_groups, list):
        raise ValueError("link groups JSON must be a list or dict containing series entries.")

    norm = []
    for s in link_groups:
        if not isinstance(s, dict):
            continue
        sname = str(s.get("series_name", "") or "").strip()
        desc = s.get("desc", "")
        tags = s.get("tags", "")
        coops = s.get("co_operators", "")
        groups = []
        if isinstance(s.get("groups"), list):
            groups = s["groups"]
        else:
            for v in s.values():
                if isinstance(v, dict) and "duplicated_id_list" in v:
                    groups.append(v)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict) and "duplicated_id_list" in item:
                            groups.append(item)
        ngroups = []
        for g in groups:
            gid = g.get("id")
            lids = g.get("duplicated_id_list", [])
            ngroups.append({"id": gid, "duplicated_id_list": lids})
        norm.append({"series_name": sname, "desc": desc, "tags": tags, "co_operators": coops, "groups": ngroups})
    return norm


def generate_works(schema1: List[Dict[str, Any]],
                   records: List[Dict[str, Any]],
                   link_groups: List[Dict[str, Any]]):
    keys1 = filter_schema_keys(schema1)
    index = {r["link_id"]: r for r in records}
    works, series_map = [], {}
    for series_entry in link_groups:
        sname = str(series_entry.get("series_name", "") or "").strip()
        for g in series_entry.get("groups", []):
            lids = [str(x) for x in g.get("duplicated_id_list", []) if str(x).strip()]
            if not lids:
                continue
            row = build_work_row(keys1, index, lids)
            row["_meta"] = {"series_name": sname, "group_id": g.get("id")}
            works.append(row)
            series_map.setdefault(sname, []).append(row)
    return works, series_map


# ----------------- series generation -----------------

def generate_series(schema2: List[Dict[str, Any]],
                    series_map: Dict[str, List[Dict[str, Any]]],
                    series_groups: List[Dict[str, Any]]):
    keys2 = filter_schema_keys(schema2)
    meta = {str(s.get("series_name", "")).strip(): {
        "desc": s.get("desc", ""),
        "tags": s.get("tags", ""),
        "co_operators": s.get("co_operators", ""),
    } for s in series_groups}

    series_rows = []
    for sname, works in series_map.items():
        out = OD((k, "") for k in keys2)
        if "series_id" in out: out["series_id"] = md5_8(sname)
        if "series_name" in out: out["series_name"] = sname
        if "desc" in out: out["desc"] = meta.get(sname, {}).get("desc", "") or ""
        if "tags" in out:
            seed_tags = meta.get(sname, {}).get("tags", "")
            merged_tags = merge_tags_alpha([seed_tags] + [w.get("tags", "") for w in works])
            out["tags"] = merged_tags
        if "co_operators" in out:
            seed_coops = meta.get(sname, {}).get("co_operators", "")
            merged_coops = merge_coops_alpha([seed_coops] + [w.get("co_operators", "") for w in works])
            out["co_operators"] = merged_coops
        if "work_id_list" in out:
            def _gid(x):
                gid = ((x.get("_meta") or {}).get("group_id"))
                try:
                    return (0, int(gid))
                except Exception:
                    return (1, str(gid))
            sorted_works = sorted(works, key=_gid)
            out["work_id_list"] = ",".join([w["work_id"] for w in sorted_works if w.get("work_id")])
        series_rows.append(out)

    for s in series_groups:
        sname = str(s.get("series_name", "")).strip()
        if sname not in series_map:
            out = OD((k, "") for k in keys2)
            if "series_id" in out: out["series_id"] = md5_8(sname)
            if "series_name" in out: out["series_name"] = sname
            if "desc" in out: out["desc"] = s.get("desc", "") or ""
            if "tags" in out: out["tags"] = merge_tags_alpha([s.get("tags", "") or ""])
            if "co_operators" in out: out["co_operators"] = merge_coops_alpha([s.get("co_operators", "") or ""])
            series_rows.append(out)
    return series_rows


# ----------------- CSV helpers -----------------

def save_csv(path: str, rows: List[Dict[str, Any]]):
    if not rows:
        with open(path, "w", newline="", encoding="utf-8") as f:
            f.write("")
        return
    headers = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            clean = {k: ("" if v is None else v) for k, v in r.items()}
            writer.writerow(clean)


# ----------------- main -----------------

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate works & series JSON/CSV.")
    p.add_argument("--schema", required=True)
    p.add_argument("--series-schema", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--link-ids-file", required=True)
    p.add_argument("--works-out", default="works_output.json")
    p.add_argument("--series-out", default="series_output.json")
    p.add_argument("--works-csv", default="works_output.csv")
    p.add_argument("--series-csv", default="series_output.csv")
    p.add_argument("--keep-meta", action="store_true", help="Keep _meta in works output for debugging")
    args = p.parse_args()

    with open(args.schema, "r", encoding="utf-8") as f:
        schema1 = json.load(f)
    with open(args.series_schema, "r", encoding="utf-8") as f:
        schema2 = json.load(f)
    with open(args.data, "r", encoding="utf-8") as f:
        records = json.load(f)
    with open(args.link_ids_file, "r", encoding="utf-8") as f:
        link_groups_raw = json.load(f)

    link_groups = parse_link_groups(link_groups_raw)
    works_rows, series_map = generate_works(schema1, records, link_groups)

    if not args.keep_meta:
        for w in works_rows:
            w.pop("_meta", None)

    series_rows = generate_series(schema2, series_map, link_groups)

    with open(args.works_out, "w", encoding="utf-8") as f:
        json.dump(works_rows, f, ensure_ascii=False, indent=2)
    with open(args.series_out, "w", encoding="utf-8") as f:
        json.dump(series_rows, f, ensure_ascii=False, indent=2)

    save_csv(args.works_csv, works_rows)
    save_csv(args.series_csv, series_rows)
