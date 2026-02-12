@echo off
cd /d "%~dp0"
set "APP_DIR=%~dp0"
set "APP_PY=%APP_DIR%app.py"
if exist "%APP_DIR%venv\Scripts\streamlit.exe" (
    "%APP_DIR%venv\Scripts\streamlit.exe" run "%APP_PY%"
) else if exist "%APP_DIR%venv\Scripts\python.exe" (
    "%APP_DIR%venv\Scripts\python.exe" -m streamlit run "%APP_PY%"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m streamlit run "%APP_PY%"
) else (
    echo No se encontro Python con Streamlit. Crea un venv en esta carpeta y ejecuta: pip install -r requirements.txt
    pause
    exit /b 1
)
pause
