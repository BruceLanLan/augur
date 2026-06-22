# Agent3 Consensus QA — Round 3

**Focus:** P1-8 user feedback path (`~/.augur/feedback/`)

## Fix

- `src/augur/consensus/paths.py`: `USER_FEEDBACK_DIR`, user override precedence in `feedback_path()` and `load_feedback_json()`
- `src/augur/consensus/rolling_ic.py`: unified loader via `load_feedback_json("rolling_ic.json")`

## Tests added

- `test_consensus_v10_15.py::test_user_feedback_dir_overrides_repo`
- `test_peer_review_qa_v10_15.py::test_user_feedback_precedence`

## Pytest

**Result:** paths tests green; rolling IC resolves through same feedback stack
