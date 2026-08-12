# -*- coding: utf-8 -*-
"""
tests/test_review_comment.py — E06 Review & Comment tests.

Validates:
  1. add_comment creates a Comment with correct fields.
  2. add_comment auto-generates unique comment_id.
  3. add_comment with explicit comment_id works.
  4. add_comment rejects invalid target_type.
  5. add_comment rejects duplicate comment_id.
  6. resolve marks comment resolved and sets resolved_at.
  7. resolve returns False for already-resolved or missing comment.
  8. reopen returns True for resolved comment and clears resolved_at.
  9. list_by_target filters by target_type and target_id.
 10. list_by_target filters by resolved status.
 11. get_unresolved returns only unresolved comments.
 12. remove_comment deletes and returns True; False for missing.
 13. comment_count and unresolved_count track state correctly.
"""

from __future__ import annotations

import pytest

from augur.review_comment import Comment, ReviewSystem


# ---------------------------------------------------------------------------
# 1. add_comment
# ---------------------------------------------------------------------------

def test_add_comment_creates_comment():
    """add_comment returns a Comment with correct fields."""
    rs = ReviewSystem()
    c = rs.add_comment(
        target_type="claim",
        target_id="c_001",
        author="Alice",
        text="Needs citation.",
    )
    assert isinstance(c, Comment)
    assert c.target_type == "claim"
    assert c.target_id == "c_001"
    assert c.author == "Alice"
    assert c.text == "Needs citation."
    assert c.resolved is False
    assert c.resolved_at is None
    assert len(c.comment_id) > 0
    assert c.created_at  # non-empty ISO timestamp


def test_add_comment_auto_generates_unique_ids():
    """Each comment gets a unique auto-generated id."""
    rs = ReviewSystem()
    c1 = rs.add_comment("claim", "c_001", "A", "t1")
    c2 = rs.add_comment("claim", "c_001", "B", "t2")
    assert c1.comment_id != c2.comment_id


def test_add_comment_with_explicit_id():
    """Explicit comment_id is honoured."""
    rs = ReviewSystem()
    c = rs.add_comment(
        "claim", "c_001", "Alice", "text",
        comment_id="my-id",
    )
    assert c.comment_id == "my-id"


def test_add_comment_rejects_invalid_target_type():
    """target_type must be 'claim' or 'evidence'."""
    rs = ReviewSystem()
    with pytest.raises(ValueError, match="target_type"):
        rs.add_comment("invalid", "id1", "A", "text")


def test_add_comment_rejects_duplicate_id():
    """Explicit duplicate comment_id raises ValueError."""
    rs = ReviewSystem()
    rs.add_comment("claim", "c_001", "A", "t1", comment_id="dup")
    with pytest.raises(ValueError, match="dup"):
        rs.add_comment("claim", "c_002", "B", "t2", comment_id="dup")


# ---------------------------------------------------------------------------
# 2. resolve / reopen
# ---------------------------------------------------------------------------

def test_resolve_marks_comment_resolved():
    """resolve sets resolved=True and resolved_at."""
    rs = ReviewSystem()
    c = rs.add_comment("claim", "c_001", "A", "text")
    assert rs.resolve(c.comment_id) is True
    # Re-fetch
    fetched = rs.get_comment(c.comment_id)
    assert fetched is not None
    assert fetched.resolved is True
    assert fetched.resolved_at is not None


def test_resolve_returns_false_for_already_resolved():
    """Resolving an already-resolved comment returns False."""
    rs = ReviewSystem()
    c = rs.add_comment("claim", "c_001", "A", "text")
    rs.resolve(c.comment_id)
    assert rs.resolve(c.comment_id) is False


def test_resolve_returns_false_for_missing():
    """Resolving a nonexistent id returns False."""
    rs = ReviewSystem()
    assert rs.resolve("nonexistent") is False


