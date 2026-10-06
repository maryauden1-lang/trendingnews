from django.contrib.sitemaps import Sitemap
from .models import Article, Category, LegalPage


class ArticleSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.9

    def items(self):
        return Article.objects.filter(status='published').order_by('-created_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f"/article/{obj.slug}/"


class CategorySitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.8

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return f"/category/{obj.slug}/"


class StaticViewSitemap(Sitemap):
    changefreq = 'hourly'
    priority = 1.0

    def items(self):
        return ['/']

    def location(self, item):
        return item


class LegalPageSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        return LegalPage.objects.all()

    def location(self, obj):
        return f"/legal/{obj.slug}/"