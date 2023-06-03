from flask import Flask, render_template, Response
import cv2
import imutils
from scipy.spatial import distance
from imutils import face_utils
import dlib

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

thresh = 0.27

drowsy_threshold = 4
frame_check = 10

app = Flask(__name__)
cap = cv2.VideoCapture(0)

def generate_frames():
    frame_buffer = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
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

                print("EAR :" + str(ear))

                message = ""
                if ear < thresh:
                    frame_buffer.append(1)
                    message = "drowsy"
                else:
                    frame_buffer.append(0)
                    message = "awake"

                print("State: " + str(message))
        else:
            message = "not recognized"

        if len(frame_buffer) > frame_check:
            frame_buffer = frame_buffer[-frame_check:]

        num_closed = sum(frame_buffer)

        if num_closed >= drowsy_threshold and frame_buffer[-1] == 1:
            cv2.putText(frame, "****************ALERT!****************", (10, 30),cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, "****************ALERT!****************", (10,325),cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        frameToDisplay = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frameToDisplay + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True, port = 8888)