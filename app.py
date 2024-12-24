from flask import Flask, render_template, jsonify
import pyrebase
from sense_emu import SenseHat
import time
import numpy as np
import sqlite3

app = Flask(__name__)

# Cấu hình Firebase
config = {
  "apiKey": "AIzaSyBXy3suI4dmd0GFmvmtTOxKM1wMCdru_8I",
  "authDomain": "hoangvu-6f114.firebaseapp.com",
  "databaseURL": "https://hoangvu-6f114-default-rtdb.firebaseio.com",
  "projectId": "hoangvu-6f114",
  "storageBucket": "hoangvu-6f114.firebasestorage.app",
  "messagingSenderId": "662610250655",
  "appId": "1:662610250655:web:de868576392c18675f4baa",
  "measurementId": "G-7QHG2FLFBS"
};

# Khởi tạo Firebase và SenseHAT
firebase = pyrebase.initialize_app(config)
database = firebase.database()
sense = SenseHat()

# Cấu hình SQLite
db_connection = sqlite3.connect('/home/dhoangvu/BT/data.db')
cursor = db_connection.cursor()

# Tạo bảng nếu chưa có
cursor.execute('''
    CREATE TABLE IF NOT EXISTS temperature_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        temperature REAL,
        timestamp TEXT
    )
''')
db_connection.commit()

# Biến toàn cục
n = 5  # Kích thước lịch sử mảng
history = [0] * n  # Khởi tạo mảng lịch sử
previous_T = 0  # Giá trị T trước đó
temperature_change_threshold = 1  # Ngưỡng thay đổi nhiệt độ (1 độ)

# Hàm lưu dữ liệu vào SQLite
def save_to_sqlite(temp, timestamp):
    cursor.execute('''
        INSERT INTO temperature_history (temperature, timestamp)
        VALUES (?, ?)
    ''', (temp, timestamp))
    db_connection.commit()

# Hàm đọc dữ liệu và tối ưu gửi
def push_optimized_data():
    global history, previous_T  # Sử dụng biến toàn cục
    while True:
        try:
            # Đọc nhiệt độ hiện tại từ SenseHAT
            current_temp = round(sense.get_temperature(), 2)

            # Tính trung bình của lịch sử
            mean_temp = np.mean(history)

            # Tính T_cập_nhật
            T_cap_nhat = round((current_temp + mean_temp) / 2, 2)

            # So sánh sự thay đổi nhiệt độ với ngưỡng
            if abs(current_temp - previous_T) > temperature_change_threshold:
                # Gửi dữ liệu lên Firebase
                sensor_data = {
                    "temperature": T_cap_nhat,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                database.child("OptimizedSensorData").set(sensor_data)
                print("Đã gửi dữ liệu lên Firebase:", sensor_data)

                # Lưu vào SQLite
                save_to_sqlite(T_cap_nhat, sensor_data["timestamp"])

                # Cập nhật T
                previous_T = T_cap_nhat

            # Cập nhật mảng lịch sử
            history.pop(0)  # Xóa phần tử đầu tiên
            history.append(current_temp)  # Thêm giá trị mới vào cuối

            # In mảng lịch sử ra màn hình
            print("Lịch sử nhiệt độ:", history)
            time.sleep(5)

        except Exception as e:
            print("Lỗi xảy ra:", e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_data')
def get_data():
    # Trả về dữ liệu nhiệt độ hiện tại và độ ẩm (giả sử độ ẩm được tính hoặc lấy từ một nguồn khác)
    current_temp = round(sense.get_temperature(), 2)
    humidity = round(sense.get_humidity(), 2)  # Đo độ ẩm từ SenseHAT (giả sử)
    optimized_temp = round((current_temp + np.mean(history)) / 2, 2)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    return jsonify({
        'temperature': current_temp,
        'humidity': humidity,
        'optimized_temperature': optimized_temp,
        'timestamp': timestamp
    })

@app.route('/get_history')
def get_history():
    cursor.execute("SELECT temperature, timestamp FROM temperature_history ORDER BY id DESC LIMIT 5")
    rows = cursor.fetchall()
    return jsonify([{'temperature': row[0], 'timestamp': row[1]} for row in rows])

if __name__ == "__main__":
    # Lấy IP của Raspberry Pi
    import socket
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)

    print(f"Trang web có thể truy cập tại: http://{ip_address}:5000")

    # Chạy ứng dụng Flask
    app.run(host='0.0.0.0', port=5000, debug=True)
