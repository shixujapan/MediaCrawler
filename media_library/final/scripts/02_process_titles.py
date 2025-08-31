import pandas as pd
import re
import json
import argparse
from typing import List, Dict, Set, Tuple
from datetime import datetime
from pathlib import Path


def load_rules(rules_path: str) -> Dict:
    """加载 rules.json 配置文件"""
    with open(rules_path, 'r', encoding='utf-8') as f:
        return json.load(f)


ID_PAREN_RE = re.compile(r"\([A-Za-z0-9]{6,}\)")
# 吞掉 @用户名 后紧跟的任意括号说明，如 (下乡版)/(O3x..)/(中文)
AT_WITH_ID_RE = re.compile(r"@([A-Za-z0-9_\u4e00-\u9fff·•・]+)(?:[（(][^）)]+[）)])?")
HASH_TAG_RE = re.compile(r"#([A-Za-z0-9_\u4e00-\u9fff\-]+)")


def normalize_punctuations(text: str) -> str:
    """替换常见中文标点到英文, 统一括号"""
    if not isinstance(text, str):
        return ""
    text = text.replace('：', ':').replace('，', ',')
    text = text.replace('（', '(').replace('）', ')')
    return text


def remove_id_tokens(text: str) -> str:
    return ID_PAREN_RE.sub('', text)


def collapse_spaces(text: str) -> str:
    return ' '.join(text.split())


