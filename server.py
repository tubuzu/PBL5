# import thư viện
import io
import socket
import struct
from PIL import Image
import cv2
import numpy as np
import imutils
import requests
from threading import Thread

from scipy.spatial import distance
from imutils import face_utils
import dlib

# Hàm tính khoảng cách EAR
def eye_aspect_ratio(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    ear = (A + B) / (2.0 * C)
    return ear

# Hàm phát hiện khuôn mặt và nhận diện các đặc trưng khuôn mặt
detect = dlib.get_frontal_face_detector()
predict = dlib.shape_predictor("models/shape_predictor_68_face_landmarks.dat")

# Vị trí của các điểm đặc trưng mắt
(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_68_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_68_IDXS["right_eye"]

# Địa chỉ IP và cổng của máy chủ
host_ip = "0.0.0.0"
port = 9999

# Khởi tạo socket server
server_socket = socket.socket()
server_socket.bind((host_ip, port))
server_socket.listen(0)
print("Listening")

# Chấp nhận kết nối từ client
client_socket, client_address = server_socket.accept()
print("Client connected from {}:{}".format(client_address[0], client_address[1]))
connection = client_socket.makefile('rwb')

# Ngưỡng EAR để xác định trạng thái mắt ngủ gật
thresh = 0.25
# frame buffer để lưu trữ thông tin về tình trạng mắt của tài xế (đóng hay mở)
frame_buffer = []
# Số frame tối thiểu cần để xác định tình trạng ngủ gật
drowsy_threshold = 4
# Số khung hình dùng để kiểm tra tình trạng ngủ gật
frame_check = 10
# Biến trạng thái có đang cảnh báo ngủ gật hay không
warning = False

# Flask server details
flask_host = '127.0.0.1'  # Replace with the actual IP address of the Flask server
flask_port = 5000  # Replace with the actual port of the Flask server

# Hàm gửi post request gồm biến warning và ảnh đến flask server
def send_request(img_encoded):
    try:
        data = {
            'warning': warning
        }
        requests.post(f"http://{flask_host}:{flask_port}/frame", files={"image": img_encoded}, data=data)
    except requests.exceptions.RequestException as e:
        # Handle the exception here
        pass

try:
    while True:
        # Đọc kích thước ảnh từ kết nối
        data = connection.read(struct.calcsize('<L'))
        image_len = 0
        if len(data) == struct.calcsize('<L'):
            image_len = struct.unpack('<L', data)[0]
        else:
            break
        if image_len == 0:
            break

        # Đọc dữ liệu ảnh từ kết nối
        image_stream = io.BytesIO()
        image_stream.write(connection.read(image_len))
        image_stream.seek(0)
        image = Image.open(image_stream)

        # Chuyển đổi ảnh sang mảng numpy và điều chỉnh kích thước
        frame = np.array(image)
        frame = imutils.resize(frame, width=450)

        # Chuyển đổi sang ảnh grayscale và tìm kiếm khuôn mặt
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        subjects = detect(gray, 0)

        if len(subjects):
            for subject in subjects:
                # Dự đoán các điểm đặc trưng khuôn mặt
                shape = predict(gray, subject)
                shape = face_utils.shape_to_np(shape)

                # Xác định mắt trái và mắt phải
                leftEye = shape[lStart:lEnd]
                rightEye = shape[rStart:rEnd]

                # Tính toán tỷ lệ khung mắt
                leftEAR = eye_aspect_ratio(leftEye)
                rightEAR = eye_aspect_ratio(rightEye)
                ear = (leftEAR + rightEAR) / 2.0

                # Vẽ đường biên quanh mắt lên khung hình
                leftEyeHull = cv2.convexHull(leftEye)
                rightEyeHull = cv2.convexHull(rightEye)
                cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
                cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)

                print("EAR: " + str(ear))

                message = ""
                if ear < thresh:
                    # Mắt nhắm
                    frame_buffer.append(1)
                    message = "drowsy"
                    connection.write(message.encode())
                    connection.flush()
                else:
                    # Mắt mở
                    frame_buffer.append(0)
                    message = "awake"
                    connection.write(message.encode())
                    connection.flush()

                print("State: " + str(message))

        else:
            # Không nhận diện được khuôn mặt
            message = "not recognized"
            connection.write(message.encode())
            connection.flush()
        
        print("State: " + str(message))

        # Nếu độ dài frame_buffer lớn hơn frame_check thì rút gọn lại
        if len(frame_buffer) > frame_check:
            frame_buffer = frame_buffer[-frame_check:]

        # Số lần mắt nhắm trong frame_check khung hình
        num_closed = sum(frame_buffer)

        if num_closed >= drowsy_threshold and frame_buffer[-1] == 1:
            # Cảnh báo khi ngủ gật
            cv2.putText(frame, "****************ALERT!****************", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, "****************ALERT!****************", (10, 325),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            warning = True
        else:
            warning = False
            
        # Gửi khung hình tới Flask server
        _, img_encoded = cv2.imencode('.jpg', frame)
        request_thread = Thread(target=send_request, args=(img_encoded,))
        request_thread.start()

        # Hiển thị khung hình
        cv2.imshow('Video', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

finally:
    connection.close()
    server_socket.close()