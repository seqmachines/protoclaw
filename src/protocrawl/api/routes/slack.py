from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from protocrawl.config import settings
from protocrawl.services.slack import handle_slack_command, verify_slack_request

router = APIRouter()


@router.post("/commands", response_class=PlainTextResponse)
async def slack_commands(request: Request) -> PlainTextResponse:
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "0")
    signature = request.headers.get("X-Slack-Signature")

    if settings.slack_signing_secret and not verify_slack_request(
        settings.slack_signing_secret,
        timestamp=timestamp,
        body=body,
        signature=signature,
    ):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    form = parse_qs(body.decode())
    text = form.get("text", [""])[0]
    response_text = await handle_slack_command(text)
    return PlainTextResponse(response_text)
