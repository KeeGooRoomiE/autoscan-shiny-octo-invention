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

# ── Fonts ─────────────────────────────────────────────────────────────────────
pdfmetrics.registerFont(TTFont(
    'ArialBold',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
))

def fit_size(text, max_w, sizes):
    for sz in sizes:
        if pdfmetrics.stringWidth(text, 'ArialBold', sz) <= max_w:
            return sz
    return sizes[-1]

# ── Overlay: Аксента (новый макет) ───────────────────────────────────────────
# Two side-by-side rounded boxes
# USER box: x=64  y=392 w=234.72 h=42  text x=78
# PASS box: x=312.72 y=392 w=234.72 h=42  text x=326.72
# Corner radius ~4.5pt → inset 6pt to avoid clipping
# BG: rgb(239,246,254)  Text: rgb(0.043,0.180,0.369)

def make_overlay_axenta(pw, ph, login, password):
    BG   = (239/255, 246/255, 254/255)
    FG   = (0.043, 0.180, 0.369)
    INSET = 6.0
    PAD_R = 10.0

    USER_X = 64.0;    USER_W = 234.72; TXT_USER_X = 78.0
    PASS_X = 312.72;  PASS_W = 234.72; TXT_PASS_X = 326.72
    CELL_Y = 392.0;   CELL_H = 42.0

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(pw, ph))

    c.setFillColorRGB(*BG)
    c.rect(USER_X + INSET, CELL_Y + INSET, USER_W - INSET*2, CELL_H - INSET*2, fill=1, stroke=0)
    c.rect(PASS_X + INSET, CELL_Y + INSET, PASS_W - INSET*2, CELL_H - INSET*2, fill=1, stroke=0)

    c.setFillColorRGB(*FG)

    sz = fit_size(login, USER_W - (TXT_USER_X - USER_X) - PAD_R, (16, 13, 10, 8))
    c.setFont('ArialBold', sz)
    c.drawString(TXT_USER_X, CELL_Y + CELL_H / 2 - sz * 0.3, login)

    sz = fit_size(password, PASS_W - (TXT_PASS_X - PASS_X) - PAD_R, (16, 13, 10, 8))
    c.setFont('ArialBold', sz)
    c.drawString(TXT_PASS_X, CELL_Y + CELL_H / 2 - sz * 0.3, password)

    c.save()
    buf.seek(0)
    return buf

# ── Overlay: Глонасс / Wialon (старый макет) ─────────────────────────────────
# Single wide table, two rows
# Right cell: x=190.9 y=485.7/444.8 w=383.7 h=37.7/40.3
# BG: rgb(197,217,240)  Text: black

def make_overlay_classic(pw, ph, login, password):
    BG  = (0.773, 0.851, 0.941)  # #C5D9F0
    FG  = (0, 0, 0)
    CELL_LEFT  = 190.9
    CELL_RIGHT = 574.6
    TEXT_X     = CELL_LEFT + 8
    MAX_W      = CELL_RIGHT - TEXT_X - 8

    USER_CELL_Y = 494.0;  USER_CELL_H = 28.0
    PASS_CELL_Y = 454.5;  PASS_CELL_H = 29.5

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(pw, ph))

    c.setFillColorRGB(*BG)
    c.rect(CELL_LEFT, USER_CELL_Y, CELL_RIGHT - CELL_LEFT, USER_CELL_H, fill=1, stroke=0)
    c.rect(CELL_LEFT, PASS_CELL_Y, CELL_RIGHT - CELL_LEFT, PASS_CELL_H, fill=1, stroke=0)

    c.setFillColorRGB(*FG)

    sz = fit_size(login, MAX_W, (18, 14, 11, 9))
    c.setFont('ArialBold', sz)
    c.drawString(TEXT_X, USER_CELL_Y + USER_CELL_H / 2 - sz * 0.3, login)

    sz = fit_size(password, MAX_W, (18, 14, 11, 9))
    c.setFont('ArialBold', sz)
    c.drawString(TEXT_X, PASS_CELL_Y + PASS_CELL_H / 2 - sz * 0.3, password)

    c.save()
    buf.seek(0)
    return buf

# ── Apply overlay ─────────────────────────────────────────────────────────────
reader = PdfReader(pdf_path)
writer = PdfWriter()
page   = reader.pages[0]
pw, ph = float(page.mediabox.width), float(page.mediabox.height)

if system == 'axenta':
    overlay_buf = make_overlay_axenta(pw, ph, doc_login, doc_password)
else:
    overlay_buf = make_overlay_classic(pw, ph, doc_login, doc_password)

page.merge_page(PdfReader(overlay_buf).pages[0])
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