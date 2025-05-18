import json
import pytz
import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from firebase_admin import auth, firestore, db
import requests
from django.core.mail import send_mail
from django.conf import settings

# Initialize Firestore (giữ nguyên cho user data)
db_firestore = firestore.client()
FIREBASE_API_KEY = 'AIzaSyDZwUeNkjNGUpvsyz2S3PjqojQG0LozMo8'

# Tham chiếu đến Realtime Database (đã khởi tạo trong settings.py)
db_ref = db.reference('/')

def convert_timestamp_to_vn_time(timestamp):
    utc_time = datetime.datetime.utcfromtimestamp(timestamp)
    utc_time = utc_time.replace(tzinfo=pytz.UTC)
    vn_timezone = pytz.timezone('Asia/Ho_Chi_Minh')
    vn_time = utc_time.astimezone(vn_timezone)
    return vn_time.strftime('%d/%m/%Y %H:%M:%S')

@csrf_exempt
def signup(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')
            password_confirm = data.get('password_confirm')
            display_name = data.get('username')

            if password != password_confirm:
                return JsonResponse({
                    'error': 'Password and password_confirm do not match',
                    'required_fields': ['password', 'password_confirm']
                }, status=400)
            
            if not all([email, password, display_name]):
                return JsonResponse({
                    'error': 'Missing required fields',
                    'required_fields': ['email', 'password', 'username']
                }, status=400)

            user = auth.create_user(
                email=email,
                password=password,
                display_name=display_name
            )
            db_firestore.collection('users').document(user.uid).set({
                'email': email,
                'username': display_name
            })
            return JsonResponse({'uid': user.uid, 'email': user.email, 'username': display_name}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def login_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')

            if not all([email, password]):
                return JsonResponse({
                    'error': 'Missing required fields',
                    'required_fields': ['email', 'password']
                }, status=400)

            print("Login Payload:", {"email": email, "password": password})

            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }

            response = requests.post(url, json=payload)

            print("Firebase Response:", response.json())

            if response.status_code == 200:
                token = response.json().get('idToken')
                return JsonResponse({
                    'email': email,
                    'token': token
                })
            else:
                return JsonResponse({
                    'error': 'Invalid email or password',
                    'details': response.json()
                }, status=401)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def getMe(request):
    if request.method == 'GET':
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return JsonResponse({
                    'error': 'Missing or invalid Authorization header',
                    'required_format': 'Authorization: Bearer <token>'
                }, status=400)

            token = auth_header.split(' ')[1]

            try:
                decoded_token = auth.verify_id_token(token)
            except Exception as e:
                print("Token verification error:", str(e))
                return JsonResponse({'error': 'Invalid or expired token'}, status=401)

            uid = decoded_token['uid']

            user_ref = db_firestore.collection('users').document(uid)
            user_doc = user_ref.get()

            if user_doc.exists:
                user_data = user_doc.to_dict()
                return JsonResponse(user_data, status=200)
            else:
                return JsonResponse({'error': 'User not found'}, status=404)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def get_weather_data_daily(request):
    if request.method == 'GET':
        try:
            today = datetime.datetime.now().date()
            weather_data = db_ref.get()

            result = []
            if weather_data:
                for timestamp_str, data in weather_data.items():
                    try:
                        timestamp = int(timestamp_str)
                        timestamp_date = datetime.datetime.fromtimestamp(timestamp).date()
                        if timestamp_date == today:
                            result.append({
                                'timestamp': timestamp,
                                'formatted_timestamp': convert_timestamp_to_vn_time(timestamp),
                                'temp': data.get('temp'),
                                'humid': data.get('humid'),
                                'pressure': data.get('pressure'),
                                'pred': data.get('pred')
                            })
                    except (ValueError, TypeError):
                        continue

            if not result:
                return JsonResponse({'message': 'Không có dữ liệu nào thuộc hôm nay'}, status=404)

            return JsonResponse(result, safe=False, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def get_weather_data_by_date_range(request):
    if request.method == 'GET':
        try:
            # Lấy ngày từ query parameters
            start_date_str = request.GET.get('start_date')
            end_date_str = request.GET.get('end_date')

            if not start_date_str or not end_date_str:
                return JsonResponse({
                    'error': 'Missing required parameters',
                    'required_fields': ['start_date', 'end_date'],
                    'format': 'dd/mm/yyyy'
                }, status=400)

            # Chuyển đổi ngày thành timestamp Unix 
            def parse_date_to_timestamp(date_str):
                try:
                    date_obj = datetime.datetime.strptime(date_str, '%d/%m/%Y')
                    # Đặt giờ về 00:00:00
                    start_of_day = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
                    return int(start_of_day.timestamp())
                except ValueError:
                    raise ValueError('Invalid date format. Use dd/mm/yyyy')

            start_timestamp = parse_date_to_timestamp(start_date_str)
            end_timestamp = parse_date_to_timestamp(end_date_str)
            # Thêm 1 ngày cho end_timestamp để bao gồm toàn bộ ngày cuối
            end_timestamp += 24 * 60 * 60 - 1

            # Lấy dữ liệu từ Realtime Database
            weather_data = db_ref.get()

            # Lọc dữ liệu theo khoảng thời gian
            result = []
            if weather_data:
                for timestamp_str, data in weather_data.items():
                    try:
                        timestamp = int(timestamp_str)
                        if start_timestamp <= timestamp <= end_timestamp:
                            result.append({
                                'timestamp': timestamp,
                                'formatted_timestamp': convert_timestamp_to_vn_time(timestamp),
                                'temp': data.get('temp'),
                                'humid': data.get('humid'),
                                'pressure': data.get('pressure'),
                                'pred': data.get('pred')
                            })
                    except (ValueError, TypeError):
                        continue

            if not result:
                return JsonResponse({'message': 'Không có dữ liệu trong khoảng thời gian này'}, status=404)

            return JsonResponse(result, safe=False, status=200)

        except ValueError as ve:
            return JsonResponse({'error': str(ve)}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

import os
from django.core.mail import send_mail
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def send_alert_email(request):
    if request.method == 'POST':
        try:
            # Lấy dữ liệu từ body yêu cầu
            data = json.loads(request.body)
            temp_threshold = data.get('temp_threshold')
            humid_threshold = data.get('humid_threshold')
            pressure_threshold = data.get('pressure_threshold')
            email_to = data.get('email_to')

            # Kiểm tra các trường bắt buộc
            if not all([temp_threshold, humid_threshold, pressure_threshold, email_to]):
                return JsonResponse({
                    'error': 'Missing required fields',
                    'required_fields': ['temp_threshold', 'humid_threshold', 'pressure_threshold', 'email_to']
                }, status=400)

            # Chuyển đổi ngưỡng thành float
            try:
                temp_threshold = float(temp_threshold)
                humid_threshold = float(humid_threshold)
                pressure_threshold = float(pressure_threshold)
            except (ValueError, TypeError):
                return JsonResponse({'error': 'Thresholds must be numeric values'}, status=400)

            # Lấy dữ liệu từ Realtime Database
            try:
                weather_data = db_ref.get()
                if not weather_data:
                    return JsonResponse({'error': 'No weather data available'}, status=404)
            except Exception as e:
                return JsonResponse({'error': f'Failed to fetch weather data: {str(e)}'}, status=500)

            # Tìm bản ghi mới nhất (dựa trên timestamp lớn nhất)
            try:
                # Ensure all keys are properly processed as strings first
                timestamps = list(weather_data.keys())
                
                # Convert timestamps to integers for comparison
                int_timestamps = [int(ts) for ts in timestamps]
                latest_timestamp = max(int_timestamps)
                
                # Get the original string key that corresponds to the max timestamp
                latest_key = timestamps[int_timestamps.index(latest_timestamp)]
                latest_data = weather_data[latest_key]
                
            except Exception as e:
                return JsonResponse({'error': f'Error processing timestamps: {str(e)}'}, status=400)

            # Lấy các giá trị thời tiết
            try:
                temp = float(latest_data.get('temp', 0))
                humid = float(latest_data.get('humid', 0))
                pressure = float(latest_data.get('pressure', 0))
            except (ValueError, TypeError) as e:
                return JsonResponse({'error': f'Invalid weather data format: {str(e)}'}, status=400)

            # Kiểm tra điều kiện vượt ngưỡng
            if not (temp >= temp_threshold or humid >= humid_threshold or pressure >= pressure_threshold):
                return JsonResponse({
                    'message': 'No alerts triggered based on the thresholds',
                    'current_values': {
                        'timestamp': latest_timestamp,
                        'formatted_timestamp': convert_timestamp_to_vn_time(latest_timestamp),
                        'temp': temp,
                        'humid': humid,
                        'pressure': pressure
                    }
                }, status=200)

            # Gửi email cảnh báo
            subject = 'Weather Alert Notification'
            message = (
                f"Weather Alert at {convert_timestamp_to_vn_time(latest_timestamp)}:\n\n"
                f"Temperature: {temp} °C (Threshold: {temp_threshold} °C)\n"
                f"Humidity: {humid} % (Threshold: {humid_threshold} %)\n"
                f"Pressure: {pressure} hPa (Threshold: {pressure_threshold} hPa)\n\n"
                "Please take necessary actions."
            )

            # Sử dụng cấu hình email từ settings
            sender_email = settings.EMAIL_HOST_USER

            if not sender_email:
                return JsonResponse({
                    'error': 'Email configuration is missing. Please set EMAIL_HOST_USER in environment variables.'
                }, status=500)

            send_mail(
                subject,
                message,
                sender_email,
                [email_to],
                fail_silently=False,
            )

            return JsonResponse({
                'message': 'Alert email sent successfully',
                'alert_data': {
                    'timestamp': latest_timestamp,
                    'formatted_timestamp': convert_timestamp_to_vn_time(latest_timestamp),
                    'temp': temp,
                    'humid': humid,
                    'pressure': pressure
                }
            }, status=200)

        except Exception as e:
            # Improved error logging
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in send_alert_email: {error_details}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)