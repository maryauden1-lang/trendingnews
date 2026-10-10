from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.views.decorators.http import require_GET

from .models import Article, Category, Subscriber, Comment, SiteSetting, LegalPage, AdBanner
from .emails import send_welcome_email, _send_async_mail


def get_common_context():
    """Injects site settings, categories, breaking ticker, trending-now algorithm, active ads, and legal pages."""
    site_setting = SiteSetting.objects.first()
    categories = Category.objects.all()
    
    # Priority ticker: published stories marked as is_breaking=True; fallback to latest published
    breaking_qs = Article.objects.filter(status='published', is_breaking=True)[:8]
    if not breaking_qs.exists():
        breaking_qs = Article.objects.filter(status='published')[:8]

    # Algorithm: Trending / Most Read in past 72 hours, fallback to all-time
    recent_threshold = timezone.now() - timedelta(days=3)
    trending_qs = Article.objects.filter(
        status='published',
        created_at__gte=recent_threshold
    ).order_by('-views_count', '-created_at')[:5]

    if trending_qs.count() < 3:
        trending_qs = Article.objects.filter(status='published').order_by('-views_count', '-created_at')[:5]

    # Active Sponsor Ads dictionary by slot
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
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

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
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

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

    # Anti-inflation view tracking:
    # 1. Staff and admins never increment the counter
    # 2. Regular visitors only count once per browser session
    session_key = f'viewed_article_{article.id}'
    if not request.user.is_staff and not request.session.get(session_key, False):
        article.views_count += 1
        article.save(update_fields=['views_count'])
        request.session[session_key] = True

    live_updates = article.live_updates.all() if article.is_live_blog else []

    related_articles = Article.objects.filter(
        category=article.category, 
        status='published'
    ).exclude(id=article.id)[:3]

    if len(related_articles) < 3:
        fallback = Article.objects.filter(status='published').exclude(
            id=article.id
        ).exclude(
            id__in=[r.id for r in related_articles]
        )[:3 - len(related_articles)]
        related_articles = list(related_articles) + list(fallback)

    word_count = len(article.content.split())
    reading_time = max(1, round(word_count / 200))

    context = get_common_context()
    context.update({
        'article': article,
        'live_updates': live_updates,
        'related_articles': related_articles,
        'reading_time': reading_time,
    })
    return render(request, 'news/article_detail.html', context)


def legal_detail(request, slug):
    page = LegalPage.objects.filter(slug=slug).first()
    if not page:
        page = get_object_or_404(LegalPage, title__iexact=slug.replace('-', ' '))
        
    context = get_common_context()
    context.update({
        'page': page,
    })
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
            Q(tags__icontains=query) |
            Q(category__name__icontains=query)
        ).filter(status='published').distinct()

    all_articles = list(articles)
    featured_lead = all_articles[0] if len(all_articles) > 0 else None
    featured_sub = all_articles[1:4] if len(all_articles) > 1 else []
    remaining_articles = all_articles[4:] if len(all_articles) > 4 else []

    context = get_common_context()
    context.update({
        'search_query': query,
        'featured_lead': featured_lead,
        'featured_sub': featured_sub,
        'remaining_articles': remaining_articles,
        'has_articles': len(all_articles) > 0,
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
        else:
            messages.info(request, "Comment cannot be blank.")
    return redirect('article_detail', slug=slug)


def subscribe(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        if email and '@' in email:
            if Subscriber.objects.filter(email=email).exists():
                messages.info(request, "You are already subscribed to Trending News!")
            else:
                Subscriber.objects.create(email=email)
                send_welcome_email(email)
                messages.success(request, "Welcome! A confirmation email has been sent to your inbox.")
        else:
            messages.info(request, "Please enter a valid email address.")
    return redirect(request.META.get('HTTP_REFERER', 'home'))


def user_register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not confirm_password:
            confirm_password = request.POST.get('password_confirm', '') or request.POST.get('password_2', '')

        if not username or not password:
            messages.error(request, "Username and password cannot be empty.")
            return render(request, 'news/register.html', get_common_context())

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'news/register.html', get_common_context())

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, f"The username '{username}' is already taken. Please pick another.")
            return render(request, 'news/register.html', get_common_context())

        try:
            validate_password(password)
        except ValidationError as err:
            for error_msg in err.messages:
                messages.error(request, error_msg)
            return render(request, 'news/register.html', get_common_context())

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            auth_login(request, user)
            messages.success(request, f"Welcome to Trending News, {username}!")
            return redirect('home')
        except Exception as e:
            messages.error(request, f"Error creating account: {str(e)}")
            return render(request, 'news/register.html', get_common_context())

    return render(request, 'news/register.html', get_common_context())


def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            messages.success(request, f"Welcome back, {username}!")
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'news/login.html', get_common_context())


