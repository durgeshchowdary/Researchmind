import json
from datetime import datetime, timezone

from fastapi import HTTPException

from app.db.session import get_db
from app.models.schemas import (
    AskRequest,
    EvalQuestionCreateRequest,
    EvalQuestionPatchRequest,
    EvalQuestionPublic,
    EvalRunPublic,
    EvalSetCreateRequest,
    EvalSetPublic,
    EvaluationCase,
    EvaluationRunResponse,
    SearchRequest,
)
from app.services.evaluation_benchmark_service import evaluation_benchmark_service
from app.services.workspace_service import workspace_service


class EvaluationDatasetService:
    def create_set(self, payload: EvalSetCreateRequest, user_id: int) -> EvalSetPublic:
        workspace_id = workspace_service.resolve_workspace_id(user_id, payload.workspace_id)
        workspace_service.require_role(user_id, workspace_id, "editor")
        timestamp = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO eval_sets (workspace_id, name, description, created_at) VALUES (?, ?, ?, ?)",
                (workspace_id, payload.name.strip(), payload.description, timestamp),
            )
            conn.commit()
        return self.get_set(int(cursor.lastrowid), user_id)

    def list_sets(self, user_id: int, workspace_id: int | None = None) -> list[EvalSetPublic]:
        resolved = workspace_service.resolve_workspace_id(user_id, workspace_id)
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM eval_sets WHERE workspace_id = ? ORDER BY datetime(created_at) DESC",
                (resolved,),
            ).fetchall()
        return [self.get_set(int(row["id"]), user_id) for row in rows]

    def get_set(self, eval_set_id: int, user_id: int) -> EvalSetPublic:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM eval_sets WHERE id = ?", (eval_set_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Evaluation set not found.")
        workspace_service.require_role(user_id, int(row["workspace_id"]), "viewer")
        return self._set_from_row(row, self._questions_for_set(eval_set_id))

    def add_question(self, eval_set_id: int, payload: EvalQuestionCreateRequest, user_id: int) -> EvalQuestionPublic:
        eval_set = self.get_set(eval_set_id, user_id)
        workspace_service.require_role(user_id, eval_set.workspace_id, "editor")
        timestamp = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO eval_questions (
                    eval_set_id, workspace_id, question, expected_answer, expected_terms,
                    expected_document_ids, expected_citation_chunk_ids, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eval_set_id,
                    eval_set.workspace_id,
                    payload.question,
                    payload.expected_answer,
                    json.dumps(payload.expected_terms),
                    json.dumps(payload.expected_document_ids),
                    json.dumps(payload.expected_citation_chunk_ids),
                    timestamp,
                    timestamp,
                ),
            )
            conn.commit()
        return self.get_question(int(cursor.lastrowid), user_id)

    def get_question(self, question_id: int, user_id: int) -> EvalQuestionPublic:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM eval_questions WHERE id = ?", (question_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Evaluation question not found.")
        workspace_service.require_role(user_id, int(row["workspace_id"]), "viewer")
        return self._question_from_row(row)

    def patch_question(self, question_id: int, payload: EvalQuestionPatchRequest, user_id: int) -> EvalQuestionPublic:
        question = self.get_question(question_id, user_id)
        workspace_service.require_role(user_id, question.workspace_id, "editor")
        values = question.model_dump()
        for key, value in payload.model_dump(exclude_unset=True).items():
            values[key] = value
        with get_db() as conn:
            conn.execute(
                """
                UPDATE eval_questions
                SET question = ?, expected_answer = ?, expected_terms = ?, expected_document_ids = ?,
                    expected_citation_chunk_ids = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    values["question"],
                    values["expected_answer"],
                    json.dumps(values["expected_terms"]),
                    json.dumps(values["expected_document_ids"]),
                    json.dumps(values["expected_citation_chunk_ids"]),
                    datetime.now(timezone.utc).isoformat(),
                    question_id,
                ),
            )
            conn.commit()
        return self.get_question(question_id, user_id)

    def delete_question(self, question_id: int, user_id: int) -> dict[str, str]:
        question = self.get_question(question_id, user_id)
        workspace_service.require_role(user_id, question.workspace_id, "editor")
        with get_db() as conn:
            conn.execute("DELETE FROM eval_questions WHERE id = ?", (question_id,))
            conn.commit()
        return {"status": "deleted"}

    async def run_set(self, eval_set_id: int, user_id: int) -> EvalRunPublic:
        eval_set = self.get_set(eval_set_id, user_id)
        cases = [
            EvaluationCase(
                question=question.question,
                expected_terms=question.expected_terms,
                expected_document_titles=[],
                expected_citation_chunk_ids=question.expected_citation_chunk_ids,
                ideal_answer_summary=question.expected_answer,
            )
            for question in eval_set.questions
        ]
        response = await evaluation_benchmark_service.run_cases(cases, user_id, eval_set.workspace_id)
        timestamp = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO eval_runs (eval_set_id, workspace_id, summary_json, created_at) VALUES (?, ?, ?, ?)",
                (eval_set_id, eval_set.workspace_id, response.summary.model_dump_json(), timestamp),
            )
            run_id = int(cursor.lastrowid)
            for question, result in zip(eval_set.questions, response.results):
                conn.execute(
                    "INSERT INTO eval_run_results (run_id, question_id, result_json) VALUES (?, ?, ?)",
                    (run_id, question.id, result.model_dump_json()),
                )
            conn.commit()
        return self.get_run(run_id, user_id)

    def get_run(self, run_id: int, user_id: int) -> EvalRunPublic:
        with get_db() as conn:
            run = conn.execute("SELECT * FROM eval_runs WHERE id = ?", (run_id,)).fetchone()
            if not run:
                raise HTTPException(status_code=404, detail="Evaluation run not found.")
            workspace_service.require_role(user_id, int(run["workspace_id"]), "viewer")
            results = conn.execute("SELECT * FROM eval_run_results WHERE run_id = ? ORDER BY id", (run_id,)).fetchall()
        from app.models.schemas import EvaluationQuestionResult, EvaluationSummary

        return EvalRunPublic(
            id=int(run["id"]),
            eval_set_id=int(run["eval_set_id"]),
            workspace_id=int(run["workspace_id"]),
            summary=EvaluationSummary.model_validate_json(str(run["summary_json"])),
            results=[EvaluationQuestionResult.model_validate_json(str(row["result_json"])) for row in results],
            created_at=datetime.fromisoformat(str(run["created_at"])),
        )

    def list_runs(self, eval_set_id: int, user_id: int) -> list[EvalRunPublic]:
        eval_set = self.get_set(eval_set_id, user_id)
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id FROM eval_runs WHERE eval_set_id = ? AND workspace_id = ? ORDER BY datetime(created_at) DESC",
                (eval_set_id, eval_set.workspace_id),
            ).fetchall()
        return [self.get_run(int(row["id"]), user_id) for row in rows]

    def _questions_for_set(self, eval_set_id: int) -> list[EvalQuestionPublic]:
        with get_db() as conn:
            rows = conn.execute("SELECT * FROM eval_questions WHERE eval_set_id = ? ORDER BY id", (eval_set_id,)).fetchall()
        return [self._question_from_row(row) for row in rows]

    def _set_from_row(self, row, questions: list[EvalQuestionPublic]) -> EvalSetPublic:
        return EvalSetPublic(
            id=int(row["id"]),
            workspace_id=int(row["workspace_id"]),
            name=str(row["name"]),
            description=str(row["description"]) if row["description"] else None,
            created_at=datetime.fromisoformat(str(row["created_at"])),
            questions=questions,
        )

    def _question_from_row(self, row) -> EvalQuestionPublic:
        return EvalQuestionPublic(
            id=int(row["id"]),
            eval_set_id=int(row["eval_set_id"]),
            workspace_id=int(row["workspace_id"]),
            question=str(row["question"]),
            expected_answer=str(row["expected_answer"]) if row["expected_answer"] else None,
            expected_terms=json.loads(row["expected_terms"] or "[]"),
            expected_document_ids=json.loads(row["expected_document_ids"] or "[]"),
            expected_citation_chunk_ids=json.loads(row["expected_citation_chunk_ids"] or "[]"),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )


evaluation_dataset_service = EvaluationDatasetService()
