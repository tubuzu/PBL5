from flask import Flask, render_template, request, Response, jsonify
import os
import firebase_admin
from firebase_admin import credentials, db
# from PIL import Image
import time
import matplotlib.pyplot as plt
import io
import base64
import matplotlib as mpl
mpl.use('Agg')

from datetime import datetime, timedelta

cred = credentials.Certificate("firebase/driver-4bbdf-firebase-adminsdk-ja22n-815c025c70.json")
firebase_admin.initialize_app(cred,{
'databaseURL':
'https://driver-4bbdf-default-rtdb.asia-southeast1.firebasedatabase.app'
})
now = datetime.now()
now_time = now.strftime("%H:%M:%S")
now_date = now.strftime("%d/%m/%Y")
drowsy_time = []
awake_time = []
warning = False
def add_time(time):
    time_node = db.reference('times').push()
    time_node.set(time)
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
    warning = str(request.form.get('warning')).lower() == "true"
    if warning and not was_warning:
        drowsy_time = [datetime.now().strftime("%H:%M:%S"), datetime.now().strftime("%d/%m/%Y")]
    if not warning and was_warning:
        awake_time = [datetime.now().strftime("%H:%M:%S"), datetime.now().strftime("%d/%m/%Y")]
        add_time({
                'time_drowsy' : drowsy_time[0],
                'date_drowsy': drowsy_time[1],
                'time_awake': awake_time[0],
                'date_awake': awake_time[1],
            })
        drowsy_time = []
        awake_time = []

    # if len(drowsy_time) == 2 and len(awake_time) == 2:

    cur_image = uploaded_file.read()
    response = jsonify(message="ok")
    return response

def generate_frames():
    global cur_image
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

@app.route('/history')
def history():
    history_ref = db.reference('times')
    history_data = reversed(list(history_ref.get().values()))
    return render_template('history.html', history_data=history_data)

@app.route('/frequency', methods=['GET', 'POST'])
def frequency():
    history_ref = db.reference('times')
    history_data = history_ref.get()

    days = int(request.form.get('days', 1))
    today = datetime.now().date()
    three_days_ago = today - timedelta(days=days)

    filtered_data = []

    for data in history_data.values():
        dated = datetime.strptime(data['date_drowsy'], '%d/%m/%Y').date()
        if dated >= three_days_ago and dated <= today:
            filtered_data.append(data)
    nap_count = [0] * 24

    # Tính toán tổng số lần ngủ gật cho từng giờ trong ngày
    for data in filtered_data:
        date = datetime.strptime(data['date_drowsy'], '%d/%m/%Y').date()
        hour = datetime.strptime(data['time_drowsy'], '%H:%M:%S').hour
        nap_count[hour] += 1

    # Vẽ biểu đồ cột thống kê số lần ngủ gật theo từng giờ trong ngày
    plt.bar(range(24), nap_count)

    # Đặt tên cho trục x và trục y
    plt.xlabel('Giờ trong ngày')
    plt.ylabel('Tổng số lần ngủ gật')

    # Lưu biểu đồ vào một tệp ảnh và trả về ở dạng HTML
    figfile = io.BytesIO()
    plt.savefig(figfile, format='png')
    figfile.seek(0)
    figdata_png = base64.b64encode(figfile.getvalue()).decode('ascii')
    plt.close()

    return render_template('frequency.html', figdata_png=figdata_png)
if __name__ == '__main__':
    app.run(debug=True, port = 5000)