@echo off
cd /d "%~dp0"
set "DATABASE_URL="
set "ADMIN_PASSWORD=Todivo#2026!CL"
set "ADMIN_SESSION_SECRET=todivo-local-session-2026-change-before-production"
if not exist "todivo.db" echo Se creara la base de datos local automaticamente.
start "TODIVO CL - Servidor" cmd /k "python server.py"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:5000/"
