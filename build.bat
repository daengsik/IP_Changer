@echo off
REM ============================================================
REM  IP Changer - 단일 EXE 빌드 스크립트
REM
REM  결과물: dist\IPChanger.exe
REM    - 단일 파일 (콘솔 없음, 더블클릭 시 UAC 자동 요청)
REM    - 어디든 두고 실행하면 %APPDATA%\IPChanger\ 가 자동 생성됨
REM
REM  사전 조건:
REM    - Python 3.10+ 가 PATH 에 있어야 함 (`python --version` 으로 확인)
REM ============================================================

setlocal
cd /d "%~dp0"

echo.
echo [1/4] Python 버전 확인...
python --version || (
    echo  ERROR: Python 을 PATH 에서 찾지 못했습니다.
    pause
    exit /b 1
)

echo.
echo [2/4] 의존성 설치...
python -m pip install --upgrade pip                || goto :fail
python -m pip install -r requirements.txt          || goto :fail
python -m pip install --upgrade pyinstaller        || goto :fail

echo.
echo [3/4] 이전 빌드 정리...
if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist

echo.
echo [4/4] PyInstaller 실행...
python -m PyInstaller IPChanger.spec --clean --noconfirm   || goto :fail

if not exist dist\IPChanger.exe goto :fail

echo.
echo ============================================================
echo  빌드 완료!
echo    %~dp0dist\IPChanger.exe
echo.
echo  배포 방법:
echo    1) dist\IPChanger.exe 를 원하는 위치(USB/공유폴더 등)로 복사
echo    2) 더블클릭 → UAC 승인 → 자동으로 %%APPDATA%%\IPChanger\ 생성
echo    3) 별도 설치 절차 없음
echo ============================================================
echo.
pause
exit /b 0


:fail
echo.
echo ============================================================
echo  빌드 실패!
echo ============================================================
echo.
pause
exit /b 1
