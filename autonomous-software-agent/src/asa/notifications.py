from __future__ import annotations

import os
import smtplib
import subprocess
from email.message import EmailMessage


def desktop_notify(title: str, message: str) -> bool:
    if os.name != "nt":
        return False
    t = title.replace("'", "''")
    m = message.replace("'", "''")
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; "
        "$n=New-Object System.Windows.Forms.NotifyIcon; $n.Icon=[System.Drawing.SystemIcons]::Information; "
        "$n.Visible=$true; "
        f"$n.ShowBalloonTip(10000,'{t}','{m}',[System.Windows.Forms.ToolTipIcon]::Info); "
        "Start-Sleep -Seconds 4; $n.Dispose();"
    )
    try:
        subprocess.Popen(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def send_outlook_email(to: str, subject: str, body: str) -> bool:
    if os.name != "nt" or not to:
        return False
    to_s, sub_s, body_s = [x.replace("'", "''") for x in [to, subject, body]]
    ps = "$o=New-Object -ComObject Outlook.Application; $m=$o.CreateItem(0); " + f"$m.To='{to_s}'; $m.Subject='{sub_s}'; $m.Body='{body_s}'; $m.Send();"
    try:
        subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], check=True, timeout=60, capture_output=True, text=True)
        return True
    except Exception:
        return False


def send_smtp_email(to: str, subject: str, body: str, host: str, port: int, username: str, password: str, use_tls: bool = True) -> bool:
    if not all([to, host, username, password]):
        return False
    msg = EmailMessage(); msg["From"] = username; msg["To"] = to; msg["Subject"] = subject; msg.set_content(body)
    try:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            if use_tls: smtp.starttls()
            smtp.login(username, password); smtp.send_message(msg)
        return True
    except Exception:
        return False


def notify(config: dict, title: str, message: str) -> dict:
    result = {"desktop": desktop_notify(title, message), "email": False, "email_provider": None}
    email = config.get("email", {})
    recipient = email.get("to", "")
    if recipient and email.get("provider", "outlook") == "outlook":
        result["email"] = send_outlook_email(recipient, title, message); result["email_provider"] = "outlook"
    elif recipient and email.get("provider") == "smtp":
        password = os.environ.get(email.get("password_env", "ASA_SMTP_PASSWORD"), "")
        result["email"] = send_smtp_email(recipient, title, message, email.get("host", ""), int(email.get("port", 587)), email.get("username", ""), password, bool(email.get("use_tls", True))); result["email_provider"] = "smtp"
    return result
