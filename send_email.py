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

# ── PDF overlay ───────────────────────────────────────────────────────────────
pdfmetrics.registerFont(TTFont(
    'ArialBold',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
))

BG         = (0.773, 0.851, 0.941)  # #C5D9F0
CELL_LEFT  = 190.9
CELL_RIGHT = 574.6
PADDING    = 8
TEXT_X     = CELL_LEFT + PADDING
MAX_W      = CELL_RIGHT - TEXT_X - PADDING

# Cell inner bounds from PDF stream
USER_CELL_Y = 494.0
USER_CELL_H = 28.0
PASS_CELL_Y = 454.5
PASS_CELL_H = 29.5

def fit_font_size(text, sizes=(18, 14, 11, 9)):
    for sz in sizes:
        if pdfmetrics.stringWidth(text, 'ArialBold', sz) <= MAX_W:
            return sz
    return sizes[-1]

def make_overlay(pw, ph, login, password):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(pw, ph))

    # Erase old values
    c.setFillColorRGB(*BG)
    c.rect(CELL_LEFT, USER_CELL_Y, CELL_RIGHT - CELL_LEFT, USER_CELL_H, fill=1, stroke=0)
    c.rect(CELL_LEFT, PASS_CELL_Y, CELL_RIGHT - CELL_LEFT, PASS_CELL_H, fill=1, stroke=0)

    # Draw login — left-aligned, vertically centered in cell
    c.setFillColorRGB(0, 0, 0)
    sz = fit_font_size(login)
    c.setFont('ArialBold', sz)
    c.drawString(TEXT_X, USER_CELL_Y + USER_CELL_H / 2 - sz * 0.3, login)

    # Draw password
    sz = fit_font_size(password)
    c.setFont('ArialBold', sz)
    c.drawString(TEXT_X, PASS_CELL_Y + PASS_CELL_H / 2 - sz * 0.3, password)

    c.save()
    buf.seek(0)
    return buf

reader = PdfReader(pdf_path)
writer = PdfWriter()
page   = reader.pages[0]
pw, ph = float(page.mediabox.width), float(page.mediabox.height)

page.merge_page(PdfReader(make_overlay(pw, ph, doc_login, doc_password)).pages[0])
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