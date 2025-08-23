#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Async bulk-create Notion pages (large-scale optimized):

- CSV headers == schema.name
- Notion property keys use schema.label (fallback to name)
- Relation OPTIONAL:
    Priority for source column:
      --ids-column > relation.name > relation.label > 'related_platform_ids'
    Values are comma-separated "titles" of the related DB.
- Large-scale strategies:
    * Chunked processing: --chunk-size controls memory & index scope per wave
    * Batched queries: --max-or controls per-request OR predicates for title equals
    * Avoid full scans:
        - Existing titles are fetched by batched filters, not by scanning full DB
        - Related index only loads what's needed per chunk

Env:
  NOTION_TOKEN=secret_xxx

Usage:
  python add_main_with_relation_async.py \
    --main-db-id <MAIN_DB_ID> \
    --main-schema main.schema.json \
    --main-csv main.csv \
    [--related-db-id <RELATED_DB_ID>] \
    [--related-schema related.schema.json] \
    [--ids-column related_platform_ids] \
    [--concurrency 16] [--rps 3] \
    [--chunk-size 100] [--max-or 20] \
    [--dry-run] [--verbose]
"""
from __future__ import annotations
import argparse, asyncio, csv, json, logging, os, sys, time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Set

import httpx

API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
log = logging.getLogger("notion-bulk")

# ---------------- utils ----------------
SchemaItem = Mapping[str, Any]
Properties = Dict[str, Any]
Row = Mapping[str, str]

def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )

def trim(s: str, /, *, maxlen: int = 150) -> str:
    s = (s or "").strip()
    return s if len(s) <= maxlen else s[:maxlen]

def nonempty(x: Any) -> bool:
    return not (x is None or (isinstance(x, str) and x.strip() == ""))

def split_ids(cell: Optional[str]) -> List[str]:
    if not cell:
        return []
    return [x.strip() for x in str(cell).split(",") if x.strip()]

def print_progress(done: int, total: int, skipped: int) -> None:
    pct = (done + skipped) / total * 100 if total else 100
    bar_len = 30
    filled = int(bar_len * pct / 100)
    bar = "#" * filled + "-" * (bar_len - filled)
    sys.stderr.write(f"\r[{bar}] {pct:5.1f}% | created={done} skipped={skipped}/{total}")
    sys.stderr.flush()

def chunks(iterable: List[Row], size: int) -> Iterable[List[Row]]:
    for i in range(0, len(iterable), size):
        yield iterable[i:i+size]

# ---------------- schema / csv ----------------
def load_schema(path: Path) -> List[SchemaItem]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("schema 顶层必须是数组")
    return data

def find_title(schema: Sequence[SchemaItem]) -> Tuple[str, str]:
    for it in schema:
        if it.get("is_displayed", True) and it.get("type") == "title":
            csv_name = (it.get("name") or "").strip()
            label = trim((it.get("label") or it.get("name") or ""))
            if csv_name and label:
                return csv_name, label
    raise SystemExit("schema 中未找到可见的 title 字段")

def find_optional_first_relation(schema: Sequence[SchemaItem]) -> Optional[Tuple[str, str]]:
    for it in schema:
        if it.get("is_displayed", True) and it.get("type") == "relation":
            return (it.get("name") or "").strip(), trim((it.get("label") or it.get("name") or ""))
    return None

def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [{(k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()} for r in reader]

# ---------------- Notion client ----------------
class TokenBucket:
    def __init__(self, rps: float) -> None:
        self.capacity = max(rps, 0.1)
        self.tokens = self.capacity
        self.rate = self.capacity
        self.updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            dt = now - self.updated
            self.updated = now
            self.tokens = min(self.capacity, self.tokens + dt * self.rate)
            if self.tokens < 1.0:
                sleep_for = (1.0 - self.tokens) / self.rate
                await asyncio.sleep(sleep_for)
                self.tokens = 0.0
                self.updated = time.monotonic()
            else:
                self.tokens -= 1.0

@dataclass
class NotionAsync:
    token: str
    rps: float = 3.0
    concurrency: int = 16
    timeout: float = 60.0

    def __post_init__(self) -> None:
        self._bucket = TokenBucket(self.rps)
        self._sem = asyncio.Semaphore(max(1, self.concurrency))
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "NotionAsync":
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
                "Accept-Encoding": "gzip",
            },
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, *_exc) -> None:
        if self._client:
            await self._client.aclose()

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        assert self._client is not None
        MAX_RETRIES, BASE, MAX_BACKOFF = 6, 1.7, 10.0
        attempt = 0
        while True:
            await self._bucket.acquire()
            async with self._sem:
                try:
                    resp = await self._client.request(method, url, **kwargs)
                except (httpx.TransportError, httpx.TimeoutException) as e:
                    attempt += 1
                    if attempt > MAX_RETRIES:
                        log.error("[HTTPX] %s", e)
                        raise
                    delay = min(MAX_BACKOFF, BASE**attempt)
                    log.debug("[RETRY-EXC] %s sleep %.2fs", e.__class__.__name__, delay)
                    await asyncio.sleep(delay)
                    continue

                if resp.status_code in (429, 502, 503, 504):
                    attempt += 1
                    if attempt > MAX_RETRIES:
                        resp.raise_for_status()
                    ra = resp.headers.get("Retry-After")
                    try:
                        delay = float(ra) if ra else min(MAX_BACKOFF, BASE**attempt)
                    except ValueError:
                        delay = min(MAX_BACKOFF, BASE**attempt)
                    log.debug("[RETRY] %s %s sleep %.2fs", method, url, delay)
                    await asyncio.sleep(delay)
                    continue

                resp.raise_for_status()
                return resp

    async def create_page(self, db_id: str, properties: Mapping[str, Any]) -> str:
        url = f"{API_BASE}/pages"
        body = {"parent": {"database_id": db_id}, "properties": dict(properties)}
        print(body)
        r = await self._request("POST", url, json=body)
        return r.json().get("id", "")

    async def query_db_filtered_titles(
        self, db_id: str, title_label: str, titles: List[str]
    ) -> Set[str]:
        """
        Return LOWERCASED titles existing in db among the given 'titles' by OR-equals filter.
        Splits into multiple requests when titles is large.
        """
        existing: Set[str] = set()
        # Notion compound filter supports {"or":[ ... ]}
        def build_filter(batch: List[str]) -> Dict[str, Any]:
            return {
                "or": [
                    {"property": title_label, "title": {"equals": t}}
                    for t in batch
                ]
            }
        # Empirically keep page_size small; we rely on equals match
        for batch in chunks_list(titles, _MAX_OR):  # uses global set later
            url = f"{API_BASE}/databases/{db_id}/query"
            body = {"page_size": 100, "filter": build_filter(batch)}

            print(body)
            # paginate just in case
            while True:
                r = await self._request("POST", url, json=body)
                data = r.json()
                for p in data.get("results", []):
                    t = extract_title(p, title_label)
                    if t:
                        existing.add(t.lower())
                if data.get("has_more"):
                    body["start_cursor"] = data.get("next_cursor")
                else:
                    break
        return existing

    async def query_related_pages_by_titles(
        self, db_id: str, title_label: str, needed: List[str]
    ) -> Dict[str, str]:
        """
        Return mapping title -> page_id for a set of titles existing in related db.
        """
        out: Dict[str, str] = {}

        def build_filter(batch: List[str]) -> Dict[str, Any]:
            return {
                "or": [
                    {"property": title_label, "title": {"equals": t}}
                    for t in batch
                ]
            }

        url = f"{API_BASE}/databases/{db_id}/query"
        for batch in chunks_list(needed, _MAX_OR):
            body = {"page_size": 100, "filter": build_filter(batch)}
            while True:
                r = await self._request("POST", url, json=body)
                data = r.json()
                for p in data.get("results", []):
                    t = extract_title(p, title_label)
                    if t:
                        out[t] = p["id"]
                if data.get("has_more"):
                    body["start_cursor"] = data.get("next_cursor")
                else:
                    break
        return out

def chunks_list(items: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield items[i:i+size]

def extract_title(page: Mapping[str, Any], title_label: str) -> str:
    prop = page.get("properties", {}).get(title_label, {})
    arr = prop.get("title", [])
    if isinstance(arr, list) and arr:
        blk = arr[0]
        return (blk.get("plain_text") or blk.get("text", {}).get("content") or "").strip()
    return ""

# ---------------- property builders ----------------
def csv_cell_to_value(notion_type: str, raw: Any) -> Optional[Dict[str, Any]]:
    if not nonempty(raw):
        return None
    s = str(raw)
    if notion_type == "title":
        return {"title": [{"type": "text", "text": {"content": s}}]}
    if notion_type == "rich_text":
        return {"rich_text": [{"type": "text", "text": {"content": s}}]}
    if notion_type == "url":
        return {"url": s}
    if notion_type == "number":
        try:
            return {"number": float(s)}
        except Exception:
            log.warning("[SKIP] 数字解析失败: %s", s)
            return None
    if notion_type == "checkbox":
        return {"checkbox": s.strip().lower() in {"1", "true", "yes", "y", "t"}}
    if notion_type == "select":
        return {"select": {"name": s}}
    if notion_type == "multi_select":
        names = [x.strip() for x in s.split(",") if x.strip()]
        return {"multi_select": [{"name": n} for n in names]}
    if notion_type == "date":
        return {"date": {"start": s.replace("/", "-")}}
    if notion_type == "email":
        return {"email": s}
    if notion_type == "phone_number":
        return {"phone_number": s}
    return None  # relation/rollup/people/files skipped here

def build_basic_properties(schema: Sequence[SchemaItem], row: Row) -> Properties:
    props: Properties = {}
    for it in schema:
        if not it.get("is_displayed", True):
            continue
        t = it.get("type", "rich_text")
        if t in {"rollup", "relation", "people", "files"}:
            continue
        csv_col = (it.get("name") or "").strip()
        if csv_col not in row:
            continue
        payload = csv_cell_to_value(t, row[csv_col])
        if payload is None:
            continue
        header = trim(it.get("label") or it.get("name") or "")
        if header:
            props[header] = payload
    return props

def pick_relation_source_column(
    row: Row,
    prefer_column: Optional[str],
    rel_name: Optional[str],
    rel_label: Optional[str],
) -> Optional[str]:
    if prefer_column and nonempty(row.get(prefer_column)):
        return prefer_column
    if rel_name and nonempty(row.get(rel_name)):
        return rel_name
    if rel_label and nonempty(row.get(rel_label)):
        return rel_label
    if nonempty(row.get("related_platform_ids")):
        return "related_platform_ids"
    return None

def build_relation_property_for_row(
    row: Row,
    rel_label: str,
    prefer_column: Optional[str],
    rel_name: Optional[str],
    rel_label_in_csv: Optional[str],
    related_title_to_page: Mapping[str, str],
    *,
    dry_placeholder: bool = False,
) -> Optional[Tuple[str, Dict[str, Any]]]:
    src_col = pick_relation_source_column(row, prefer_column, rel_name, rel_label_in_csv)
    if not src_col:
        return None
    ids = split_ids(row.get(src_col))
    if not ids:
        return None

    if dry_placeholder:
        return rel_label, {"relation": [{"id": f"dry:{pid}"} for pid in ids]}

    page_ids = [related_title_to_page.get(pid) for pid in ids]
    page_ids = [p for p in page_ids if p]
    if not page_ids:
        return None
    return rel_label, {"relation": [{"id": p} for p in page_ids]}

# ---------------- worker ----------------
async def create_main_row(
    client: NotionAsync,
    main_db_id: str,
    main_schema: Sequence[SchemaItem],
    row: Row,
    main_title_csv: str,
    main_title_label: str,
    rel_tuple: Optional[Tuple[str, str]],
    prefer_ids_column: Optional[str],
    related_title_to_page: Mapping[str, str],
) -> bool:
    title_value = row.get(main_title_csv, "")
    if not nonempty(title_value):
        log.warning("[SKIP] 缺少 Title 值: %s", row)
        return False

    props = build_basic_properties(main_schema, row)
    props.setdefault(main_title_label, {"title": [{"type": "text", "text": {"content": str(title_value)}}]})

    if rel_tuple:
        rel_name, rel_label = rel_tuple
        rel_payload = build_relation_property_for_row(
            row,
            rel_label=rel_label,
            prefer_column=prefer_ids_column,
            rel_name=rel_name,
            rel_label_in_csv=rel_label,
            related_title_to_page=related_title_to_page,
        )
        if rel_payload:
            header, payload = rel_payload
            props[header] = payload

    page_id = await client.create_page(main_db_id, props)
    log.debug("[NEW] %s -> %s (page_id=%s)", main_title_label, title_value, page_id)
    return True

# ---------------- CLI ----------------
@dataclass(slots=True)
class Args:
    main_db_id: str
    main_schema: Path
    main_csv: Path
    related_db_id: Optional[str]
    related_schema: Optional[Path]
    ids_column: Optional[str]
    concurrency: int
    rps: float
    chunk_size: int
    max_or: int
    dry_run: bool
    verbose: bool

def parse_args() -> Args:
    ap = argparse.ArgumentParser(description="Create main pages (optionally with relation) at creation time – large-scale optimized.")
    ap.add_argument("--main-db-id", required=True)
    ap.add_argument("--main-schema", required=True, type=Path)
    ap.add_argument("--main-csv", required=True, type=Path)
    ap.add_argument("--related-db-id")
    ap.add_argument("--related-schema", type=Path)
    ap.add_argument("--ids-column", help="CSV 列名（逗号分隔，值是对端 DB 的 Title 文本）；优先于 relation.name / relation.label / related_platform_ids")
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--rps", type=float, default=3.0)
    ap.add_argument("--chunk-size", type=int, default=50, help="每批处理的 CSV 行数")
    ap.add_argument("--max-or", type=int, default=10, help="单次查询中 OR 条件的最大数量（过大可能触发 400/429）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ns = ap.parse_args()

    # Set globals for helper using _MAX_OR
    global _MAX_OR
    _MAX_OR = max(1, ns.max_or)

    return Args(
        main_db_id=ns.main_db_id,
        main_schema=ns.main_schema,
        main_csv=ns.main_csv,
        related_db_id=ns.related_db_id,
        related_schema=ns.related_schema,
        ids_column=ns.ids_column,
        concurrency=max(1, ns.concurrency),
        rps=max(0.1, ns.rps),
        chunk_size=max(1, ns.chunk_size),
        max_or=_MAX_OR,
        dry_run=ns.dry_run,
        verbose=ns.verbose,
    )

# ---------------- main ----------------
def collect_needed_titles_for_chunk(
    rows: List[Row],
    rel_tuple: Optional[Tuple[str, str]],
    ids_column: Optional[str],
) -> Set[str]:
    """从 chunk 里收集 relation 对端所需的 titles（去重）。"""
    needed: Set[str] = set()
    if not rel_tuple:
        return needed
    rel_name, rel_label = rel_tuple
    for r in rows:
        src = pick_relation_source_column(r, ids_column, rel_name, rel_label)
        if not src:
            continue
        for tid in split_ids(r.get(src)):
            if tid:
                needed.add(tid)
    return needed

def sample_payload_for_dry_run(
    main_db_id: str,
    main_schema: Sequence[SchemaItem],
    row: Row,
    main_title_csv: str,
    main_title_label: str,
    rel_tuple: Optional[Tuple[str, str]],
    prefer_ids_column: Optional[str],
) -> Dict[str, Any]:
    props = build_basic_properties(main_schema, row)
    title_val = row.get(main_title_csv, "")
    if nonempty(title_val):
        props.setdefault(main_title_label, {"title": [{"type": "text", "text": {"content": str(title_val)}}]})
    if rel_tuple:
        rel_name, rel_label = rel_tuple
        rel = build_relation_property_for_row(
            row,
            rel_label=rel_label,
            prefer_column=prefer_ids_column,
            rel_name=rel_name,
            rel_label_in_csv=rel_label,
            related_title_to_page={},
            dry_placeholder=True,
        )
        if rel:
            header, payload = rel
            props[header] = payload
    return {"parent": {"database_id": main_db_id}, "properties": props}

async def amain() -> None:
    args = parse_args()
    setup_logging(args.verbose)

    token = os.getenv("NOTION_TOKEN")
    if not token:
        raise SystemExit("请先设置 NOTION_TOKEN")

    main_schema = load_schema(args.main_schema)
    rows = read_csv_rows(args.main_csv)

    main_title_csv, main_title_label = find_title(main_schema)
    rel_tuple = find_optional_first_relation(main_schema)

    # Dry run: print ONE sample body
    if args.dry_run:
        sample = next((r for r in rows if nonempty(r.get(main_title_csv, ""))), None)
        print(json.dumps(
            sample_payload_for_dry_run(
                args.main_db_id, main_schema, sample or {},
                main_title_csv, main_title_label,
                rel_tuple, args.ids_column
            ),
            ensure_ascii=False, indent=2
        ))
        return

    # If relation is present but related DB info is missing, we skip relation quietly.
    related_ready = bool(rel_tuple and args.related_db_id and args.related_schema)
    related_title_label = None
    if related_ready:
        related_schema = load_schema(args.related_schema)  # type: ignore[arg-type]
        _csv, related_title_label = find_title(related_schema)

    created = skipped = 0
    total = len(rows)

    async with NotionAsync(token, rps=args.rps, concurrency=args.concurrency) as notion:
        # Chunked processing loop
        for chunk_rows in chunks(rows, args.chunk_size):
            # 1) 去重：只查询本 chunk 中出现的标题，避免全库扫描
            chunk_titles = list({(r.get(main_title_csv, "") or "").strip() for r in chunk_rows if nonempty(r.get(main_title_csv))})
            print(chunk_titles)
            chunk_titles_lc = [t.lower() for t in chunk_titles]
            existing_lc: Set[str] = set()
            if chunk_titles:
                existing_lc = await notion.query_db_filtered_titles(args.main_db_id, main_title_label, chunk_titles)

            # 2) relation 对端索引：仅索引本 chunk 需要的 titles
            related_index: Dict[str, str] = {}
            if related_ready and related_title_label:
                needed = collect_needed_titles_for_chunk(chunk_rows, rel_tuple, args.ids_column)
                if needed:
                    related_index = await notion.query_related_pages_by_titles(args.related_db_id, related_title_label, list(needed))  # type: ignore[arg-type]
                log.debug("[INDEX][chunk] needed=%d got=%d", len(needed), len(related_index))

            # 3) 并发创建本 chunk 的页面
            async def runner(row: Row) -> None:
                nonlocal created, skipped
                title_value = (row.get(main_title_csv, "") or "").strip()
                if not title_value:
                    skipped += 1
                    print_progress(created, total, skipped)
                    return
                if title_value.lower() in existing_lc:
                    skipped += 1
                    print_progress(created, total, skipped)
                    return
                ok = await create_main_row(
                    notion,
                    args.main_db_id,
                    main_schema,
                    row,
                    main_title_csv,
                    main_title_label,
                    rel_tuple if related_ready else None,
                    args.ids_column,
                    related_index,
                )
                if ok:
                    created += 1
                else:
                    skipped += 1
                print_progress(created, total, skipped)

            await asyncio.gather(*(runner(r) for r in chunk_rows))

    sys.stderr.write("\n")
    print(json.dumps({"created": created, "skipped": skipped}, ensure_ascii=False))

def main() -> None:
    asyncio.run(amain())

if __name__ == "__main__":
    # 默认 OR 上限（可被 --max-or 覆盖）
    _MAX_OR = 20
    main()
