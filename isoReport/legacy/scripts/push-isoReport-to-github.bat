@echo off
REM Sube solo el contenido de Repos/isoReport/ a GitHub (ivnamo/isoReport)
REM Ejecutar desde la raiz de Repos (donde esta .git)
cd /d "%~dp0"
git branch -D deploy-isoReport 2>nul
git subtree split -P isoReport -b deploy-isoReport
git push origin deploy-isoReport:master
git branch -D deploy-isoReport
echo.
echo Listo: GitHub tiene solo el contenido de isoReport en la raiz.
pause
