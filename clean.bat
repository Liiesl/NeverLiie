@echo off
:: This prevents commands from being displayed as they are executed.

title Python Cache Cleaner

echo Cleaning Python build and cache files...
echo.

:: -----------------------------------------------------------------
::  Build a list of items to ignore from .gitignore
:: -----------------------------------------------------------------
set "IGNORE_LIST="
if exist ".gitignore" (
    echo Found .gitignore, building ignore list...
    for /f "usebackq delims=" %%i in (".gitignore") do (
        set "IGNORE_LIST=!IGNORE_LIST! %%i"
    )
)

:: -----------------------------------------------------------------
::  1. Remove __pycache__ directories
::
::  The 'for' loop searches for directories (/d) recursively (/r).
::  It now includes checks to skip directories that start with a '.'
::  or are listed in the .gitignore file.
:: -----------------------------------------------------------------
echo Removing __pycache__ directories...
setlocal enabledelayedexpansion
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        set "dir_name=%%~nd"
        set "first_char=!dir_name:~0,1!"
        set "should_delete=true"

        if "!first_char!" == "." (
            set "should_delete=false"
        )

        for %%i in (%IGNORE_LIST%) do (
            if "%%~i" == "!dir_name!" (
                set "should_delete=false"
            )
        )

        if !should_delete! == true (
            rd /s /q "%%d"
        ) else (
            echo Skipping ignored directory: %%d
        )
    )
)
endlocal


:: -----------------------------------------------------------------
::  2. Remove .pyc files
::
::  The 'for' loop recursively finds all .pyc files.
::  It now checks if the file name starts with a '.' or if the file
::  is listed in .gitignore before deleting.
:: -----------------------------------------------------------------
echo Removing .pyc files...
setlocal enabledelayedexpansion
for /r . %%f in (*.pyc) do (
    if exist "%%f" (
        set "file_name=%%~nf"
        set "first_char=!file_name:~0,1!"
        set "should_delete=true"

        if "!first_char!" == "." (
            set "should_delete=false"
        )

        for %%i in (%IGNORE_LIST%) do (
            if "%%~i" == "!file_name!%%~xf" (
                set "should_delete=false"
            )
        )

        if !should_delete! == true (
            del /q "%%f"
        ) else (
            echo Skipping ignored file: %%f
        )
    )
)
endlocal


echo.
echo Cleaning complete.

:: The 'pause' command will wait for a key press before closing the window.
:: This is useful if you double-click the file to run it.
pause