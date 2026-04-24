from dataclasses import dataclass

from app.core.config import get_settings
from app.models.schemas import AnswerSource, Citation, EvidenceStrength, SearchResult
from app.utils.text import preprocess_text


settings = get_settings()


@dataclass(frozen=True)
class EvidenceAssessment:
    evidence_strength: EvidenceStrength
    evidence_score: int
    evidence_reasons: list[str]
    evidence_warnings: list[str]


class EvidenceService:
    def assess(
        self,
        question: str,
        citations: list[Citation],
        supporting_chunks: list[SearchResult],
        answer_source: AnswerSource,
        answer: str = "",
    ) -> EvidenceAssessment:
        if not citations or not supporting_chunks:
            return EvidenceAssessment(
                evidence_strength="insufficient",
                evidence_score=0,
                evidence_reasons=["No citations or supporting chunks were available."],
                evidence_warnings=["The answer is not grounded in retrieved evidence."],
            )

        question_terms = set(preprocess_text(question))
        top_score = max(chunk.score for chunk in supporting_chunks)
        avg_top_score = sum(chunk.score for chunk in supporting_chunks[:3]) / max(len(supporting_chunks[:3]), 1)
        matched_terms = {term for chunk in supporting_chunks for term in chunk.matched_terms}
        overlap_ratio = len(question_terms & matched_terms) / max(len(question_terms), 1)
        document_diversity = len({chunk.document_id for chunk in supporting_chunks})
        citation_coverage = min(len(citations) / max(len(supporting_chunks), 1), 1.0)

        score = 0
        score += min(int(top_score * 35), 35)
        score += min(int(avg_top_score * 20), 20)
        score += min(len(citations) * 8, 20)
        score += min(document_diversity * 5, 10)
        score += int(citation_coverage * 10)
        score += int(overlap_ratio * 15)

        reasons: list[str] = [
            f"Top retrieval score was {top_score:.2f}.",
            f"{len(citations)} citation(s) and {len(supporting_chunks)} supporting chunk(s) were used.",
        ]
        warnings: list[str] = []

        if document_diversity > 1:
            reasons.append(f"Evidence spans {document_diversity} documents.")
        if overlap_ratio >= 0.4:
            reasons.append("Retrieved chunks overlap well with the question terms.")
        elif overlap_ratio > 0:
            warnings.append("Only part of the question wording appears in the supporting chunks.")
        else:
            warnings.append("The retrieved chunks have little direct keyword overlap with the question.")

        if answer_source == "extractive_fallback":
            reasons.append("The answer used extractive fallback, which stays close to source text.")
            score += 5
        elif answer_source == "llm":
            warnings.append("The answer was synthesized, so citations should be reviewed.")
            score -= 5
        elif answer_source == "insufficient_evidence":
            warnings.append("The insufficient-evidence guardrail was triggered.")
            score = min(score, 25)

        if self._has_citation_markers(answer, citations):
            reasons.append("The answer includes explicit citation markers.")
            score += 5
        else:
            warnings.append("The answer does not include explicit citation markers for every claim.")
            score -= 10

        score = max(0, min(100, score))
        strength = self._strength_from_score(score, top_score, len(citations), overlap_ratio, answer_source)
        return EvidenceAssessment(
            evidence_strength=strength,
            evidence_score=score,
            evidence_reasons=reasons,
            evidence_warnings=warnings,
        )

    def _strength_from_score(
        self,
        score: int,
        top_score: float,
        citation_count: int,
        overlap_ratio: float,
        answer_source: AnswerSource,
    ) -> EvidenceStrength:
        if answer_source == "insufficient_evidence" or citation_count == 0:
            return "insufficient"
        if top_score < settings.ask_min_grounded_score:
            return "weak"
        if score >= 78 and citation_count >= 2 and overlap_ratio >= 0.25:
            return "strong"
        if score >= 52:
            return "medium"
        return "weak"

    def _has_citation_markers(self, answer: str, citations: list[Citation]) -> bool:
        if not answer:
            return False
        return any(f"[chunk:{citation.chunk_id}]" in answer for citation in citations)


evidence_service = EvidenceService()
