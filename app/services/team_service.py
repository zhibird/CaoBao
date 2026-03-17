from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import EntityConflictError
from app.models.team import Team
from app.schemas.team import TeamCreate


class TeamService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_team(self, payload: TeamCreate) -> Team:
        existing = self.db.get(Team, payload.team_id)
        if existing is not None:
            raise EntityConflictError(f"Team '{payload.team_id}' already exists.")

        team = Team(
            team_id=payload.team_id,
            name=payload.name,
            description=payload.description,
        )
        self.db.add(team)
        self.db.commit()
        self.db.refresh(team)
        return team

    def get_by_id(self, team_id: str) -> Team | None:
        return self.db.get(Team, team_id)

    def list_teams(self) -> list[Team]:
        stmt = select(Team).order_by(Team.created_at.desc())
        return list(self.db.scalars(stmt).all())
