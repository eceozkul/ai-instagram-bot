# Kurulum Talimatları

Bu botu kendi kullanımına almak için adım adım rehber. Her adım bir kez yapılır, sonra otomatik çalışır.

**Toplam süre:** ~45 dakika

---

## 📦 1. Bu Repoyu Kendi Hesabına Al

GitHub'da bu repoyu **Fork** et veya yeni bir repo açıp dosyaları yükle.

---

## 🔑 2. Gemini API Key Al

1. [aistudio.google.com/apikey](https://aistudio.google.com/apikey) sayfasına git
2. **Create API Key** ile yeni bir key oluştur
3. Key'i kopyala, kaydet (örn. `AIza...` ile başlar)
4. **Billing aç:** [console.cloud.google.com](https://console.cloud.google.com) → Billing → ödeme yöntemi ekle
   - Ücretsiz tier kısıtlı, billing olmadan sürekli `429 quota exceeded` alırsın
   - Aylık ~$2-5 harcar, 1. ay $300 kredi var

---

## 📸 3. Meta (Instagram) API Erişimi

Gereksinimler: **Instagram Business hesabı** (ayarlardan Creator/Business'a çevir).

1. [developers.facebook.com](https://developers.facebook.com) → **My Apps → Create App** (tip: Business/İşletme)
2. App'e **Instagram** ürününü ekle → **API setup with Instagram business login**
3. **Generate access tokens** bölümünde Instagram hesabını bağla
4. Hesabın altında görünen numerik ID'yi not al → bu senin `IG_BUSINESS_ID`
5. **Generate token** ile access token oluştur → bu senin `META_ACCESS_TOKEN` (`IGAA...` ile başlar)

> ⚠️ Token ~60 günde bir yenilenmeli. Süresi dolunca bot Telegram'dan hata bildirir;
> yeni token üretip GitHub Secret'ı güncellemen yeterli.

> ⚠️ Repo **public** olmalı — Meta, görselleri `raw.githubusercontent.com` URL'sinden indirir,
> private repolarda bu URL dışarıya kapalıdır.

---

## 💬 4. Telegram Bot Oluştur

### Bot oluşturma:
1. Telegram'da `@BotFather`'a yaz
2. `/newbot` gönder
3. İsim ver: `My AI Bot`
4. Username ver: `my_ai_news_bot` (sonu `_bot` bitmeli)
5. Sana bir **token** verecek (`123456:ABC-DEF...` formatında) — kopyala

### Chat ID'ni bul:
1. Oluşturduğun botu Telegram'da bul ve **Start** bas, bir mesaj yaz
2. Tarayıcıda aç: `https://api.telegram.org/bot<TOKEN>/getUpdates`
   (`<TOKEN>` yerine yukarıdaki token'ı koy)
3. Çıkan JSON'da `"chat":{"id":XXXXXXX}` kısmındaki sayıyı kopyala

---

## 📊 5. Google Sheets Hazırlığı

### Sheet oluştur:
1. [sheets.google.com](https://sheets.google.com) → yeni boş sheet aç
2. Adını ver (örn. `bot-data`)
3. URL'den **Sheet ID**'yi kopyala: `https://docs.google.com/spreadsheets/d/SHEET_ID_BURADA/edit`

### Sayfa1'i hazırla — Feed listesi:

| name | url | priority | Kategori |
|------|-----|----------|----------|
| TechCrunch AI | https://techcrunch.com/category/artificial-intelligence/feed/ | 1 | News |
| Hacker News | https://news.ycombinator.com/rss | 1 | Community |

(Kendi konuna göre RSS URL'lerini doldur — Google'da `[KONU] RSS feed` ararsan bulursun)

### Service Account oluştur (Sheet'e yazma için):

1. [console.cloud.google.com](https://console.cloud.google.com) → projeyi seç
2. **APIs & Services → Library** → **Google Sheets API** ara → **Enable**
3. **IAM & Admin → Service Accounts → Create Service Account**
   - İsim: `bot-sheets`
   - Role: gerek yok, **Done**
4. Oluşan account'a tıkla → **Keys → Add Key → Create new key → JSON** → indir
5. JSON dosyasını aç, içindeki `client_email` adresini (`xxx@xxx.iam.gserviceaccount.com`) kopyala
6. Google Sheet'i aç → **Share** → bu email'i **Editor** olarak ekle

### `src/config.py`'de Sheet ID'yi güncelle:

```python
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "SENİN_SHEET_ID_BURAYA")
```

---

## 🔐 6. GitHub Secrets'a Değerleri Ekle

Reponun **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Değer |
|-------------|-------|
| `GEMINI_API_KEY` | 2. adımdaki key (`AIza...`) |
| `META_ACCESS_TOKEN` | 3. adımdaki Instagram access token (`IGAA...`) |
| `IG_BUSINESS_ID` | 3. adımdaki numerik Instagram hesap ID'si |
| `TELEGRAM_BOT_TOKEN` | 4. adımdaki bot token |
| `TELEGRAM_CHAT_ID` | 4. adımdaki chat ID |
| `GOOGLE_SERVICE_ACCOUNT` | 5. adımdaki JSON dosyasının **tüm içeriği tek satırda** |

### GOOGLE_SERVICE_ACCOUNT için ipucu:
JSON dosyasının içeriğini terminalde tek satıra çevir:

```bash
python3 -c "import json; print(json.dumps(json.load(open('downloaded-key.json'))))"
```

Çıkan tek satırlık metni yapıştır.

---

## 🎨 7. (Opsiyonel) Marka Kimliği

### Logo eklemek istersen:
- `src/logo.png` dosyası olarak repoya yükle (PNG, şeffaf arkaplan, ~200x200px)
- Bot otomatik tanır, görsele ekler
- Dosya yoksa logosuz devam eder

### Hashtag'leri kendi konuna göre değiştir:
`src/config.py` → `HASHTAGS` listesini güncelle.

### Görsel stilini değiştir:
`src/image.py` → `build_image_prompt` fonksiyonundaki `style` değişkenini düzenle.

### Caption stilini değiştir:
`src/content.py` → `generate_caption` içindeki prompt'u kendi tonuna göre yaz.

---

## ▶️ 8. İlk Çalıştırma

1. GitHub'da **Actions** sekmesine git
2. **AI Instagram Bot** workflow'unu seç
3. **Run workflow** → **Run workflow** bas
4. Çalışmasını bekle (3-5 dk)
5. Telegram'a görsel + caption gelmeli
6. **✅ Onayla** bas → Instagram'a post atılır

### Sonraki çalıştırmalar:
Bot otomatik olarak **4 saatte bir** çalışacak (UTC saatiyle 00:00, 04:00, 08:00, 12:00, 16:00, 20:00).

---

## 🧪 9. Yerel Test (Opsiyonel)

Bilgisayarında test etmek istersen:

```bash
# Repoyu klonla
git clone https://github.com/SENİN_KULLANICI_ADIN/REPO_ADIN.git
cd REPO_ADIN

# Sanal ortam
python3 -m venv .venv
source .venv/bin/activate

# Bağımlılıklar
pip install -r requirements.txt

# .env dosyası oluştur
cp .env.example .env
# .env'i aç ve değerleri doldur (GitHub Secrets'taki ile aynı)

# Çalıştır
cd src
python main.py
```

---

## ❓ Sıkça Karşılaşılan Sorunlar

### "404 model not found"
Gemini modeli değişmiş. `src/config.py` → `GEMINI_TEXT_MODEL` ve `GEMINI_IMAGE_MODEL` değerlerini güncelle.
Mevcut modelleri görmek için:
```python
from google import genai
import os
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
for m in client.models.list():
    print(m.name)
```

### "Invalid OAuth access token"
Meta token'ı yanlış kopyalanmış veya süresi dolmuş (~60 gün). Meta developer panelinden yeni token üret, `META_ACCESS_TOKEN` secret'ını güncelle.

### "Media download has failed"
Meta görseli indiremiyor — repo private kalmış olabilir, public yap.

### "429 RESOURCE_EXHAUSTED"
Gemini ücretsiz kotanı geçtin. Google Cloud Console → Billing'i aktif et.

### "GOOGLE_SERVICE_ACCOUNT ortam değişkeni eksik"
GitHub Secrets'a JSON içeriğini eklemeyi unutmuşsun veya tek satırda değil.

### Telegram tepki vermiyor
- Bot'a en az bir kez manuel mesaj atmadıysan `getUpdates` boş döner
- Token veya Chat ID yanlış olabilir
- Workflow log'una bak: `⚠️ Telegram ayarları eksik` mesajı varsa secret eksik

### Sheet'e yazamıyor
- Service account email'ini Sheet'le paylaşmamışsın
- Editor yetkisi vermemişsin
- Sheet ID yanlış

---

## 🔄 Bot Kontrolü

Çalıştıktan sonra Telegram'dan:
- `/pause` → durdur (sonraki çalışmadan itibaren)
- `/resume` → devam ettir
- `/status` → şu an aktif mi?

Komutlar her çalışmanın başında (4 saatte bir) okunur. Acil durumda Google Sheet'teki
Ayarlar sayfasından `bot_status` değerini elle değiştirebilirsin.

---

## 🚪 Geliştirici Notları

Bu projeyi Claude Code ile birlikte geliştirdim. Yeni özellik eklemek istediğinde Claude Code'a şunları söyle:

1. "Bu repo bir AI Instagram otomasyon botu. README.md'yi okuyup sistemi anla."
2. "Şu özelliği eklemek istiyorum: ..."

Sistem modüler tasarlandı, her dosya bir sorumluluk:
- `research.py` → haber + puanlama
- `content.py` → metin
- `image.py` → görsel
- `post.py` → yayın
- `sheets.py` → veritabanı
- `telegram_approval.py` → onay
- `main.py` → orkestratör

Yeni bir aşama ekleyeceksen `main.py`'deki run() fonksiyonuna bağla.
