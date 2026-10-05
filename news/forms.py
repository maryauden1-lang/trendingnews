from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .emails import _send_async_mail

class BrevoPasswordResetForm(PasswordResetForm):
    def save(self, domain_override=None, subject_template_name=None,
             email_template_name=None, use_https=True,
             token_generator=default_token_generator,
             from_email=None, request=None, html_email_template_name=None,
             extra_email_context=None):
        email = self.cleaned_data["email"]
        domain = domain_override or (request.get_host() if request else "trendingnewsonline.org")
        protocol = "https" if use_https else "http"

        for user in self.get_users(email):
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_generator.make_token(user)
            reset_url = f"{protocol}://{domain}/password-reset-confirm/{uid}/{token}/"

            subject = "Reset Your Password - Trending News"
            text_content = f"Hello {user.username},\n\nClick the link below to reset your password:\n{reset_url}\n\nIf you did not request this, please ignore this email."
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px;">
                <h2 style="color: #bb1919; margin-top: 0;">TRENDING NEWS</h2>
                <p>Hello <strong>{user.username}</strong>,</p>
                <p>You requested a password reset. Click the button below to set a new password:</p>
                <div style="margin: 24px 0;">
                    <a href="{reset_url}" style="background: #bb1919; color: #ffffff; padding: 12px 24px; text-decoration: none; font-weight: bold; border-radius: 4px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                <p style="font-size: 13px; color: #64748b;">If the button doesn't work, copy and paste this URL into your browser:<br><a href="{reset_url}">{reset_url}</a></p>
                <p style="font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 12px;">If you didn't request this, you can safely ignore this email.</p>
            </div>
            """

            _send_async_mail(subject, text_content, html_content, [user.email])