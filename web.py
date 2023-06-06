from flask import Flask, render_template, request, Response, jsonify
import os
import firebase_admin
from firebase_admin import credentials, db
# from PIL import Image
import time

cred = credentials.Certificate("firebase/driver-4bbdf-firebase-adminsdk-ja22n-815c025c70.json")
firebase_admin.initialize_app(cred,{
'databaseURL':
'https://driver-4bbdf-default-rtdb.asia-southeast1.firebasedatabase.app'
})

app = Flask(__name__)

image_path = 'images/image.jpg'
cur_image = None
with open('images/white.jpg', 'rb') as f:
    cur_image = f.read()

@app.route('/frame', methods=['POST'])
def receive_frame():
    global cur_image
    # Get the image file from the POST request
    uploaded_file = request.files['image']
    cur_image = uploaded_file.read()
    response = jsonify(message="ok")
    return response

def generate_frames():
    # global cur_image
    while True:
        yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + cur_image + b'\r\n')

@app.route('/')
def index():
    return render_template('base.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/camera')
def camera():
    return render_template('camera.html')

@app.route('/frequency')
def frequency():
    return render_template('frequency.html')

@app.route('/history')
def history():
    history_ref = db.reference('times')
    history_data = reversed(list(history_ref.get().values()))
    return render_template('history.html', history_data=history_data)
if __name__ == '__main__':
    app.run(debug=True, port = 5000)