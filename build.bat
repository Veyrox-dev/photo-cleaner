@echo off
REM Quick build script for PhotoCleaner executable (Windows)
REM Uses lazy-loading for numpy-dependent modules to avoid PyInstaller issues

setlocal enabledelayedexpansion

echo.
echo ====================================
echo PhotoCleaner v0.8.2 Build Script
echo ====================================
echo.

REM Activate virtual environment
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found!
    pause
    exit /b 1
)

REM Configure persistent pip cache (speeds up rebuilds)
if not defined PIP_CACHE_DIR set "PIP_CACHE_DIR=%USERPROFILE%\.cache\pip"
if not exist "%PIP_CACHE_DIR%" mkdir "%PIP_CACHE_DIR%" >nul 2>&1
echo Using PIP_CACHE_DIR=%PIP_CACHE_DIR%

REM Install/ensure PyInstaller (pinned)
echo Ensuring PyInstaller 6.7.x is installed...
pip install pyinstaller==6.7.0 --quiet

REM Preflight check (strict)
echo.
echo Running preflight check...
.venv\Scripts\python.exe scripts\preflight_check.py --strict
if errorlevel 1 (
    echo.
    echo PREFLIGHT FAILED - build aborted
    pause
    exit /b 1
)

REM Build flags: clean, fast
set CLEAN_BUILD=0
set FAST_BUILD=0
for %%A in (%*) do (
    if /i "%%A"=="clean" set CLEAN_BUILD=1
    if /i "%%A"=="fast" set FAST_BUILD=1
)
if %FAST_BUILD%==1 set "PHOTOCLEANER_FAST=1"
if %CLEAN_BUILD%==1 (
    echo Cleaning previous builds...
    if exist dist rmdir /s /q dist
    if exist build rmdir /s /q build
)

REM Build with spec file
if exist PhotoCleaner.spec (
    echo.
    echo Building with PhotoCleaner.spec...
    echo.
    if %FAST_BUILD%==1 (
        echo Fast build enabled: noarchive + no optimization
    )
    if %CLEAN_BUILD%==1 (
        pyinstaller PhotoCleaner.spec --clean --noconfirm
    ) else (
        pyinstaller PhotoCleaner.spec --noconfirm
    )
    
    if exist dist\PhotoCleaner\PhotoCleaner.exe (
        echo.
        echo ====================================
        echo BUILD SUCCESS!
        echo ====================================
        for %%F in (dist\PhotoCleaner\PhotoCleaner.exe) do (
            set size=%%~zF
            set /a sizeMB=!size! / 1048576
            echo Output: %%F
            echo Size: !sizeMB! MB
        )
        echo.
    ) else (
        echo.
        echo BUILD FAILED - exe not created
        pause
        exit /b 1
    )
) else (
    echo ERROR: PhotoCleaner.spec not found!
    pause
    exit /b 1
)

echo.
endlocal
pause
