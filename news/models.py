from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from cloudinary.models import CloudinaryField


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Article(models.Model):
    STATUS_CHOICES = (
        ('published', 'Published'),
        ('draft', 'Draft / In Review'),
        ('archived', 'Archived'),
    )

    # Core Editorial
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    sub_headline = models.CharField(
        max_length=300, 
        blank=True, 
        help_text="Standfirst / 1-2 sentence lead summary displayed under the title."
    )
    author = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='articles',
        help_text="Staff journalist or editorial desk attributing this story."
    )
    location_dateline = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="e.g. LAGOS, ABUJA, LONDON, WASHINGTON"
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='articles')
    excerpt = models.TextField(max_length=350, help_text="Short card teaser for homepage and listing feeds.")
    content = models.TextField(help_text="Full news article body.")

    # High-Standard Highlights Box
    key_points = models.TextField(
        blank=True, 
        help_text="Enter key takeaways. Put each point on a new line (they will render as BBC-style bullet highlights)."
    )

    # Media & Visual Attribution
    image = CloudinaryField('image', blank=True, null=True)
    image_caption = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Description of what is happening in the photo."
    )
    image_credit = models.CharField(
        max_length=150, 
        blank=True, 
        help_text="e.g. Photo: Trending News / Reuters / AFP"
    )
    lead_video_url = models.URLField(
        blank=True, 
        help_text="Optional YouTube embed or video URL (e.g. https://www.youtube.com/embed/VIDEO_ID)."
    )

    # Search Optimization (SEO) & Social Overrides
    meta_title = models.CharField(
        max_length=160, 
        blank=True, 
        help_text="SEO search engine title (Google SERP limit ~60-70 chars). Defaults to title if blank."
    )
    meta_description = models.TextField(
        max_length=255, 
        blank=True, 
        help_text="SEO meta description snippet. Defaults to excerpt if blank."
    )
    tags = models.CharField(
        max_length=300, 
        blank=True, 
        help_text="Comma-separated topics (e.g. Politics, Economy, Champions League, Technology)."
    )

    # Live Blog & Publishing Controls
    is_live_blog = models.BooleanField(
        default=False, 
        help_text="Enable live rolling coverage with timestamped updates (BBC-style liveblog)."
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='published')
    is_breaking = models.BooleanField(
        default=False, 
        help_text="Tick this to push this headline straight to the top Flash Wire marquee."
    )
    updated_notice = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="e.g. 'Updated at 3:15 PM with police statement'"
    )

    # Metrics & Timestamps
    views_count = models.PositiveIntegerField(default=0)
    likes = models.ManyToManyField(User, related_name='liked_articles', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('article_detail', kwargs={'slug': self.slug})

    @property
    def total_likes(self):
        return self.likes.count()

    @property
    def key_points_list(self):
        if not self.key_points:
            return []
        return [point.strip() for point in self.key_points.splitlines() if point.strip()]

    @property
    def tags_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def __str__(self):
        return self.title


class LiveBlogUpdate(models.Model):
    """Timestamped micro-posts inside an active breaking story."""
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='live_updates')
    headline = models.CharField(max_length=255, help_text="Short headline for this specific update")
    body = models.TextField(help_text="Short update text (supports paragraphs)")
    image = CloudinaryField('image', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.created_at:%H:%M}] {self.headline} ({self.article.title[:30]}...)"


class AdBanner(models.Model):
    SLOT_CHOICES = (
        ('top_header', 'Top Header Leaderboard (728x90 / responsive)'),
        ('mid_article', 'Article Body Sponsor Slot (Responsive / 728x90)'),
        ('sidebar', 'Sidebar Rectangle (300x250)'),
        ('footer', 'Bottom Footer Banner'),
    )

    name = models.CharField(max_length=120, help_text="Campaign / Client Name (e.g. Zenith Bank Promo)")
    slot = models.CharField(max_length=30, choices=SLOT_CHOICES, default='sidebar')
    image = CloudinaryField('banner_image', blank=True, null=True, help_text="Upload static banner image")
    destination_url = models.URLField(blank=True, help_text="Link where the click directs to")
    html_code = models.TextField(blank=True, help_text="Paste Google AdSense / HTML embed script if not using image banner")
    is_active = models.BooleanField(default=True, help_text="Toggle to display or hide this banner")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} [{self.get_slot_display()}] ({'Active' if self.is_active else 'Paused'})"


class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='news_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.article.title}"


class SiteSetting(models.Model):
    site_name = models.CharField(max_length=150, default="Trending News")
    site_description = models.TextField(blank=True, default="Your trusted source for verified news, crime alerts, and breaking stories.")
    site_logo = CloudinaryField('logo', blank=True, null=True)
    contact_email = models.EmailField(default="contact@trendingnewsonline.org")
    whatsapp_channel_url = models.URLField(blank=True, help_text="Direct link to your WhatsApp Channel or Community group.")
    x_url = models.URLField(blank=True, verbose_name="X / Twitter URL")
    facebook_url = models.URLField(blank=True, verbose_name="Facebook URL")
    instagram_url = models.URLField(blank=True, verbose_name="Instagram URL")
    tiktok_url = models.URLField(blank=True, verbose_name="TikTok URL")
    linkedin_url = models.URLField(blank=True, verbose_name="LinkedIn URL")
    youtube_url = models.URLField(blank=True, verbose_name="YouTube URL")

    def __str__(self):
        return self.site_name


class LegalPage(models.Model):
    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    content = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class AdminCommandLog(models.Model):
    command = models.CharField(max_length=255)
    executed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    response_message = models.TextField()
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-executed_at']

    def __str__(self):
        return f"{self.command} ({self.executed_at:%Y-%m-%d %H:%M})"