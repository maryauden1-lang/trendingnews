from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from cloudinary.models import CloudinaryField

class SiteSetting(models.Model):
    site_name = models.CharField(max_length=150, default="Trending News")
    site_logo = CloudinaryField(
        'image',
        folder='site_assets',
        overwrite=True,
        resource_type='image',
        blank=True,
        null=True,
        help_text="Upload your rectangular website logo"
    )
    gmail_address = models.EmailField(blank=True, null=True, help_text="Your official Gmail address for sending notifications")
    gmail_app_password = models.CharField(max_length=200, blank=True, null=True, help_text="Google App Password")
    
    x_url = models.URLField(blank=True, null=True, default="https://x.com", help_text="X / Twitter Page Link")
    facebook_url = models.URLField(blank=True, null=True, default="https://facebook.com", help_text="Facebook Page Link")
    instagram_url = models.URLField(blank=True, null=True, default="https://instagram.com", help_text="Instagram Page Link")
    tiktok_url = models.URLField(blank=True, null=True, default="https://tiktok.com", help_text="TikTok Profile Link")
    linkedin_url = models.URLField(blank=True, null=True, default="https://linkedin.com", help_text="LinkedIn Page Link")
    youtube_url = models.URLField(blank=True, null=True, default="https://youtube.com", help_text="YouTube Channel Link")

    class Meta:
        verbose_name = "Site Configuration"
        verbose_name_plural = "Site Configuration"

    def __str__(self):
        return self.site_name


class LegalPage(models.Model):
    title = models.CharField(max_length=200, help_text="e.g. Terms of Use, Privacy Policy, Cookies Policy, About Us")
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    content = models.TextField(help_text="Full legal or informative text for this page")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Article(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='articles')
    image = CloudinaryField(
        'image',
        folder='articles',
        overwrite=True,
        resource_type='image',
        blank=True,
        null=True
    )
    excerpt = models.TextField(max_length=300, help_text="Brief summary shown on cards")
    content = models.TextField(help_text="Full news or gossip story")
    views_count = models.PositiveIntegerField(default=0)
    is_breaking = models.BooleanField(default=False, help_text="Check to prioritize in breaking news ticker")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.ManyToManyField(User, related_name='liked_articles', blank=True)

    class Meta:
        ordering = ['-created_at']

    def total_likes(self):
        return self.likes.count()

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Article.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

        # Trigger automatic notification to all subscribers only on newly created articles
        if is_new:
            try:
                from .emails import send_new_article_alert
                send_new_article_alert(self)
            except Exception as e:
                print(f"[ARTICLE EMAIL ALERT ERROR]: {e}")

    def __str__(self):
        return self.title


class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.article.title}"


class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class AdminCommandLog(models.Model):
    command = models.CharField(max_length=255, help_text="The instruction you ran")
    executed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.BooleanField(default=True, help_text="True if succeeded")
    response_message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Admin Command Console"
        verbose_name_plural = "Admin Command Console"

    def __str__(self):
        return f"[{'SUCCESS' if self.status else 'FAILED'}] {self.command}"