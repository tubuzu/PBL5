import io
import socket
import struct
import time
import picamera
import pygame
import threading
path = "music.wav"
pygame.mixer.init()
speaker_volume = 0.5
pygame.mixer.music.set_volume(speaker_volume)
pygame.mixer.music.load(path)
BUFF_SIZE = 65536
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(("192.168.25.102", 9999))
frame_buffer = []
drowsy_threshold = 4
frame_check = 10
can_play = False
volume = 0.3
sleep_count = 0
last_sleep_time = 0
connection = client_socket.makefile('rwb')

def is_drowsy():
    return sum(frame_buffer) >= drowsy_threshold and frame_buffer[-1] == 1

def play_music():
    global can_play
    global volume
    while True:
        if can_play and not pygame.mixer.music.get_busy():
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops=1)
        time.sleep(0.1)

def capture_loop():
    global frame_buffer
    global can_play
    global volume
    global sleep_count
    global last_sleep_time
    with picamera.PiCamera() as camera:
        camera.resolution = (640, 480)
        camera.framerate = 60
        print("Starting Camera...........")
        time.sleep(1)
        stream = io.BytesIO()
        for foo in camera.capture_continuous(stream, 'jpeg'):
            connection.write(struct.pack('<L', stream.tell()))
            connection.flush()
            stream.seek(0)
            connection.write(stream.read())
            stream.seek(0)
            stream.truncate(0)
            data, _ = client_socket.recvfrom(BUFF_SIZE)
            x = data.decode('utf-8')
            frame_buffer.append(1 if x == 'drowsy' else 0)
            if len(frame_buffer) >= frame_check:
                frame_buffer = frame_buffer[-frame_check:]
            
            time_gap = time.time() - last_sleep_time

            if is_drowsy():
                if time_gap <= 10 or time_gap >= 3:
                    sleep_count += 1
                last_sleep_time = time.time()
                can_play = True
            elif not is_drowsy():
                # Không ngủ gục
                if time_gap > 10:
                    sleep_count = 0
                    volume = 0.4
                can_play = False

            print("frame buffer: " + str(frame_buffer))
            print("số lần nhắm mắt: " + str(sum(frame_buffer)))
                
            if sleep_count == 1:
                # Phát âm thanh cảnh báo volume mức độ 1
                volume = 0.3
            elif sleep_count == 4:
                # Phát âm thanh cảnh báo volume mức độ 2
                volume = 0.65
            elif sleep_count == 8:
                # Phát âm thanh cảnh báo volume mức độ 3
                volume = 1
            
            print("volume: " + str(volume))
        connection.close()
        client_socket.close()
play_thread = threading.Thread(target=play_music)
play_thread.start()
capture_loop()