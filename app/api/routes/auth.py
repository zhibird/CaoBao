from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import get_auth_service, require_current_active_user
from app.core.exceptions import DomainValidationError, EntityConflictError
from app.models.user import User
from app.schemas.auth import AuthSessionResponse, ChangePasswordRequest, LoginRequest, RegisterRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthSessionResponse:
    try:
        result = auth_service.register(
            payload,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except (DomainValidationError, EntityConflictError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    auth_service.write_auth_cookies(response, access_token=result.access_token, refresh_token=result.refresh_token)
    return AuthSessionResponse(
        user_id=result.user.user_id,
        team_id=result.user.team_id,
        team_name=result.team_name,
        display_name=result.user.display_name,
        role=result.user.role,
        is_active=result.user.is_active,
    )


@router.post("/login", response_model=AuthSessionResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthSessionResponse:
    try:
        result = auth_service.login(
            payload,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    auth_service.write_auth_cookies(response, access_token=result.access_token, refresh_token=result.refresh_token)
    return AuthSessionResponse(
        user_id=result.user.user_id,
        team_id=result.user.team_id,
        team_name=result.team_name,
        display_name=result.user.display_name,
        role=result.user.role,
        is_active=result.user.is_active,
    )


@router.get("/me", response_model=AuthSessionResponse)
def me(
    current_user: User = Depends(require_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthSessionResponse:
    team_name = auth_service.get_team_name(current_user.team_id)
    return AuthSessionResponse(
        user_id=current_user.user_id,
        team_id=current_user.team_id,
        team_name=team_name,
        display_name=current_user.display_name,
        role=current_user.role,
        is_active=current_user.is_active,
    )


@router.post("/refresh", response_model=AuthSessionResponse)
def refresh(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthSessionResponse:
    try:
        result = auth_service.refresh(
            refresh_token=request.cookies.get(auth_service.settings.auth_refresh_cookie_name),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    auth_service.write_auth_cookies(response, access_token=result.access_token, refresh_token=result.refresh_token)
    return AuthSessionResponse(
        user_id=result.user.user_id,
        team_id=result.user.team_id,
        team_name=result.team_name,
        display_name=result.user.display_name,
        role=result.user.role,
        is_active=result.user.is_active,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    auth_service.revoke_refresh_session(
        request.cookies.get(auth_service.settings.auth_refresh_cookie_name)
    )
    auth_service.clear_auth_cookies(response)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    current_user: User = Depends(require_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    try:
        auth_service.change_password(
            current_user,
            current_password=payload.current_password,
            new_password=payload.new_password,
            confirm_new_password=payload.confirm_new_password,
        )
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    auth_service.clear_auth_cookies(response)
