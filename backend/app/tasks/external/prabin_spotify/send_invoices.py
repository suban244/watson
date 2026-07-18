import asyncio
import re
import smtplib
from datetime import datetime, timedelta
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import logfire
from config import settings
from taskiq_app import broker

_DIR = Path(__file__).parent
_TEMPLATE = _DIR / "invoice_template.html"
_QR = _DIR / "esewa_qr_prabin.png"
_RECIPIENTS = _DIR / "recipients.txt"


def _load_recipients() -> list[dict]:
    """Load recipients from recipients.txt. Format: email,multiplier,Name"""
    if not _RECIPIENTS.exists():
        logfire.error("recipients.txt not found in prabin_spotify task dir")
        return []
    out = []
    with open(_RECIPIENTS) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            email = parts[0].strip()
            try:
                multiplier = float(parts[1].strip()) if len(parts) > 1 else 1.0
            except ValueError:
                multiplier = 1.0
            name = parts[2].strip() if len(parts) > 2 else email.split("@")[0]
            out.append({"email": email, "multiplier": multiplier, "name": name})
    return out


def _inject_globals(html: str) -> str:
    today = datetime.now()
    due = today + timedelta(days=7)
    invoice_date = today.strftime("%d %b %Y").lstrip("0")
    due_date = due.strftime("%d %b %Y").lstrip("0")
    invoice_num = f"SPOT-{today.strftime('%Y-%m')}"
    qr_block = (
        '<img src="cid:esewa_qr" alt="eSewa QR" style="width:150px;height:150px;'
        'border-radius:6px;display:block;margin:0 auto 12px;background:#fff;padding:6px;">'
        if _QR.exists()
        else '<div class="qr-placeholder">QR coming soon</div>'
    )
    return (
        html.replace("{{INVOICE_DATE}}", invoice_date)
        .replace("{{DUE_DATE}}", due_date)
        .replace("{{INVOICE_NUM}}", invoice_num)
        .replace("{{QR_BLOCK}}", qr_block)
    )


def _apply_multiplier(html: str, multiplier: float) -> str:
    def _mul(m):
        try:
            return f"${float(m.group(1)) * multiplier:.2f}"
        except ValueError:
            return m.group(0)

    return re.sub(r"\$(\d+\.?\d*)", _mul, html)


def send_invoice(email: str, multiplier: float = 1.0, name: str = "") -> bool:
    """Render the invoice template and email it to a single recipient."""
    html = _inject_globals(_TEMPLATE.read_text(encoding="utf-8"))
    html = html.replace("{{CUSTOMER_NAME}}", name)
    if multiplier != 1.0:
        html = _apply_multiplier(html, multiplier)

    msg = MIMEMultipart("related")
    msg["Subject"] = f"Spotify Invoice — {datetime.now().strftime('%B %Y')} 🎵"
    msg["From"] = (
        f"{settings.EXTERNAL_PRABIN_EMAIL_SENDER_NAME} <{settings.EXTERNAL_PRABIN_EMAIL_SENDER}>"
    )
    msg["To"] = email

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html, "html"))
    msg.attach(alt)

    if _QR.exists():
        raw = _QR.read_bytes()
        subtype = "jpeg" if raw[:2] == b"\xff\xd8" else "png"
        img = MIMEImage(raw, _subtype=subtype)
        img.add_header("Content-ID", "<esewa_qr>")
        img.add_header("Content-Disposition", "inline", filename=_QR.name)
        msg.attach(img)

    try:
        with smtplib.SMTP(
            settings.EXTERNAL_PRABIN_EMAIL_SMTP_SERVER,
            settings.EXTERNAL_PRABIN_EMAIL_SMTP_PORT,
        ) as server:
            server.starttls()
            server.login(
                settings.EXTERNAL_PRABIN_EMAIL_SENDER,
                settings.EXTERNAL_PRABIN_EMAIL_PASSWORD,
            )
            server.send_message(msg)
        logfire.info(f"Invoice sent to {email}")
        return True
    except Exception as e:
        logfire.error(f"Failed to send invoice to {email}", error=str(e))
        return False


@broker.task
async def send_prabin_spotify_invoices() -> dict:
    with logfire.span("starting email job"):
        recipients = _load_recipients()
        if not recipients:
            return {"success": 0, "failed": 0, "total": 0}

        results = {"success": 0, "failed": 0, "total": len(recipients)}

        for r in recipients:
            # send_invoice does blocking SMTP; keep it off the event loop.
            if await asyncio.to_thread(
                send_invoice, r["email"], r.get("multiplier", 1.0), r.get("name", "")
            ):
                results["success"] += 1
            else:
                results["failed"] += 1

        print(
            f"Invoice run complete: {results['success']} sent, {results['failed']} failed"
        )
        return results