def dedupe_punctuations(text: str) -> str:
    text = re.sub(r",+", ",", text)
    text = re.sub(r"\s*,\s*", ",", text)
    text = re.sub(r"\s*:\s*", ":", text)
    text = re.sub(r"\s*\|\s*", "|", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def balance_brackets(text: str) -> str:
    pairs = {')': '(', ']': '[', '}': '{', '】': '【'}
    open_set = set(pairs.values())
    close_set = set(pairs.keys())
    stack: List[Tuple[str, int]] = []
    keep = [True] * len(text)
    for i, ch in enumerate(text):
        if ch in open_set:
            stack.append((ch, i))
        elif ch in close_set:
            if stack and stack[-1][0] == pairs[ch]:
                stack.pop()
            else:
                keep[i] = False
    for _, idx in stack:
        keep[idx] = False
    return ''.join(ch for i, ch in enumerate(text) if keep[i])


def split_names(raw: str) -> List[str]:
    parts = re.split(r"[,，、/\s]+", raw)
    return [p for p in (s.strip() for s in parts) if p]


def normalize_name(name: str, normalize_rules: List[Dict]) -> str:
    clean = name.lstrip('@').strip()
    clean = ID_PAREN_RE.sub('', clean)
    for rule in normalize_rules:
        if rule.get('pattern') and rule['pattern'] in clean:
            clean = rule['replacement']
    return clean


def extract_roles_and_remove(title: str, role_titles: List[str], ignore_roles: List[str]) -> Tuple[str, List[str]]:
    names: List[str] = []
    new_title = title
    # 构造角色正则 (逐个角色名匹配, 捕获直到下一个角色/标签/行尾)
    ignore_set = set(ignore_roles or [])
    for role in sorted(role_titles, key=len, reverse=True):
        if role in ignore_set:
            continue
        role_q = re.escape(role)
        # 允许空载荷, 并在下一个 角色: / @提及 / #标签 / 行尾 处终止
        pattern = re.compile(rf"{role_q}\s*[:：]\s*([^#@]*?)(?=(?:\s+[\u4e00-\u9fffA-Za-z]+\s*[:：])|\s*@|\s*#|$)")
        while True:
            m = pattern.search(new_title)
            if not m:
                break
            payload = m.group(1)
            names.extend(split_names(payload))
            # 删除整个匹配段(角色:内容)
            start, end = m.span()
            new_title = new_title[:start] + new_title[end:]
    return new_title, names


def extract_plain_mentions(title: str) -> Tuple[str, List[str]]:
    names: List[str] = []
    def repl(m: re.Match) -> str:
        names.append(m.group(1))
        return ''
    new_title = AT_WITH_ID_RE.sub(repl, title)
    # 清理可能残留的孤立 '@'
    new_title = re.sub(r"\s@\s*", " ", new_title)
    return new_title, names


def extract_tags(title: str) -> Tuple[str, List[str]]:
    tags: List[str] = []
    def repl(m: re.Match) -> str:
        tags.append(m.group(1))
        return ''
    new_title = HASH_TAG_RE.sub(repl, title)
    return new_title, tags


def process_dataframe(df: pd.DataFrame, rules: Dict) -> Tuple[pd.DataFrame, Set[str]]:
    stop_words: Set[str] = set(rules.get('stop_words', []))
    normalize_rules = rules.get('normalize_coop', [])
    role_titles: List[str] = rules.get('titles', [])
    ignore_roles: List[str] = rules.get('titles_ignore', [])

    all_coops: Set[str] = set()

    # 第一次遍历: 基础清洗 + 提取合作者 (不处理标签归属)
    processed_rows = []
    for _, row in df.iterrows():
        title_raw = row.get('title', '')
        title = normalize_punctuations(title_raw)
        title = remove_id_tokens(title)
        title = collapse_spaces(title)

        # 提取角色:合作者 并从标题移除
        title, role_names = extract_roles_and_remove(title, role_titles, ignore_roles)
        # 提取 @提及 并从标题移除
        title, at_names = extract_plain_mentions(title)
        # 提取 #标签 并从标题移除 (仅提取, 二遍处理归属)
        title, title_tags = extract_tags(title)

        # 合并初始 co_operators 列
        existing = []
        if pd.notna(row.get('co_operators')):
            existing = [s.strip() for s in str(row.get('co_operators')).split(',') if s and s.strip()]

        # 合作者汇总顺序: @提及 → 角色提取 → 原co_operators
        names = at_names + role_names + existing
        # 规范化 & 过滤
        norm_names: List[str] = []
        seen: Set[str] = set()
        for n in names:
            nn = normalize_name(n, normalize_rules)
            if nn and nn not in stop_words and nn not in seen:
                seen.add(nn)
                norm_names.append(nn)

        all_coops.update(norm_names)

        # 清理标题标点/空格/括号
        title = normalize_punctuations(title)
        title = remove_id_tokens(title)
        title = dedupe_punctuations(title)
        title = balance_brackets(title)
        title = dedupe_punctuations(title)

        processed_rows.append({
            'row': row,
            'title': title,
            'title_tags': title_tags,
            'coops': norm_names
        })

    # 第二次遍历: 处理标签归属与最终格式
    coop_index: Set[str] = set(all_coops)
    replacement_set: Set[str] = set(r['replacement'] for r in normalize_rules if r.get('replacement'))

    out_rows = []
    for item in processed_rows:
        row = item['row'].copy()
        title = item['title']
        coops = list(item['coops'])

        # 合并已有 tags 列
        merged_tags: List[str] = []
        seen_tags: Set[str] = set()
        def push_tag(t: str):
            if t and t not in seen_tags:
                seen_tags.add(t)
                merged_tags.append(t)

        # tags 列
        if pd.notna(row.get('tags')):
            for t in str(row.get('tags')).split('#'):
                t = t.strip()
                if t:
                    push_tag(t)
        # 标题中提取的标签
        for t in item['title_tags']:
            push_tag(t)

        # 标签归属判断: 如果是合作者名或标准化替换值 → 归入 co_operators；若为停用词则丢弃
        kept_tags: List[str] = []
        seen_coops: Set[str] = set(coops)
        for t in merged_tags:
            if t in stop_words:
                continue
            if (t in coop_index) or (t in replacement_set):
                if t not in seen_coops:
                    coops.append(t)
                    seen_coops.add(t)
            else:
                kept_tags.append(t)

        # 输出格式
        row['title'] = title
        row['co_operators'] = ','.join(coops) if coops else ''
        row['tags'] = ('#' + '#'.join(kept_tags)) if kept_tags else ''
        out_rows.append(row)

    out_df = pd.DataFrame(out_rows, columns=df.columns)
    return out_df, coop_index


def process_data(input_path: str, rules_path: str, output_csv_path: str, output_json_path: str):
    rules = load_rules(rules_path)
    df = pd.read_csv(input_path)
    out_df, _ = process_dataframe(df, rules)

    # 仅覆盖三列, 其他列保持不变 (out_df 已经基于原列赋值)
    out_df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')

    # 输出 JSON (records)
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(json.loads(out_df.to_json(orient='records', force_ascii=False)), f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='输入CSV文件路径')
    parser.add_argument('--rules', required=True, help='rules.json文件路径')
    parser.add_argument('--outdir', required=True, help='输出目录路径')
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime('%Y%m%d')
    output_csv = outdir / f'platform_links_normalized_{date_str}.csv'
    output_json = outdir / f'platform_links_normalized_{date_str}.json'

    process_data(args.input, args.rules, str(output_csv), str(output_json))