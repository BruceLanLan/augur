# Agent3 Consensus QA — Round 4

**Focus:** Missing feedback calibration examples

## Fix

- Added `feedback/agent_correlation.json.example` (diversity penalty matrix template)
- Added `feedback/rolling_ic.json.example` (IC weight template)
- Extended `TestFeedbackTemplates::test_example_files_exist_and_parse` to cover all four examples

## Pytest

**Result:** 17/17 in `test_consensus_v10_15.py` green
