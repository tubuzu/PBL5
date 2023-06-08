# import thư viện
import io
import socket
import struct
import time
import picamera
import pygame
import threading

# Đường dẫn file âm thanh
path = "music.wav"
# Khởi tạo trình phát nhạc pygame
pygame.mixer.init()
# Âm lượng ban đầu của nhạc cảnh báo
volume = 0.3
# Thiết lập âm lượng ban đầu cho nhạc cảnh báo
pygame.mixer.music.set_volume(volume)
# Load tệp nhạc
pygame.mixer.music.load(path)

# Kích thước buffer nhận dữ liệu từ server
BUFF_SIZE = 65536
# Khởi tạo socket client
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Kết nối đến địa chỉ và cổng của máy chủ
client_socket.connect(("192.168.25.102", 9999))

# frame buffer để lưu trữ thông tin về tình trạng mắt của tài xế (đóng hay mở)
frame_buffer = []
# Số frame tối thiểu cần để xác định tình trạng ngủ gật
drowsy_threshold = 4
# Số khung hình dùng để kiểm tra tình trạng ngủ gật
frame_check = 10

# Biến trạng thái để kiểm soát việc phát nhạc cảnh báo
can_play = False
# Mức độ ngủ gật
sleep_count = 0
# Thời gian của lần cuối cùng tài xế bị cảnh báo ngủ gật
last_sleep_time = 0

# Tạo một kết nối đọc/ghi với socket
connection = client_socket.makefile('rwb')

# Hàm kiểm tra tình trạng ngủ gật dựa trên 10 frame gần nhất
def is_drowsy():
    return sum(frame_buffer) >= drowsy_threshold and frame_buffer[-1] == 1

# Hàm phát nhạc cảnh báo
def play_music():
    global can_play
    global volume
    while True:
        if can_play and not pygame.mixer.music.get_busy():
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops=1)
        time.sleep(0.1)

# Hàm chụp ảnh từ camera và gửi lên server để xác định tình trạng ngủ gật
def capture_loop():
    global frame_buffer
    global can_play
    global volume
    global sleep_count
    global last_sleep_time
    with picamera.PiCamera() as camera:
        # Thiết lập camera
        camera.resolution = (640, 480)
        camera.framerate = 60
        print("Starting Camera...........")
        time.sleep(1)
        stream = io.BytesIO()
        for foo in camera.capture_continuous(stream, 'jpeg'):
            # Gửi ảnh lên server
            connection.write(struct.pack('<L', stream.tell()))
            connection.flush()
            stream.seek(0)
            connection.write(stream.read())
            stream.seek(0)
            stream.truncate(0)
            # Nhận kết quả từ server và lưu trữ vào frame_buffer
            data, _ = client_socket.recvfrom(BUFF_SIZE)
            x = data.decode('utf-8')
            frame_buffer.append(1 if x == 'drowsy' else 0)
            if len(frame_buffer) >= frame_check:
                frame_buffer = frame_buffer[-frame_check:]
            
            # Kiểm tra tình trạng ngủ gật và điều khiển việc phát nhạc cảnh báo
            time_gap = time.time() - last_sleep_time

            if is_drowsy():
                if time_gap <= 10 or time_gap >= 3:
                    sleep_count += 1
                last_sleep_time = time.time()
                can_play = True
            elif not is_drowsy():
                # Không ngủ gật
                if time_gap > 10:
                    sleep_count = 0
                    volume = 0.4
                can_play = False

            # In ra các thông tin cần thiết để theo dõi quá trình chạy chương trình
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

# Tạo một luồng riêng để phát nhạc cảnh báo
play_thread = threading.Thread(target=play_music)
play_thread.start()

# Chạy vòng lặp chính để chụp ảnh và xác định tình trạng ngủ gật
capture_loop()