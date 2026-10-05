from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.views.static import serve
from django.views.generic.base import RedirectView, TemplateView
from django.contrib.staticfiles.storage import staticfiles_storage
from django.contrib.auth import views as auth_views
from news import views as news_views
from news.sitemaps import ArticleSitemap, CategorySitemap, StaticViewSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'categories': CategorySitemap,
    'articles': ArticleSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('news.urls')),

    # SEO: Sitemap and Robots.txt (Served through custom view to strip blocking headers)
    path('sitemap.xml', news_views.custom_sitemap_view, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),

    # Direct browser root /favicon.ico request redirect
    path(
        'favicon.ico',
        RedirectView.as_view(url=staticfiles_storage.url('image/trending-news-favicon.png')),
    ),

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