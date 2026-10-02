import re
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Article, Category, Comment, Subscriber, LegalPage, SiteSetting

# Commercial spam and bot patterns only (safe for crime/legal discussions)
COMMERCIAL_SPAM_PATTERNS = [
    'crypto', 'casino', 'betting', 'viagra', 'whatsapp me', 'forex', 
    'earn money', 'quick loan', 'urgent loan', 'investment plan', 
    'lottery', 'sugar mummy', 'hack account', 'telegram link', 
    'dm me for', 'click link below', 'cashapp', 'free money'
]


def run_admin_command(command_text):
    """
    Parses natural language instructions and executes database updates safely.
    Returns: (status: bool, message: str)
    """
    cmd = command_text.strip().lower()
    
    if not cmd:
        return False, "Command cannot be empty."

    # 1. SYSTEM STATS & REPORT
    if any(phrase in cmd for phrase in ['show stats', 'system report', 'site stats', 'analytics summary']):
        total_articles = Article.objects.count()
        total_views = sum(Article.objects.values_list('views_count', flat=True))
        total_comments = Comment.objects.count()
        total_subs = Subscriber.objects.count()
        total_users = User.objects.count()
        
        report = (
            f"SYSTEM REPORT:\n"
            f"• Articles Published: {total_articles}\n"
            f"• Total Reads / Views: {total_views}\n"
            f"• Reader Comments: {total_comments}\n"
            f"• Active Newsletter Subscribers: {total_subs}\n"
            f"• Registered User Accounts: {total_users}"
        )
        return True, report

    # 2. PURGE COMMERCIAL & BOT SPAM (CRIME-SAFE)
    if 'clean spam' in cmd or 'clear spam' in cmd or 'delete spam' in cmd or 'remove spam' in cmd:
        q_filter = Q()
        for kw in COMMERCIAL_SPAM_PATTERNS:
            q_filter |= Q(content__icontains=kw)

        qs = Comment.objects.filter(q_filter)
        deleted_count = qs.count()
        qs.delete()
        return True, f"Cleaned commercial spam: Removed {deleted_count} bot/ad comments."

    # 3. MANUAL PHRASE PURGE (For when you specifically want to remove an exact phrase)
    match_phrase = re.search(r'(?:delete|remove|clear)\s+comments?\s+(?:containing|with)\s+(.+)', cmd)
    if match_phrase:
        target_phrase = match_phrase.group(1).strip().strip('"').strip("'")
        qs = Comment.objects.filter(content__icontains=target_phrase)
        count = qs.count()
        qs.delete()
        return True, f"Removed {count} comments containing the specific phrase '{target_phrase}'."

    # 4. DELETE ALL COMMENTS BY USERNAME: e.g. "delete comments from user john"
    match_user = re.search(r'(?:delete|remove)\s+comments?\s+(?:from|by)\s+(?:user\s+)?([a-zA-Z0-9_\-]+)', cmd)
    if match_user:
        target_username = match_user.group(1).strip()
        qs = Comment.objects.filter(user__username__iexact=target_username)
        count = qs.count()
        qs.delete()
        return True, f"Removed {count} comments posted by user '{target_username}'."

    # 5. CREATE CATEGORY: e.g. "create category Cyber Crime"
    match_cat = re.search(r'(?:create|add)\s+category\s+([a-zA-Z0-9\s\-]+)', cmd)
    if match_cat:
        cat_name = match_cat.group(1).strip().title()
        cat_slug = slugify(cat_name)
        if Category.objects.filter(slug=cat_slug).exists():
            return False, f"Category '{cat_name}' already exists."
        Category.objects.create(name=cat_name, slug=cat_slug)
        return True, f"Category '{cat_name}' created successfully with slug '{cat_slug}'."

    # 6. FEATURE ARTICLE: e.g. "feature article 3"
    match_feat = re.search(r'(?:feature|bump|lead)\s+article\s+(\d+)', cmd)
    if match_feat:
        art_id = int(match_feat.group(1))
        try:
            art = Article.objects.get(id=art_id)
            from django.utils import timezone
            art.created_at = timezone.now()
            art.save(update_fields=['created_at'])
            return True, f"Article #{art.id} ('{art.title[:45]}...') bumped to top lead story."
        except Article.DoesNotExist:
            return False, f"No article found with ID #{art_id}."

    # 7. CLEAN INVALID SUBSCRIBERS
    if 'clean subscriber' in cmd or 'prune subscriber' in cmd or 'verify subscriber' in cmd:
        email_regex = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
        removed = 0
        for sub in Subscriber.objects.all():
            if not email_regex.match(sub.email):
                sub.delete()
                removed += 1
        return True, f"Subscriber hygiene complete: {removed} invalid emails pruned from database."

    # 8. RESET / REFRESH LEGAL PAGES
    if 'refresh legal' in cmd or 'reset legal' in cmd or 'sync legal' in cmd:
        defaults = [
            ("Privacy Policy", "At Trending News, your privacy is our top priority. We respect your confidentiality and ensure that personal details such as newsletter subscription emails are kept strictly safe, encrypted, and never sold to third parties."),
            ("Terms of Use", "Welcome to Trending News. By accessing or using our platform, you agree to post respectful comments, avoid libelous remarks, and comply with all applicable copyright and media laws."),
            ("Cookies", "Trending News uses standard session cookies to remember authentication state and deliver optimal page performance."),
            ("About Us", "Trending News is an independent digital newsroom providing real-time breaking news, verified crime alerts, and celebrity journalism."),
            ("Contact Us", "Reach out directly to our 24/7 editorial desk via email at newsdesk@trendingnews.com."),
        ]
        created_count = 0
        for title, content in defaults:
            slug = slugify(title)
            obj, created = LegalPage.objects.get_or_create(title=title, defaults={'content': content, 'slug': slug})
            if created:
                created_count += 1
        return True, f"Legal pages verified: {created_count} new pages created. All core legal routes active."

    return False, (
        f"Unknown command: '{command_text}'.\n\n"
        f"Available commands include:\n"
        f"• show stats\n"
        f"• clear spam comments (ad/crypto/bot cleanup)\n"
        f"• delete comments with [phrase]\n"
        f"• delete comments from user [username]\n"
        f"• create category [Category Name]\n"
        f"• feature article [ID]\n"
        f"• clean invalid subscribers\n"
        f"• refresh legal pages"
    )