from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.views.decorators.http import require_GET

from .models import Article, Category, Subscriber, Comment, SiteSetting, LegalPage, AdBanner


def get_common_context():
    site_setting = SiteSetting.objects.first()
    categories = Category.objects.all()

    breaking_qs = Article.objects.filter(status='published', is_breaking=True)[:8]
    if not breaking_qs.exists():
        breaking_qs = Article.objects.filter(status='published')[:8]

    recent_threshold = timezone.now() - timedelta(days=3)
    trending_qs = Article.objects.filter(
        status='published',
        created_at__gte=recent_threshold
    ).order_by('-views_count', '-created_at')[:5]

    if trending_qs.count() < 3:
        trending_qs = Article.objects.filter(status='published').order_by('-views_count', '-created_at')[:5]

    active_ads = {
        'top_header': AdBanner.objects.filter(slot='top_header', is_active=True).first(),
        'mid_article': AdBanner.objects.filter(slot='mid_article', is_active=True).first(),
        'sidebar': AdBanner.objects.filter(slot='sidebar', is_active=True).first(),
        'footer': AdBanner.objects.filter(slot='footer', is_active=True).first(),
    }

    legal_pages = LegalPage.objects.all()
    return {
        'site_setting': site_setting,
        'categories': categories,
        'ticker_news': breaking_qs,
        'trending_articles': trending_qs,
        'ads': active_ads,
        'legal_pages': legal_pages,
    }


def home(request):
    all_articles = Article.objects.filter(status='published')
    featured_lead = all_articles.first() if all_articles.exists() else None
    featured_sub = list(all_articles[1:4]) if all_articles.count() > 1 else []
    remaining_qs = all_articles[4:] if all_articles.count() > 4 else Article.objects.none()

    page = request.GET.get('page', 1)
    paginator = Paginator(remaining_qs, 8)
    try:
        page_obj = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    context = get_common_context()
    context.update({
        'featured_lead': featured_lead,
        'featured_sub': featured_sub,
        'remaining_articles': page_obj.object_list,
        'page_obj': page_obj,
        'has_articles': all_articles.exists(),
        'current_category': None,
    })
    return render(request, 'news/home.html', context)


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    articles = Article.objects.filter(category=category, status='published')
    featured_lead = articles.first() if articles.exists() else None
    featured_sub = list(articles[1:4]) if articles.count() > 1 else []
    remaining_qs = articles[4:] if articles.count() > 4 else Article.objects.none()

    page = request.GET.get('page', 1)
    paginator = Paginator(remaining_qs, 8)
    try:
        page_obj = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    context = get_common_context()
    context.update({
        'selected_category': category,
        'current_category': category.slug,
        'featured_lead': featured_lead,
        'featured_sub': featured_sub,
        'remaining_articles': page_obj.object_list,
        'page_obj': page_obj,
        'has_articles': articles.exists(),
    })
    return render(request, 'news/home.html', context)


def article_detail(request, slug):
    if request.user.is_staff:
        article = get_object_or_404(Article, slug=slug)
    else:
        article = get_object_or_404(Article, slug=slug, status='published')

    session_key = f'viewed_article_{article.id}'
    if not request.user.is_staff and not request.session.get(session_key, False):
        article.views_count += 1
        article.save(update_fields=['views_count'])
        request.session[session_key] = True

    related_articles = Article.objects.filter(
        category=article.category,
        status='published'
    ).exclude(id=article.id)[:3]

    word_count = len(article.content.split())
    reading_time = max(1, round(word_count / 200))

    context = get_common_context()
    context.update({
        'article': article,
        'related_articles': related_articles,
        'reading_time': reading_time,
    })
    return render(request, 'news/article_detail.html', context)


def legal_detail(request, slug):
    page = get_object_or_404(LegalPage, slug=slug)
    context = get_common_context()
    context.update({'page': page})
    return render(request, 'news/legal_detail.html', context)


def search(request):
    query = request.GET.get('q', '').strip()
    articles = Article.objects.none()
    if query:
        articles = Article.objects.filter(
            Q(title__icontains=query) |
            Q(sub_headline__icontains=query) |
            Q(content__icontains=query) |
            Q(excerpt__icontains=query) |
            Q(tags__icontains=query)
        ).filter(status='published').distinct()

    context = get_common_context()
    context.update({
        'search_query': query,
        'remaining_articles': articles,
        'has_articles': articles.exists(),
    })
    return render(request, 'news/home.html', context)


@login_required(login_url='login')
def like_article(request, slug):
    article = get_object_or_404(Article, slug=slug)
    if article.likes.filter(id=request.user.id).exists():
        article.likes.remove(request.user)
    else:
        article.likes.add(request.user)
    return redirect('article_detail', slug=slug)


@login_required(login_url='login')
def add_comment(request, slug):
    if request.method == 'POST':
        article = get_object_or_404(Article, slug=slug)
        content = request.POST.get('content', '').strip()
        if content:
            Comment.objects.create(article=article, user=request.user, content=content)
            messages.success(request, "Your comment has been posted!")
    return redirect('article_detail', slug=slug)


def subscribe(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        if email and '@' in email:
            Subscriber.objects.get_or_create(email=email)
            messages.success(request, "Subscribed successfully!")
    return redirect(request.META.get('HTTP_REFERER', 'home'))


def user_register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        if username and password:
            if User.objects.filter(username__iexact=username).exists():
                messages.error(request, "Username taken.")
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                auth_login(request, user)
                return redirect('home')
    return render(request, 'news/register.html', get_common_context())


def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username', ''), password=request.POST.get('password', ''))
        if user:
            auth_login(request, user)
            return redirect('home')
        messages.error(request, "Invalid username or password.")
    return render(request, 'news/login.html', get_common_context())


def user_logout(request):
    auth_logout(request)
    return redirect('home')


@require_GET
def google_news_sitemap_view(request):
    two_days_ago = timezone.now() - timedelta(hours=48)
    recent_articles = Article.objects.filter(
        status='published',
        created_at__gte=two_days_ago
    ).order_by('-created_at')[:1000]

    if not recent_articles.exists():
        recent_articles = Article.objects.filter(status='published').order_by('-created_at')[:20]

    domain = request.get_host()
    protocol = 'https'

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">'
    ]

    for item in recent_articles:
        loc = f"{protocol}://{domain}{item.get_absolute_url()}"
        pub_date = item.created_at.strftime("%Y-%m-%dT%H:%M:%S+01:00")
        title_escaped = (
            item.title.replace('&', '&amp;')
                      .replace('<', '&lt;')
                      .replace('>', '&gt;')
                      .replace('"', '&quot;')
                      .replace("'", '&apos;')
        )
        xml_lines.append('  <url>')
        xml_lines.append(f'    <loc>{loc}</loc>')
        xml_lines.append('    <news:news>')
        xml_lines.append('      <news:publication>')
        xml_lines.append('        <news:name>Trending News</news:name>')
        xml_lines.append('        <news:language>en</news:language>')
        xml_lines.append('      </news:publication>')
        xml_lines.append(f'      <news:publication_date>{pub_date}</news:publication_date>')
        xml_lines.append(f'      <news:title>{title_escaped}</news:title>')
        xml_lines.append('    </news:news>')
        xml_lines.append('  </url>')

    xml_lines.append('</urlset>')

    response = HttpResponse('\n'.join(xml_lines), content_type='application/xml; charset=utf-8')
    response['X-Robots-Tag'] = 'all'
    return response