"""
Fact Checker - No LLM, low cost
Compares LLM output against a source URL using NLP techniques.

Returns:
    fact_score     : float 0.0 - 1.0  (1.0 = fully supported)
    reason_for_score: str  (what matched / what didn't)
    mitigation      : str  (what to fix or verify)
"""

import re
import requests
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────
# Data model  (maps directly to your DB columns)
# ─────────────────────────────────────────────
@dataclass
class FactCheckResult:
    fact_score: float           # 0.0 – 1.0
    reason_for_score: str       # human-readable explanation
    mitigation: str             # what the user / system should do
    # bonus fields (optional – store or discard as you like)
    matched_claims: list[str]   # sentences in LLM output supported by source
    unmatched_claims: list[str] # sentences NOT found in source


# ─────────────────────────────────────────────
# 1. Fetch & clean source page
# ─────────────────────────────────────────────
def fetch_source_text(url: str, timeout: int = 10) -> str:
    """Download URL, strip HTML tags, return plain text."""
    headers = {"User-Agent": "Mozilla/5.0 (FactChecker/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Could not fetch URL: {e}")

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove noise tags
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ─────────────────────────────────────────────
# 2. Split text into sentences (no NLTK needed)
# ─────────────────────────────────────────────
def split_sentences(text: str) -> list[str]:
    """Simple regex sentence splitter."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 20]


# ─────────────────────────────────────────────
# 3. Core scoring logic
# ─────────────────────────────────────────────
SIMILARITY_THRESHOLD = 0.35   # tune this (0.25 = loose, 0.45 = strict)

def score_claim(claim: str, source_sentences: list[str], vectorizer) -> float:
    """
    Returns the highest cosine similarity between one LLM claim
    and any sentence in the source text.
    """
    try:
        matrix = vectorizer.transform([claim] + source_sentences)
        claim_vec = matrix[0]
        source_vecs = matrix[1:]
        sims = cosine_similarity(claim_vec, source_vecs)[0]
        return float(sims.max())
    except Exception:
        return 0.0


# ─────────────────────────────────────────────
# 4. Number / entity consistency check
# ─────────────────────────────────────────────
def extract_numbers(text: str) -> set[str]:
    """Pull out all numbers, percentages, years, money figures."""
    return set(re.findall(r"\b\d[\d,\.]*(?:%|bn|million|billion|k|USD|EUR)?\b", text))

def check_number_consistency(llm_output: str, source_text: str) -> tuple[float, list[str]]:
    """
    Penalise claims that contain numbers NOT present in source.
    Returns (penalty 0–1, list of suspicious numbers).
    """
    llm_nums = extract_numbers(llm_output)
    src_nums = extract_numbers(source_text)
    if not llm_nums:
        return 0.0, []  # no numbers → no penalty
    missing = llm_nums - src_nums
    penalty = len(missing) / len(llm_nums)
    return penalty, list(missing)


# ─────────────────────────────────────────────
# 5. Main entry point
# ─────────────────────────────────────────────
def fact_check(url: str, llm_output: str) -> FactCheckResult:
    """
    Full pipeline:
        URL  →  fetch  →  compare with llm_output  →  FactCheckResult

    Args:
        url        : source page to verify against
        llm_output : the text produced by the LLM that needs checking
    """

    # --- Fetch source ---
    source_text = fetch_source_text(url)

    # --- Split into chunks ---
    source_sentences = split_sentences(source_text)
    llm_sentences    = split_sentences(llm_output)

    if not source_sentences:
        return FactCheckResult(
            fact_score=0.0,
            reason_for_score="Source page returned no readable text.",
            mitigation="Check if the URL requires login or JavaScript rendering.",
            matched_claims=[],
            unmatched_claims=llm_sentences,
        )

    # --- Fit TF-IDF on ALL text so vocabulary is shared ---
    all_text = source_sentences + llm_sentences
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),   # unigrams + bigrams
        stop_words="english",
        max_features=20_000,
    )
    vectorizer.fit(all_text)

    # --- Score each LLM sentence ---
    matched, unmatched = [], []
    claim_scores = []

    for claim in llm_sentences:
        sim = score_claim(claim, source_sentences, vectorizer)
        claim_scores.append(sim)
        if sim >= SIMILARITY_THRESHOLD:
            matched.append(claim)
        else:
            unmatched.append(claim)

    # --- Base score: fraction of claims supported ---
    base_score = (
        sum(1 for s in claim_scores if s >= SIMILARITY_THRESHOLD) / len(claim_scores)
        if claim_scores else 0.0
    )

    # --- Number consistency penalty ---
    num_penalty, suspicious_nums = check_number_consistency(llm_output, source_text)
    # Apply penalty (up to 30% reduction)
    final_score = round(max(0.0, base_score - 0.30 * num_penalty), 4)

    # ─── Build human-readable fields ───

    # reason_for_score
    pct_matched = round(base_score * 100)
    if final_score >= 0.85:
        label = "STRONG MATCH"
    elif final_score >= 0.60:
        label = "MODERATE MATCH"
    elif final_score >= 0.35:
        label = "WEAK MATCH"
    else:
        label = "LOW SUPPORT"

    reason_parts = [
        f"{label} — {pct_matched}% of LLM claims found in source.",
        f"{len(matched)} / {len(llm_sentences)} sentences supported.",
    ]
    if suspicious_nums:
        reason_parts.append(
            f"Numbers in LLM output not found in source: {', '.join(suspicious_nums[:5])}."
        )
    reason_for_score = " ".join(reason_parts)

    # mitigation
    if final_score >= 0.85:
        mitigation = "No action required. LLM output is well-supported by the source."
    elif final_score >= 0.60:
        mitigation = (
            "Review the following unsupported claims before publishing: "
            + " | ".join(unmatched[:3])
            + ("..." if len(unmatched) > 3 else "")
        )
    elif final_score >= 0.35:
        mitigation = (
            "Several claims could not be verified. Consider re-running with a more "
            "targeted prompt or adding citations. Unsupported claims: "
            + " | ".join(unmatched[:5])
        )
    else:
        mitigation = (
            "LLM output is largely unsupported by the source. "
            "Re-generate with stricter grounding instructions or verify the URL is correct."
        )

    return FactCheckResult(
        fact_score=final_score,
        reason_for_score=reason_for_score,
        mitigation=mitigation,
        matched_claims=matched,
        unmatched_claims=unmatched,
    )


# ─────────────────────────────────────────────
# Quick test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    TEST_URL = "https://en.wikipedia.org/wiki/Python_(programming_language)"
    TEST_LLM_OUTPUT = """
    Python is a high-level, general-purpose programming language.
    It was created by Guido van Rossum and first released in 1991.
    Python supports multiple programming paradigms including structured,
    object-oriented and functional programming. It is dynamically typed.
    Python was invented in 1750 by Napoleon Bonaparte as a military tool.
    """

    print("Running fact check...\n")
    result = fact_check(TEST_URL, TEST_LLM_OUTPUT)

    print(f"fact_score        : {result.fact_score}")
    print(f"reason_for_score  : {result.reason_for_score}")
    print(f"mitigation        : {result.mitigation}")
    print(f"\nMatched ({len(result.matched_claims)})   : {result.matched_claims[:2]}")
    print(f"Unmatched ({len(result.unmatched_claims)}) : {result.unmatched_claims}")