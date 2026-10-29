"""v12: research questions survive a restart (ROADMAP step 15)."""
from augur.questions import QuestionQueue, ResearchQuestion


def _q(text):
    return ResearchQuestion(question_id="", ticker="aapl", question=text, context="", created_at="")


def test_questions_survive_reload(tmp_path):
    path = tmp_path / "thesis" / "questions.json"
    q1 = QuestionQueue(storage_path=path)
    qid = q1.add(_q("Is services growth durable?"))
    q1.add(_q("What changed in the buyback?"))
    q1.answer(qid, run_id="run-1", answer="yes", confidence="medium")

    q2 = QuestionQueue(storage_path=path)
    assert [x.question for x in q2.list("AAPL")] == ["What changed in the buyback?"]
    answered = q2.list("AAPL", status="answered")
    assert answered[0].question_id == qid
    assert answered[0].answered_by_run_id == "run-1"


def test_empty_created_at_gets_timestamp_and_distinct_ids(tmp_path):
    q = QuestionQueue(storage_path=tmp_path / "q.json")
    a = q.add(_q("same text"))
    assert q.list("AAPL")[0].created_at
    assert a.startswith("q_")


def test_in_memory_default_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    q = QuestionQueue()
    q.add(_q("ephemeral"))
    assert list(tmp_path.iterdir()) == []


def test_corrupt_file_starts_empty(tmp_path):
    path = tmp_path / "q.json"
    path.write_text("{not json", encoding="utf-8")
    assert QuestionQueue(storage_path=path).list("") == []


def test_persistent_uses_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AUGUR_DATA_DIR", str(tmp_path))
    q = QuestionQueue.persistent()
    q.add(_q("x"))
    assert (tmp_path / "thesis" / "questions.json").exists()
