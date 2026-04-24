from collections import Counter, defaultdict
from math import log


class RankingService:
    def bm25_score(
        self,
        query_terms: list[str],
        inverted_index: dict[str, dict[int, int]],
        doc_freqs: dict[str, int],
        chunk_lengths: dict[int, int],
        avg_chunk_length: float,
        *,
        limit: int,
        k1: float = 1.5,
        b: float = 0.75,
        title_matches: dict[int, float] | None = None,
        title_boost: float = 0.0,
    ) -> list[tuple[int, float]]:
        if not query_terms or not chunk_lengths:
            return []

        total_docs = len(chunk_lengths)
        scores: dict[int, float] = defaultdict(float)

        query_term_counts = Counter(query_terms)

        for term, query_tf in query_term_counts.items():
            postings = inverted_index.get(term)
            if not postings:
                continue
            df = doc_freqs.get(term, 0)
            idf = log(1 + ((total_docs - df + 0.5) / (df + 0.5)))
            for chunk_id, tf in postings.items():
                doc_length = chunk_lengths.get(chunk_id, 0) or 1
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_length / max(avg_chunk_length, 1)))
                scores[chunk_id] += idf * (numerator / denominator) * (1 + log(1 + query_tf))

        if title_matches and title_boost:
            for chunk_id, boost in title_matches.items():
                if chunk_id in scores:
                    scores[chunk_id] += boost * title_boost

        return sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]

    def normalize_scores(self, scored_items: list[tuple[int, float]]) -> dict[int, float]:
        if not scored_items:
            return {}
        values = [score for _, score in scored_items]
        minimum = min(values)
        maximum = max(values)
        if maximum == minimum:
            return {item_id: 1.0 for item_id, _ in scored_items}
        return {
            item_id: (score - minimum) / (maximum - minimum)
            for item_id, score in scored_items
        }

    def fuse_scores(
        self,
        bm25_scores: list[tuple[int, float]],
        semantic_scores: list[tuple[int, float]],
        *,
        bm25_weight: float,
        semantic_weight: float,
        limit: int,
    ) -> list[tuple[int, float, float, float]]:
        normalized_bm25 = self.normalize_scores(bm25_scores)
        normalized_semantic = self.normalize_scores(semantic_scores)
        all_ids = set(normalized_bm25) | set(normalized_semantic)
        combined = [
            (
                chunk_id,
                normalized_bm25.get(chunk_id, 0.0) * bm25_weight
                + normalized_semantic.get(chunk_id, 0.0) * semantic_weight,
                normalized_bm25.get(chunk_id),
                normalized_semantic.get(chunk_id),
            )
            for chunk_id in all_ids
        ]
        combined.sort(key=lambda item: item[1], reverse=True)
        return combined[:limit]


ranking_service = RankingService()
