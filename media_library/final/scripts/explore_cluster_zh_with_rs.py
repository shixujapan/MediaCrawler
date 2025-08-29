#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chinese-friendly clustering with related_series as hard labels.
- Uses jieba for tokenization (plus user dict + auto terms from related_series & tags)
- Stopwords support
- TF-IDF + KMeans for only those rows where related_series is empty
- Outputs:
    *_token_freq.csv      : token frequencies
    *_videos_clusters.csv : original + cluster + final_series + method
    *_cluster_terms.csv   : top terms per cluster (interpretability)
"""

import argparse, math, re, logging
from pathlib import Path
from typing import List, Sequence, Set

import numpy as np
import pandas as pd
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# 静音 jieba 日志
jieba.setLogLevel(logging.WARNING)

STOPWORDS: Set[str] = set()

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser("Clustering with hard labels from related_series")
    p.add_argument("--input", required=True, help="Input CSV (utf-8 recommended)")
    p.add_argument("--encoding", default="utf-8")
    p.add_argument("--text-cols", nargs="+",
                   default=["title", "tags", "bgm", "co_operators"],
                   help="Columns used to build text")
    p.add_argument("--keep-cols", nargs="*", default=[],
                   help="Extra columns to keep in output (e.g., link_id platform pubdate)")
    p.add_argument("--related-col", default="related_series",
                   help="Column name for hard labels (same value => same class)")
    p.add_argument("--user-dict", help="jieba user dict file")
    p.add_argument("--stopwords", help="stopwords file (one token per line)")
    p.add_argument("--k", type=int, default=6, help="Num clusters for unlabeled rows")
    p.add_argument("--auto-k", nargs="*", type=int,
                   help="Try multiple K and pick best silhouette for unlabeled rows")
    p.add_argument("--min-df", type=int, default=1)
    p.add_argument("--max-features", type=int, default=8000)
    p.add_argument("--output-prefix", required=True, help="Output file prefix")
    return p.parse_args()

def load_stopwords(path: str | None) -> Set[str]:
    sw = set()
    if not path: return sw
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            t = line.strip()
            if t: sw.add(t)
    return sw

def normalize_text(s: str) -> str:
    if not isinstance(s, str): return ""
    s = s.strip()
    s = re.sub(r"[|/_;、，。！？：:\t]+", " ", s)  # 常见分隔符替换为空格
    s = re.sub(r"\s+", " ", s)
    return s

def build_text(df: pd.DataFrame, cols: Sequence[str]) -> pd.Series:
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df[cols].astype(str).agg(" ".join, axis=1).map(normalize_text)

def jieba_tokenizer(text: str) -> List[str]:
    tokens = []
    for w in jieba.cut(text, HMM=False):
        w = w.strip()
        if not w: continue
        if w in STOPWORDS: continue
        if w.startswith("#"):
            if len(w) >= 2 and w not in STOPWORDS:
                tokens.append(w)
            continue
        if len(w) >= 2:
            tokens.append(w)
    return tokens

def top_terms_per_cluster(X, labels, feature_names, topk=15) -> pd.DataFrame:
    rows = []
    for k in sorted(set(labels)):
        mask = (labels == k)
        if mask.sum() == 0:
            rows.append({"cluster": k, "top_terms": ""})
            continue
        centroid = X[mask].mean(axis=0).A1
        idx = centroid.argsort()[::-1][:topk]
        terms = [feature_names[i] for i in idx]
        rows.append({"cluster": k, "top_terms": " | ".join(terms)})
    return pd.DataFrame(rows)

def choose_k_auto(X, k_list: Sequence[int]) -> int:
    best_k, best_score = None, -1.0
    for k in k_list:
        if k <= 1 or k >= X.shape[0]:
            continue
        km = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = km.fit_predict(X)
        try:
            score = silhouette_score(X, labels, sample_size=min(2000, X.shape[0]))
        except Exception:
            score = float("nan")
        if not math.isnan(score) and score > best_score:
            best_k, best_score = k, score
    return best_k or k_list[0]

def main():
    args = parse_args()

    # 1) 载入用户词典（可选）
    if args.user_dict:
        try:
            jieba.load_userdict(args.user_dict)
        except Exception:
            with open(args.user_dict, "r", encoding="utf-8") as f:
                for line in f:
                    w = line.strip().split()[0]
                    if w: jieba.add_word(w)

    # 2) 读数据
    df = pd.read_csv(args.input, encoding=args.encoding)
    related_col = args.related_col if args.related_col in df.columns else "related_series"
    if related_col not in df.columns:
        df[related_col] = pd.NA

    # 3) 自动把 related_series 值 和 tags 里的话题 加入 jieba 词典
    rs_vals = (
        df[related_col]
        .where(df[related_col].notna(), None)
        .astype(str)
        .map(lambda s: s.strip())
        .replace({"": None})
        .dropna()
        .unique()
    )
    for v in rs_vals:
        try: jieba.add_word(v)
        except: pass

    if "tags" in df.columns:
        tag_terms = set()
        for t in df["tags"].fillna("").astype(str):
            for m in re.findall(r"#([\u4e00-\u9fa5A-Za-z0-9_]+)", t):
                if m.strip(): tag_terms.add(m.strip())
        for w in tag_terms:
            try: jieba.add_word(w)
            except: pass

    # 4) 停用词
    global STOPWORDS
    STOPWORDS = load_stopwords(args.stopwords)

    # 5) 文本构建
    text_all = build_text(df, args.text_cols)

    # 6) 词频统计
    cv = CountVectorizer(
        analyzer="word",
        tokenizer=jieba_tokenizer,
        token_pattern=None,
        min_df=args.min_df,
        max_features=max(5000, args.max_features // 2),
    )
    X_count_all = cv.fit_transform(text_all)
    vocab_count = cv.get_feature_names_out()
    token_freq = X_count_all.sum(axis=0).A1
    freq_df = pd.DataFrame({"token": vocab_count, "count": token_freq}).sort_values("count", ascending=False)

    # 7) 划分已标注/未标注
    is_labeled = df[related_col].notna() & (df[related_col].astype(str).str.strip() != "")
    labeled_df = df[is_labeled].copy()
    unlabeled_df = df[~is_labeled].copy()

    # 8) 聚类未标注
    if not unlabeled_df.empty:
        text_unlab = build_text(unlabeled_df, args.text_cols)
        tfidf = TfidfVectorizer(
            analyzer="word",
            tokenizer=jieba_tokenizer,
            token_pattern=None,
            min_df=args.min_df,
            max_features=args.max_features,
        )
        X_unlab = tfidf.fit_transform(text_unlab)
        feature_names = tfidf.get_feature_names_out()

        if args.auto_k:
            k = choose_k_auto(X_unlab, args.auto_k)
        else:
            k = min(max(2, args.k), X_unlab.shape[0]) if X_unlab.shape[0] > 1 else 1

        if k > 1 and X_unlab.shape[0] >= k:
            km = KMeans(n_clusters=k, n_init=20, random_state=42)
            labels_unlab = km.fit_predict(X_unlab)
            top_terms = top_terms_per_cluster(X_unlab, labels_unlab, feature_names, topk=15)
        else:
            labels_unlab = np.zeros(X_unlab.shape[0], dtype=int)
            top_terms = pd.DataFrame([{"cluster": 0, "top_terms": ""}])
        unlabeled_df["cluster"] = labels_unlab
        unlabeled_df["final_series"] = "cluster_" + unlabeled_df["cluster"].astype(str)
        unlabeled_df["method"] = "cluster"
    else:
        unlabeled_df["cluster"] = pd.Series(dtype=int)
        unlabeled_df["final_series"] = pd.Series(dtype=str)
        unlabeled_df["method"] = pd.Series(dtype=str)
        top_terms = pd.DataFrame(columns=["cluster", "top_terms"])

    # 9) 已标注样本
    if labeled_df.empty:
        labeled_df["cluster"] = pd.Series(dtype=object)
    labeled_df["final_series"] = labeled_df[related_col].astype(str).str.strip()
    labeled_df["method"] = "rule"

    # 10) 合并与导出
    out_df = pd.concat([labeled_df, unlabeled_df], axis=0).sort_index()

    prefix = Path(args.output_prefix)
    token_out = prefix.with_name(prefix.name + "_token_freq.csv")
    clusters_out = prefix.with_name(prefix.name + "_videos_clusters.csv")
    terms_out = prefix.with_name(prefix.name + "_cluster_terms.csv")
    token_out.parent.mkdir(parents=True, exist_ok=True)

    freq_df.to_csv(token_out, index=False, encoding="utf-8")

    base_cols = list(dict.fromkeys([*args.keep_cols, *args.text_cols]))
    base_cols = [c for c in base_cols if c in out_df.columns]
    export_cols = base_cols + [related_col, "cluster", "final_series", "method"]
    out_df.to_csv(clusters_out, index=False, encoding="utf-8", columns=[c for c in export_cols if c in out_df.columns])

    top_terms.to_csv(terms_out, index=False, encoding="utf-8")

    n_clusters = len(sorted(set(unlabeled_df["cluster"]))) if not unlabeled_df.empty else 0
    if n_clusters > 0:
        print(f"[INFO] Unlabeled rows clustered into {n_clusters} clusters.")
    else:
        print("[INFO] No unlabeled rows or clustering not required.")
    print(f"[OK] Saved:\n - Token freq:       {token_out}\n - Videos clusters:  {clusters_out}\n - Cluster topterms: {terms_out}")

if __name__ == "__main__":
    main()
