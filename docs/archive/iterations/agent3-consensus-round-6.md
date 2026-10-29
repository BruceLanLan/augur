# Agent3 Consensus QA — Round 6

**Focus:** Consensus weighting observability in metadata

## Fix

- `registry.py` `get_consensus`: export `metadata.weighting` with `industry`, `industry_label`, `regime`, `participating_agents`, `agent_weights`

## Tests

- `test_get_consensus_uses_consensus_modules` asserts weighting block
- `test_consensus_block_present_and_well_formed` asserts API returns `metadata.weighting`

## Pytest

**Result:** integration metadata assertions green
