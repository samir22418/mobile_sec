from __future__ import annotations

import hashlib
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.chat import OpenRouterChatProvider
from app.shieldy.providers import ChatProviderNotConfigured
from app.api.feedback import ALLOWED_FEEDBACK_LABELS
from app.auth.bearer import verify_analyst_token
from app.dependencies import get_session
from app.models import (
    AIRiskDecision,
    AnalystFeedback,
    ChatAction,
    ChatMessage,
    ChatSession,
    ImportantLog,
    RiskAssessment,
    TelemetryPayload,
)

router = APIRouter()


class CreateChatSessionRequest(BaseModel):
    title: str | None = None


class ChatMessageRequest(BaseModel):
    content: str
    context_payload_id: str | None = None


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/api/v1/chat/sessions", status_code=status.HTTP_201_CREATED)
def create_chat_session(
    body: CreateChatSessionRequest,
    session: Session = Depends(get_session),
    token: str = Depends(verify_analyst_token),
) -> dict:
    chat = ChatSession(
        id=str(uuid.uuid4()),
        title=body.title or "AEGIS AI chat",
        analyst_token_hash=token_hash(token),
    )
    session.add(chat)
    session.commit()
    return serialize_session(chat)


@router.post("/api/v1/chat/sessions/{session_id}/messages")
def create_chat_message(
    session_id: str,
    body: ChatMessageRequest,
    request: Request,
    session: Session = Depends(get_session),
    token: str = Depends(verify_analyst_token),
) -> dict:
    chat = session.get(ChatSession, session_id)
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "session_not_found"})

    context = build_chat_context(session, body.context_payload_id) if body.context_payload_id else None
    messages = [
        {"role": message.role, "content": message.content}
        for message in session.scalars(
            select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
        ).all()
        if message.role in {"user", "assistant"}
    ]
    messages.append({"role": "user", "content": body.content})

    provider = OpenRouterChatProvider(request.app.state.settings)
    try:
        assistant = provider.send(messages, context=context)
    except ChatProviderNotConfigured as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"error": "chat_not_configured", "message": str(error)})
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={"error": "chat_provider_failed", "message": str(error)})

    user_message = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=body.content,
        context_payload_id=body.context_payload_id,
    )
    assistant_message = ChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=str(assistant.get("answer", "")),
        context_payload_id=body.context_payload_id,
        model_name=provider.model_name,
    )
    session.add_all([user_message, assistant_message])
    actions = create_pending_actions(session, session_id, assistant_message.id, assistant, token)
    session.commit()
    return {
        "message": serialize_message(assistant_message),
        "actions": [serialize_action(action) for action in actions],
        "route": assistant.get("route"),
        "safety": assistant.get("safety"),
    }


@router.post("/api/v1/chat/actions/{action_id}/confirm")
def confirm_chat_action(
    action_id: str,
    session: Session = Depends(get_session),
    token: str = Depends(verify_analyst_token),
) -> dict:
    action = session.get(ChatAction, action_id)
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "action_not_found"})
    if action.status == "COMPLETED":
        return serialize_action(action)
    payload = json.loads(action.payload_json)
    if action.tool_name == "create_analyst_feedback":
        label = payload.get("label", "NEEDS_MORE_DATA")
        if label not in ALLOWED_FEEDBACK_LABELS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "invalid_label"})
        feedback = AnalystFeedback(
            finding_id=payload.get("finding_id", action.id),
            payload_id=payload.get("payload_id"),
            analyst_id=payload.get("analyst_id", "chat_assistant"),
            label=label,
            notes=payload.get("notes"),
        )
        session.add(feedback)
        session.flush()
        action.status = "COMPLETED"
        action.result_json = json.dumps({"feedback_id": feedback.id, "label": feedback.label}, sort_keys=True)
    elif action.tool_name == "create_review_note":
        action.status = "COMPLETED"
        action.result_json = json.dumps({"note": payload.get("notes", ""), "status": "recorded"}, sort_keys=True)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "tool_not_allowed"})
    action.analyst_token_hash = token_hash(token)
    session.commit()
    return serialize_action(action)


def build_chat_context(session: Session, payload_id: str | None) -> dict | None:
    if not payload_id:
        return None
    payload = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == payload_id))
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "payload_not_found"})
    risk = session.scalar(select(RiskAssessment).where(RiskAssessment.payload_id == payload_id))
    decision = session.scalar(select(AIRiskDecision).where(AIRiskDecision.payload_id == payload_id))
    logs = session.scalars(
        select(ImportantLog)
        .where(ImportantLog.payload_id == payload_id)
        .order_by(ImportantLog.observed_at_epoch_ms.desc())
        .limit(10)
    ).all()
    return {
        "payload_id": payload.payload_id,
        "device_id": payload.device_id,
        "scan_id": payload.scan_id,
        "processing_status": payload.processing_status,
        "received_at": payload.received_at.isoformat(),
        "risk": {
            "score": risk.risk_score,
            "label": risk.risk_label,
            "confidence": risk.confidence,
            "reasons": json.loads(risk.reasons_json),
            "recommended_action": risk.recommended_action,
        } if risk else None,
        "ai_decision": {
            "deterministic_score": decision.deterministic_score,
            "deterministic_label": decision.deterministic_label,
            "final_score": decision.final_score,
            "final_label": decision.final_label,
            "evidence_refs": json.loads(decision.evidence_refs_json),
            "used_ai_final": decision.used_ai_final,
        } if decision else None,
        "redacted_logs": [
            {
                "tag": log.tag,
                "level": log.level,
                "matched_rule": log.matched_rule,
                "message_redacted": log.message_redacted,
                "message_hash": log.message_hash,
            }
            for log in logs
        ],
    }


def create_pending_actions(
    session: Session,
    session_id: str,
    message_id: str,
    assistant: dict,
    token: str,
) -> list[ChatAction]:
    actions = []
    for item in assistant.get("actions", []):
        if not isinstance(item, dict):
            continue
        tool_name = item.get("tool_name")
        if tool_name not in {"create_analyst_feedback", "create_review_note"}:
            continue
        action = ChatAction(
            id=str(uuid.uuid4()),
            session_id=session_id,
            message_id=message_id,
            tool_name=tool_name,
            payload_json=json.dumps(item.get("payload", {}), sort_keys=True),
            status="PENDING",
            analyst_token_hash=token_hash(token),
        )
        session.add(action)
        actions.append(action)
    return actions


def serialize_session(chat: ChatSession) -> dict:
    return {
        "id": chat.id,
        "title": chat.title,
        "created_at": chat.created_at.isoformat(),
    }


def serialize_message(message: ChatMessage) -> dict:
    return {
        "id": message.id,
        "session_id": message.session_id,
        "role": message.role,
        "content": message.content,
        "context_payload_id": message.context_payload_id,
        "model_name": message.model_name,
        "status": message.status,
        "created_at": message.created_at.isoformat(),
    }


def serialize_action(action: ChatAction) -> dict:
    return {
        "id": action.id,
        "session_id": action.session_id,
        "message_id": action.message_id,
        "tool_name": action.tool_name,
        "payload": json.loads(action.payload_json),
        "result": json.loads(action.result_json) if action.result_json else None,
        "status": action.status,
        "created_at": action.created_at.isoformat(),
    }
