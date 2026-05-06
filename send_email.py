import os
import io
import smtplib
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from email import encoders

# ── Inputs ────────────────────────────────────────────────────────────────────
recipient    = os.environ['RECIPIENT']
manager_name = os.environ['MANAGER_NAME']
system       = os.environ['SYSTEM']
doc_login    = os.environ['DOC_LOGIN']
doc_password = os.environ['DOC_PASSWORD']
sender_email = os.environ['SENDER_EMAIL']
sender_pass  = os.environ['SENDER_PASS']

DOCS = {
    'axenta':  ('docs/axenta.pdf',  'Памятка_Аксента'),
    'glonass': ('docs/glonass.pdf', 'Памятка_ГлонасСофт'),
    'wialon':  ('docs/wialon.pdf',  'Памятка_Wialon_Local'),
}
SYSTEM_NAMES = {
    'axenta':  'АКСЕНТА',
    'glonass': 'ГЛОНАСССОФТ',
    'wialon':  'WIALON LOCAL',
}

pdf_path, doc_basename = DOCS[system]
system_name  = SYSTEM_NAMES[system]
pdf_filename = f'Памятка_{system_name}_{doc_login}.pdf'

# ── Overlay: erase USER/PASSWORD, draw new values ────────────────────────────
pdfmetrics.registerFont(TTFont(
    'ArialBold',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
))

BG = (0.773, 0.851, 0.941)  # #C5D9F0 — cell background

def make_overlay(pw, ph, login, password):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(pw, ph))

    # Erase old values with background color rects (exact cell inner bounds)
    c.setFillColorRGB(*BG)
    c.rect(191.9, 494.0, 381.7, 28.0, fill=1, stroke=0)  # USER row
    c.rect(191.9, 454.5, 381.7, 29.5, fill=1, stroke=0)  # PASSWORD row

    # Draw new values
    c.setFillColorRGB(0, 0, 0)
    c.setFont('ArialBold', 18)
    c.drawString(364.7, 498.4, login)
    c.drawString(340.5, 458.8, password)

    c.save()
    buf.seek(0)
    return buf

reader = PdfReader(pdf_path)
writer = PdfWriter()
page   = reader.pages[0]
pw, ph = float(page.mediabox.width), float(page.mediabox.height)

overlay_pdf = PdfReader(make_overlay(pw, ph, doc_login, doc_password))
page.merge_page(overlay_pdf.pages[0])
writer.add_page(page)

pdf_buf = io.BytesIO()
writer.write(pdf_buf)
pdf_bytes = pdf_buf.getvalue()
print(f'PDF ready: {len(pdf_bytes)} bytes')

# ── Compose & send email ──────────────────────────────────────────────────────
msg = MIMEMultipart()
msg['From']    = formataddr((str(Header('АвтоСкан', 'utf-8')), sender_email))
msg['To']      = formataddr((str(Header(manager_name, 'utf-8')), recipient))
msg['Subject'] = Header(f'Памятка пользователя — {system_name}', 'utf-8')

body = f"""

Данные для входа:
  Логин:  {doc_login}
  Пароль: {doc_password}

"""
msg.attach(MIMEText(body, 'plain', 'utf-8'))

att = MIMEBase('application', 'pdf')
att.set_payload(pdf_bytes)
encoders.encode_base64(att)
att.add_header('Content-Disposition', 'attachment', filename=('utf-8', '', pdf_filename))
msg.attach(att)

print(f'Sending to {recipient} ({manager_name}) from {sender_email} ...')
with smtplib.SMTP_SSL('smtp.mail.ru', 465) as smtp:
    smtp.login(sender_email, sender_pass)
    smtp.sendmail(sender_email, recipient, msg.as_string().encode('utf-8'))

print('Done.')