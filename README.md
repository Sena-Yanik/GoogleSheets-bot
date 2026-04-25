# 🤖 Telegram Google Sheets Bot

Google Sheets verilerini **doğal Türkçe** ile sorgulayabilen, LLM destekli bir Telegram bot.

> Kullanıcı doğal dilde soru sorar → LLM sorguyu yapılandırılmış JSON'a çevirir → Python deterministik olarak hesaplar → Telegram'da formatlanmış yanıt döner.

---

## ✨ Özellikler

- 🗣️ **Doğal Dil Sorguları** — Türkçe doğal dilde veri sorgulama
- 📊 **4 Rapor Tipi** — Genel, performans, risk ve kategori raporları
- 🔢 **Hassas Hesaplama** — `float` yerine `Decimal` ile finansal doğruluk
- 🧠 **LLM Güvenliği** — LLM sadece doğal dili JSON'a çevirir, hesaplama yapmaz
- ⚡ **Redis Cache** — TTL bazlı cache ile hızlı yanıt
- 🔒 **Güvenlik** — Whitelist, rate limiting, webhook secret doğrulama
- 🛡️ **KVKK/GDPR Uyumu** — Chat ID hash'leme, sorgu maskeleme
- ❓ **Clarification Akışı** — Belirsiz sorgularda kullanıcıya soru sorma
- 🐳 **Docker Desteği** — Tek komutla deployment

---

## 🏗️ Mimari

```
Kullanıcı Sorgusu (Türkçe)
        │
        ▼
┌─────────────────┐
│   Telegram Bot   │  ← Webhook + Secret Token
│   (handlers.py)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  Security Check  │────▶│ Rate Limiter     │
│  (Whitelist)     │     │ (Redis)          │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐
│   LLM Parser     │  ← Groq API (Llama 3.3 70B)
│   (llm_parser)   │     Sadece JSON çıktı
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Validator      │  ← Intent, field, operator, tip doğrulama
│   (query_valid.) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ Execution Engine │────▶│ Report Engine     │
│ (Deterministik)  │     │ (4 rapor tipi)   │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐
│   Formatter      │  ← Telegram MarkdownV2
│   (formatter.py) │
└─────────────────┘
```

---

## 📂 Proje Yapısı

```
├── main.py                     # FastAPI uygulama giriş noktası
├── Dockerfile                  # Docker image tanımı
├── docker-compose.yml          # Bot + Redis + Ngrok orchestration
├── requirements.txt            # Python bağımlılıkları
│
├── bot/
│   ├── handlers.py             # Telegram mesaj işleyici
│   └── formatter.py            # MarkdownV2 yanıt formatlayıcı
│
├── core/
│   ├── config.py               # Uygulama ayarları + alan haritaları
│   ├── logger.py               # Yapısal loglama (structlog)
│   └── security.py             # Whitelist + rate limiting
│
├── data/
│   ├── sheets_client.py        # Google Sheets API istemcisi
│   └── cache.py                # Redis cache yönetimi
│
├── engine/
│   ├── execution_engine.py     # Deterministik sorgu motoru
│   └── report_engine.py        # Rapor üretim motoru
│
├── parser/
│   ├── llm_parser.py           # Groq LLM API istemcisi
│   ├── prompt_builder.py       # Sistem prompt'u + few-shot örnekler
│   └── schemas.py              # Pydantic veri şemaları
│
├── session/
│   └── session_manager.py      # Redis oturum yönetimi
│
├── validation/
│   └── query_validator.py      # LLM çıktı doğrulayıcı
│
└── tests/                      # Birim testleri (40+ test)
    ├── conftest.py
    ├── test_engine.py
    ├── test_parser.py
    ├── test_sheets.py
    └── test_validator.py
```

---

## 🚀 Kurulum

### Gereksinimler

