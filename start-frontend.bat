@echo off
cd /d "%~dp0frontend"
if not exist "node_modules" call pnpm install
pnpm dev