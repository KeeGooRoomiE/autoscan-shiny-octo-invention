import os
import io
import smtplib
import zipfile
import subprocess
import tempfile
import re
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from email import encoders

# ── Inputs ────────────────────────────────────────────────────────────────────
recipient     = os.environ['RECIPIENT']
manager_name  = os.environ['MANAGER_NAME']
system        = os.environ['SYSTEM']
doc_login     = os.environ['DOC_LOGIN']
doc_password  = os.environ['DOC_PASSWORD']
sender_email  = os.environ['SENDER_EMAIL']
sender_pass   = os.environ['SENDER_PASS']

DOCS = {
    'axenta':  ('docs/axenta.docx',  'Памятка_Аксента'),
    'glonass': ('docs/glonass.docx', 'Памятка_ГлонасСофт'),
    'wialon':  ('docs/wialon.docx',  'Памятка_Wialon_Local'),
}
SYSTEM_NAMES = {
    'axenta':  'АКСЕНТА',
    'glonass': 'ГЛОНАСССОФТ',
    'wialon':  'WIALON LOCAL',
}

doc_path, doc_basename = DOCS[system]
system_name  = SYSTEM_NAMES[system]
pdf_filename = f'Памятка_{system_name}_{doc_login}.pdf'

# ── Patch document.xml ────────────────────────────────────────────────────────
def escape_xml(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

with open(doc_path, 'rb') as f:
    original = f.read()

with zipfile.ZipFile(io.BytesIO(original)) as zin:
    xml = zin.read('word/document.xml').decode('utf-8')

# 1. Fix USER alignment and substitute value
ct = '<w:jc w:val="center"/>'
lt = '<w:jc w:val="left"/>'

ui = xml.index('>USER</w:t>')
uj = xml.rindex(ct, 0, ui)
xml = xml[:uj] + lt + xml[uj+len(ct):]
xml = xml.replace('>USER</w:t>', f'>{escape_xml(doc_login)}</w:t>', 1)

pi = xml.index('>PASSWORD</w:t>')
pj = xml.rindex(ct, 0, pi)
xml = xml[:pj] + lt + xml[pj+len(ct):]
xml = xml.replace('>PASSWORD</w:t>', f'>{escape_xml(doc_password)}</w:t>', 1)

# 2. Fix creds table width: auto -> fixed (11088 dxa = 3393 + 7695)
#    LibreOffice mishandles tblW="0" type="auto" — fix to pct 100% instead
#    Find the specific table containing our creds (the one with the patched login)
login_idx = xml.index(f'>{escape_xml(doc_login)}</w:t>')
tbl_start = xml.rindex('<w:tbl>', 0, login_idx)
tbl_end   = xml.index('</w:tbl>', login_idx) + len('</w:tbl>')

table_xml = xml[tbl_start:tbl_end]

# Fix tblW to fixed width
table_xml = table_xml.replace(
    '<w:tblW w:w="0" w:type="auto"/>',
    '<w:tblW w:w="11088" w:type="dxa"/>'
)

# Remove negative character spacing only inside this table
# (keeps document-level spacing untouched)
table_xml = re.sub(r'<w:spacing w:val="-\d+"/>', '', table_xml)

# Also fix tblLayout to fixed so LibreOffice respects cell widths
if '<w:tblLayout' not in table_xml:
    table_xml = table_xml.replace(
        '</w:tblPr>',
        '<w:tblLayout w:type="fixed"/></w:tblPr>'
    )
else:
    table_xml = re.sub(
        r'<w:tblLayout[^/]*/>', 
        '<w:tblLayout w:type="fixed"/>', 
        table_xml
    )

xml = xml[:tbl_start] + table_xml + xml[tbl_end:]

# ── Repack docx ───────────────────────────────────────────────────────────────
buf = io.BytesIO()
with zipfile.ZipFile(io.BytesIO(original)) as zin:
    with zipfile.ZipFile(buf, 'w') as zout:
        for item in zin.infolist():
            if item.filename.endswith('/'):
                continue
            data = xml.encode('utf-8') if item.filename == 'word/document.xml' else zin.read(item.filename)
            info = zipfile.ZipInfo(item.filename)
            info.date_time     = item.date_time
            info.compress_type = item.compress_type
            zout.writestr(info, data)

docx_bytes = buf.getvalue()

# ── Convert docx → PDF via LibreOffice ───────────────────────────────────────
with tempfile.TemporaryDirectory() as tmpdir:
    docx_path = os.path.join(tmpdir, doc_basename + '.docx')
    pdf_path  = os.path.join(tmpdir, doc_basename + '.pdf')

    with open(docx_path, 'wb') as f:
        f.write(docx_bytes)

    r = subprocess.run(
        ['libreoffice', '--headless', '--convert-to', 'pdf',
         '--outdir', tmpdir, docx_path],
        capture_output=True, text=True, timeout=60
    )
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr)
        raise RuntimeError('LibreOffice conversion failed')

    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

print(f'PDF: {len(pdf_bytes)} bytes')

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