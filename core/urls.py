from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.views.static import serve
from django.contrib.auth import views as auth_views
from news import views as news_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('news.urls')),

    # Media files route fallback
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),

    # Password Reset Flow (Brevo HTTPS REST API)
    path('password-reset/', news_views.password_reset_request_view, name='password_reset'),
    path('password-reset/done/', news_views.password_reset_done_view, name='password_reset_done'),
    path(
        'password-reset-confirm/<uidb64>/<token>/', 
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url='/password-reset-complete/'
        ), 
        name='password_reset_confirm'
    ),
    path(
        'password-reset-complete/', 
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ), 
        name='password_reset_complete'
    ),
]