- Python 3.11+
- Docker & Docker Compose
- [Telegram Bot Token](https://core.telegram.org/bots#botfather)
- [Google Service Account](https://console.cloud.google.com/iam-admin/serviceaccounts) (Sheets API erişimi)
- [Groq API Key](https://console.groq.com/)
- [Ngrok Account](https://ngrok.com/) (webhook tunnel için)

### 1. Repoyu Klonlayın

```bash
git clone https://github.com/kullanici-adi/telegram-sheets-bot.git
cd telegram-sheets-bot
```

### 2. Ortam Değişkenlerini Ayarlayın

```bash
cp .env.example .env
```

`.env` dosyasını düzenleyin:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_WEBHOOK_URL=https://your-domain.ngrok-free.dev
TELEGRAM_SECRET_TOKEN=your_secret_token
WEBHOOK_PATH=/webhook/your_random_path

# Groq (LLM)
GROQ_API_KEY=your_groq_api_key

# Google Sheets
GOOGLE_SHEETS_ID=your_spreadsheet_id
GOOGLE_CREDENTIALS_JSON=base64_encoded_service_account_json

# Redis
REDIS_URL=redis://redis:6379

# Güvenlik
ALLOWED_CHAT_IDS=[your_chat_id]
ADMIN_CHAT_IDS=[your_chat_id]
LOG_SALT=random_salt_string
MAX_REQUESTS_PER_MINUTE=10

# Cache
CACHE_TTL_SECONDS=300

# Ngrok
NGROK_AUTHTOKEN=your_ngrok_auth_token
```

> **Google Credentials:** Service account JSON dosyasını Base64'e çevirmek için:
> ```bash
> base64 -w 0 service-account.json
> ```

### 3. Docker ile Çalıştırın

```bash
docker compose up -d
```

Bu komut 3 servis başlatır:
- **bot** — FastAPI uygulaması (port 8000)
- **redis** — Cache ve session store
- **ngrok** — Webhook tunnel

### 4. Lokal Geliştirme (Docker olmadan)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

> ⚠️ Lokal geliştirmede Redis sunucusu ayrıca çalışıyor olmalıdır.

---

## 💬 Kullanım

### Örnek Sorgular

| Sorgu | Açıklama |
|-------|----------|
| `50 binden fazla borcu olan müşteriler` | Filtrelenmiş liste |
| `dava olan müşteri sayısı` | Sayım |
| `konut kategorisindeki toplam borç` | Toplam hesaplama |
| `ortalama ödeme oranı` | Ortalama hesaplama |
| `genel rapor` | Özet istatistikler |
| `performans raporu` | Ödeme oranı dağılımı |
| `risk raporu` | Davalar ve düşük ödemeler |

### Bot Komutları

| Komut | Açıklama |
|-------|----------|
| `/rapor` | Genel rapor oluştur |
| `/yenile` | Cache temizle (sadece admin) |
| `/iptal` | Aktif işlemi iptal et |
| `/yardim` | Yardım mesajını göster |

---

## 🧪 Testler

```bash
# Tüm testleri çalıştır
pytest

# Kapsam raporu ile
pytest --cov=. --cov-report=html

# Belirli bir modül
pytest tests/test_engine.py -v
```

---

## 📋 Google Sheets Formatı

Bot, aşağıdaki sütunlara sahip bir Google Sheets tablosu bekler:

| Sütun Adı | Sistem Adı | Tip | Açıklama |
|-----------|------------|-----|----------|
| `id` | `id` | String | Kayıt ID'si |
| `entity_name` | `musteri_adi` | String | Müşteri adı |
| `entity_type` | `musteri_turu` | String | Müşteri türü (bireysel/kurumsal) |
| `numeric_value_1` | `toplam_borc` | Decimal | Toplam borç |
| `numeric_value_2` | `odenen_tutar` | Decimal | Ödenen tutar |
| `status_flag` | `dava_var_mi` | Boolean | Dava durumu (evet/hayır) |
| `date_field` | `kayit_tarihi` | Date | Kayıt tarihi (GG.AA.YYYY) |
| `category` | `kategori` | String | Kategori |

> Sayı formatları hem Türkçe (`10.000,50`) hem İngilizce (`10,000.50`) desteklenir.

---

## 🔒 Güvenlik

- **Webhook Secret Token** — Telegram'dan gelen istekler doğrulanır
- **Chat ID Whitelist** — Sadece yetkili kullanıcılar erişebilir
- **Rate Limiting** — Redis tabanlı, dakikada max istek sınırı
- **Log Güvenliği** — Chat ID hash'lenir, sorgu içeriği maskelenir (KVKK/GDPR)
- **Secrets Management** — Tüm hassas veriler `.env` dosyasında

---

## 🛠️ Teknolojiler

| Teknoloji | Kullanım |
|-----------|----------|
| [FastAPI](https://fastapi.tiangolo.com/) | Web framework (webhook endpoint) |
| [python-telegram-bot](https://python-telegram-bot.org/) | Telegram Bot API |
| [Groq](https://groq.com/) | LLM API (Llama 3.3 70B) |
| [gspread](https://gspread.readthedocs.io/) | Google Sheets API |
| [Redis](https://redis.io/) | Cache + Rate Limiting + Session |
| [Pydantic](https://docs.pydantic.dev/) | Veri doğrulama + Ayarlar |
| [structlog](https://www.structlog.org/) | Yapısal JSON loglama |
| [Docker](https://www.docker.com/) | Konteynerizasyon |
| [Ngrok](https://ngrok.com/) | Webhook tunnel |

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) altında lisanslanmıştır.
