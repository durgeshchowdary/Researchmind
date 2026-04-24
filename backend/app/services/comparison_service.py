from collections import Counter, defaultdict

from app.models.schemas import (
    ChunkRecord,
    Citation,
    CompareRequest,
    CompareResponse,
    ComparisonPoint,
    DocumentDetail,
    SearchExplanation,
    SearchRequest,
    SearchResult,
)
from app.services.document_service import document_service
from app.services.evidence_service import evidence_service
from app.services.search_service import search_service
from app.utils.text import highlight_terms, make_snippet, preprocess_text


class ComparisonService:
    def compare(self, payload: CompareRequest, user_id: int | None = None) -> CompareResponse:
        document_ids = list(dict.fromkeys(payload.document_ids))
        if len(document_ids) < 2 or len(document_ids) > 4:
            raise ValueError("Select between 2 and 4 documents to compare.")

        documents = [document_service.get_document_detail(document_id, user_id) for document_id in document_ids]
        if any(document is None for document in documents):
            raise ValueError("One or more selected documents could not be found.")
        selected_documents = [document for document in documents if document is not None]

        supporting_results, warnings = self._supporting_results(selected_documents, payload.question, user_id)
        citations = [self._citation_from_result(result) for result in supporting_results]
        theme_map = {document.id: self._top_terms(document) for document in selected_documents}
        chunk_lookup = self._chunk_lookup(supporting_results)

        agreements = self._agreements(theme_map, chunk_lookup, selected_documents)
        unique_points = self._unique_points(theme_map, chunk_lookup, selected_documents)
        differences = self._differences(theme_map, chunk_lookup, selected_documents)
        summary = self._summary(payload.question, selected_documents, agreements, differences, unique_points, citations)
        assessment = evidence_service.assess(
            payload.question or summary,
            citations,
            supporting_results,
            "extractive_fallback",
            summary,
        )

        if not supporting_results:
            warnings.append("No searchable chunks were available for the selected documents.")
        if payload.question and not citations:
            warnings.append("No retrieved evidence matched the comparison question.")

        return CompareResponse(
            comparison_summary=summary,
            agreements=agreements,
            differences=differences,
            unique_points=unique_points,
            citations=citations,
            evidence_strength=assessment.evidence_strength,
            evidence_score=assessment.evidence_score,
            evidence_reasons=assessment.evidence_reasons,
            evidence_warnings=assessment.evidence_warnings,
            warnings=warnings,
        )

    def _supporting_results(
        self,
        documents: list[DocumentDetail],
        question: str | None,
        user_id: int | None,
    ) -> tuple[list[SearchResult], list[str]]:
        results: list[SearchResult] = []
        warnings: list[str] = []
        if question and question.strip():
            for document in documents:
                response = search_service.hybrid_search(
                    SearchRequest(query=question, limit=6, document_id=document.id),
                    user_id=user_id,
                )
                warnings.extend(response.warnings)
                results.extend(response.results[:3])

            allowed = {document.id for document in documents}
            filtered = [result for result in results if result.document_id in allowed]
            if filtered:
                return self._dedupe_results(filtered)[:10], list(dict.fromkeys(warnings))

        fallback_results: list[SearchResult] = []
        query_terms = preprocess_text(question or " ".join(term for document in documents for term in self._top_terms(document)[:4]))
        for document in documents:
            chunks = sorted(document.chunks, key=lambda chunk: chunk.token_count, reverse=True)[:2]
            for chunk in chunks:
                fallback_results.append(self._result_from_chunk(document, chunk, query_terms))
        return fallback_results[:10], list(dict.fromkeys(warnings))

    def _result_from_chunk(self, document: DocumentDetail, chunk: ChunkRecord, query_terms: list[str]) -> SearchResult:
        snippet = make_snippet(chunk.text, 260)
        matched_terms = sorted(set(query_terms) & set(preprocess_text(chunk.text)))
        score = 0.55 + min(len(matched_terms) * 0.06, 0.25)
        return SearchResult(
            chunk_id=chunk.id,
            document_id=document.id,
            document_title=document.title,
            chunk_index=chunk.chunk_index,
            page_number=chunk.page_number,
            score=round(score, 4),
            keyword_score=round(score, 4),
            semantic_score=None,
            snippet=snippet,
            highlighted_snippet=highlight_terms(snippet, matched_terms) if matched_terms else snippet,
            raw_text=chunk.text,
            matched_terms=matched_terms,
            retrieval_mode="keyword",
            explanation=SearchExplanation(
                keyword_overlap=matched_terms,
                semantic_match=False,
                title_match=False,
                keyword_score=round(score, 4),
                semantic_score=None,
                hybrid_score=round(score, 4),
                title_boost_applied=False,
                score_breakdown=[f"Theme overlap terms: {', '.join(matched_terms[:5])}" if matched_terms else "Selected as representative document text."],
                summary="representative chunk selected for document comparison",
            ),
        )

    def _citation_from_result(self, result: SearchResult) -> Citation:
        return Citation(
            chunk_id=result.chunk_id,
            document_id=result.document_id,
            document_title=result.document_title,
            chunk_index=result.chunk_index,
            chunk_text_snippet=result.snippet,
            supporting_chunk_text=result.raw_text,
            highlighted_snippet=result.highlighted_snippet,
            matched_terms=result.matched_terms,
            explanation_summary=result.explanation.summary,
            page_number=result.page_number,
        )

    def _top_terms(self, document: DocumentDetail) -> list[str]:
        text = " ".join(chunk.text for chunk in document.chunks[:10])
        counts = Counter(preprocess_text(text))
        return [term for term, count in counts.most_common(12) if count >= 1 and len(term) > 2]

    def _chunk_lookup(self, results: list[SearchResult]) -> dict[int, list[SearchResult]]:
        lookup: dict[int, list[SearchResult]] = defaultdict(list)
        for result in results:
            lookup[result.document_id].append(result)
        return lookup

    def _agreements(
        self,
        theme_map: dict[int, list[str]],
        chunk_lookup: dict[int, list[SearchResult]],
        documents: list[DocumentDetail],
    ) -> list[ComparisonPoint]:
        term_documents: dict[str, set[int]] = defaultdict(set)
        for document_id, terms in theme_map.items():
            for term in terms[:10]:
                term_documents[term].add(document_id)

        points: list[ComparisonPoint] = []
        title_by_id = {document.id: document.title for document in documents}
        for term, ids in sorted(term_documents.items(), key=lambda item: (-len(item[1]), item[0])):
            if len(ids) < 2:
                continue
            chunk_ids = self._supporting_chunk_ids(ids, chunk_lookup)
            names = ", ".join(title_by_id[document_id] for document_id in sorted(ids))
            points.append(
                ComparisonPoint(
                    text=f"{names} share a recurring theme around \"{term}\".",
                    document_ids=sorted(ids),
                    supporting_chunk_ids=chunk_ids,
                    confidence=min(92, 58 + len(ids) * 10 + len(chunk_ids) * 3),
                    type="agreement",
                )
            )
            if len(points) >= 4:
                break
        return points

    def _unique_points(
        self,
        theme_map: dict[int, list[str]],
        chunk_lookup: dict[int, list[SearchResult]],
        documents: list[DocumentDetail],
    ) -> list[ComparisonPoint]:
        all_terms = Counter(term for terms in theme_map.values() for term in set(terms[:10]))
        points: list[ComparisonPoint] = []
        for document in documents:
            unique_terms = [term for term in theme_map[document.id] if all_terms[term] == 1]
            if not unique_terms:
                continue
            chunk_ids = self._supporting_chunk_ids({document.id}, chunk_lookup)
            points.append(
                ComparisonPoint(
                    text=f"{document.title} has distinctive emphasis on {', '.join(unique_terms[:3])}.",
                    document_ids=[document.id],
                    supporting_chunk_ids=chunk_ids,
                    confidence=min(88, 56 + len(unique_terms[:3]) * 8),
                    type="unique",
                )
            )
        return points[:6]

    def _differences(
        self,
        theme_map: dict[int, list[str]],
        chunk_lookup: dict[int, list[SearchResult]],
        documents: list[DocumentDetail],
    ) -> list[ComparisonPoint]:
        points: list[ComparisonPoint] = []
        all_terms = Counter(term for terms in theme_map.values() for term in set(terms[:10]))
        for first, second in zip(documents, documents[1:]):
            first_unique = [term for term in theme_map[first.id] if all_terms[term] == 1][:2]
            second_unique = [term for term in theme_map[second.id] if all_terms[term] == 1][:2]
            if not first_unique or not second_unique:
                continue
            ids = {first.id, second.id}
            points.append(
                ComparisonPoint(
                    text=(
                        f"{first.title} leans toward {', '.join(first_unique)}, "
                        f"while {second.title} leans toward {', '.join(second_unique)}."
                    ),
                    document_ids=sorted(ids),
                    supporting_chunk_ids=self._supporting_chunk_ids(ids, chunk_lookup),
                    confidence=72,
                    type="difference",
                )
            )
        return points[:4]

    def _summary(
        self,
        question: str | None,
        documents: list[DocumentDetail],
        agreements: list[ComparisonPoint],
        differences: list[ComparisonPoint],
        unique_points: list[ComparisonPoint],
        citations: list[Citation],
    ) -> str:
        names = ", ".join(document.title for document in documents)
        focus = f" for \"{question.strip()}\"" if question and question.strip() else ""
        cited = f" using {len(citations)} cited chunk(s)" if citations else ""
        pieces = [f"Compared {len(documents)} documents{focus}: {names}{cited}."]
        if agreements:
            pieces.append(f"Shared themes include {self._compact_terms(agreements[0].text)}.")
        if differences:
            pieces.append("The strongest differences come from the documents' distinct recurring themes.")
        if unique_points:
            pieces.append("Each document also has at least one distinctive emphasis worth reviewing.")
        if citations:
            pieces.append(" ".join(f"[chunk:{citation.chunk_id}]" for citation in citations[:3]))
        return " ".join(pieces)

    def _compact_terms(self, text: str) -> str:
        return text.replace(" share a recurring theme around ", ": ").replace("\"", "")

    def _supporting_chunk_ids(self, document_ids: set[int], chunk_lookup: dict[int, list[SearchResult]]) -> list[int]:
        chunk_ids: list[int] = []
        for document_id in sorted(document_ids):
            for result in chunk_lookup.get(document_id, [])[:2]:
                if result.chunk_id not in chunk_ids:
                    chunk_ids.append(result.chunk_id)
        return chunk_ids[:6]

    def _dedupe_results(self, results: list[SearchResult]) -> list[SearchResult]:
        seen: set[int] = set()
        deduped: list[SearchResult] = []
        for result in sorted(results, key=lambda item: item.score, reverse=True):
            if result.chunk_id in seen:
                continue
            seen.add(result.chunk_id)
            deduped.append(result)
        return deduped


comparison_service = ComparisonService()
