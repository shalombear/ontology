@echo off
setlocal EnableExtensions

cd /d "%~dp0" || exit /b 1

set "DB=%~dp0..\data\db\wikipull.db"
set "PYTHON=python"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=%~dp0.venv\Scripts\python.exe"
)

set "VERSION=%~1"
if not defined VERSION (
    for /f %%G in ('git rev-parse --short HEAD 2^>nul') do set "VERSION=%%G"
)

if not defined VERSION (
    echo ERROR: Specify a benchmark version.
    exit /b 1
)

echo Benchmark version: %VERSION%

rem Simple tests: independent databases

call :reset || exit /b 1
call :run Alphabet 3 S1 || exit /b 1

call :reset || exit /b 1
call :run Alphabet 4 S2 || exit /b 1

call :reset || exit /b 1
call :run Mathematics 3 S3 || exit /b 1

call :reset || exit /b 1
call :run Mathematics 4 S4 || exit /b 1

rem Complex tests: shared database within each pair

call :reset || exit /b 1
call :run Mathematics 3 C1a || exit /b 1
call :run Mathematics 4 C1b || exit /b 1

call :reset || exit /b 1
call :run Alphabet 3 C2a || exit /b 1
call :run Alphabet 4 C2b || exit /b 1

call :reset || exit /b 1
call :run Mathematics 3 C3a || exit /b 1
call :run Alphabet 4 C3b || exit /b 1

call :reset || exit /b 1
call :run Alphabet 3 C4a || exit /b 1
call :run Mathematics 4 C4b || exit /b 1

rem Deep cross-seed tests

call :reset || exit /b 1
call :run Alphabet 4 D1a || exit /b 1
call :run Mathematics 4 D1b || exit /b 1

call :reset || exit /b 1
call :run Mathematics 4 D2a || exit /b 1
call :run Alphabet 4 D2b || exit /b 1

call :reset || exit /b 1

echo Benchmark suite completed.
exit /b 0

:reset
echo Resetting benchmark database...

for %%F in ("%DB%" "%DB%-wal" "%DB%-shm") do (
    if exist "%%~F" (
        del /f /q "%%~F"
        if exist "%%~F" (
            echo ERROR: Could not delete %%~F
            exit /b 1
        )
    )
)
exit /b 0

:run
echo Running %~3: %~1 depth %~2
"%PYTHON%" runscript.py "%~1" "%~2" "%VERSION%" "%~3"
if errorlevel 1 (
    echo ERROR: Test %~3 failed.
    exit /b 1
)
exit /b 0