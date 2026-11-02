# TOON vs JSON vs XML — Benchmark Raporu

**Oluşturulma tarihi:** 2026-05-31 20:10  
**Proje:** Büyük Dil Modellerinde Veri Serileştirme  
**Grup:** Grup 5 — Eskişehir Osmangazi Üniversitesi

---

## 1. LLM Benchmark Sonuçları (Ollama)

### Model: `gemma3:1b` | Veri: `flat`
**Soru:** How many records are in the users list and what are their field names?

| Format | Doğruluk | Prompt Token | TTFT (s) | Toplam Süre (s) | Boyut (byte) | Token Tasarrufu | Durum |
|--------|----------|-------------|----------|-----------------|--------------|-----------------|-------|
| JSON | %100 | 4096.0 | 3.181 | 5.166 | 12887 |  | ✓ OK |
| TOON | %100 | 3044.0 | 2.384 | 22.583 | 5334 | +25.7% | ✓ OK |
| XML | %0 | 4096.0 | 3.177 | 7.548 | 17913 | +0.0% | ✓ OK |

### Model: `gemma3:1b` | Veri: `flat`
**Soru:** What is the capital of Country_42?

| Format | Doğruluk | Prompt Token | TTFT (s) | Toplam Süre (s) | Boyut (byte) | Token Tasarrufu | Durum |
|--------|----------|-------------|----------|-----------------|--------------|-----------------|-------|
| JSON | %0 | 4096.0 | 3.169 | 3.664 | 12887 |  | ✓ OK |
| TOON | %0 | 3039.0 | 2.368 | 2.512 | 5334 | +25.8% | ✓ OK |
| XML | %0 | 4096.0 | 3.18 | 3.229 | 17913 | +0.0% | ✓ OK |

### Model: `gemma3:1b` | Veri: `flat`
**Soru:** How many users have the 'admin' role?

| Format | Doğruluk | Prompt Token | TTFT (s) | Toplam Süre (s) | Boyut (byte) | Token Tasarrufu | Durum |
|--------|----------|-------------|----------|-----------------|--------------|-----------------|-------|
| JSON | %100 | 4096.0 | 3.173 | 14.874 | 12887 |  | ✓ OK |
| TOON | %67 | 3039.0 | 2.382 | 2.405 | 5334 | +25.8% | ✓ OK |
| XML | %0 | 4096.0 | 3.198 | 3.369 | 17913 | +0.0% | ✓ OK |

---

## 2. Flat vs Nested Veri Analizi (Token Tahmini)

### Flat (Düz) Veri

| Format | Karakter | Byte | Satır | Tahmini Token | Token Tasarrufu |
|--------|----------|------|-------|---------------|-----------------|
| JSON (sıkıştırılmış) | 12,887 | 12,887 | 1 | 4,007 |  |
| TOON | 5,334 | 5,334 | 203 | 2,334 | +41.8% |
| XML (minified) | 17,913 | 17,913 | 1 | 6,213 | -55.1% |

### Nested (İç İçe) Veri

| Format | Karakter | Byte | Satır | Tahmini Token | Durum |
|--------|----------|------|-------|---------------|-------|
| JSON (sıkıştırılmış) | 6,987 | 6,987 | 1 | 2,403 | ✅ Başarılı |
| XML (minified) | 9,904 | 9,904 | 1 | 3,609 | ✅ Başarılı |
| TOON | — | — | — | — | ❌ Desteklenmiyor |

### Bulgular

- **Flat veride TOON**, sıkıştırılmış JSON'a kıyasla **%41.8 daha az token** harcıyor.
- **Flat veride XML**, JSON'a kıyasla **%55.1 daha fazla token** harcıyor.
- **Nested veride TOON** dönüşümü başarısız oluyor — bu TOON'un belgelenmiş bir yapısal limitasyonudur. JSON ve XML bu noktada öne çıkıyor.
- Adil karşılaştırma için baz format olarak **sıkıştırılmış (minified) JSON** kullanılmıştır ve token sayıları **tiktoken (BPE)** kullanılarak hesaplanmıştır.

---

## 3. Genel Değerlendirme

### Metodolojik İyileştirmeler
Önceki analizdeki kusurlar giderilmiş ve daha adil bir kıyaslama sunulmuştur:
1. **XML Adaleti:** XML dosyaları ham, boşluklu formatta okutulmak yerine tıpkı JSON gibi Python nesnesinden minified (boşluksuz) olarak üretilerek teste dahil edildi.
2. **Soru Zorlukları (Önyargı Önleme):** TOON formatının sadece header (başlık) okuyarak avantaj sağladığı şema sorularının yanına, modelin veriyi okumasını zorunlu kılan 'arama' ve 'kümeleme' soruları eklendi.
3. **Doğruluk Kontrolü:** Modelin hızlı ancak halüsinasyon içeren yanlış cevaplar vermesi durumu, beklenen anahtar kelimeler ile test edilerek *Doğruluk (%)* metriği ile rapora dahil edildi.
4. **Gerçekçi Token Tahmini:** İlkel `len//4` formülü yerine, noktalama işaretlerini ayrı sayan endüstri standardı `tiktoken` (BPE algoritması) entegre edilerek, TOON'un %58 gibi abartılı görünen tasarruf iddiası gerçekçi boyutlara indirgendi.

### TOON'un Güçlü Yönleri
- Düz (flat) tablo verilerinde tekrarlayan alan adlarını kaldırarak token tasarrufu sağlar.
- Şema bilgisini (alan adları ve kayıt sayısı) header'da önceden belirterek LLM'in veri yapısını hızlı kavramasına yardımcı olur.

### TOON'un Zayıf Yönleri
- İç içe geçmiş (nested) veri yapılarını **desteklemiyor** — hiyerarşik verilerde kullanılamıyor.
- JSON ve XML'in aksine standart bir ekosistemi ve doğrulayıcısı yoktur.

### Sonuç
TOON, **yalnızca düz ve sabit alanlı veri listelerinde** anlamlı bir token tasarrufu sağlar. Karmaşık ve hiyerarşik veri yapılarında JSON tek geçerli ve en güvenli seçenek olmaya devam etmektedir. Token maliyetinin kritik olduğu büyük düz veri setlerinde TOON değerlendirilebilir ancak genel amaçlı bir alternatif değildir.
