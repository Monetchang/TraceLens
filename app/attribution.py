import tiktoken
from app.config import OVERLAP_EPSILON

enc = tiktoken.get_encoding("cl100k_base")


def tokenize(text: str) -> list[int]:
    return enc.encode(text)


def compute_ngram_overlap(answer_tokens: list[int], chunk_tokens: list[int], n: int = 3) -> int:
    if len(answer_tokens) < n or len(chunk_tokens) < n:
        return 0
    answer_ngrams = set(tuple(answer_tokens[i:i+n]) for i in range(len(answer_tokens) - n + 1))
    chunk_ngrams = set(tuple(chunk_tokens[i:i+n]) for i in range(len(chunk_tokens) - n + 1))
    overlap_ngrams = answer_ngrams & chunk_ngrams
    return len(overlap_ngrams) * n


def compute_attribution(answer_text: str, chunk_content: str) -> tuple[int, float]:
    answer_tokens = tokenize(answer_text)
    chunk_tokens = tokenize(chunk_content)
    total_answer_tokens = len(answer_tokens)
    if total_answer_tokens == 0:
        return 0, 0.0
    overlap_tokens = compute_ngram_overlap(answer_tokens, chunk_tokens)
    overlap_ratio = overlap_tokens / total_answer_tokens
    return overlap_tokens, overlap_ratio


def is_chunk_used(overlap_ratio: float) -> bool:
    return overlap_ratio > OVERLAP_EPSILON

