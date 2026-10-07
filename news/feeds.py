from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Rss201rev2Feed
from .models import Article, SiteSetting


class LatestArticlesFeed(Feed):
    feed_type = Rss201rev2Feed

    def title(self):
        setting = SiteSetting.objects.first()
        return f"{setting.site_name if setting else 'Trending News'} - Latest Headlines"

    def link(self):
        return "/"

    def description(self):
        setting = SiteSetting.objects.first()
        return setting.site_description if setting else "Real-time breaking news, verified reporting, and political updates."

    def items(self):
        return Article.objects.filter(status='published').order_by('-created_at')[:30]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt or item.sub_headline or item.content[:280]

    def item_pubdate(self, item):
        return item.created_at

    def item_updateddate(self, item):
        return item.updated_at

    def item_categories(self, item):
        cats = [item.category.name]
        if item.tags_list:
            cats.extend(item.tags_list)
        return cats