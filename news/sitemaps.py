from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Article, Category


class ArticleSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Article.objects.all().order_by('-created_at')

    def lastmod(self, obj):
        return obj.created_at

    def location(self, obj):
        return reverse('article_detail', args=[obj.slug])


class CategorySitemap(Sitemap):
    changefreq = "daily"
    priority = 0.7

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return reverse('category_detail', args=[obj.slug])


class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = "always"

    def items(self):
        return ['home']

    def location(self, item):
        return reverse(item)