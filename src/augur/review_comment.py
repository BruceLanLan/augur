# -*- coding: utf-8 -*-
"""
Review & Comment (E06)
======================

Lightweight review-comment system for claims and evidence produced by
the analysis pipeline.  Supports inline threaded comments with
resolve/reopen semantics.

Provenance: standard code-review / document-annotation patterns
(GitHub review threads, Google Docs comments, Hypothesis annotation).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

#: Kinds of research artifact a comment can be attached to.
TARGET_TYPES = ("claim", "evidence", "run", "thesis", "decision")


# ============================================================================
# Comment
# ============================================================================


@dataclass
class Comment:
    """A single review comment on a claim or evidence item.

    Attributes
    ----------
    comment_id : str
        Unique identifier (UUID4 hex by default).
    target_type : str
        One of :data:`TARGET_TYPES` — the kind of item being commented on.
    target_id : str
        The identifier of the claim or evidence item.
    author : str
        Display name of the comment author.
    text : str
        Comment body (may contain markdown).
    created_at : str
        ISO-8601 UTC timestamp of creation.
    resolved : bool
        Whether the comment thread has been resolved.
    resolved_at : Optional[str]
        ISO-8601 UTC timestamp of resolution, if resolved.
    """

    comment_id: str
    target_type: str
    target_id: str
    author: str
    text: str
    created_at: str
    resolved: bool = False
    resolved_at: Optional[str] = None


# ============================================================================
# ReviewSystem
# ============================================================================


class ReviewSystem:
    """Manage review comments on claims and evidence.

    Usage::

        rs = ReviewSystem()
        c = rs.add_comment(
            target_type="claim",
            target_id="c_abc123",
            author="Alice",
            text="This claim needs a data source citation.",
        )
        rs.resolve(c.comment_id)
        unresolved = rs.list_by_target("claim", "c_abc123", resolved=False)
    """

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        """Create a review system.

        With ``storage_path`` every change is written to that JSON file and
        existing comments are loaded from it; without it comments live only
        in memory (the original behaviour, used by tests and ad-hoc callers).
        Use :meth:`persistent` for the data-dir backed store the CLI uses.
        """
        self._comments: Dict[str, Comment] = {}
        self._path = Path(storage_path) if storage_path is not None else None
        self._load()

    @classmethod
    def persistent(cls) -> "ReviewSystem":
        """Return a store backed by ``get_data_dir() / "review_comments.json"``."""
        from augur.data_dir import get_data_dir

        return cls(storage_path=get_data_dir() / "review_comments.json")

    def _load(self) -> None:
        if self._path is None or not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for item in raw:
            try:
                comment = Comment(**item)
            except TypeError:
                continue
            self._comments[comment.comment_id] = comment

    def _save(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps([asdict(c) for c in self._comments.values()], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self._path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_comment(
        self,
        target_type: str,
        target_id: str,
        author: str,
        text: str,
        *,
        comment_id: Optional[str] = None,
    ) -> Comment:
        """Add a new comment and return it.

        Parameters
        ----------
        target_type : str
            One of :data:`TARGET_TYPES`.
        target_id : str
            The item being commented on.
        author : str
            Display name.
        text : str
            Comment body.
        comment_id : Optional[str]
            Explicit comment id; auto-generated if omitted.

        Raises
        ------
        ValueError
            If *target_type* is not in :data:`TARGET_TYPES`, or
            if the explicit *comment_id* is already in use.
        """
        if target_type not in TARGET_TYPES:
            raise ValueError(
                f"target_type must be one of {', '.join(TARGET_TYPES)}, got {target_type!r}"
            )

        cid = comment_id or uuid4().hex
        if cid in self._comments:
            raise ValueError(f"Comment id {cid!r} already exists")

        now = datetime.now(timezone.utc).isoformat()
        comment = Comment(
            comment_id=cid,
            target_type=target_type,
            target_id=target_id,
            author=author,
            text=text,
            created_at=now,
            resolved=False,
            resolved_at=None,
        )
        self._comments[cid] = comment
        self._save()
        return comment

    def resolve(self, comment_id: str) -> bool:
        """Mark a comment as resolved.

        Returns True if the comment existed and was unresolved;
        returns False if it was already resolved or not found.
        """
        comment = self._comments.get(comment_id)
        if comment is None or comment.resolved:
            return False
        comment.resolved = True
        comment.resolved_at = datetime.now(timezone.utc).isoformat()
        self._save()
        return True

    def reopen(self, comment_id: str) -> bool:
        """Reopen a previously resolved comment.

        Returns True if the comment existed and was resolved;
        returns False if it was already unresolved or not found.
        """
        comment = self._comments.get(comment_id)
        if comment is None or not comment.resolved:
            return False
        comment.resolved = False
        comment.resolved_at = None
        self._save()
        return True

    def list_by_target(
        self,
        target_type: str,
        target_id: str,
        *,
        resolved: Optional[bool] = None,
    ) -> List[Comment]:
        """List comments for a specific target.

        Parameters
        ----------
        target_type : str
            One of :data:`TARGET_TYPES`.
        target_id : str
            The item id.
        resolved : Optional[bool]
            If True, return only resolved comments.
            If False, return only unresolved comments.
            If None (default), return all.
        """
        result: List[Comment] = []
        for c in self._comments.values():
            if c.target_type != target_type or c.target_id != target_id:
                continue
            if resolved is not None and c.resolved != resolved:
                continue
            result.append(c)
        return result

    def list_all(self, *, resolved: Optional[bool] = None) -> List[Comment]:
        """List all comments, optionally filtered by resolved status."""
        if resolved is None:
            return list(self._comments.values())
        return [c for c in self._comments.values() if c.resolved == resolved]

    def get_unresolved(self) -> List[Comment]:
        """Convenience: list all unresolved comments."""
        return self.list_all(resolved=False)

    def get_comment(self, comment_id: str) -> Optional[Comment]:
        """Look up a single comment by id, or None."""
        return self._comments.get(comment_id)

    def remove_comment(self, comment_id: str) -> bool:
        """Delete a comment by id.

        Returns True if the comment existed and was removed.
        """
        if comment_id in self._comments:
            del self._comments[comment_id]
            self._save()
            return True
        return False

    @property
    def comment_count(self) -> int:
        """Total number of comments in the system."""
        return len(self._comments)

    @property
    def unresolved_count(self) -> int:
        """Number of unresolved comments."""
        return sum(1 for c in self._comments.values() if not c.resolved)
