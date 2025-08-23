#!/usr/bin/env python3
"""
Create a Notion database from a JSON schema (pythonic, hardened, Pydantic v2, logging).

Features:
- Strong schema validation with Pydantic v2
  * At least one visible `title`
  * Duplicate header detection (after trim)
  * If type == relation: require a `relation` block and XOR(single_property, dual_property)
  * If type == rollup: require a `rollup` block; names must be present
- Robust HTTP with retries, backoff, throttle (handles 429/5xx)
- Configurable RPS and timeouts via CLI
- Optional --parent-page-id CLI override (else read env)
- "-" schema path means read JSON from STDIN
- Logging with stdlib `logging` (INFO default, DEBUG with --verbose)
- stdout prints ONLY the created DB id for scripting; all logs/errors go to stderr
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import argparse
import json
import logging
import os
import sys
import time

import requests
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

# ---------------- Constants ----------------
API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

REQ_TIMEOUT = 60       # seconds
MAX_RETRIES = 5
BACKOFF_BASE = 1.6
MAX_BACKOFF = 8.0      # seconds

# ---------------- Logging setup ----------------
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,  # logs to stderr
    )


# ---------------- Pydantic models -----------------
class NotionType(str, Enum):
    title = "title"
    rich_text = "rich_text"
    number = "number"
    select = "select"
    multi_select = "multi_select"
    date = "date"
    url = "url"
    files = "files"
    checkbox = "checkbox"
    email = "email"
    phone_number = "phone_number"
    people = "people"
    relation = "relation"
    rollup = "rollup"


class RelationSpec(BaseModel):
    """
    Validated only if a `relation` block exists on the item.

    Rules:
    - database_id is required
    - exactly one of single_property or dual_property must be provided (XOR)
    - synced_property_name is optional (pass-through)
    """
    model_config = ConfigDict(extra="forbid")
    database_id: str
    single_property: Optional[Dict[str, Any]] = None
    dual_property: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def _xor_single_dual(self):
        sp = self.single_property is not None
        dp = self.dual_property is not None
        if (sp + dp) != 1:
            raise ValueError("relation 需要且仅需要 single_property 或 dual_property 其中之一")
        return self


class RollupSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    relation_property_name: str
    rollup_property_name: str
    function: str = "show_original"

class OptionModel(BaseModel):
    name: str
    color: Optional[str] = None

class SchemaItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order: int = 0
    name: str = ""
    type: NotionType = Field(default=NotionType.rich_text)
    description: Optional[str] = None
    label: Optional[str] = None
    is_displayed: bool = True
    options: Optional[List[OptionModel]] = None
    relation: Optional[RelationSpec] = None
    rollup: Optional[RollupSpec] = None

    @property
    def header(self) -> str:
        # prefer label if present, else name
        return (self.label or self.name).strip()

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("label")
    @classmethod
    def _strip_label(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v

    @field_validator("options", mode="before")
    @classmethod
    def _normalize_options(cls, v: Optional[List[Dict]]) -> Optional[List[Dict]]:
        if not v:
            return None
        cleaned = []
        for x in v:
            if isinstance(x, dict):
                name = str(x.get("name", "")).strip()
                color = str(x.get("color", "")).strip() or None
                if name:  # skip empty names
                    cleaned.append({"name": name, "color": color})
        return cleaned or None


# -------------- Property builders -------------
def _select_options(opts: Optional[Iterable[OptionModel]]) -> Dict[str, Any]:
    values = [{"name": str(o.name), "color": str(o.color)} for o in (opts or []) if str(o.name).strip()]
    return {"options": values} if values else {}


def to_notion_prop(item: SchemaItem) -> Dict[str, Any]:
    t = item.type
    if t == NotionType.title:
        return {"title": {}}
    if t == NotionType.rich_text:
        return {"rich_text": {}}
    if t == NotionType.number:
        return {"number": {}}
    if t == NotionType.select:
        return {"select": _select_options(item.options)}
    if t == NotionType.multi_select:
        return {"multi_select": _select_options(item.options)}
    if t == NotionType.date:
        return {"date": {}}
    if t == NotionType.url:
        return {"url": {}}
    if t == NotionType.files:
        return {"files": {}}
    if t == NotionType.checkbox:
        return {"checkbox": {}}
    if t == NotionType.email:
        return {"email": {}}
    if t == NotionType.phone_number:
        return {"phone_number": {}}
    if t == NotionType.people:
        return {"people": {}}
    if t == NotionType.relation:
        if not item.relation:
            # validate_items() should have caught this already; be defensive
            raise ValueError(f"字段 '{item.header}' 为 relation，但缺少 relation 配置")
        return {"relation": item.relation.model_dump(exclude_none=True)}
    if t == NotionType.rollup:
        if not item.rollup:
            raise ValueError(f"字段 '{item.header}' 为 rollup，但缺少 rollup 配置")
        return {"rollup": item.rollup.model_dump(exclude_none=True)}
    # fallback
    return {"rich_text": {}}


def _trim_header(h: str) -> str:
    h = h.strip()
    return h[:150] if len(h) > 150 else h


def build_properties(schema_items: List[SchemaItem]) -> Dict[str, Any]:
    props: Dict[str, Any] = {}
    for it in sorted(schema_items, key=lambda x: x.order):
        if not it.is_displayed:
            logger.info("[SKIP] 隐藏字段（未创建）: %s", it.header)
            continue
        if not it.header:
            logger.warning("[SKIP] 缺少 label/name 的字段: %s", it)
            continue
        header = _trim_header(it.header)
        if header in props:
            logger.warning("[WARN] 重复的属性名，后者覆盖前者: %s", header)
        props[header] = to_notion_prop(it)
    return props


# ---------------- Validation ------------------
class SchemaError(Exception):
    pass


def validate_items(items: List[SchemaItem]) -> None:
    if not items:
        raise SchemaError("schema 为空")

    displayed = [x for x in items if x.is_displayed]
    if not any(x.type == NotionType.title for x in displayed):
        raise SchemaError("至少需要一个可见的 title 属性")

    # Duplicate headers after trimming
    seen: Dict[str, int] = {}
    for x in displayed:
        h = _trim_header(x.header)
        if h:
            seen[h] = seen.get(h, 0) + 1
    dups = [k for k, n in seen.items() if n > 1]
    if dups:
        raise SchemaError(f"存在重复表头: {dups}")

    # Presence + minimal field checks for relation/rollup
    for x in displayed:
        if x.type == NotionType.relation:
            if x.relation is None:
                raise SchemaError(f"字段 '{x.header}' 为 relation，但缺少 relation 配置")
            # RelationSpec already ensures XOR(single_property, dual_property) and database_id
        if x.type == NotionType.rollup:
            if x.rollup is None:
                raise SchemaError(f"字段 '{x.header}' 为 rollup，但缺少 rollup 配置")
            if not x.rollup.relation_property_name or not x.rollup.rollup_property_name:
                raise SchemaError(
                    f"rollup 字段 '{x.header}' 需要 relation_property_name 和 rollup_property_name"
                )


# --------------- Notion client ----------------
class NotionClient:
    def __init__(self, token: str, dry_run: bool = False, rps: float = 3.0) -> None:
        self.dry_run = dry_run
        self._last = 0.0
        self._interval = 1.0 / max(rps, 0.1)
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        })

    def _throttle(self) -> None:
        dt = time.time() - self._last
        if dt < self._interval:
            time.sleep(self._interval - dt)
        self._last = time.time()

    def _request_with_retries(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        attempt = 0
        while True:
            self._throttle()
            try:
                kwargs.setdefault("timeout", REQ_TIMEOUT)
                resp = self.s.request(method, url, **kwargs)
                if resp.status_code in (429, 502, 503, 504):
                    retry_after = resp.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else min(MAX_BACKOFF, BACKOFF_BASE ** attempt)
                    attempt += 1
                    if attempt > MAX_RETRIES:
                        resp.raise_for_status()
                    logger.debug("[RETRY] %s %s -> %s (sleep %.2fs)", method, url, resp.status_code, delay)
                    time.sleep(delay)
                    continue
                resp.raise_for_status()
                return resp
            except requests.RequestException as exc:
                attempt += 1
                if attempt > MAX_RETRIES:
                    logger.error("[HTTP-ERR] %s", str(exc))
                    # Do not print to stdout; let caller handle failure
                    raise
                delay = min(MAX_BACKOFF, BACKOFF_BASE ** attempt)
                logger.debug("[RETRY-EXC] %s %s (%s) -> sleep %.2fs", method, url, exc.__class__.__name__, delay)
                time.sleep(delay)

    def create_database(self, parent_page_id: str, title: str, properties: Dict[str, Any]) -> str:
        body = {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": properties,
        }
        if self.dry_run:
            logger.info("[DRY] create database payload: %s", json.dumps(body, ensure_ascii=False))
            return "dry-db-id"
        resp = self._request_with_retries("POST", f"{API_BASE}/databases", json=body)
        data = resp.json()
        return data.get("id", "")


# --------------------- CLI ---------------------
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Create Notion database from JSON schema")
    ap.add_argument("--schema", required=True, help="schema.json 路径，或 '-' 代表从 STDIN 读取")
    ap.add_argument("--db-title", required=True, help="新数据库标题")
    ap.add_argument("--dry-run", action="store_true", help="仅打印请求体到日志，不真正创建")
    ap.add_argument("--rps", type=float, default=3.0, help="最大每秒请求数 (默认 3.0)")
    ap.add_argument("--parent-page-id", dest="parent_page_id", help="覆盖环境变量 NOTION_PARENT_PAGE_ID")
    ap.add_argument("--verbose", action="store_true", help="调试模式，输出 DEBUG 日志")
    return ap.parse_args()


def load_schema(path: str) -> List[SchemaItem]:
    if path == "-":
        raw_text = sys.stdin.read()
    else:
        raw_text = Path(path).read_text(encoding="utf-8")
    raw = json.loads(raw_text)
    if not isinstance(raw, list):
        raise SystemExit("schema.json 顶层必须是数组")
    try:
        return [SchemaItem.model_validate(item) for item in raw]
    except Exception as e:
        logger.error("[SCHEMA-VALIDATION] %s", str(e))
        raise


def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)

    token = os.getenv("NOTION_TOKEN")
    parent_page_id = args.parent_page_id or os.getenv("NOTION_PARENT_PAGE_ID")
    if not token or not parent_page_id:
        # Keep stdout clean; error to stderr
        logger.error("请先设置 NOTION_TOKEN 与 NOTION_PARENT_PAGE_ID（或使用 --parent-page-id）")
        raise SystemExit(1)

    try:
        items = load_schema(args.schema)
        validate_items(items)
        props = build_properties(items)
    except (json.JSONDecodeError, SchemaError, ValueError) as err:
        logger.error("[ERR] %s", err)
        raise SystemExit(2)

    notion = NotionClient(token, dry_run=args.dry_run, rps=args.rps)
    try:
        dbid = notion.create_database(parent_page_id, args.db_title, props)
        if args.dry_run:
            # In dry-run, don't print DB id to stdout
            logger.info("[DRY] 跳过创建（未输出 DB id）")
            return
    except requests.RequestException as exc:
        # Detailed logs already emitted; keep stdout clean
        logger.error("[HTTP-ERR] 请求失败")
        raise SystemExit(3)

    # Print only DB id to stdout for scripting
    print(dbid)
    logger.info("[OK] 数据库已创建: %s", dbid)


if __name__ == "__main__":
    main()
