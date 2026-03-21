from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_admin_service, require_dev_admin
from app.core.exceptions import DomainValidationError, EntityNotFoundError
from app.schemas.admin import (
    AdminConversationItem,
    AdminDashboardResponse,
    AdminDocumentDetail,
    AdminDocumentItem,
    AdminSessionResponse,
    AdminTeamItem,
    AdminUserItem,
    AdminUserRoleUpdate,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", dependencies=[Depends(require_dev_admin)])


@router.get("/session", response_model=AdminSessionResponse)
def get_admin_session(
    admin_service: AdminService = Depends(get_admin_service),
) -> AdminSessionResponse:
    admin_user = admin_service.ensure_admin_account()
    return AdminSessionResponse.from_account(
        account_id=admin_user.user_id,
        team_id=admin_user.team_id,
        display_name=admin_user.display_name,
        role=admin_user.role,
    )


@router.get("/dashboard", response_model=AdminDashboardResponse)
def get_admin_dashboard(
    admin_service: AdminService = Depends(get_admin_service),
) -> AdminDashboardResponse:
    return admin_service.dashboard()


@router.get("/teams", response_model=list[AdminTeamItem])
def list_admin_teams(
    limit: int = Query(default=200, ge=1, le=500),
    admin_service: AdminService = Depends(get_admin_service),
) -> list[AdminTeamItem]:
    return admin_service.list_teams(limit=limit)


@router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_team(
    team_id: str,
    admin_service: AdminService = Depends(get_admin_service),
) -> None:
    try:
        admin_service.delete_team(team_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/users", response_model=list[AdminUserItem])
def list_admin_users(
    team_id: str | None = Query(default=None, min_length=1, max_length=64),
    limit: int = Query(default=300, ge=1, le=800),
    admin_service: AdminService = Depends(get_admin_service),
) -> list[AdminUserItem]:
    return admin_service.list_users(team_id=team_id, limit=limit)


@router.patch("/users/{user_id}/role", response_model=AdminUserItem)
def update_admin_user_role(
    user_id: str,
    payload: AdminUserRoleUpdate,
    admin_service: AdminService = Depends(get_admin_service),
) -> AdminUserItem:
    try:
        return admin_service.update_user_role(user_id=user_id, role=payload.role)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_user(
    user_id: str,
    admin_service: AdminService = Depends(get_admin_service),
) -> None:
    try:
        admin_service.delete_user(user_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/conversations", response_model=list[AdminConversationItem])
def list_admin_conversations(
    team_id: str | None = Query(default=None, min_length=1, max_length=64),
    user_id: str | None = Query(default=None, min_length=1, max_length=64),
    limit: int = Query(default=300, ge=1, le=800),
    admin_service: AdminService = Depends(get_admin_service),
) -> list[AdminConversationItem]:
    return admin_service.list_conversations(
        team_id=team_id,
        user_id=user_id,
        limit=limit,
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_conversation(
    conversation_id: str,
    admin_service: AdminService = Depends(get_admin_service),
) -> None:
    try:
        admin_service.delete_conversation(conversation_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/documents", response_model=list[AdminDocumentItem])
def list_admin_documents(
    team_id: str | None = Query(default=None, min_length=1, max_length=64),
    user_id: str | None = Query(default=None, min_length=1, max_length=64),
    conversation_id: str | None = Query(default=None, min_length=1, max_length=36),
    limit: int = Query(default=300, ge=1, le=800),
    admin_service: AdminService = Depends(get_admin_service),
) -> list[AdminDocumentItem]:
    return admin_service.list_documents(
        team_id=team_id,
        user_id=user_id,
        conversation_id=conversation_id,
        limit=limit,
    )


@router.get("/documents/{document_id}", response_model=AdminDocumentDetail)
def get_admin_document(
    document_id: str,
    admin_service: AdminService = Depends(get_admin_service),
) -> AdminDocumentDetail:
    try:
        return admin_service.get_document(document_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_document(
    document_id: str,
    admin_service: AdminService = Depends(get_admin_service),
) -> None:
    try:
        admin_service.delete_document(document_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
