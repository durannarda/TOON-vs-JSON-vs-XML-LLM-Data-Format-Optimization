"""
generate_report.py
benchmark_results.csv ve nested_vs_flat_results.csv dosyalarını okuyarak
hem ekrana hem de report.md dosyasına özet rapor üretir.
"""

import argparse
import csv
import os
from collections import defaultdict
from datetime import datetime

BENCHMARK_CSV      = "benchmark_results.csv"
NESTED_FLAT_CSV    = "nested_vs_flat_results.csv"
DEFAULT_OUTPUT_MD  = "report.md"

def read_csv(path: str) -> list:
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def process_benchmark(rows: list) -> dict:
    groups = defaultdict(list)
    for row in rows:
        key = (row["model"], row["data_type"], row["question"])
        groups[key].append(row)
    return groups

def format_benchmark_section(groups: dict) -> str:
    lines = []
    lines.append("## 1. LLM Benchmark Sonuçları (Ollama)\n")

    if not groups:
        lines.append("_Henüz benchmark verisi yok. `python3 benchmark.py` çalıştırın._\n")
        return "\n".join(lines)

    for (model, data_type, question), rows in groups.items():
        lines.append(f"### Model: `{model}` | Veri: `{data_type}`")
        lines.append(f"**Soru:** {question}\n")

        lines.append("| Format | Doğruluk | Prompt Token | TTFT (s) | Toplam Süre (s) | Boyut (byte) | Token Tasarrufu | Durum |")
        lines.append("|--------|----------|-------------|----------|-----------------|--------------|-----------------|-------|")

        baseline = next((r for r in rows if r["format"] == "json"), None)
        baseline_tokens = float(baseline["avg_prompt_tokens"]) if baseline and baseline["avg_prompt_tokens"] else None

        for row in rows:
            fmt     = row["format"].upper()
            
            # Doğruluk oranını formatla
            acc_raw = row.get('accuracy_pct', '')
            acc     = f"%{float(acc_raw):.0f}" if acc_raw else "—"
            
            tokens  = row.get("avg_prompt_tokens", "—") or "—"
            ttft    = row.get("avg_ttft_s", "—")         or "—"
            total   = row.get("avg_total_time_s", "—")   or "—"
            bytesize = row.get("data_bytes", "—")         or "—"
            overflow = row.get("overflow", "")
            status   = "⚠ OVERFLOW" if str(overflow).lower() == "true" else "✓ OK"

            savings = ""
            if baseline_tokens and row.get("avg_prompt_tokens") and row["format"] != "json":
                diff = baseline_tokens - float(row["avg_prompt_tokens"])
                pct  = diff / baseline_tokens * 100
                savings = f"{pct:+.1f}%"

            lines.append(f"| {fmt} | {acc} | {tokens} | {ttft} | {total} | {bytesize} | {savings} | {status} |")

        overflow_rows = [r for r in rows if str(r.get("overflow", "")).lower() == "true"]
        if overflow_rows:
            overflow_fmts = ", ".join(r["format"].upper() for r in overflow_rows)
            lines.append(f"\n> ⚠ **DİKKAT:** {overflow_fmts} formatları context penceresini doldurdu.")
            lines.append("> Bu formatlar için token sayısı, süre ölçümleri ve doğruluk **güvenilmez**.\n")

        lines.append("")

    return "\n".join(lines)

def format_nested_flat_section(rows: list) -> str:
    lines = []
    lines.append("## 2. Flat vs Nested Veri Analizi (Token Tahmini)\n")

    if not rows:
        lines.append("_Henüz veri yok. `python3 nested_vs_flat_test.py` çalıştırın._\n")
        return "\n".join(lines)

    last_ts = rows[-1]["timestamp"] if rows else ""
    flat_rows   = [r for r in rows if r["data_type"] == "flat"   and r["timestamp"] == last_ts]
    nested_rows = [r for r in rows if r["data_type"] == "nested" and r["timestamp"] == last_ts]

    lines.append("### Flat (Düz) Veri\n")
    lines.append("| Format | Karakter | Byte | Satır | Tahmini Token | Token Tasarrufu |")
    lines.append("|--------|----------|------|-------|---------------|-----------------|")

    baseline_flat = next((r for r in flat_rows if "JSON" in r["label"]), None)
    baseline_tokens = int(baseline_flat["tokens_est"]) if baseline_flat and baseline_flat.get("tokens_est") else None

    for row in flat_rows:
        if not row.get("tokens_est"):
            continue
        savings = ""
        if baseline_tokens and "JSON" not in row["label"]:
            diff = baseline_tokens - int(row["tokens_est"])
            pct  = diff / baseline_tokens * 100
            savings = f"{pct:+.1f}%"
        lines.append(f"| {row['label']} | {int(row['chars']):,} | {int(row['bytes']):,} | {int(row['lines']):,} | {int(row['tokens_est']):,} | {savings} |")

    lines.append("")
    lines.append("### Nested (İç İçe) Veri\n")
    lines.append("| Format | Karakter | Byte | Satır | Tahmini Token | Durum |")
    lines.append("|--------|----------|------|-------|---------------|-------|")

    for row in nested_rows:
        if row.get("error"):
            lines.append(f"| {row['label']} | — | — | — | — | ❌ Desteklenmiyor |")
        else:
            lines.append(f"| {row['label']} | {int(row['chars']):,} | {int(row['bytes']):,} | {int(row['lines']):,} | {int(row['tokens_est']):,} | ✅ Başarılı |")

    lines.append("")
    lines.append("### Bulgular\n")

    if baseline_tokens:
        toon_flat = next((r for r in flat_rows if r["label"] == "TOON" and r.get("tokens_est")), None)
        if toon_flat:
            savings_pct = (baseline_tokens - int(toon_flat["tokens_est"])) / baseline_tokens * 100
            lines.append(f"- **Flat veride TOON**, sıkıştırılmış JSON'a kıyasla **%{savings_pct:.1f} daha az token** harcıyor.")
            
        xml_flat = next((r for r in flat_rows if r["label"] == "XML (minified)" and r.get("tokens_est")), None)
        if xml_flat:
            xml_diff = int(xml_flat["tokens_est"]) - baseline_tokens
            xml_pct = xml_diff / baseline_tokens * 100
            lines.append(f"- **Flat veride XML**, JSON'a kıyasla **%{xml_pct:.1f} daha fazla token** harcıyor.")

    toon_nested_error = next((r for r in nested_rows if r["label"] == "TOON" and r.get("error")), None)
    if toon_nested_error:
        lines.append("- **Nested veride TOON** dönüşümü başarısız oluyor — bu TOON'un belgelenmiş bir yapısal limitasyonudur. JSON ve XML bu noktada öne çıkıyor.")

    lines.append("- Adil karşılaştırma için baz format olarak **sıkıştırılmış (minified) JSON** kullanılmıştır ve token sayıları **tiktoken (BPE)** kullanılarak hesaplanmıştır.")
    lines.append("")

    return "\n".join(lines)

