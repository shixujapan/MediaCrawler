#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Process #A#B tags and A,B co_operators with:
- Clean-first (emoji/kaomoji/newlines/extra spaces) + NFKC
- Global co-operator set (from whole column, normalized)
- Role annotations like "🎬:@千里明", "👗:七月夕", "出境:我" → extract as co_operators (drop self refs & id-like)
  * ROLE_IGNORE_SET: keep these segments in title (no extraction)
- Remove co-operators from tags, promote to co_operators
- Remove non-ignored role segments and bracketed id-like tokens from final title
- Balance unmatched brackets ()（）[]【】{}; remove empty parentheses
- Robust punctuation cleanup (no repeated punctuations, remove unmatched quotes)
- Skip specific rows by link_id (or custom id column)

I/O policy:
- Overwrite ONLY three columns: title / tags / co_operators
- tags: space-separated (e.g. "#剧情 #古风")
- co_operators: space-separated (e.g. "锦超 庄翰_Roya")
"""
from __future__ import annotations
import argparse, json, re, unicodedata
from pathlib import Path
from typing import Any, List, Tuple, Set
import pandas as pd

# ========= Regex =========
TAG_INLINE_RE = re.compile(r"#([A-Za-z0-9_\u4e00-\u9fff]+)")
AT_INLINE_RE  = re.compile(r"(?<!\w)@([A-Za-z0-9_\u4e00-\u9fff·•・]+)")

EMOJI_RE = re.compile("[" "\U0001F300-\U0001FAFF" "\U00002700-\U000027BF" "\U0001F900-\U0001F9FF" "]+")
KAOMOJI_RE = re.compile(
    r"[\(\（【\[]"
    r"[^()\[\]{}（）【】\n]{0,20}?"
    r"[°\^\-_ωдД∀▽╯╰Tt﹏><ﾉノー~ゝツ]"
    r"[^()\[\]{}（）【】\n]{0,20}?"
    r"[\)\）】\]]"
)

# Role annotations: capture (role)(names)
# 允许 emoji/白名单中文角色词；在 role 与 冒号之间容忍零宽字符 (ZWSP/ZWJ/FEFF)
ROLE_KV_RE = re.compile(
    r"("  # 角色捕获组
    r"(?:[\u2600-\u27BF\U0001F300-\U0001FAFF]{1,3})"   # 1-3 个 emoji
    r"|出境|出镜|摄影|剪辑|衣服|服装|化妆|妆容|设定|摄/后|拍摄|妆造|动作指导|发起人|导演|编剧|编导|策划|制作|监制|主演|主演/配音|配音|配音演员|配音导演|角色|角色扮演|角色/配音|角色/出境|角色/出镜|角色/扮演|角色/出演|角色/主演|角色/客串|扮演|出演|客串|嘉宾|特别出演|友情出演|友情客串|友情客串/出境|友情客串/出镜|友情客串/配音|友情出演/配音|友情出演/出境|友情出演/出镜|特别出演/配音|特别出演/出境|特别出演/出镜"
    r")"
    r"(?:[\u200B-\u200D\uFEFF])?\s*[:：]\s*"
    r"@?([A-Za-z0-9_\u4e00-\u9fff·•・]+(?:[、,/&和以及]\s*[A-Za-z0-9_\u4e00-\u9fff·•・]+)*)"
)
NAME_SEP_RE = re.compile(r"[、,/&和以及]+")

# tokens
PAREN_ID_TOKEN_RE = re.compile(r"[\(\（\[\【\{]\s*[A-Za-z0-9]{8,}\s*[\)\）\]\】\}]")  # (AB12...)
ID_LIKE_RE = re.compile(r"^[A-Za-z0-9]{8,}$")
EMPTY_PAREN_RE = re.compile(r"[\(\（\[\【\{]\s*[\)\）\]\】\}]")

# punctuation helpers
REPEAT_PUNCT_RE = re.compile(r"([!！?？。，、,:：;；…—\-~·])\1{1,}")
SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([!！?？。，、,:：;；…])")
PUNCT_AROUND_QUOTES_RE = re.compile(r"\s*([\"“”'‘’])\s*")

MYSELF_SET = {"我", "本人", "自己", "me", "i"}
MYSELF_LOWER = {w.lower() for w in MYSELF_SET}
# 忽略抽取且保留在 title 的角色段
ROLE_IGNORE_SET = {"设定", "内心深处的两个灵魂", "食腐寄生变异体"}

# ========= Utils =========
def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s) if isinstance(s, str) else s

def dedup_preserve_order(seq: List[str], key=lambda s: s.lower()) -> List[str]:
    seen, out = set(), []
    for x in seq:
        k = key(x)
        if k not in seen:
            seen.add(k); out.append(x)
    return out

def split_names(s: str) -> List[str]:
    if not isinstance(s, str) or not s.strip(): return []
    return [nfkc(x).strip().lstrip("@") for x in NAME_SEP_RE.split(s) if nfkc(x).strip()]

# ========= Rules =========
def load_rules(rules_path: Path):
    with open(rules_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    stop_words = {nfkc(str(w)).strip().lower() for w in cfg.get("stop_words", []) if str(w).strip()}
    coop_rules = []
    for r in cfg.get("normalize_coop", []):
        pat = nfkc(str(r.get("pattern", ""))).strip()
        rep = nfkc(str(r.get("replacement", ""))).strip()
        if pat and rep:
            coop_rules.append((pat, rep))
    return stop_words, coop_rules

def make_is_stopword(stop_words: Set[str]):
    def is_stopword(s: str) -> bool:
        if not isinstance(s, str): return False
        raw = nfkc(s).lstrip("#").strip().lower()
        return raw in stop_words
    return is_stopword

def make_normalize_coop(coop_rules: List[Tuple[str, str]]):
    folded = [(pat.casefold(), rep) for pat, rep in coop_rules]
    def normalize_coop(name: str) -> str:
        if not isinstance(name, str) or not name.strip(): return ""
        s = nfkc(name).strip()
        s_cf = s.casefold()
        for pat_cf, rep in folded:
            if pat_cf in s_cf:
                return rep
        return s
    return normalize_coop

def make_is_coop_name(coop_rules: List[Tuple[str, str]]):
    pats_cf = [pat.casefold() for pat, _ in coop_rules]
    def is_coop_name(name: str) -> bool:
        if not isinstance(name, str) or not name.strip(): return False
        s_cf = nfkc(name).strip().casefold()
        return any(p in s_cf for p in pats_cf)
    return is_coop_name

# ========= Cleaning & Finalization =========
def clean_text(s: Any, keep_emoji: bool = False) -> str:
    """Clean text; optionally keep emoji (for role extraction robustness)."""
    if not isinstance(s, str) or not s.strip():
        return "" if not isinstance(s, str) else s.strip()
    t = nfkc(s)
    if not keep_emoji:
        t = EMOJI_RE.sub(" ", t)
    t = KAOMOJI_RE.sub(" ", t)
    t = re.sub(r"[\r\n\t]+", " ", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t

def finalize_punctuation(s: str) -> str:
    if not s: return s
    t = s
    t = REPEAT_PUNCT_RE.sub(lambda m: m.group(1), t)
    t = SPACE_BEFORE_PUNCT_RE.sub(r"\1", t)
    t = PUNCT_AROUND_QUOTES_RE.sub(r"\1", t)

    def strip_if_odd(t: str, chars: str) -> str:
        count = sum(t.count(ch) for ch in chars)
        if count % 2 != 0:
            for ch in chars:
                t = t.replace(ch, "")
        return t
    t = strip_if_odd(t, '"'); t = strip_if_odd(t, "'")
    t = strip_if_odd(t, "“”"); t = strip_if_odd(t, "‘’")

    t = t.strip(" \"'“”‘’，。？！、；：:;…—-~·")
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t

def balance_brackets(s: str) -> str:
    """Balance unmatched (), （）, [], 【】, {} by appending missing right brackets at the end."""
    if not s: return s
    pairs = [("(", ")"), ("（", "）"), ("[", "]"), ("【", "】"), ("{", "}")]
    t = s
    for left, right in pairs:
        diff = t.count(left) - t.count(right)
        if diff > 0:
            t = t + (right * diff)
    return t

# ========= Split according to your schema =========
def split_tags_cell(cell: Any) -> List[str]:
    if not isinstance(cell, str) or not cell: return []
    return ["#" + t for t in TAG_INLINE_RE.findall(nfkc(cell))]

def split_coops_cell(cell: Any) -> List[str]:
    if not isinstance(cell, str) or not cell: return []
    return [nfkc(x).strip().lstrip("@") for x in cell.split(",") if nfkc(x).strip()]

# ========= Title extraction =========
NON_PERSON_RE = re.compile(r"(你们看着|你们|我们|大家|网友|评论区|朋友们)")

def extract_role_coops(text: str) -> List[str]:
    """Extract names from role annotations; ignore roles in ROLE_IGNORE_SET; drop self & id-like & non-person phrases."""
    if not text: 
        return []
    hits = []
    for role, names in ROLE_KV_RE.findall(text):
        role_norm = nfkc(role).strip()
        if role_norm in ROLE_IGNORE_SET:
            continue
        for n in split_names(names):
            if not n: continue
            n = n.strip().lstrip("@")
            nl = n.lower()
            if nl in MYSELF_LOWER:
                continue
            if ID_LIKE_RE.match(n):
                continue
            if NON_PERSON_RE.search(n):
                continue
            hits.append(n)
    return hits

def extract_from_title(title_clean: str):
    if not title_clean:
        return [], [], []
    tags = TAG_INLINE_RE.findall(title_clean)
    ats  = AT_INLINE_RE.findall(title_clean)
    roles = extract_role_coops(title_clean)
    return tags, ats, roles

# ========= Skip-list helpers =========
def build_skip_set(df: pd.DataFrame, id_col: str, skip_ids: str | None, skip_file: str | None) -> Set[str]:
    skip: Set[str] = set()
    if skip_ids:
        for x in skip_ids.split(","):
            x = x.strip()
            if x:
                skip.add(x)
    if skip_file:
        p = Path(skip_file)
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    skip.add(line)
    if id_col not in df.columns:
        if 'id' in df.columns:
            id_col = 'id'
        else:
            return set()
    return skip

# ========= Core processing =========
def process_dataframe(df: pd.DataFrame, stop_words: set, coop_rules: List[Tuple[str, str]],
                      id_col: str, skip_set: Set[str]):
    is_stopword    = make_is_stopword(stop_words)
    normalize_coop = make_normalize_coop(coop_rules)
    is_coop_name   = make_is_coop_name(coop_rules)

    if "title" not in df.columns:
        raise ValueError("Input CSV must contain a 'title' column.")

    # Build GLOBAL coop set
    global_coops = set()
    if "co_operators" in df.columns:
        for s in df["co_operators"].fillna(""):
            for c in split_coops_cell(s):
                norm = normalize_coop(c)
                if norm and not is_stopword(norm):
                    global_coops.add(norm.strip().lower())

    new_titles, new_tags_col, new_coops_col = [], [], []

    for _, row in df.iterrows():
        # skip?
        row_id = str(row.get(id_col, "")) if id_col in df.columns else ""
        if row_id and row_id in skip_set:
            new_titles.append(str(row.get("title", "")))
            new_tags_col.append(" ".join(split_tags_cell(row.get("tags", ""))))
            new_coops_col.append(" ".join(split_coops_cell(row.get("co_operators", ""))))
            continue

        # 0) clean (two versions)
        raw_title = str(row.get("title", ""))
        title_for_roles = clean_text(raw_title, keep_emoji=True)   # 保留 emoji → 角色抽取更稳
        title = clean_text(raw_title, keep_emoji=False)            # 正常清理 → 其它抽取 & 最终展示

        # 1) split base
        base_tags  = split_tags_cell(row.get("tags", ""))
        base_coops = split_coops_cell(row.get("co_operators", ""))

        # 2) extract (use title_for_roles)
        title_tags_raw, title_coops_raw, roles_coops_raw = extract_from_title(title_for_roles)

        # 3) initial coops
        coops_all  = base_coops + title_coops_raw + roles_coops_raw
        coops_norm = [normalize_coop(c) for c in coops_all]
        coops_norm = [c for c in coops_norm if c and not is_stopword(c)]
        coops_norm = dedup_preserve_order(coops_norm, key=lambda s: s.strip().lower())
        coops_set  = {c.strip().lower() for c in coops_norm}

        # 4) tags candidate
        tags_all = base_tags + ["#" + t for t in title_tags_raw]

        # 5) remove coops from tags; promote
        tags_clean = []
        for t in tags_all:
            if is_stopword(t):
                continue
            name = t.lstrip("#").strip()
            name_lc = name.lower()
            should_promote = (name_lc in global_coops) or is_coop_name(name_lc)
            if should_promote:
                if name_lc not in coops_set:
                    nn = normalize_coop(name)
                    if nn and not is_stopword(nn):
                        coops_norm.append(nn)
                        coops_set.add(nn.strip().lower())
                continue
            tags_clean.append(t)

        tags_clean = dedup_preserve_order(tags_clean, key=lambda s: s.lstrip("#").lower())
        coops_norm = dedup_preserve_order(coops_norm, key=lambda s: s.strip().lower())

        # 6) build final title:
        #    - remove #tags
        #    - remove @names (from @ and roles) + 兜底去掉 ":名字" & ":我/本人/自己/me/i"
        #    - remove non-ignored role segments
        #    - remove bracketed id-like and empty parentheses
        clean_t = title
        if title_tags_raw:
            pat = r"(?:\s*#(?:" + "|".join(map(re.escape, set(title_tags_raw))) + r"))(?!\w)"
            clean_t = re.sub(pat, " ", clean_t)

        extracted_names = set(title_coops_raw) | set(roles_coops_raw)
        if extracted_names:
            # 删带 @ 的名字
            pat = r"(?:\s*@(?:" + "|".join(map(re.escape, extracted_names)) + r"))(?!\w)"
            clean_t = re.sub(pat, " ", clean_t)
            # 兜底：删掉“:名字”（可能因前面 emoji 被删导致左侧角色缺失）
            pat2 = r"(^|[\s，。！？!?.])[:：]\s*(?:" + "|".join(map(re.escape, extracted_names)) + r")(?!\w)"
            clean_t = re.sub(pat2, r"\1", clean_t)

        # ★ 兜底再兜底：删掉 “:我/本人/自己/me/i”，避免出现“……:我”
        SELF_WORDS = ["我", "本人", "自己", "me", "i"]
        pat_self = r"(^|[\s，。！？!?.])[:：]\s*(?:" + "|".join(map(re.escape, SELF_WORDS)) + r")(?!\w)"
        clean_t = re.sub(pat_self, r"\1", clean_t)

        # remove role segments entirely, but keep ignored ones like 设定:AAA / 内心深处的两个灵魂:...
        def _remove_roles(m: re.Match) -> str:
            role = nfkc(m.group(1)).strip()
            return m.group(0) if role in ROLE_IGNORE_SET else " "
        clean_t = ROLE_KV_RE.sub(_remove_roles, clean_t)

        clean_t = PAREN_ID_TOKEN_RE.sub(" ", clean_t)  # (AB12...) anywhere
        clean_t = EMPTY_PAREN_RE.sub(" ", clean_t)     # () （） [] 【】 {}
        clean_t = re.sub(r"\s{2,}", " ", clean_t).strip()

        # 删掉句末孤立的冒号
        clean_t = re.sub(r"[:：]\s*$", "", clean_t)
        # 删掉“悬挂的冒号”：句首/空白/标点 后紧跟 冒号+空格+文字 的冒号
        clean_t = re.sub(r"(^|[\s，。！？!?.])[:：]\s+(?=[\u4e00-\u9fffA-Za-z0-9])", r"\1", clean_t)

        # balance unmatched brackets then finalize punctuation
        clean_t = balance_brackets(clean_t)
        clean_t = finalize_punctuation(clean_t)

        # 7) overwrite columns
        new_titles.append(clean_t)
        new_tags_col.append("".join(tags_clean))
        new_coops_col.append(",".join(coops_norm))

    df["title"] = new_titles
    df["tags"] = new_tags_col
    df["co_operators"] = new_coops_col

    # overviews (optional)
    all_tags = []
    for s in df["tags"].fillna(""):
        all_tags.extend([x.strip() for x in s.split(" ") if x.strip()])
    tags_overview = sorted(set(all_tags), key=lambda s: s.lstrip("#").lower())

    all_coops = []
    for s in df["co_operators"].fillna(""):
        all_coops.extend([x.strip() for x in s.split(" ") if x.strip()])
    coops_overview = sorted(set(all_coops), key=lambda s: s.lower())

    return df, tags_overview, coops_overview

# ========= CLI =========
def main():
    ap = argparse.ArgumentParser(description="Process tags/co_operators with GLOBAL coop set & role extraction (JSON-driven).")
    ap.add_argument("--input", required=True, help="Input CSV path")
    ap.add_argument("--rules", required=True, help="rules.json path")
    ap.add_argument("--output", help="Output CSV path")
    ap.add_argument("--tags-overview", help="Write tags overview (txt)")
    ap.add_argument("--coops-overview", help="Write co_operators overview (txt)")
    ap.add_argument("--skip-ids", help="Comma-separated link ids to skip (e.g., 'a,b,c')", default=None)
    ap.add_argument("--skip-ids-file", help="Path to a file with one link id per line", default=None)
    ap.add_argument("--id-col", help="ID column name (default 'link_id', fallback 'id')", default="link_id")
    args = ap.parse_args()

    in_path = Path(args.input); rules_path = Path(args.rules)
    if not in_path.exists(): raise FileNotFoundError(f"Input CSV not found: {in_path}")
    if not rules_path.exists(): raise FileNotFoundError(f"Rules JSON not found: {rules_path}")

    df = pd.read_csv(in_path)
    stop_words, coop_rules = load_rules(rules_path)

    # build skip set
    skip_set = set()
    if args.skip_ids or args.skip_ids_file:
        skip_set = build_skip_set(df, args.id_col, args.skip_ids, args.skip_ids_file)

    df_proc, tags_overview, coops_overview = process_dataframe(
        df, stop_words, coop_rules, args.id_col, skip_set
    )

    if args.output:
        out_path = Path(args.output)
        df_proc.to_csv(out_path, index=False)
        print(f"[OK] Wrote cleaned CSV -> {out_path}")

    if args.tags_overview:
        Path(args.tags_overview).write_text("\n".join(tags_overview), encoding="utf-8")
        print(f"[OK] Wrote tags overview -> {args.tags_overview}")

    if args.coops_overview:
        Path(args.coops_overview).write_text("\n".join(coops_overview), encoding="utf-8")
        print(f"[OK] Wrote co_operators overview -> {args.coops_overview}")

    if not (args.output or args.tags_overview or args.coops_overview):
        print("tags_overview:", tags_overview)
        print("co_operators_overview:", coops_overview)

if __name__ == "__main__":
    main()
