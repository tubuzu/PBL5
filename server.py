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
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime

cred = credentials.Certificate("firebase/driver-4bbdf-firebase-adminsdk-ja22n-815c025c70.json")
firebase_admin.initialize_app(cred,{
'databaseURL':
'https://driver-4bbdf-default-rtdb.asia-southeast1.firebasedatabase.app'
})
now = datetime.now()
now_time = now.strftime("%H:%M:%S")
now_date = now.strftime("%d/%m/%Y")
time_node = db.reference('times').push()
time_dr=''
def add_time(time):
    time_node.set(time)
    return ''

def eye_aspect_ratio(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    ear = (A + B) / (2.0 * C)
    return ear

detect = dlib.get_frontal_face_detector()
predict = dlib.shape_predictor("models/shape_predictor_68_face_landmarks.dat")

(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_68_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_68_IDXS["right_eye"]

host_ip = "0.0.0.0"
port = 9999
server_socket = socket.socket()
server_socket.bind((host_ip, port))
server_socket.listen(0)
print("Listening")

client_socket, client_address = server_socket.accept()
print("Client connected from {}:{}".format(client_address[0], client_address[1]))
connection = client_socket.makefile('rwb')

thresh = 0.27
frame_buffer = []
drowsy_threshold = 4
frame_check = 10

# Flask server details
flask_host = '127.0.0.1'  # Replace with the actual IP address of the Flask server
flask_port = 5000  # Replace with the actual port of the Flask server

# Function to send the request
def send_request(img_encoded):
    try:
        requests.post(f"http://{flask_host}:{flask_port}/frame", files={"image": img_encoded})
    except requests.exceptions.RequestException as e:
        # Handle the exception here
        pass

try:
    while True:
        data = connection.read(struct.calcsize('<L'))
        image_len = 0
        if len(data) == struct.calcsize('<L'):
            image_len = struct.unpack('<L', data)[0]
        else:
            break
        if image_len == 0:
            break

        image_stream = io.BytesIO()
        image_stream.write(connection.read(image_len))
        image_stream.seek(0)
        image = Image.open(image_stream)
        frame = np.array(image)
        frame = imutils.resize(frame, width=450)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        subjects = detect(gray, 0)

        if len(subjects):
            for subject in subjects:
                shape = predict(gray, subject)
                shape = face_utils.shape_to_np(shape)

                leftEye = shape[lStart:lEnd]
                rightEye = shape[rStart:rEnd]
                leftEAR = eye_aspect_ratio(leftEye)
                rightEAR = eye_aspect_ratio(rightEye)
                ear = (leftEAR + rightEAR) / 2.0

                leftEyeHull = cv2.convexHull(leftEye)
                rightEyeHull = cv2.convexHull(rightEye)
                cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
                cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)

                print("EAR: " + str(ear))

                message = ""
                if ear < thresh:
                    frame_buffer.append(1)
                    message = "drowsy"
                    connection.write(message.encode())
                    connection.flush()
                else:
                    frame_buffer.append(0)
                    message = "awake"
                    connection.write(message.encode())
                    connection.flush()

                print("State: " + str(message))

        else:
            message = "not recognized"
            connection.write(message.encode())
            connection.flush()
        
        print("State: " + str(message))

        if len(frame_buffer) > frame_check:
            frame_buffer = frame_buffer[-frame_check:]

        num_closed = sum(frame_buffer)

        if num_closed >= drowsy_threshold and frame_buffer[-1] == 1:
            time_dr=now_time
            cv2.putText(frame, "****************ALERT!****************", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, "****************ALERT!****************", (10, 325),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:  
            add_time({
                'time_drowsy' : time_dr,
                'time_awake': now_time,
                'date': now_date
            })
        # Send frame to Flask server
        _, img_encoded = cv2.imencode('.jpg', frame)
        request_thread = Thread(target=send_request, args=(img_encoded,))
        request_thread.start()
        cv2.imshow('Video', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

finally:
    connection.close()
    server_socket.close()