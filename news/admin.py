from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Article, Category, Subscriber, Comment, SiteSetting, LegalPage, AdminCommandLog
from .command_runner import run_admin_command


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'views_count', 'total_likes', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'content', 'excerpt')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'created_at', 'short_content')
    list_filter = ('created_at',)
    search_fields = ('content', 'user__username', 'article__title')

    def short_content(self, obj):
        return obj.content[:60] + '...' if len(obj.content) > 60 else obj.content


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at')
    search_fields = ('email',)


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'x_url', 'facebook_url', 'instagram_url')


@admin.register(LegalPage)
class LegalPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'updated_at')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(AdminCommandLog)
class AdminCommandLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'status_badge', 'command', 'executed_by')
    list_filter = ('status', 'timestamp')
    search_fields = ('command', 'response_message')
    readonly_fields = ('command', 'executed_by', 'status', 'response_message', 'timestamp')
    change_list_template = "admin/command_console.html"

    def status_badge(self, obj):
        return "SUCCESS" if obj.status else "FAILED"
    status_badge.short_description = "Status"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('execute-command/', self.admin_site.admin_view(self.execute_command_view), name='execute_command'),
        ]
        return custom_urls + urls

    def execute_command_view(self, request):
        if request.method == 'POST':
            cmd_text = request.POST.get('command', '').strip()
            success, msg = run_admin_command(cmd_text)

            AdminCommandLog.objects.create(
                command=cmd_text,
                executed_by=request.user if request.user.is_authenticated else None,
                status=success,
                response_message=msg
            )

            if success:
                messages.success(request, f"Command executed successfully: {msg}")
            else:
                messages.error(request, msg)

        return redirect('admin:news_admincommandlog_changelist')