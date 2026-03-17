from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainValidationError
from app.models.document import Document
from app.models.incident import Incident


class ToolService:
    """Minimal tool plugin executor for operational actions."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(
        self,
        *,
        team_id: str,
        user_id: str,
        action: str,
        arguments: dict[str, object],
    ) -> dict[str, object]:
        action_name = action.strip().lower()

        if action_name == "create_incident":
            return self._create_incident(
                team_id=team_id,
                user_id=user_id,
                arguments=arguments,
            )

        if action_name == "list_recent_documents":
            return self._list_recent_documents(team_id=team_id, arguments=arguments)

        raise DomainValidationError(
            "Unsupported action. Available actions: create_incident, list_recent_documents."
        )

    def _create_incident(
        self,
        *,
        team_id: str,
        user_id: str,
        arguments: dict[str, object],
    ) -> dict[str, object]:
        raw_title = str(arguments.get("title", "")).strip()
        if not raw_title:
            raise DomainValidationError("create_incident requires a non-empty 'title'.")
        if len(raw_title) > 255:
            raise DomainValidationError("title must be at most 255 characters.")

        severity = str(arguments.get("severity", "P2")).upper().strip()
        if severity not in {"P1", "P2", "P3"}:
            raise DomainValidationError("severity must be one of: P1, P2, P3.")

        incident = Incident(
            incident_id=str(uuid4()),
            team_id=team_id,
            created_by_user_id=user_id,
            title=raw_title,
            severity=severity,
            status="open",
        )
        self.db.add(incident)
        self.db.commit()
        self.db.refresh(incident)

        return {
            "tool_name": "create_incident",
            "message": "Incident created successfully.",
            "incident": {
                "incident_id": incident.incident_id,
                "team_id": incident.team_id,
                "created_by_user_id": incident.created_by_user_id,
                "title": incident.title,
                "severity": incident.severity,
                "status": incident.status,
                "created_at": incident.created_at.isoformat(),
            },
        }

    def _list_recent_documents(
        self,
        *,
        team_id: str,
        arguments: dict[str, object],
    ) -> dict[str, object]:
        limit = self._parse_limit(arguments.get("limit", 5))

        stmt = (
            select(Document)
            .where(Document.team_id == team_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        documents = list(self.db.scalars(stmt).all())

        return {
            "tool_name": "list_recent_documents",
            "message": f"Fetched {len(documents)} documents.",
            "documents": [
                {
                    "document_id": item.document_id,
                    "source_name": item.source_name,
                    "content_type": item.content_type,
                    "created_at": item.created_at.isoformat(),
                }
                for item in documents
            ],
        }

    def _parse_limit(self, raw_value: object) -> int:
        try:
            limit = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise DomainValidationError("limit must be an integer between 1 and 20.") from exc

        if limit < 1 or limit > 20:
            raise DomainValidationError("limit must be an integer between 1 and 20.")

        return limit
