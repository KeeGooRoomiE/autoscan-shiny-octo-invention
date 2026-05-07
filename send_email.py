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

SYSTEM_NAMES = {
    'axenta':  'AXENTA',
    'glonass': 'GlonassSoft',
    'wialon':  'Wialon Local',
}
system_name = SYSTEM_NAMES[system]

# ── Email subject ─────────────────────────────────────────────────────────────
subject = f'{doc_login} {system_name}'

# ── Email HTML body ───────────────────────────────────────────────────────────
CONTENT = {
    'wialon': {
        'title': 'Вход в Wialon Local',
        'site':  'w.avtoscan42.ru',
        'site_url': 'https://w.avtoscan42.ru',
        'app_name': 'Wialon Local',
        'app_links': [
            ('Google Play', 'https://play.google.com/store/apps/details?id=com.gurtam.wialon_local_1504&hl=ru'),
            ('App Store',   'https://apps.apple.com/ru/app/wialon-local/id1011136393'),
        ],
        'app_alt_url':  'https://wialon-service.ru/mobilnoe-prilozhenie-wialon',
        'server_note': '<p style="margin:6px 0 0 20px;color:#555;font-size:14px;">В настройках приложения укажите адрес сервера: <a href="https://w.avtoscan42.ru" style="color:#1a56a0;">w.avtoscan42.ru</a></p>',
    },
    'axenta': {
        'title': 'Вход в AXENTA',
        'site':  'axenta.cloud',
        'site_url': 'https://axenta.cloud',
        'app_name': 'AXENTA',
        'app_links': [
            ('Google Play', 'https://play.google.com/store/apps/details?id=ru.nekta.axenta&hl=ru),
            ('App Store',   'https://apps.apple.com/ru/app/axenta/id6474660071'),
            ('RuStore',     'https://www.rustore.ru/catalog/app/ru.nekta.axenta?rcvr=1730461258081'),
        ],
        'app_alt_url': 'https://axenta.tech/mobile-app/',
        'server_note': '',
    },
    'glonass': {
        'title': 'Вход в GlonassSoft',
        'site':  'hosting.glonasssoft.ru',
        'site_url': 'https://hosting.glonasssoft.ru',
        'app_name': 'GlonassSoft',
        'app_links': [
            ('Google Play', 'https://play.google.com/store/apps/details?id=ru.glonasssoft.hosting'),
            ('App Store',   'https://apps.apple.com/ru/app/glonasssoft/id1503150794'),
            ('RuStore',     'https://www.rustore.ru/catalog/app/ru.glonasssoft.hostingapp'),
        ],
        'app_alt_url': 'https://glonasssoft.ru/ru/sistema-monitoringa/mobile-monitoring',
        'server_note': '',
    },
}

c = CONTENT[system]

store_links = ''.join(
    f'<a href="{url}" style="display:inline-block;margin:4px 6px 4px 0;padding:6px 14px;'
    f'background:#1a56a0;color:#fff;text-decoration:none;border-radius:5px;font-size:13px;font-weight:600;">'
    f'{name}</a>'
    for name, url in c['app_links']
)

html = f"""<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:32px 16px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,0.10);">

  <!-- Header -->
  <tr><td style="background:#1a56a0;padding:28px 36px;">
    <div style="color:#fff;font-size:22px;font-weight:700;margin-bottom:4px;">{c['title']}</div>
    <div style="color:#a8c4e8;font-size:14px;">Данные для входа в систему мониторинга</div>
  </td></tr>

  <!-- Body -->
  <tr><td style="padding:32px 36px;">

    <!-- Section: Computer -->
    <div style="font-size:16px;font-weight:700;color:#1a2a4a;margin-bottom:12px;">
      🖥 Через компьютер
    </div>
    <ol style="margin:0 0 24px 0;padding-left:20px;color:#333;font-size:15px;line-height:1.8;">
      <li>Перейдите на сайт <a href="{c['site_url']}" style="color:#1a56a0;font-weight:600;">{c['site']}</a></li>
      <li>Введите имя пользователя и пароль</li>
    </ol>

    <!-- Credentials block -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
    <tr>
      <td style="background:#eef4fb;border:1.5px solid #c5d9f0;border-radius:8px;padding:20px 24px;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td width="50%" style="padding-right:16px;">
              <div style="font-size:11px;font-weight:700;color:#6b7f9a;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Имя пользователя</div>
              <div style="font-size:22px;font-weight:700;color:#0f3870;letter-spacing:0.5px;word-break:break-all;">{doc_login}</div>
            </td>
            <td width="1" style="background:#c5d9f0;width:1px;">&nbsp;</td>
            <td width="50%" style="padding-left:16px;">
              <div style="font-size:11px;font-weight:700;color:#6b7f9a;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Пароль</div>
              <div style="font-size:22px;font-weight:700;color:#0f3870;letter-spacing:0.5px;word-break:break-all;">{doc_password}</div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
    </table>

    <!-- Section: Mobile -->
    <div style="font-size:16px;font-weight:700;color:#1a2a4a;margin-bottom:12px;">
      📱 Через смартфон
    </div>
    <ol style="margin:0 0 16px 0;padding-left:20px;color:#333;font-size:15px;line-height:1.8;">
      <li style="margin-bottom:8px;">
        Установите приложение <strong>«{c['app_name']}»</strong> — перейдите по ссылке и выберите версию для вашего устройства:<br>
        <a href="{c['app_alt_url']}" style="color:#1a56a0;font-size:13px;">{c['app_alt_url']}</a><br>
        <span style="color:#777;font-size:13px;">или найдите в:</span><br>
        {store_links}
      </li>
      {f'<li style="margin-bottom:8px;">{c["server_note"][c["server_note"].find("В"):c["server_note"].rfind("</p>")]}</li>' if c['server_note'] else ''}
      <li>Для входа используйте те же логин и пароль, что и для компьютерной версии</li>
    </ol>

  </td></tr>

  <!-- Footer -->
  <tr><td style="background:#f4f7fb;border-top:1px solid #e0e8f0;padding:18px 36px;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="color:#6b7f9a;font-size:13px;">АвтоСкан — Системы контроля транспорта</td>
        <td align="right" style="color:#6b7f9a;font-size:13px;">avtoscan42.ru</td>
      </tr>
    </table>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

# ── Plain text fallback ───────────────────────────────────────────────────────
plain = f"""{c['title']}

Данные для входа:
  Логин:    {doc_login}
  Пароль:   {doc_password}

Через компьютер:
  {c['site_url']}

Через смартфон:
  {c['app_alt_url']}
"""

# ── Compose email ─────────────────────────────────────────────────────────────
msg = MIMEMultipart('alternative')
msg['From']    = formataddr((str(Header('АвтоСкан', 'utf-8')), sender_email))
msg['To']      = formataddr((str(Header(manager_name, 'utf-8')), recipient))
msg['Subject'] = Header(subject, 'utf-8')

msg.attach(MIMEText(plain, 'plain', 'utf-8'))
msg.attach(MIMEText(html,  'html',  'utf-8'))

print(f'Sending to {recipient} ({manager_name}) from {sender_email} ...')
with smtplib.SMTP_SSL('smtp.mail.ru', 465) as smtp:
    smtp.login(sender_email, sender_pass)
    smtp.sendmail(sender_email, recipient, msg.as_string().encode('utf-8'))

print('Done.')