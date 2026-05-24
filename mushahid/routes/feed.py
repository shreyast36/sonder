"""
Social feed routes — user-authored posts + threaded comments.

Posts are visible to every signed-in user. There's no mute / report /
moderation surface in v1; sanitize_user_input runs on every text field
to scrub prompt-injection / control-char attempts. Image uploads are
plumbed via `image_url` but no upload endpoint exists yet — frontend
v1 posts text-only.

Endpoints:
    GET    /api/feed                        newest-first feed page
    POST   /api/feed/posts                  create a post
    GET    /api/feed/posts/{post_id}        single post detail
    DELETE /api/feed/posts/{post_id}        author-only
    GET    /api/feed/posts/{post_id}/comments
    POST   /api/feed/posts/{post_id}/comments
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from mushahid.auth import verify_token
from mushahid.realtime.firestore import (
    delete_social_post, get_social_post, get_user_profile,
    increment_post_comment_count, list_social_comments, list_social_posts,
    write_social_comment, write_social_post,
)
from mushahid.utils.sanitize import sanitize_user_input
from shreyas.cotraveller.chat import manager as ws_manager

router = APIRouter()
logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def _profile_summary(user_id: str) -> tuple[str, str | None]:
    try:
        p = await get_user_profile(user_id) or {}
        return (p.get("display_name") or "Traveller", p.get("avatar_url"))
    except Exception:
        return ("Traveller", None)


# ── Request models ────────────────────────────────────────────────────────


class PostCreateRequest(BaseModel):
    text:           str = Field(..., min_length=1, max_length=600)
    linked_trip_id: str | None = None
    image_url:      str | None = None


class CommentCreateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=400)


# ── Routes ────────────────────────────────────────────────────────────────


@router.get("/feed")
async def get_feed(
    limit:  int        = Query(default=30, ge=1, le=60),
    before: str | None = Query(default=None),
    uid:    str        = Depends(verify_token),
):
    """Newest-first feed page. `before` is the ISO timestamp of the
    oldest post the client already has — passing it walks older pages."""
    posts = await list_social_posts(limit=limit, before=before)
    return {"posts": posts, "next_before": posts[-1].get("created_at") if posts else None}


@router.post("/feed/posts")
async def create_post(body: PostCreateRequest, uid: str = Depends(verify_token)):
    """Author a new post. The author's display_name + avatar_url are
    denormalised onto the post doc so the feed reader doesn't need to
    join against user_profiles per row."""
    text = sanitize_user_input(body.text)[:600].strip()
    if not text:
        raise HTTPException(status_code=400, detail="Post text is empty after sanitisation")
    name, avatar = await _profile_summary(uid)
    post = {
        "post_id":        _new_id("post"),
        "author_id":      uid,
        "author_name":    name,
        "author_avatar":  avatar,
        "text":           text,
        "linked_trip_id": (body.linked_trip_id or None),
        "image_url":      (body.image_url or None),
        "comment_count":  0,
        "created_at":     _now_iso(),
    }
    await write_social_post(post)
    # Push to every connected user so the Discover feed surfaces new
    # posts in real time without waiting on the 6s poll. The author is
    # excluded; their local state already has the post.
    try:
        await ws_manager.broadcast_global(
            {"type": "discover_post_new", "post": post},
            exclude_user=uid,
        )
    except Exception as e:
        logger.debug("broadcast_global(discover_post_new) failed: %s", e)
    return {"post": post}


@router.get("/feed/posts/{post_id}")
async def get_post(post_id: str, uid: str = Depends(verify_token)):
    post = await get_social_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"post": post}


@router.delete("/feed/posts/{post_id}")
async def delete_post(post_id: str, uid: str = Depends(verify_token)):
    """Author-only delete. Cascades to all child comments."""
    post = await get_social_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.get("author_id") != uid:
        raise HTTPException(status_code=403, detail="Only the author can delete this post")
    ok = await delete_social_post(post_id)
    if not ok:
        raise HTTPException(status_code=502, detail="Delete failed")
    return {"deleted": True, "post_id": post_id}


@router.get("/feed/posts/{post_id}/comments")
async def get_comments(post_id: str, uid: str = Depends(verify_token)):
    """Oldest-first thread of comments under a post."""
    # Confirm the post exists before walking its subcollection.
    post = await get_social_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    comments = await list_social_comments(post_id)
    return {"comments": comments}


@router.post("/feed/posts/{post_id}/comments")
async def add_comment(post_id: str, body: CommentCreateRequest, uid: str = Depends(verify_token)):
    """Append a comment to a post. Denormalised comment_count on the
    post bumps so the feed list stays accurate without subcollection
    counts."""
    post = await get_social_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    text = sanitize_user_input(body.text)[:400].strip()
    if not text:
        raise HTTPException(status_code=400, detail="Comment text is empty after sanitisation")
    name, avatar = await _profile_summary(uid)
    comment = {
        "comment_id":    _new_id("cm"),
        "post_id":       post_id,
        "author_id":     uid,
        "author_name":   name,
        "author_avatar": avatar,
        "text":          text,
        "created_at":    _now_iso(),
    }
    await write_social_comment(post_id, comment)
    await increment_post_comment_count(post_id, delta=1)
    # Push to the post author's notification socket so their feed
    # surfaces the comment in real time. Skip self-notifies (author
    # commenting on their own post sees it from the local state).
    if post.get("author_id") and post["author_id"] != uid:
        try:
            await ws_manager.notify_user(
                post["author_id"],
                {"type": "comment_new", "post_id": post_id, "comment": comment},
            )
        except Exception as e:
            logger.debug("notify_user(comment_new) failed: %s", e)
        # Push + email so the post author hears about the reply even
        # with the tab closed / next time they open mail.
        try:
            from mushahid.realtime.notify import notify_event
            commenter = comment.get("author_name") or "Someone"
            preview   = (comment.get("text") or "").strip()[:140]
            import asyncio as _asyncio
            _asyncio.create_task(notify_event(
                recipient_uid=post["author_id"], kind="comment",
                title=f"{commenter} replied to your post",
                body=preview,
                link_path="/dashboard",
                tag=f"sonder-comment-{post_id}",
            ))
        except Exception as e:
            logger.debug("notify_event(comment) failed: %s", e)
    return {"comment": comment}
