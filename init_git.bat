@echo off
REM Git initialization script for Windows

echo ================================
echo  Git Initialization for Pick-My-Child
echo ================================
echo.

cd C:\Dev\pickmychild

echo [1/8] Removing old git repository...
if exist .git (
    rmdir /s /q .git
    echo       Old git removed
) else (
    echo       No old git found
)
echo.

echo [2/8] Initializing new git repository...
git init
echo.

echo [3/8] Configuring git user...
git config user.name "Roei Birger"
REM Replace with your email:
git config user.email "roei.birger@example.com"
echo       User configured
echo.

echo [4/8] Adding GitHub remote...
git remote add origin https://github.com/roei-birger/Pick-My-Child.git
echo       Remote added
echo.

echo [5/8] Adding all files...
git add .
echo       Files added
echo.

echo [6/8] Creating initial commit...
git commit -m "Initial commit - pickmychild bot v1.0"
if %errorlevel% == 0 (
    echo       Commit created
) else (
    echo       ERROR: Commit failed!
    pause
    exit /b 1
)
echo.

echo [7/8] Setting main branch...
git branch -M main
echo       Branch set to main
echo.

echo [8/8] Pushing to GitHub...
echo       This will replace everything in GitHub!
echo.
pause
git push -f origin main
if %errorlevel% == 0 (
    echo       SUCCESS! Code pushed to GitHub
) else (
    echo       ERROR: Push failed!
    echo       You may need to authenticate with GitHub
    pause
    exit /b 1
)
echo.

echo ================================
echo  DONE! Check your repository:
echo  https://github.com/roei-birger/Pick-My-Child
echo ================================
echo.

pause
