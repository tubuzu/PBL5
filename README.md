# Driver-Drowsiness-Detection
Driver drowsiness detection là một dự án viết bằng Python, sử dụng thư viện Dlib và OpenCV và model shape_predictor_68_face_landmark để dự đoán các điểm đặc trưng trên khuôn mặt.

<b> <a href="http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2">Model model shape_predictor_68_face_landmark tải ở đây</a></B>

### Dependencies 
#### On server
`pip install numpy opencv-python dlib imutils flask`
#### On raspberry
`pip install numpy picamera pygame`

### Lưu ý
#### Cần thay đổi host ip của server bằng ip máy chủ trong file server.py và client.py

### Run
#### On server
`python server.py`
#### On raspberry
`python3 client.py`