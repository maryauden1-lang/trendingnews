import json
import urllib.request
import threading
from django.conf import settings

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
BREVO_API_KEY = "xsmtpsib-baf7f4f5c7870dee4c8fa23b63fe2183da53b9114300daad5a467db20d935f7b-r3mIPZzDyZ35Pa5L"
SENDER_NAME = "Trending News Update"
SENDER_EMAIL = "newsupdate@trendingnewsonline.org"


def _send_async_mail(subject, text_content, html_content, to_list):
    """
    Sends emails in a background thread using Brevo's HTTPS API.
    Bypasses Render's outbound SMTP socket blocks completely.
    """
    def _worker():
        for recipient in to_list:
            payload = {
                "sender": {
                    "name": SENDER_NAME,
                    "email": SENDER_EMAIL
                },
                "to": [
                    {"email": recipient}
                ],
                "subject": subject,
                "htmlContent": html_content,
                "textContent": text_content,
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                BREVO_API_URL,
                data=data,
                headers={
                    "accept": "application/json",
                    "api-key": BREVO_API_KEY,
                    "content-type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as response:
                    res_body = response.read().decode("utf-8")
                    print(f"[BREVO API SUCCESS] Sent to {recipient}: {res_body}")
            except urllib.error.HTTPError as e:
                err_detail = e.read().decode("utf-8")
                print(f"!!! [BREVO API ERROR {e.code}] !!! -> {err_detail}")
            except Exception as e:
                print(f"!!! [BREVO API FAILED] !!! -> Error: {str(e)}")

    t = threading.Thread(target=_worker)
    t.start()


def send_welcome_email(recipient_email):
    """Sends a responsive welcome email with verified check badge."""
    subject = "Welcome to Trending News Desk"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Welcome to Trending News</title>
      <style>
        body {{ margin: 0; padding: 0; background-color: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
        .container {{ max-width: 600px; margin: 30px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border: 1px solid #e5e7eb; }}
        .header {{ background-color: #bb1919; padding: 28px 24px; text-align: center; }}
        .content {{ padding: 36px 28px; color: #1f2937; line-height: 1.65; }}
        .greeting {{ font-size: 22px; font-weight: 700; color: #111827; margin-top: 0; margin-bottom: 14px; }}
        .intro-p {{ font-size: 15px; color: #4b5563; margin-bottom: 20px; }}
        .highlight-box {{ background-color: #f9fafb; border-left: 4px solid #bb1919; padding: 16px 18px; border-radius: 4px; margin: 24px 0; font-size: 14px; color: #374151; }}
        .btn-wrapper {{ text-align: center; margin: 32px 0 20px 0; }}
        .btn {{ display: inline-block; background-color: #bb1919; color: #ffffff !important; padding: 14px 32px; border-radius: 6px; font-weight: 700; text-decoration: none; font-size: 15px; }}
        .footer {{ background-color: #f9fafb; padding: 22px 24px; text-align: center; border-top: 1px solid #e5e7eb; font-size: 12px; color: #6b7280; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <table role="presentation" border="0" cellpadding="0" cellspacing="0" align="center">
            <tr>
              <td style="color:#ffffff; font-size:24px; font-weight:800; letter-spacing:-0.5px; text-transform:uppercase;">
                TRENDING NEWS
              </td>
              <td style="padding-left: 8px;">
                <img src="https://img.icons8.com/color/48/verified-badge.png" width="22" height="22" alt="Verified" style="display:block; border:0;" />
              </td>
            </tr>
          </table>
        </div>
        <div class="content">
          <h1 class="greeting">You're officially on the inside.</h1>
          <p class="intro-p">
            Welcome to <strong>Trending News</strong>! Your subscription is active, and you're all set to receive fast, verified updates across politics, entertainment, sports, and business directly from our newsroom.
          </p>
          <div class="highlight-box">
            <strong>What to expect:</strong> Instant alerts whenever breaking stories drop, daily curated roundups, and exclusive scoops right in your inbox.
          </div>
          <div class="btn-wrapper">
            <a href="https://trendingnewsonline.org/" class="btn" target="_blank">Explore Today's Headlines</a>
          </div>
          <p style="font-size: 13px; color: #9ca3af; text-align: center; margin-top: 24px;">
            You subscribed via <span style="color:#4b5563;">{recipient_email}</span>.
          </p>
        </div>
        <div class="footer">
          &copy; 2026 Trending News Desk &bull; All rights reserved.<br>
          <a href="https://trendingnewsonline.org/" style="color:#bb1919; text-decoration:none;">trendingnewsonline.org</a>
        </div>
      </div>
    </body>
    </html>
    """
    text_content = f"Welcome to Trending News!\n\nYour subscription is confirmed for {recipient_email}.\n\nVisit: https://trendingnewsonline.org/"
    
    _send_async_mail(subject, text_content, html_content, [recipient_email])


def send_new_article_alert(article):
    """Sends an article alert to all active subscribers in batch."""
    from .models import Subscriber
    subscribers = list(Subscriber.objects.values_list('email', flat=True))
    if not subscribers:
        return

    subject = f"BREAKING: {article.title}"
    article_url = f"https://trendingnewsonline.org/article/{article.slug}/"
    image_url = article.image.url if hasattr(article, 'image') and article.image else ""

    image_markup = ""
    if image_url:
        image_markup = f"""
        <div style="margin: 20px 0; border-radius: 8px; overflow: hidden;">
          <a href="{article_url}" target="_blank">
            <img src="{image_url}" alt="{article.title}" style="width: 100%; max-height: 320px; object-fit: cover; display: block; border: 0;" />
          </a>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>{article.title}</title>
      <style>
        body {{ margin: 0; padding: 0; background-color: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
        .container {{ max-width: 600px; margin: 30px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border: 1px solid #e5e7eb; }}
        .header {{ background-color: #bb1919; padding: 20px 24px; text-align: center; }}
        .content {{ padding: 30px 24px; color: #1f2937; }}
        .tag {{ display: inline-block; background-color: #fee2e2; color: #b91c1c; font-size: 11px; font-weight: 700; text-transform: uppercase; padding: 4px 10px; border-radius: 4px; margin-bottom: 12px; }}
        .headline {{ font-size: 22px; font-weight: 800; line-height: 1.35; color: #111827; margin: 0 0 16px 0; }}
        .excerpt {{ font-size: 15px; color: #4b5563; line-height: 1.6; margin-bottom: 24px; }}
        .btn-wrapper {{ text-align: center; margin: 24px 0 12px 0; }}
        .btn {{ display: inline-block; background-color: #bb1919; color: #ffffff !important; padding: 13px 30px; border-radius: 6px; font-weight: 700; text-decoration: none; font-size: 15px; }}
        .footer {{ background-color: #f9fafb; padding: 20px 24px; text-align: center; border-top: 1px solid #e5e7eb; font-size: 12px; color: #6b7280; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <table role="presentation" border="0" cellpadding="0" cellspacing="0" align="center">
            <tr>
              <td style="color:#ffffff; font-size:20px; font-weight:800; text-transform:uppercase;">TRENDING NEWS</td>
              <td style="padding-left: 6px;">
                <img src="https://img.icons8.com/color/48/verified-badge.png" width="18" height="18" alt="Verified" style="display:block; border:0;" />
              </td>
            </tr>
          </table>
        </div>
        <div class="content">
          <span class="tag">{article.category.name}</span>
          <h1 class="headline">{article.title}</h1>
          {image_markup}
          <p class="excerpt">{article.excerpt}</p>
          <div class="btn-wrapper">
            <a href="{article_url}" class="btn" target="_blank">Read Full Story &rarr;</a>
          </div>
        </div>
        <div class="footer">
          You are receiving this email because you subscribed to Trending News Desk.<br>
          <a href="https://trendingnewsonline.org/" style="color:#bb1919; text-decoration:none;">trendingnewsonline.org</a>
        </div>
      </div>
    </body>
    </html>
    """
    text_content = f"{article.title}\n\nCategory: {article.category.name}\n\n{article.excerpt}\n\nRead here: {article_url}"

    _send_async_mail(subject, text_content, html_content, subscribers)