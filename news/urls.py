from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .feeds import LatestArticlesFeed

urlpatterns = [
    # Core Editorial & News Routes
    path('', views.home, name='home'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('article/<slug:slug>/', views.article_detail, name='article_detail'),
    path('legal/<slug:slug>/', views.legal_detail, name='legal_detail'),
    path('article/<slug:slug>/like/', views.like_article, name='like_article'),
    path('article/<slug:slug>/comment/', views.add_comment, name='add_comment'),
    path('search/', views.search, name='search'),
    path('subscribe/', views.subscribe, name='subscribe'),

    # RSS 2.0 Syndication Feed (Google News, Feedly, Aggregators)
    path('feed/', LatestArticlesFeed(), name='article_feed'),
    path('rss/', LatestArticlesFeed(), name='article_rss'),

    # User Authentication
    path('register/', views.user_register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Password Reset Workflow
    path('password-reset/', views.password_reset_request_view, name='password_reset'),
    path('password-reset/done/', views.password_reset_done_view, name='password_reset_done'),
    path(
        'password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'),
        name='password_reset_confirm'
    ),
    path(
        'password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'),
        name='password_reset_complete'
    ),
]