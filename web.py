from flask import Flask, render_template, request, Response, jsonify
import os
import firebase_admin
from firebase_admin import credentials, db
# from PIL import Image
import time

from datetime import datetime

import json

cred = credentials.Certificate("firebase/driver-4bbdf-firebase-adminsdk-ja22n-815c025c70.json")
firebase_admin.initialize_app(cred,{
'databaseURL':
'https://driver-4bbdf-default-rtdb.asia-southeast1.firebasedatabase.app'
})
now = datetime.now()
now_time = now.strftime("%H:%M:%S")
now_date = now.strftime("%d/%m/%Y")
time_node = db.reference('times').push()
drowsy_time=[]
awake_time=[]
warning = False

def add_time(time):
    time_node.set(time)
    print("OK")
    return ''

app = Flask(__name__)

image_path = 'images/image.jpg'
cur_image = None
with open('images/white.jpg', 'rb') as f:
    cur_image = f.read()

@app.route('/frame', methods=['POST'])
def receive_frame():
    global drowsy_time
    global awake_time
    global cur_image
    global warning
    # Get the image file from the POST request
    uploaded_file = request.files['image']

    was_warning = warning
    #warning = json.loads(is_drowsy_str)
    #warning = request.form.get('warning')
    warning = str(request.form.get('warning')).lower() == "true"
    print("warning: "+ str(warning))
    print("waswarning: "+ str(was_warning))
    print(warning==False)
    print(was_warning==False)
    print(warning==True and  was_warning==False)
    if warning==True and  was_warning==False:
        print(warning)
        drowsy_time = [now_time, now_date]
    elif not warning and was_warning:
        print(warning)
        awake_time = [now_time, now_date]
    else:
        drowsy_time=[]
        awake_time=[]
    if len(drowsy_time)!=0 and len(awake_time)!=0:
        print(now_time)
        add_time({
                'time_drowsy' : drowsy_time[0],
                'date_drowsy': drowsy_time[1],
                'time_awake': awake_time[0],
                'date_awake': awake_time[1],
            })
        drowsy_time = []
        awake_time = []

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