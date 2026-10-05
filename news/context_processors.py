from .models import Article, Category, SiteSetting, LegalPage

def common_site_data(request):
    """Injected automatically into every template across the entire site."""
    try:
        site_setting = SiteSetting.objects.first()
        categories = list(Category.objects.all())
        ticker_news = list(Article.objects.all()[:8])
        legal_pages = list(LegalPage.objects.all())
    except Exception:
        site_setting = None
        categories = []
        ticker_news = []
        legal_pages = []

    return {
        'site_setting': site_setting,
        'categories': categories,
        'ticker_news': ticker_news,
        'legal_pages': legal_pages,
    }