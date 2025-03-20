@echo off
REM Check if venv folder exists
if not exist venv (
    echo Virtual environment not found. Creating one...
    python -m venv venv
    echo Virtual environment created successfully.
) else (
    echo Virtual environment already exists.
)

REM Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

REM Install dependencies from requirements.txt (if it exists)
if exist requirements.txt (
    echo Installing dependencies from requirements.txt...
    pip install -q -r requirements.txt
) else (
    echo requirements.txt not found. Skipping dependency installation.
)

REM Run the setup.py script
echo Running setup.py...
python setup.py

REM Deactivate the virtual environment (optional)
echo Deactivating virtual environment...
deactivate

REM Pause to see the output (optional)
pause