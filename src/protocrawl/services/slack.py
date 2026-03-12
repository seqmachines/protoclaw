from __future__ import annotations

import hashlib
import hmac
import time
import uuid

from protocrawl.agents.formatter.tools import generate_summary, render_read_diagram
from protocrawl.db import repositories as repo
from protocrawl.db.engine import async_session
from protocrawl.services.protocols import row_to_protocol


def verify_slack_request(
    signing_secret: str,
    *,
    timestamp: str,
    body: bytes,
    signature: str | None,
) -> bool:
    if not signing_secret:
        return True
    if not signature:
        return False

    try:
        request_time = int(timestamp)
    except ValueError:
        return False

    if abs(time.time() - request_time) > 60 * 5:
        return False

    basestring = f"v0:{timestamp}:{body.decode()}".encode()
    digest = hmac.new(signing_secret.encode(), basestring, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"v0={digest}", signature)


async def _find_protocol(query: str):
    async with async_session() as session:
        exact = await repo.get_protocol_by_slug(session, query)
        if exact is not None:
            return exact
        matches = await repo.search_protocols(session, query, limit=1)
        return matches[0] if matches else None


async def _list_pending_reviews() -> list[str]:
    async with async_session() as session:
        reviews = await repo.list_pending_reviews(session)
        lines = []
        for review in reviews[:10]:
            protocol_name = review.protocol.name if review.protocol else str(review.protocol_id)
            lines.append(
                f"{review.id} | {protocol_name} | score={review.confidence_score:.2f}"
            )
        return lines


async def _update_review(
    review_id: uuid.UUID,
    decision: str,
) -> bool:
    async with async_session() as session:
        review = await repo.update_review_status(
            session,
            review_id,
            decision,
            protocol_published=decision == "approved",
        )
        await session.commit()
        return review is not None


async def handle_slack_command(text: str) -> str:
    parts = text.strip().split()
    if not parts:
        return (
            "Usage: protocol <query> | read <query> | reviews | "
            "review <review_id> approve|reject"
        )

    command = parts[0].lower()

    if command == "protocol":
        query = " ".join(parts[1:]).strip()
        if not query:
            return "Usage: protocol <slug or name>"
        protocol = await _find_protocol(query)
        if protocol is None:
            return f"No protocol found for '{query}'."
        return generate_summary(row_to_protocol(protocol))

    if command == "read":
        query = " ".join(parts[1:]).strip()
        if not query:
            return "Usage: read <slug or name>"
        protocol = await _find_protocol(query)
        if protocol is None:
            return f"No protocol found for '{query}'."
        return render_read_diagram(row_to_protocol(protocol))

    if command == "reviews":
        lines = await _list_pending_reviews()
        if not lines:
            return "No pending reviews."
        return "Pending reviews:\n" + "\n".join(lines)

    if command == "review":
        if len(parts) < 3:
            return "Usage: review <review_id> approve|reject"
        try:
            review_id = uuid.UUID(parts[1])
        except ValueError:
            return "Review ID must be a UUID."

        action = parts[2].lower()
        if action not in {"approve", "approved", "reject", "rejected"}:
            return "Review action must be approve or reject."

        decision = "approved" if action.startswith("approve") else "rejected"
        updated = await _update_review(review_id, decision)
        if not updated:
            return f"Review {review_id} not found."
        return f"Review {review_id} marked {decision}."

    return (
        "Unknown command. Use: protocol <query> | read <query> | reviews | "
        "review <review_id> approve|reject"
    )
