@echo off
cd /d "%~dp0.."
if "%BACKEND_PORT%"=="" set BACKEND_PORT=8000
echo ============================================================
echo  Face Attendance Backend
echo  May nay (local):   http://127.0.0.1:%BACKEND_PORT%/
echo  May khac cung LAN: http://CAN_IP_MAY_NAY:%BACKEND_PORT%/   ^(go ipconfig - tim IPv4^)
echo  API docs:          http://127.0.0.1:%BACKEND_PORT%/docs
echo  ---
echo  Lang nghe 0.0.0.0 de demo. Neu bi chan: Firewall ^> cho phep Python hoac cong %BACKEND_PORT%
echo ============================================================
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port %BACKEND_PORT%
pause
