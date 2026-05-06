import os
import io
import smtplib
import zipfile
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from email import encoders

# ── Inputs from workflow ──────────────────────────────────────────────────────
recipient   = os.environ['RECIPIENT']
manager_key = os.environ['MANAGER_KEY']   # manager1 .. manager5
system      = os.environ['SYSTEM']        # axenta / glonass / wialon
doc_login   = os.environ['DOC_LOGIN']
doc_password = os.environ['DOC_PASSWORD']

# ── Manager credentials from secrets ─────────────────────────────────────────
key = manager_key.upper()  # MANAGER1 .. MANAGER5
sender_name  = os.environ[f'{key}_NAME']
sender_email = os.environ[f'{key}_EMAIL']
sender_pass  = os.environ[f'{key}_PASS']

# ── Doc config ────────────────────────────────────────────────────────────────
DOCS = {
    'axenta':  ('docs/axenta.docx',  'Памятка_Аксента.docx'),
    'glonass': ('docs/glonass.docx', 'Памятка_ГлонасСофт.docx'),
    'wialon':  ('docs/wialon.docx',  'Памятка_Wialon_Local.docx'),
}

SYSTEM_NAMES = {
    'axenta':  'АКСЕНТА',
    'glonass': 'ГЛОНАСССОФТ',
    'wialon':  'WIALON LOCAL',
}

if system not in DOCS:
    raise ValueError(f'Unknown system: {system}')

doc_path, doc_filename = DOCS[system]
system_name = SYSTEM_NAMES[system]

# ── Patch document.xml inside docx ───────────────────────────────────────────
def escape_xml(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

with open(doc_path, 'rb') as f:
    original = f.read()

with zipfile.ZipFile(io.BytesIO(original), 'r') as zin:
    xml = zin.read('word/document.xml').decode('utf-8')

center_tag = '<w:jc w:val="center"/>'
left_tag   = '<w:jc w:val="left"/>'

u_idx  = xml.index('>USER</w:t>')
u_jc   = xml.rindex(center_tag, 0, u_idx)
xml    = xml[:u_jc] + left_tag + xml[u_jc + len(center_tag):]
xml    = xml.replace('>USER</w:t>', f'>{escape_xml(doc_login)}</w:t>', 1)

p_idx  = xml.index('>PASSWORD</w:t>')
p_jc   = xml.rindex(center_tag, 0, p_idx)
xml    = xml[:p_jc] + left_tag + xml[p_jc + len(center_tag):]
xml    = xml.replace('>PASSWORD</w:t>', f'>{escape_xml(doc_password)}</w:t>', 1)

# Repack zip — only document.xml changes, everything else copied as-is
out_buf = io.BytesIO()
with zipfile.ZipFile(io.BytesIO(original), 'r') as zin:
    with zipfile.ZipFile(out_buf, 'w') as zout:
        for item in zin.infolist():
            if item.filename.endswith('/'):
                continue
            if item.filename == 'word/document.xml':
                data = xml.encode('utf-8')
            else:
                data = zin.read(item.filename)
            info = zipfile.ZipInfo(item.filename)
            info.date_time    = item.date_time
            info.compress_type = item.compress_type
            zout.writestr(info, data)

doc_bytes = out_buf.getvalue()

# ── Compose email ─────────────────────────────────────────────────────────────
from email.header import Header
from email.utils import formataddr

msg = MIMEMultipart()
msg['From']    = formataddr((str(Header(sender_name, 'utf-8')), sender_email))
msg['To']      = recipient
msg['Subject'] = Header(f'Памятка пользователя — {system_name}', 'utf-8')

body = f"""Здравствуйте!

Во вложении — памятка пользователя системы мониторинга {system_name}.

Ваши данные для входа:
  Логин:  {doc_login}
  Пароль: {doc_password}

С уважением,
{sender_name}
АвтоСкан — Системы контроля транспорта
"""

msg.attach(MIMEText(body, 'plain', 'utf-8'))

attachment = MIMEBase('application', 'vnd.openxmlformats-officedocument.wordprocessingml.document')
attachment.set_payload(doc_bytes)
encoders.encode_base64(attachment)
attachment.add_header('Content-Disposition', 'attachment',
                      filename=('utf-8', '', doc_filename))
msg.attach(attachment)

# ── Send via Mail.ru SMTP ─────────────────────────────────────────────────────
print(f'Sending from {sender_email} to {recipient} ...')
with smtplib.SMTP_SSL('smtp.mail.ru', 465) as smtp:
    smtp.login(sender_email, sender_pass)
    smtp.sendmail(sender_email, recipient, msg.as_string().encode('utf-8'))

print('Done.')