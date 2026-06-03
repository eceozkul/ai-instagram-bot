# AI Instagram Otomasyon Botu

RSS kaynaklarından haber tarar, Gemini ile içerik üretir, görsel oluşturur, Telegram'dan onay alır ve Instagram'a otomatik post atar.

Bu sistem **AI/teknoloji haberleri** için yazılmış ama RSS kaynaklarını değiştirerek **herhangi bir konuda** çalıştırılabilir (moda, spor, ekonomi, sağlık vb.).

---

## 🧠 Sistem Mimarisi

```
RSS Kaynakları (Google Sheet)
       ↓
Haber Toplama (4 saatte bir)
       ↓
Gemini Puanlama (1-10)
       ↓
   ┌───┴───┐
   ↓       ↓
9-10 puan  7-8 puan
Tek Post   Carousel
   ↓       ↓
Gemini Caption + Görsel Üretimi
       ↓
Telegram Onay Bekle (3 buton)
   ✅ Onayla  ✏️ Revize  ❌ Atla
       ↓
Instagram'a Yayınla
       ↓
Google Sheets Geçmiş + Log
```

---

## 🛠️ Kullanılan Teknolojiler

| Bileşen | Servis | Maliyet |
|---------|--------|---------|
| Dil | Python 3.11 | Ücretsiz |
| Çalıştırma | GitHub Actions | Ücretsiz (ayda 2000 dk) |
| Veritabanı | Google Sheets | Ücretsiz |
| AI | Google Gemini API | Ücretli (cüzi) |
| Onay | Telegram Bot API | Ücretsiz |
| Yayın | upload-post.com | Aylık abonelik |

---

## 📂 Dosya Yapısı

```
.
├── .github/workflows/
│   ├── daily.yml              # Ana bot — 4 saatte bir
│   └── telegram_commands.yml  # /pause /resume dinleyici
├── src/
│   ├── main.py                # Orkestratör
│   ├── config.py              # Sabitler ve env değişkenleri
│   ├── research.py            # RSS tarama + puanlama
│   ├── content.py             # Gemini caption üretimi
│   ├── image.py               # Gemini görsel + overlay
│   ├── post.py                # upload-post.com API
│   ├── sheets.py              # Google Sheets okuma/yazma
│   ├── telegram_approval.py   # Telegram onay sistemi
│   ├── token_tracker.py       # Token sayacı
│   └── logo.png               # (opsiyonel) Görsele eklenir
├── requirements.txt
├── .env.example               # Yerel test için template
├── README.md                  # Bu dosya
└── SETUP.md                   # Kurulum talimatları
```

---

## 📊 Google Sheets Yapısı

Sheet'te 4 sayfa olacak (Sayfa1 + Sayfa2 hariç diğerleri otomatik oluşur):

### Sayfa1 — RSS Feed Listesi
Manuel doldurursun.

| name | url | priority | Kategori |
|------|-----|----------|----------|
| TechCrunch AI | https://techcrunch.com/.../feed/ | 1 | News |

### Sayfa2 — Notlar
İsteğe bağlı, sen kullan.

### Ayarlar — Bot kontrolü (otomatik oluşur)
| key | value | açıklama |
|-----|-------|----------|
| bot_status | active | active veya paused |

### Geçmiş — Yayınlanan postlar (otomatik oluşur)
| date | topic | post_type | post_id | source | source_link | caption |

### Log — Her çalışmanın detayı (otomatik oluşur)
| date | status | post_type | telegram | articles_found | selected_topic | score | source | link | title | input_tokens | output_tokens | cost_usd | api_errors | notes |

---

## 🤖 Telegram Komutları

Bota şunları yazabilirsin:
- `/pause` — botu duraklat (sonraki çalışmadan itibaren)
- `/resume` — botu yeniden aktif et
- `/status` — bot şu an aktif mi?

Komutlar 5 dakikada bir kontrol edilir.

---

## 🔧 Karar Mantığı

**Puanlama (Gemini):**
- 9-10 → Çok büyük haber, tek post
- 7-8 → Önemli haber, carousel (en az 2 haber varsa)
- 7 altı → Atla

**Zaman filtresi:**
- Sadece son 4 saatte yayınlanmış haberler alınır
- Yeni haber yoksa sessizce çıkar

**Tekrar önleme:**
- Geçmiş 15 günde paylaşılan başlıklar Gemini'ye gönderilir
- Benzer haberler düşük puan alır

---

## 🚀 Hızlı Başlangıç

Detaylı kurulum için **[SETUP.md](SETUP.md)** dosyasını oku.

Özet:
1. Bu repoyu fork'la
2. Gemini API key al
3. upload-post.com hesabı aç + Instagram bağla
4. Telegram bot oluştur
5. Google Sheet oluştur + service account ile paylaş
6. GitHub Secrets'a 6 değişkeni ekle
7. Actions'tan **Run workflow** çalıştır

---

## 🎨 Konuyu Değiştirme

Bu sistem AI haberleri için yazılmış. Başka konuya çevirmek için:

1. **Google Sheet'teki feed listesini değiştir** — RSS URL'leri ne hakkındaysa o konuda haber gelir
2. **`src/config.py` → `HASHTAGS`** listesini güncelle
3. **`src/research.py` → puanlama prompt'unu** kendi alanına uyarla (örn. "moda haberleri için en uygun" gibi)
4. **`src/content.py` → caption stil prompt'unu** değiştir
5. **`src/image.py` → görsel stil prompt'unu** değiştir (örn. "minimal pastel" yerine "moda tarzı")

---

## 💰 Tahmini Aylık Maliyet

- **Gemini API:** ~$2-5 (günde 6 çalışma)
- **upload-post.com:** Aboneliğine bağlı
- **GitHub Actions:** Ücretsiz
- **Diğer:** Ücretsiz

Toplam: **~$5-10/ay** + upload-post.com aboneliği

---

## 🐛 Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| 404 Model Not Found | Gemini modeli değişmiş olabilir, `config.py` güncelle |
| Username not associated | upload-post.com'da Instagram bağlı değil |
| 429 Rate Limit | Gemini ücretsiz kotanı geçtin, billing aç |
| Sheet okunamadı | Service account email Sheet'le paylaşılmamış |
| Telegram tepki yok | Bot'a önce manuel mesaj at, sonra getUpdates çalışır |
