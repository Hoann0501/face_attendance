@echo off
cd /d C:\Users\Hoannd\Downloads\data_face\Deploy
echo Starting Attendance Camera ...
echo Press I for CHECK-IN mode, O for CHECK-OUT mode, Q to quit.
python camera_app/attendance_camera.py --mode checkin
pause
