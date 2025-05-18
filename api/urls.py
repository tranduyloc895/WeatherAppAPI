from django.urls import path
from .views import signup, login_user, getMe, get_weather_data_daily, get_weather_data_by_date_range, send_alert_email

urlpatterns = [
    path('signup/', signup, name='signup'),
    path('login/', login_user, name='login'),
    path('getMe/', getMe, name='getMe'),
    path('weather/daily/', get_weather_data_daily, name='get_weather_data_daily'),
    path('weather/getDayRange/', get_weather_data_by_date_range, name='get_weather_date_range'),
    path('send_alert_email/', send_alert_email, name='send_alert'),

]