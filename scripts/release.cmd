@echo off
setlocal

REM Run release script from repo root (parent of this scripts folder)
set "REPO_ROOT=%~dp0.."
pushd "%REPO_ROOT%" >nul

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0release.ps1"
set "EXITCODE=%ERRORLEVEL%"

popd >nul
echo.
if not "%EXITCODE%"=="0" (
  echo Release script failed with exit code %EXITCODE%.
) else (
  echo Release script finished.
)
echo.
pause
endlocal
exit /b %EXITCODE%
