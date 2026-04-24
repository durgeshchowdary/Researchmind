from app.models.schemas import ClaimVerification, SearchResult
from app.utils.text import make_snippet, preprocess_text, sentence_split


class ClaimVerificationService:
    def verify(self, answer: str, supporting_chunks: list[SearchResult], insufficient_evidence: bool = False) -> list[ClaimVerification]:
        claims = self._extract_claims(answer)
        if insufficient_evidence:
            return [
                ClaimVerification(
                    claim=claim,
                    status="unsupported",
                    confidence=0,
                    evidence_chunk_ids=[],
                    evidence_snippets=[],
                    reason="The answer was produced by the insufficient-evidence guardrail.",
                )
                for claim in claims
            ]

        verifications: list[ClaimVerification] = []
        for claim in claims:
            claim_terms = set(preprocess_text(claim))
            scored: list[tuple[float, SearchResult, list[str]]] = []
            for chunk in supporting_chunks:
                chunk_terms = set(preprocess_text(chunk.raw_text))
                overlap = sorted(claim_terms & chunk_terms)
                overlap_ratio = len(overlap) / max(len(claim_terms), 1)
                phrase_bonus = 0.2 if claim.lower()[:80] in chunk.raw_text.lower() else 0.0
                scored.append((overlap_ratio + phrase_bonus + min(chunk.score, 1.0) * 0.15, chunk, overlap))

            scored.sort(key=lambda item: item[0], reverse=True)
            best_score, best_chunk, best_overlap = scored[0] if scored else (0.0, None, [])
            if best_score >= 0.48 and len(best_overlap) >= 3:
                status = "supported"
                confidence = min(100, int(best_score * 100))
                reason = "The claim has strong lexical overlap with retrieved evidence."
            elif best_score >= 0.24 and len(best_overlap) >= 1:
                status = "partially_supported"
                confidence = min(78, max(35, int(best_score * 100)))
                reason = "The claim is only partially covered by the retrieved evidence."
            else:
                status = "unsupported"
                confidence = max(0, min(30, int(best_score * 100)))
                reason = "No supporting chunk clearly backs this claim."

            evidence_chunks = [item[1] for item in scored[:2] if item[0] >= 0.18 and item[1] is not None]
            verifications.append(
                ClaimVerification(
                    claim=claim,
                    status=status,
                    confidence=confidence,
                    evidence_chunk_ids=[chunk.chunk_id for chunk in evidence_chunks],
                    evidence_snippets=[make_snippet(chunk.raw_text, 220) for chunk in evidence_chunks],
                    reason=reason,
                )
            )
        return verifications

    def _extract_claims(self, answer: str) -> list[str]:
        claims: list[str] = []
        for sentence in sentence_split(answer):
            cleaned = sentence.strip()
            if "[chunk:" in cleaned:
                cleaned = cleaned.split("[chunk:", 1)[0].strip()
            if len(cleaned) < 28:
                continue
            lower = cleaned.lower()
            if lower.startswith(("i could not find", "the available evidence is too weak")):
                continue
            claims.append(cleaned)
        return claims[:8]


claim_verification_service = ClaimVerificationService()
