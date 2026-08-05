# Reel Getiri — Gayrimenkul & Portföy Analizi

GitHub Pages üzerinde çalışan, tamamen statik bir **reel getiri** analiz aracı. Bir gayrimenkulün (veya başka bir yatırımın) giriş–çıkış kâr/zararını; dolar, euro, gram altın, BIST 100, GYO, Konut Fiyat Endeksi (KFE) ve enflasyona (TÜFE) karşı kıyaslar. Yüksek enflasyonlu bir ortamda "nominal kazandım ama alım gücüm ne oldu?" sorusunu net biçimde yanıtlar.

## İki mod

- **Hızlı Analiz** — Tek bir yatırımın alış/satış bilgilerini girip anında karşılaştırma, grafik ve "sonuç cümlesi" alırsınız.
- **Portföyüm** — Birden fazla pozisyonu (gayrimenkuller + diğerleri) tarayıcıda kaydedip (localStorage) toplam kâr/zarar, reel getiri ve portföyü tek tek alternatiflerle karşılaştırma. JSON olarak dışa/içe aktarılabilir.

## Nasıl hesaplıyor

- **Yatırılan sermaye (C0)** = alış fiyatı + alış tarafı masraflar (tapu + komisyon).
- **Gerçekleşen değer (V1)** = net satış geliri (satış − komisyon) + net kira geliri. Açık pozisyonda (hâlâ elinizdeyse) satış komisyonu uygulanmaz, bugünkü tahmini değeri girersiniz.
- **Nominal getiri** = V1 / C0 − 1, **CAGR** yıllıklandırılmış.
- **Reel getiri (TÜFE)** = V1 alış günü liralarına indirgenip C0 ile kıyaslanır → gerçek alım gücü değişimi.
- **Her enstrüman için**: "Aynı parayı buraya koysaydınız" değeri, mülkün o enstrümanı yenip yenmediği (o enstrüman cinsinden getirisi), başabaş satış fiyatı ve fırsat maliyeti.

Grafikte, aynı sermayenin her enstrümandaki zaman içi değeri gösterilir; **Nominal (₺)** ve **Reel (alış günü ₺'siyle)** görünümleri arasında geçiş yapılabilir. Reel görünümde yatay çizgi = enflasyonu tam karşılamak demektir.

## Canlı & tarihsel veri

- `data/*.json` içindeki aylık tarihsel serileri kullanır.
- USD/EUR için satış tarihi veri bitişinden yeniyse anlık kur API'sinden çekilir.
- Hiçbir seri için tahmin/projeksiyon yapılmaz. Bir serinin en yeni ayı henüz açıklanmadıysa (ör. içinde bulunulan ayın TÜFE'si) **son bilinen resmî değer** kullanılır. Bir seri belirgin biçimde geride kaldıysa üstte bilgilendirici bir not, hangi tarihe kadar veri olduğunu gösterir.

## Veriyi güncelleme

`scripts/update_data.py` her gün UTC 06:00'da GitHub Actions ile çalışır:

- **FX** (USD/EUR) → TCMB günlük kur XML'i (anahtar gerekmez).
- **Altın & BIST/GYO** → yfinance.
- **TÜFE & KFE** → TCMB EVDS (anahtar gerekir). Repo ayarlarından **Settings → Secrets and variables → Actions** altına `EVDS_API_KEY` ekleyin (ücretsiz: https://evds2.tcmb.gov.tr). Anahtar yoksa mevcut TÜFE/KFE verisi korunur.

## GitHub Pages

Repo **Settings → Pages → Build and deployment → Source** olarak **GitHub Actions** (veya `main` / root) seçilmelidir.

## Kullanım

Sayfayı açın, alış/satış bilgilerini girin, "Analiz et"e basın. Portföy için "Portföyüm" sekmesinden pozisyon ekleyin.

> Yatırım tavsiyesi değildir. Tarihsel veriler ve tahminler yanıltıcı olabilir.
