# services/email.py
"""
风险预警邮件通知
=================
异步发送 HTML 风险预警邮件，使用线程池避免阻塞主请求。
"""

import os
import time
import html
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor

from core.logging_config import logger

# 后台任务线程池（最多 2 个并发线程）
_email_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="risk-email")

# 邮件配置
EMAIL_CONFIG = {
    "smtp_server": os.environ.get("SMTP_SERVER", "smtp.qq.com"),
    "smtp_port": int(os.environ.get("SMTP_PORT", 465)),
    "sender_email": os.environ.get("SMTP_USER", ""),
    "sender_password": os.environ.get("SMTP_PASSWORD", ""),
    "receiver_email": os.environ.get("SMTP_RECEIVER", "")
}


def send_risk_email(medicine_name: str, question: str, answer: str, risk_keywords: list):
    """异步发送风险预警邮件"""
    def _send():
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"MedVision 风险预警: {medicine_name}"
            msg["From"] = EMAIL_CONFIG["sender_email"]
            msg["To"] = EMAIL_CONFIG["receiver_email"]

            # 先转义再嵌入 HTML，防止 XSS 注入
            safe_medicine = html.escape(str(medicine_name))
            safe_question = html.escape(str(question)).replace("\n", "<br>")
            safe_answer = html.escape(str(answer)).replace("\n", "<br>")
            safe_keywords = ', '.join(html.escape(str(kw)) for kw in risk_keywords)

            # HTML 邮件内容
            html_content = f"""
            <html>
            <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; padding: 20px; color: #333; line-height: 1.6;">
                <div style="max-width: 600px; margin: 0 auto; border: 1px solid #eee; border-radius: 5px; overflow: hidden;">
                    <div style="background-color: #d32f2f; color: white; padding: 15px 20px;">
                        <h2 style="margin: 0; font-size: 18px;">MedVision 风险监控通知</h2>
                    </div>

                    <div style="padding: 20px;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; color: #666; width: 80px;">检测时间</td>
                                <td style="padding: 8px 0;">{time.strftime('%Y-%m-%d %H:%M:%S')}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; color: #666;">相关药品</td>
                                <td style="padding: 8px 0; font-weight: bold;">{safe_medicine}</td>
                            </tr>
                             <tr>
                                <td style="padding: 8px 0; color: #666;">风险类型</td>
                                <td style="padding: 8px 0; color: #d32f2f; font-weight: bold;">{safe_keywords}</td>
                            </tr>
                        </table>

                        <div style="margin-top: 20px; border-top: 1px solid #eee; padding-top: 15px;">
                            <p style="margin: 0 0 5px 0; color: #666;">咨询内容:</p>
                            <div style="background-color: #f9f9f9; padding: 10px; border-radius: 4px; margin-bottom: 15px;">
                                {safe_question}
                            </div>

                            <p style="margin: 0 0 5px 0; color: #666;">系统反馈:</p>
                            <div style="background-color: #fff8f8; padding: 10px; border-radius: 4px; border-left: 3px solid #d32f2f;">
                                {safe_answer}
                            </div>
                        </div>
                    </div>

                    <div style="background-color: #f5f5f5; padding: 10px 20px; text-align: center; font-size: 12px; color: #999;">
                        本邮件由 MedVision 风险监控系统自动生成，仅供参考。
                    </div>
                </div>
            </body>
            </html>
            """

            msg.attach(MIMEText(html_content, "html", "utf-8"))

            with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
                server.login(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["sender_password"])
                server.sendmail(
                    EMAIL_CONFIG["sender_email"],
                    EMAIL_CONFIG["receiver_email"],
                    msg.as_string()
                )
            logger.info(f" 风险预警邮件已发送至 {EMAIL_CONFIG['receiver_email']}")
        except Exception as e:
            logger.warning(f" 发送邮件失败: {e}")

    # 提交到线程池执行
    _email_executor.submit(_send)