def format_conclusion() -> str:
    lines = []
    lines.append("## 3. Genel Değerlendirme\n")

    lines.append("### Metodolojik İyileştirmeler")
    lines.append("Önceki analizdeki kusurlar giderilmiş ve daha adil bir kıyaslama sunulmuştur:")
    lines.append("1. **XML Adaleti:** XML dosyaları ham, boşluklu formatta okutulmak yerine tıpkı JSON gibi Python nesnesinden minified (boşluksuz) olarak üretilerek teste dahil edildi.")
    lines.append("2. **Soru Zorlukları (Önyargı Önleme):** TOON formatının sadece header (başlık) okuyarak avantaj sağladığı şema sorularının yanına, modelin veriyi okumasını zorunlu kılan 'arama' ve 'kümeleme' soruları eklendi.")
    lines.append("3. **Doğruluk Kontrolü:** Modelin hızlı ancak halüsinasyon içeren yanlış cevaplar vermesi durumu, beklenen anahtar kelimeler ile test edilerek *Doğruluk (%)* metriği ile rapora dahil edildi.")
    lines.append("4. **Gerçekçi Token Tahmini:** İlkel `len//4` formülü yerine, noktalama işaretlerini ayrı sayan endüstri standardı `tiktoken` (BPE algoritması) entegre edilerek, TOON'un %58 gibi abartılı görünen tasarruf iddiası gerçekçi boyutlara indirgendi.\n")

    lines.append("### TOON'un Güçlü Yönleri")
    lines.append("- Düz (flat) tablo verilerinde tekrarlayan alan adlarını kaldırarak token tasarrufu sağlar.")
    lines.append("- Şema bilgisini (alan adları ve kayıt sayısı) header'da önceden belirterek LLM'in veri yapısını hızlı kavramasına yardımcı olur.\n")

    lines.append("### TOON'un Zayıf Yönleri")
    lines.append("- İç içe geçmiş (nested) veri yapılarını **desteklemiyor** — hiyerarşik verilerde kullanılamıyor.")
    lines.append("- JSON ve XML'in aksine standart bir ekosistemi ve doğrulayıcısı yoktur.\n")

    lines.append("### Sonuç")
    lines.append(
        "TOON, **yalnızca düz ve sabit alanlı veri listelerinde** anlamlı bir token tasarrufu sağlar. "
        "Karmaşık ve hiyerarşik veri yapılarında JSON tek geçerli ve en güvenli seçenek olmaya devam etmektedir. "
        "Token maliyetinin kritik olduğu büyük düz veri setlerinde TOON değerlendirilebilir ancak genel amaçlı bir alternatif değildir.\n"
    )

    return "\n".join(lines)

def generate_report(output_path: str):
    benchmark_rows   = read_csv(BENCHMARK_CSV)
    nested_flat_rows = read_csv(NESTED_FLAT_CSV)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    sections = []
    sections.append(f"# TOON vs JSON vs XML — Benchmark Raporu\n")
    sections.append(f"**Oluşturulma tarihi:** {now}  ")
    sections.append(f"**Proje:** Büyük Dil Modellerinde Veri Serileştirme  ")
    sections.append(f"**Grup:** Grup 5 — Eskişehir Osmangazi Üniversitesi\n")
    sections.append("---\n")

    sections.append(format_benchmark_section(process_benchmark(benchmark_rows)))
    sections.append("---\n")
    sections.append(format_nested_flat_section(nested_flat_rows))
    sections.append("---\n")
    sections.append(format_conclusion())

    full_report = "\n".join(sections)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_report)
        
    print(full_report)
    print(f"\n{'='*60}")
    print(f"[OK] Rapor oluşturuldu: {output_path}")
    print(f"{'='*60}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CSV sonuçlarından özet rapor üret")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_MD, help="Çıktı Markdown dosyası")
    args = parser.parse_args()

    generate_report(args.output)