@echo off
cd /d C:\Users\Hoannd\Downloads\data_face\Deploy
echo ============================================================
echo  Attendance Camera - CHECK-OUT mode
echo  Keys: I=CheckIn  O=CheckOut  Q=Quit
echo  Tip: add --camera 0 (or 1, 2) to skip camera selection
echo ============================================================
python camera_app/attendance_camera.py --mode checkout %*
pause
