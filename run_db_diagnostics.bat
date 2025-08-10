@echo off
echo ========================================
echo Othello Coach Database Diagnostics
echo ========================================
echo.

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Running quick database check...
python quick_db_check.py

echo.
echo ========================================
echo Quick check complete!
echo ========================================
echo.
echo To run full diagnostic: python db_diagnostic.py
echo To fix issues: python fix_db_issues.py
echo.
pause
