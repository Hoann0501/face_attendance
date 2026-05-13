@echo off
cd /d C:\Users\Hoannd\Downloads\data_face\Deploy
echo ============================================================
echo  Face Attendance Backend
echo  API:      http://127.0.0.1:8000
echo  Frontend: http://127.0.0.1:8000
echo  API docs: http://127.0.0.1:8000/docs
echo ============================================================
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
pause
