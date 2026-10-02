from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Article, Category, Subscriber, Comment, SiteSetting, LegalPage


def get_common_context():
    """Injects site settings, categories, breaking ticker, and dynamic legal pages everywhere."""
    site_setting = SiteSetting.objects.first()
    categories = Category.objects.all()
    ticker_news = Article.objects.all()[:8]
    legal_pages = LegalPage.objects.all()
    return {
        'site_setting': site_setting,
        'categories': categories,
        'ticker_news': ticker_news,
        'legal_pages': legal_pages,
    }


def home(request):
    all_articles = list(Article.objects.all())
    
    # Feature Grid split: 1 Lead Story, up to 3 Side Stories, remainder in grid
    featured_lead = all_articles[0] if len(all_articles) > 0 else None
    featured_sub = all_articles[1:4] if len(all_articles) > 1 else []
    remaining_articles = all_articles[4:] if len(all_articles) > 4 else []

    context = get_common_context()
    context.update({
        'featured_lead': featured_lead,
        'featured_sub': featured_sub,
        'remaining_articles': remaining_articles,
        'has_articles': len(all_articles) > 0,
        'current_category': None,
    })
    return render(request, 'news/home.html', context)


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    articles = list(Article.objects.filter(category=category))
    
    featured_lead = articles[0] if len(articles) > 0 else None
    featured_sub = articles[1:4] if len(articles) > 1 else []
    remaining_articles = articles[4:] if len(articles) > 4 else []

    context = get_common_context()
    context.update({
        'selected_category': category,
        'current_category': category.slug,
        'featured_lead': featured_lead,
        'featured_sub': featured_sub,
        'remaining_articles': remaining_articles,
        'has_articles': len(articles) > 0,
    })
    return render(request, 'news/home.html', context)


def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug)
    article.views_count += 1
    article.save(update_fields=['views_count'])

    # Related stories engine: 3 articles from the same category excluding this one
    related_articles = Article.objects.filter(category=article.category).exclude(id=article.id)[:3]
    if len(related_articles) < 3:
        fallback = Article.objects.exclude(id=article.id).exclude(id__in=[r.id for r in related_articles])[:3 - len(related_articles)]
        related_articles = list(related_articles) + list(fallback)

    # Word count and reading time estimate (approx 200 wpm)
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
            Q(content__icontains=query) |
            Q(excerpt__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()

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
        if email:
            if Subscriber.objects.filter(email=email).exists():
                messages.info(request, "You are already subscribed to Trending News!")
            else:
                Subscriber.objects.create(email=email)
                messages.success(request, "Welcome! You are now subscribed to our news desk.")
        else:
            messages.info(request, "Please enter a valid email address.")
    return redirect('home')


def user_register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if password != confirm_password:
            messages.info(request, "Passwords do not match.")
            return render(request, 'news/register.html', get_common_context())

        if User.objects.filter(username=username).exists():
            messages.info(request, "This username is already taken.")
            return render(request, 'news/register.html', get_common_context())

        user = User.objects.create_user(username=username, email=email, password=password)
        auth_login(request, user)
        messages.success(request, f"Welcome to Trending News, {username}!")
        return redirect('home')

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
            messages.info(request, "Invalid username or password.")

    return render(request, 'news/login.html', get_common_context())


def user_logout(request):
    auth_logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')