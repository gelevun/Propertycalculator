# Property Calculator

GitHub Pages üzerinde çalışan, tamamen statik gayrimenkul reel getiri analiz aracı.

## Özellikler

- Mobil uyumlu, modern ve sade arayüz
- Nominal ve reel (TÜFE) getiri, CAGR, USD/EUR bazlı getiri
- Alternatif yatırım karşılaştırması (altın, BIST100, GYO, KFE)
- Fırsat maliyeti ve başa baş satış fiyatı
- Tapu, komisyon, kira geliri ve m² desteği
- Dark / light tema
- PWA desteği

## Canlı Veri

- `data/*.json` dosyalarındaki tarihsel verileri kullanır.
- USD ve EUR için satış tarihi güncelse anlık kur API’sinden veri çeker.
- Veriler her gün UTC 06:00’da GitHub Actions ile güncellenmeye çalışılır.

## GitHub Pages Ayarları

Repo ayarlarından **Pages > Build and deployment > Source** olarak **GitHub Actions** seçilmelidir.

## Kullanım

Sayfayı açın, alış/satış bilgilerini girin ve “Analiz Et” butonuna basın.
