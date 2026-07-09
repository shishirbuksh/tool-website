$env:PYTHONPATH = "G:\tool"
Set-Location "G:\tool"
& "G:\tool\venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8090 --reload
