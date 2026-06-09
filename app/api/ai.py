"""AI Creator (recipe generation) and AI Companion (chat) endpoints.

Both run anonymously and are rate-limited per client IP. Set
GEMINI_API_KEY in the environment to switch from stub mode to real
Gemini responses.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.core.deps import ClientIP, DbSession, OptionalCurrentUser
from app.models.cuisine import Cuisine
from app.models.spice_route import SpiceRoute
from app.schemas.spice_route import (
    SUPPORTED_LANGUAGES,
    SpiceRouteCreate,
    SpiceRouteDetail,
)
from app.services.ai import gemini, rate_limit
from app.services.serialization import to_detail
from app.services.spice_routes import (
    build_ingredients,
    build_steps,
    upsert_tags,
)

log = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# /ai/recipe/generate
# ---------------------------------------------------------------------------


class RecipeGenerateRequest(BaseModel):
    idea: str = Field(min_length=2, max_length=500)
    cuisine: Cuisine | None = None
    language: str = Field(default="en", min_length=2, max_length=8)
    save: bool = False

    @field_validator("language")
    @classmethod
    def _norm_lang(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"unsupported language {v!r}")
        return v


class RecipeGenerateResponse(BaseModel):
    recipe: SpiceRouteCreate
    saved: SpiceRouteDetail | None = None


@router.post("/recipe/generate", response_model=RecipeGenerateResponse)
async def generate_recipe(
    payload: RecipeGenerateRequest,
    db: DbSession,
    ip: ClientIP,
    user: OptionalCurrentUser = None,
) -> RecipeGenerateResponse:
    """Generate a recipe via Gemini.

    Generation itself is anonymous + IP rate-limited so anyone can try it.
    `save=true` requires authentication — saving to the catalog is an authed
    action, otherwise spam-bots could fill the public list with garbage.
    """
    if payload.save and user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="sign in to save AI recipes to your catalog",
        )

    await rate_limit.check_recipe_quota(db, ip=ip)

    raw: dict[str, Any]
    try:
        raw = await gemini.generate_recipe(
            idea=payload.idea,
            cuisine=payload.cuisine.value if payload.cuisine else None,
            language=payload.language,
        )
    except gemini.AIError as exc:
        log.warning("gemini failed once, retrying: %s", exc)
        try:
            raw = await gemini.generate_recipe(
                idea=payload.idea,
                cuisine=payload.cuisine.value if payload.cuisine else None,
                language=payload.language,
            )
        except gemini.AIError as exc2:
            # Log full traceback server-side; return a stable generic
            # message to the client. Echoing `str(exc2)` into the
            # response body leaks Gemini SDK internals (project IDs,
            # quota structure, internal call stacks) into client logs
            # and crash reporters.
            log.exception("gemini generation failed twice")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI generation is temporarily unavailable",
            ) from exc2

    # The model occasionally returns extra keys (e.g. `image_prompt`); strip
    # them by validating against our schema, which silently ignores extras.
    try:
        recipe = SpiceRouteCreate.model_validate(raw)
    except Exception as exc:
        # Validation errors can include the FULL invalid payload, which
        # in turn contains the user's idea + model output — neither
        # belongs in a client-facing detail string.
        log.warning("gemini payload failed schema: %r -> %s", raw, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned a malformed recipe; please try again",
        ) from exc

    saved: SpiceRouteDetail | None = None
    if payload.save and user is not None:
        tags = await upsert_tags(db, recipe.tags)
        sr = SpiceRoute(
            user_id=user.id,
            title=recipe.title,
            description=recipe.description,
            prep_minutes=recipe.prep_minutes,
            cook_minutes=recipe.cook_minutes,
            servings=recipe.servings,
            is_public=True,
            cuisine=recipe.cuisine,
            language=recipe.language,
            spice_level=recipe.spice_level,
            is_premium=False,
            calories_per_serving=recipe.calories_per_serving,
            image_path=recipe.image_url,
            ingredients=build_ingredients(recipe.ingredients),
            steps=build_steps(recipe.steps),
            tags=tags,
        )
        db.add(sr)
        await db.commit()
        await db.refresh(sr)
        saved = to_detail(sr, owner_display_name=user.display_name)

    return RecipeGenerateResponse(recipe=recipe, saved=saved)


# ---------------------------------------------------------------------------
# /ai/chat/stream
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: Literal["user", "model"] = "user"
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
    language: str = Field(default="en", min_length=2, max_length=8)

    @field_validator("language")
    @classmethod
    def _norm_lang(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"unsupported language {v!r}")
        return v

    @field_validator("messages")
    @classmethod
    def _last_must_be_user(cls, v: list[ChatMessage]) -> list[ChatMessage]:
        if v and v[-1].role != "user":
            raise ValueError("last message must have role='user'")
        return v


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    db: DbSession,
    ip: ClientIP,
) -> StreamingResponse:
    """Streams Gemini deltas back as Server-Sent Events.

    Frame format:
        data: {"type":"delta","text":"..."}\\n\\n
        data: {"type":"done"}\\n\\n
    """
    await rate_limit.check_chat_quota(db, ip=ip)

    history = [{"role": m.role, "content": m.content} for m in payload.messages]

    async def event_gen():
        try:
            async for chunk in gemini.chat_stream(
                history=history, language=payload.language
            ):
                yield f"data: {json.dumps({'type': 'delta', 'text': chunk})}\n\n"
        except Exception:
            # Stable, generic error frame — `str(exc)` carries Gemini
            # SDK internals (project IDs, internal call paths, stack
            # traces) that don't belong in a client SSE payload. The
            # raw exception is still logged server-side via
            # `log.exception(...)` for ops debugging.
            log.exception("chat stream failed")
            yield (
                f"data: {json.dumps({'type': 'error', 'message': 'chat stream failed'})}\n\n"
            )
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
