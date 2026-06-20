"""
Email Service
Gửi email qua Gmail SMTP (provider chính).
Dùng smtplib + email.mime (stdlib, không cần cài thêm package).
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.v1.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service gửi email qua SMTP (Gmail)."""

    def __init__(self):
        """Khởi tạo với cấu hình SMTP từ settings."""
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_use_ssl = settings.SMTP_USE_SSL
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME

    def is_configured(self) -> bool:
        """Kiểm tra đã cấu hình đủ credentials SMTP chưa."""
        return bool(self.smtp_username and self.smtp_password)

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None
    ) -> bool:
        """
        Gửi email HTML qua SMTP.

        Args:
            to_email: Email người nhận
            subject: Tiêu đề email
            html_content: Nội dung HTML
            plain_content: Nội dung text thuần (fallback, optional)

        Returns:
            True nếu gửi thành công, False nếu thất bại.
        """
        if not self.is_configured():
            logger.error(
                "SMTP credentials not configured (SMTP_USERNAME/SMTP_PASSWORD trống)")
            print(
                f"\n🔑 [FALLBACK] SMTP not configured. "
                f"Would send to {to_email} | Subject: {subject}\n")
            return False

        try:
            # Build message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject

            # Attach plain text trước, HTML sau (mail client ưu tiên phần sau)
            if plain_content:
                msg.attach(MIMEText(plain_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            # Connect & send
            if self.smtp_use_ssl:
                server = smtplib.SMTP_SSL(
                    self.smtp_host, self.smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(
                    self.smtp_host, self.smtp_port, timeout=10)
                server.starttls()

            try:
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            finally:
                server.quit()

            logger.info(f"Email sent successfully to {to_email} via SMTP")
            return True

        except Exception as e:
            logger.error(
                f"Failed to send email to {to_email} via SMTP: "
                f"{type(e).__name__}: {str(e)}")
            print(
                f"\n🔑 [FALLBACK] SMTP error ({type(e).__name__}). "
                f"Would send to {to_email} | Subject: {subject}\n")
            return False


# Singleton instance
_email_service = None


def get_email_service() -> EmailService:
    """Get singleton EmailService instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
