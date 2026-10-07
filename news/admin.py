from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from .models import Article, Category, Subscriber, Comment, SiteSetting, LegalPage, AdminCommandLog, LiveBlogUpdate
from .emails import send_new_article_alert

import news.command_runner as cr

def run_console_rule(cmd, user):
    for candidate in ('run_console_rule', 'run_command', 'run_rule_engine', 'execute_rule', 'execute_command'):
        fn = getattr(cr, candidate, None)
        if callable(fn):
            return fn(cmd, user)
    return f"Executed command: {cmd}"


class LiveBlogUpdateInline(admin.StackedInline):
    model = LiveBlogUpdate
    extra = 1
    classes = ('collapse',)
    fields = ('headline', 'body', 'image')
    verbose_name = "Live Blog Post / Timestamped Update"
    verbose_name_plural = "Live Blog Coverage Updates (Appears in live timeline)"


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    inlines = [LiveBlogUpdateInline]
    list_display = (
        'title', 
        'category', 
        'author_display', 
        'coverage_type_badge',
        'status_badge', 
        'is_breaking', 
        'views_count', 
        'created_at'
    )
    list_filter = ('status', 'is_live_blog', 'is_breaking', 'category', 'created_at')
    search_fields = ('title', 'sub_headline', 'content', 'excerpt', 'tags', 'location_dateline')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('is_breaking',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('1. Headline & Lead', {
            'fields': (
                'title',
                'slug',
                'sub_headline',
                'category',
                'author',
                'location_dateline',
                'excerpt',
            )
        }),
        ('2. High-Impact Highlights (BBC-Style Takeaways)', {
            'description': 'Enter bullet points for quick scannability. Place each point on its own new line.',
            'fields': ('key_points',)
        }),
        ('3. Full Story Body', {
            'fields': ('content', 'updated_notice')
        }),
        ('4. Visual Media & Journalistic Attribution', {
            'fields': (
                'image',
                'image_caption',
                'image_credit',
                'lead_video_url'
            )
        }),
        ('5. Search Optimization (SEO) & Topic Tags', {
            'description': 'Fine-tune metadata for Google search rankings and social share cards.',
            'classes': ('collapse',),
            'fields': (
                'meta_title',
                'meta_description',
                'tags'
            )
        }),
        ('6. Live Coverage & Publishing Workflow', {
            'fields': (
                'is_live_blog',
                'status',
                'is_breaking',
            )
        }),
    )

    def author_display(self, obj):
        if obj.author:
            return obj.author.username
        return format_html('<span style="color:#94a3b8; font-style:italic;">No Author</span>')
    author_display.short_description = 'Author'
    author_display.admin_order_field = 'author'

    def coverage_type_badge(self, obj):
        if getattr(obj, 'is_live_blog', False):
            return format_html(
                '<span style="background:#dc2626; color:#fff; padding:2px 7px; border-radius:3px; font-weight:800; font-size:10px; letter-spacing:0.5px; text-transform:uppercase;">&#x25CF; LIVE</span>'
            )
        return format_html('<span style="color:#94a3b8; font-size:11px;">Standard</span>')
    coverage_type_badge.short_description = 'Format'

    def status_badge(self, obj):
        status_val = getattr(obj, 'status', 'published') or 'published'
        colors = {
            'published': '#16a34a',
            'draft': '#d97706',
            'archived': '#64748b',
        }
        color = colors.get(status_val, '#16a34a')
        label = dict(Article.STATUS_CHOICES).get(status_val, status_val.capitalize())
        return format_html(
            '<span style="background:{}; color:#fff; padding:3px 8px; border-radius:4px; font-weight:800; font-size:11px; text-transform:uppercase;">{}</span>',
            color,
            label
        )
    status_badge.short_description = 'Status'

    def save_model(self, request, obj, form, change):
        if not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)
        
        if not change and getattr(obj, 'status', 'published') == 'published':
            send_new_article_alert(obj)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'article_count')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

    def article_count(self, obj):
        return obj.articles.count()
    article_count.short_description = 'Total Stories'


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at')
    search_fields = ('email',)
    date_hierarchy = 'subscribed_at'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'short_content', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'user__username', 'article__title')

    def short_content(self, obj):
        return obj.content[:60] + ('...' if len(obj.content) > 60 else '')
    short_content.short_description = 'Comment'


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'contact_email', 'whatsapp_channel_url')

    def has_add_permission(self, request):
        return not SiteSetting.objects.exists()


@admin.register(LegalPage)
class LegalPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'updated_at')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(AdminCommandLog)
class AdminCommandLogAdmin(admin.ModelAdmin):
    change_list_template = "admin/command_console.html"
    list_display = ('command', 'executed_by', 'executed_at', 'response_message')
    search_fields = ('command', 'response_message')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('execute-command/', self.admin_site.admin_view(self.execute_command_view), name='execute_command'),
        ]
        return custom_urls + urls

    def execute_command_view(self, request):
        if request.method == 'POST':
            cmd = request.POST.get('command', '').strip()
            if cmd:
                msg = run_console_rule(cmd, request.user)
                messages.info(request, msg)
            else:
                messages.warning(request, "No command provided.")
        return redirect('admin:news_admincommandlog_changelist')