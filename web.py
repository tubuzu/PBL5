from flask import Flask, render_template, request, Response, jsonify
import os
# from PIL import Image
import time

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
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True, port = 5000)