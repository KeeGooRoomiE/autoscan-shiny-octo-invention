# Памятка пользователю — АвтоСкан

Веб-форма для отправки персонализированных инструкций по входу в системы мониторинга транспорта. Вводишь логин и пароль, выбираешь систему и менеджера — письмо уходит автоматически.

**Live:** https://keegooroomie.github.io/autoscan-shiny-octo-invention/

---

## Как это работает

1. Оператор вводит логин и пароль клиента
2. Выбирает систему мониторинга (Аксента / ГлонасСофт / Wialon Local)
3. Выбирает менеджера из списка
4. Нажимает «Отправить»
5. Браузер триггерит GitHub Actions через API
6. Actions запускает `send_email.py` — формирует HTML-письмо с инструкциями и отправляет на почту менеджера через Mail.ru SMTP

Никакого бэкенда — статика на Pages + GitHub Actions как serverless-функция.

---

## Поддерживаемые системы

| Система | Сайт | Приложение |
|---|---|---|
| AXENTA | axenta.cloud | Google Play, App Store, RuStore |
| GlonassSoft | hosting.glonasssoft.ru | Google Play, App Store, RuStore |
| Wialon Local | w.avtoscan42.ru | Google Play, App Store |

---

## Структура репозитория

```
├── index.html                   # Основная страница
├── send_email.py                # Скрипт формирования и отправки письма
├── header.jpg                   # Шапка АвтоСкан
├── footer.jpg                   # Футер АвтоСкан
├── docs/
│   ├── axenta.pdf               # Шаблон памятки Аксента
│   ├── glonass.pdf              # Шаблон памятки ГлонасСофт
│   └── wialon.pdf               # Шаблон памятки Wialon Local
└── .github/
    └── workflows/
        ├── deploy.yml           # CI/CD → GitHub Pages
        └── send-email.yml       # Отправка письма по dispatch
```

---

## GitHub Secrets

| Секрет | Описание |
|---|---|
| `MANAGER1_EMAIL` | Email отправителя (общий ящик АвтоСкан) |
| `MANAGER1_PASS` | Пароль приложения Mail.ru для этого ящика |
| `GH_DISPATCH_TOKEN` | Fine-grained PAT (Actions: Write) — подставляется в index.html при деплое |

---

## Локальный запуск

```bash
python3 -m http.server 8080
# → http://localhost:8080/
```

Открывать через локальный сервер — браузер блокирует `fetch` для `file://`.

---

## Деплой

Push в `main` → GitHub Actions автоматически публикует на Pages.

Настройка (один раз): `Settings → Pages → Source → GitHub Actions`

---

## Обновление шаблонов PDF

Заменить нужный файл в `docs/` и запушить в `main`.

## Обновление списка менеджеров

Отредактировать массив `MANAGERS` в `index.html`.