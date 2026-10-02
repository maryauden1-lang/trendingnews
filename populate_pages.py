import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from news.models import LegalPage

pages = [
    {
        "title": "Privacy Policy",
        "content": "At Trending News, your privacy is our top priority. We respect your confidentiality and ensure that personal details such as newsletter subscription emails are kept strictly safe, encrypted, and never sold to third parties."
    },
    {
        "title": "Terms of Use",
        "content": "Welcome to Trending News. By accessing or using our platform, you agree to post respectful comments, avoid libelous remarks, and comply with all applicable local and international copyright and media distribution laws."
    },
    {
        "title": "Cookies",
        "content": "Trending News uses standard technical session cookies to ensure you stay securely logged into your account, save your interactive reading preferences, and deliver optimal page loading speeds across your devices."
    },
    {
        "title": "About Us",
        "content": "Trending News is your premier digital newsroom dedicated to delivering unvarnished real-time celebrity gossip, verified crime watch briefings, and insightful political journalism."
    },
    {
        "title": "Contact Us",
        "content": "Have a verified scoop, celebrity leak, or editorial inquiry? Reach out directly to our 24/7 editorial desk via email at newsdesk@trendingnews.com or reach out via our verified social platforms."
    },
]

for p in pages:
    obj, created = LegalPage.objects.get_or_create(
        title=p["title"],
        defaults={"content": p["content"]}
    )
    status = "Created" if created else "Already exists"
    print(f"[{status}] {p['title']}")

print("\nAll default legal pages are ready!")