def test_reopen_unresolves_comment():
    """reopen clears the resolved flag."""
    rs = ReviewSystem()
    c = rs.add_comment("claim", "c_001", "A", "text")
    rs.resolve(c.comment_id)
    assert rs.reopen(c.comment_id) is True
    fetched = rs.get_comment(c.comment_id)
    assert fetched is not None
    assert fetched.resolved is False
    assert fetched.resolved_at is None


def test_reopen_returns_false_for_unresolved():
    """Reopening an already-unresolved comment returns False."""
    rs = ReviewSystem()
    c = rs.add_comment("claim", "c_001", "A", "text")
    assert rs.reopen(c.comment_id) is False


# ---------------------------------------------------------------------------
# 3. list_by_target / list_all / get_unresolved
# ---------------------------------------------------------------------------

def test_list_by_target_filters_correctly():
    """list_by_target returns only comments for the given target."""
    rs = ReviewSystem()
    rs.add_comment("claim", "c_001", "A", "t1")
    rs.add_comment("claim", "c_002", "B", "t2")
    rs.add_comment("evidence", "e_001", "C", "t3")
    rs.add_comment("claim", "c_001", "D", "t4")

    c001_comments = rs.list_by_target("claim", "c_001")
    assert len(c001_comments) == 2

    c002_comments = rs.list_by_target("claim", "c_002")
    assert len(c002_comments) == 1

    e001_comments = rs.list_by_target("evidence", "e_001")
    assert len(e001_comments) == 1


def test_list_by_target_resolved_filter():
    """list_by_target with resolved filter works."""
    rs = ReviewSystem()
    c1 = rs.add_comment("claim", "c_001", "A", "t1")
    rs.add_comment("claim", "c_001", "B", "t2")
    rs.resolve(c1.comment_id)

    unresolved = rs.list_by_target("claim", "c_001", resolved=False)
    assert len(unresolved) == 1

    resolved_list = rs.list_by_target("claim", "c_001", resolved=True)
    assert len(resolved_list) == 1
    assert resolved_list[0].comment_id == c1.comment_id


def test_get_unresolved():
    """get_unresolved returns all unresolved across all targets."""
    rs = ReviewSystem()
    c1 = rs.add_comment("claim", "c_001", "A", "t1")
    rs.add_comment("claim", "c_002", "B", "t2")
    rs.add_comment("evidence", "e_001", "C", "t3")
    rs.resolve(c1.comment_id)

    unresolved = rs.get_unresolved()
    assert len(unresolved) == 2


def test_list_all():
    """list_all returns all comments."""
    rs = ReviewSystem()
    rs.add_comment("claim", "c_001", "A", "t1")
    rs.add_comment("evidence", "e_001", "B", "t2")
    assert len(rs.list_all()) == 2

    # Filtered
    resolved = rs.list_all(resolved=True)
    assert len(resolved) == 0


# ---------------------------------------------------------------------------
# 4. remove_comment
# ---------------------------------------------------------------------------

def test_remove_comment():
    """remove_comment deletes and returns True; False for missing."""
    rs = ReviewSystem()
    c = rs.add_comment("claim", "c_001", "A", "text")
    assert rs.remove_comment(c.comment_id) is True
    assert rs.get_comment(c.comment_id) is None
    assert rs.remove_comment(c.comment_id) is False


# ---------------------------------------------------------------------------
# 5. Counts
# ---------------------------------------------------------------------------

def test_comment_count_and_unresolved_count():
    """comment_count and unresolved_count track accurately."""
    rs = ReviewSystem()
    assert rs.comment_count == 0
    assert rs.unresolved_count == 0

    c1 = rs.add_comment("claim", "c_001", "A", "t1")
    rs.add_comment("claim", "c_002", "B", "t2")
    assert rs.comment_count == 2
    assert rs.unresolved_count == 2

    rs.resolve(c1.comment_id)
    assert rs.comment_count == 2
    assert rs.unresolved_count == 1
