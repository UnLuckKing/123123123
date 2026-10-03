@echo off
setlocal enabledelayedexpansion

:MAIN_BUILD
cls
echo ========================================================
echo   VANTA APEX - FULL PIPELINE BUILDER
echo   (frontend\dist + embed backend\ui + vanta.exe)
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/3] Frontend bagimliliklari kontrol ediliyor...
if not exist "frontend" (
    echo [!] 'frontend' dizini bulunamadi!
    goto BUILD_FAILED
)
cd frontend
if not exist node_modules (
    echo [*] node_modules bulunamadi, npm install calistiriliyor...
    call npm install
    if errorlevel 1 (
        echo [!] npm install basarisiz oldu!
        cd ..
        goto BUILD_FAILED
    )
)

echo.
echo [2/3] Frontend (React + Vite + TypeScript) -^> frontend\dist ...
call npm run build
if errorlevel 1 (
    echo [!] Frontend derleme hatasi!
    cd ..
    goto BUILD_FAILED
)
cd ..

if not exist "frontend\dist\index.html" (
    echo [!] frontend\dist olusmadi, embed durduruldu!
    goto BUILD_FAILED
)

echo.
echo [3/3] Embed (frontend\dist -^> backend\ui) ve go build ...
if exist "backend\ui" rmdir /s /q "backend\ui"
mkdir "backend\ui"
robocopy "frontend\dist" "backend\ui" /E /NFL /NDL /NJH /NJS /nc /ns /np
if %errorlevel% gtr 7 (
    echo [!] Embed kopyasi basarisiz!
    goto BUILD_FAILED
)

if not exist "build\bin" mkdir "build\bin"

pushd backend
go build -tags production,desktop -ldflags="-H windowsgui -s -w" -v -o "..\build\bin\vanta.exe" .
set BUILDERR=!errorlevel!
popd

if exist "build\bin\.env" del /q "build\bin\.env"

if !BUILDERR! neq 0 (
    echo [!] Go derleme hatasi!
    goto BUILD_FAILED
)

echo.
echo ========================================================
echo   [OK] DERLEME BASARIYLA TAMAMLANDI!
echo   Executable Konumu: build\bin\vanta.exe
echo ========================================================
goto MENU

:BUILD_FAILED
echo.
echo ========================================================
echo   [X] DERLEME HATASI OLUSTU!
echo ========================================================
goto MENU

:MENU
echo.
echo ========================================================
echo   [1] Tekrar build al
echo   [2] Konsoldan cikis yap
echo ========================================================
set /p "CHOICE=Seciminiz (1 veya 2): "

if "!CHOICE!"=="1" goto MAIN_BUILD
if "!CHOICE!"=="2" exit /b 0

echo.
echo [!] Gecersiz secim. Lutfen 1 veya 2 tuslayin.
goto MENU
