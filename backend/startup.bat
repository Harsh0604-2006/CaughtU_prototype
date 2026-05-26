@echo off
REM Startup script for Red Agent (Windows)

echo ================================
echo Caught U! - Red Agent Startup
echo ================================
echo.

REM Check Python
echo Checking Python installation...
python --version
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.9+
    exit /b 1
)

REM Check .env file
echo.
echo Checking environment configuration...
if not exist ".env" (
    echo Warning: .env file not found. Creating from template...
    copy .env.example .env
    echo Created .env (please fill in your credentials)
    echo.
    echo Edit .env and add:
    echo   - NEO4J_URI
    echo   - NEO4J_USERNAME
    echo   - NEO4J_PASSWORD
    echo   - CLAUDE_API_KEY
    echo.
    exit /b 1
)

echo .env file found

REM Create data directory
echo.
echo Creating data directory...
if not exist "data" mkdir data
echo data\ directory ready

REM Install dependencies
echo.
echo Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    exit /b 1
)

echo Dependencies installed

REM Test Neo4j connection
echo.
echo Testing Neo4j connection...
python -c "
from neo4j_client import Neo4jClient
import sys
try:
    client = Neo4jClient()
    if client.check_connection():
        print('Neo4j connection successful')
        client.close()
    else:
        print('Neo4j connection failed')
        sys.exit(1)
except Exception as e:
    print(f'Error: {str(e)}')
    sys.exit(1)
"
if errorlevel 1 (
    echo Error: Neo4j connection test failed
    exit /b 1
)

echo.
echo ================================
echo All checks passed!
echo ================================
echo.
echo To start the API server, run:
echo   python -m uvicorn main:app --reload
echo.
echo Or to run examples, run:
echo   python example_usage.py
echo.
pause