def user_logout(request):
    auth_logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')


def password_reset_request_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        users = User.objects.filter(email__iexact=email, is_active=True)
        domain = request.get_host()
        protocol = 'https' if request.is_secure() else 'http'

        for user in users:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{protocol}://{domain}/password-reset-confirm/{uid}/{token}/"

            subject = "Password Reset Request — Trending News"
            text_content = f"Hello {user.username},\n\nClick the link below to reset your password:\n{reset_url}\n\nIf you did not make this request, you can ignore this email."
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px;">
                <h2 style="color: #bb1919; margin-top: 0;">TRENDING NEWS</h2>
                <p>Hello <strong>{user.username}</strong>,</p>
                <p>We received a request to reset your password. Click the button below to continue:</p>
                <div style="margin: 24px 0;">
                    <a href="{reset_url}" style="background: #bb1919; color: #ffffff; padding: 12px 24px; text-decoration: none; font-weight: bold; border-radius: 4px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                <p style="font-size: 13px; color: #64748b;">Or copy and paste this link in your browser:<br><a href="{reset_url}">{reset_url}</a></p>
                <p style="font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 12px;">If you didn't request this, you can safely ignore this email.</p>
            </div>
            """
            _send_async_mail(subject, text_content, html_content, [user.email])

        return redirect('password_reset_done')

    context = get_common_context()
    return render(request, 'registration/password_reset_form.html', context)


def password_reset_done_view(request):
    context = get_common_context()
    return render(request, 'registration/password_reset_done.html', context)


@require_GET
def custom_sitemap_view(request, sitemaps):
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]

    domain = request.get_host()
    protocol = 'https'

    for section, site in sitemaps.items():
        if callable(site):
            site_instance = site()
        else:
            site_instance = site

        for item in site_instance.items():
            if hasattr(site_instance, 'location'):
                loc = site_instance.location(item)
            elif hasattr(item, 'get_absolute_url'):
                loc = item.get_absolute_url()
            else:
                loc = str(item)

            if not loc.startswith('http'):
                loc = f"{protocol}://{domain}{loc}"

            xml_lines.append('  <url>')
            xml_lines.append(f'    <loc>{loc}</loc>')

            if hasattr(site_instance, 'lastmod'):
                lastmod_val = site_instance.lastmod(item)
                if lastmod_val:
                    xml_lines.append(f'    <lastmod>{lastmod_val.strftime("%Y-%m-%d")}</lastmod>')

            if hasattr(site_instance, 'changefreq'):
                freq = site_instance.changefreq(item) if callable(site_instance.changefreq) else site_instance.changefreq
                if freq:
                    xml_lines.append(f'    <changefreq>{freq}</changefreq>')

            if hasattr(site_instance, 'priority'):
                prio = site_instance.priority(item) if callable(site_instance.priority) else site_instance.priority
                if prio is not None:
                    xml_lines.append(f'    <priority>{prio}</priority>')

            xml_lines.append('  </url>')

    xml_lines.append('</urlset>')

    response = HttpResponse('\n'.join(xml_lines), content_type='application/xml; charset=utf-8')
    response['X-Robots-Tag'] = 'all'
    return response


@require_GET
def google_news_sitemap_view(request):
    """Outputs standard Google News XML sitemap for stories published in the last 48 hours."""
    two_days_ago = timezone.now() - timedelta(hours=48)
    recent_articles = Article.objects.filter(
        status='published',
        created_at__gte=two_days_ago
    ).order_by('-created_at')[:1000]

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