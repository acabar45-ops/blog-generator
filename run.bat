@echo off
cd /d "%~dp0"

:: Python 및 패키지 확인
python -m pip install -r requirements.txt --quiet

:: API 키가 없으면 입력 요청
if "%ANTHROPIC_API_KEY%"=="" (
    set /p ANTHROPIC_API_KEY="ANTHROPIC_API_KEY를 입력하세요: "
)

:: 앱 실행
streamlit run app.py
pause
