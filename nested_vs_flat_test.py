"""
nested_vs_flat_test.py
Flat ve nested veri yapılarında JSON, TOON ve XML'in token/boyut karşılaştırmasını yapar.

Bu test Ollama gerektirmez — sadece veri boyutu ve BPE tabanlı token tahmini üzerinden
formatların güçlü/zayıf yönlerini sayısal olarak ortaya koyar.
"""

import json
import csv
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime

from json_to_toon import json_to_toon

# Tokenizer kurulumu (Gerçekçi BPE tahmini için tiktoken önerilir)
try:
    import tiktoken
    # cl100k_base modeli (GPT-3.5/4 standardı) genel tokenizasyon karakteristiği için iyi bir referanstır
    tokenizer = tiktoken.get_encoding("cl100k_base")
    HAS_TIKTOKEN = True
    print("[BİLGİ] 'tiktoken' bulundu. Token tahminleri gerçek BPE algoritmasıyla yapılacak.")
except ImportError:
    HAS_TIKTOKEN = False
    print("[UYARI] 'tiktoken' bulunamadı. Token tahminleri Regex tabanlı Heuristic ile yapılacak.")
    print("        Daha kesin sonuçlar için: pip install tiktoken")

def estimate_tokens(text: str) -> int:
    """
    Metnin token sayısını tahmin eder.
    tiktoken varsa gerçek BPE kullanır, yoksa noktalama işaretlerini 
    ayrı token sayan gerçekçi bir Regex yaklaşımı kullanır.
    """
    if HAS_TIKTOKEN:
        return len(tokenizer.encode(text))
    else:
        # Kelimeleri veya tekil noktalama işaretlerini ayrı ayrı yakala
        # JSON ve XML'deki {, ", :, <, > gibi karakterleri affetmez
        tokens = re.findall(r'\w+|[^\w\s]', text)
        return len(tokens)

def load_flat_data() -> dict:
    with open("input.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_nested_data() -> dict:
    with open("nested_input.json", "r", encoding="utf-8") as f:
        return json.load(f)

def dict_to_xml_minified(data: dict) -> str:
    """Sözlüğü minified (boşluksuz) XML string'ine çevirir. Nested yapıyı destekler."""
    def build_tree(parent, current_data):
        if isinstance(current_data, dict):
            for k, v in current_data.items():
                safe_k = str(k).replace(" ", "_")
                child = ET.SubElement(parent, safe_k)
                build_tree(child, v)
        elif isinstance(current_data, list):
            for item in current_data:
                child = ET.SubElement(parent, "item")
                build_tree(child, item)
        else:
            parent.text = "" if current_data is None else str(current_data)

    root_el = ET.Element("root")
    for key, value in data.items():
        safe_key = str(key).replace(" ", "_")
        section_el = ET.SubElement(root_el, safe_key)
        build_tree(section_el, value)
    
    return ET.tostring(root_el, encoding="unicode")

def analyze_format(label: str, text: str) -> dict:
    chars = len(text)
    bytes_size = len(text.encode("utf-8"))
    tokens_est = estimate_tokens(text)
    lines = text.count("\n") + 1

    return {
        "label": label,
        "chars": chars,
        "bytes": bytes_size,
        "lines": lines,
        "tokens_est": tokens_est,
    }

def test_flat() -> list:
    print("\n" + "=" * 60)
    print("  TEST 1: FLAT (Düz) Veri")
    print("  Kaynak: input.json")
    print("=" * 60)

    data = load_flat_data()

    json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    xml_str = dict_to_xml_minified(data)
    toon_str = json_to_toon(data)

    json_metrics = analyze_format("JSON (sıkıştırılmış)", json_str)
    xml_metrics  = analyze_format("XML (minified)", xml_str)
    toon_metrics = analyze_format("TOON", toon_str)

    results = [json_metrics, toon_metrics, xml_metrics]
    _print_comparison(results, baseline="JSON (sıkıştırılmış)")

    return [{"data_type": "flat", **r} for r in results]

def test_nested() -> list:
    print("\n" + "=" * 60)
    print("  TEST 2: NESTED (İç İçe) Veri")
    print("  Kaynak: nested_input.json")
    print("=" * 60)

    data = load_nested_data()

    json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    json_metrics = analyze_format("JSON (sıkıştırılmış)", json_str)

    xml_str = dict_to_xml_minified(data)
    xml_metrics = analyze_format("XML (minified)", xml_str)

    print("\n  TOON dönüşümü deneniyor...")
    try:
        toon_str = json_to_toon(data)
        toon_metrics = analyze_format("TOON", toon_str)
        toon_status = "başarılı"
    except ValueError as e:
        print(f"\n  ⚠ BEKLENEN HATA: {e}")
        print("  → TOON nested veriyi desteklemiyor.")
        toon_metrics = {
            "label": "TOON", "chars": None, "bytes": None, "lines": None, "tokens_est": None, "error": str(e),
        }
        toon_status = "başarısız (beklenen)"

    results = [json_metrics, xml_metrics, toon_metrics]

    print(f"\n  Sonuç: JSON ✅  |  XML ✅  |  TOON {toon_status}")
    _print_comparison([json_metrics, xml_metrics], baseline="JSON (sıkıştırılmış)")

    return [{"data_type": "nested", **r} for r in results]

def test_flat_vs_nested_json():
    print("\n" + "=" * 60)
    print("  TEST 3: FLAT vs NESTED — JSON boyut karşılaştırması")
    print("=" * 60)

    flat_data = load_flat_data()
    nested_data = load_nested_data()

    flat_json = json.dumps(flat_data, separators=(",", ":"), ensure_ascii=False)
    nested_json = json.dumps(nested_data, separators=(",", ":"), ensure_ascii=False)

    flat_m = analyze_format("Flat JSON", flat_json)
    nested_m = analyze_format("Nested JSON", nested_json)

    flat_records = sum(len(v) for v in flat_data.values() if isinstance(v, list))
    nested_records = sum(len(v) for v in nested_data.values() if isinstance(v, list))

    print(f"\n  Flat   : {flat_records} kayıt  → {flat_m['tokens_est']} tahmini token")
    print(f"  Nested : {nested_records} kayıt  → {nested_m['tokens_est']} tahmini token")

    if flat_records == nested_records:
        ratio = nested_m["tokens_est"] / flat_m["tokens_est"]
        print(f"\n  Nested veri, flat veriye göre ~{ratio:.1f}x daha fazla token harcıyor.")

def _print_comparison(results: list, baseline: str = None):
    base = next((r for r in results if r["label"] == baseline), None)
    print(f"\n  {'Format':<25} {'Karakter':>10} {'Byte':>8} {'Satır':>7} {'Token (≈)':>10} {'Tasarruf':>10}")
    print(f"  {'-'*25} {'-'*10} {'-'*8} {'-'*7} {'-'*10} {'-'*10}")

    for r in results:
        if r.get("tokens_est") is None:
            print(f"  {r['label']:<25} {'— HATA —':>10}")
            continue
        savings = ""
        if base and r["label"] != baseline and base["tokens_est"]:
            diff = base["tokens_est"] - r["tokens_est"]
            pct = diff / base["tokens_est"] * 100
            savings = f"{pct:+.1f}%"
        print(f"  {r['label']:<25} {r['chars']:>10,} {r['bytes']:>8,} {r['lines']:>7,} {r['tokens_est']:>10,} {savings:>10}")

def save_results(all_results: list):
    output_file = "nested_vs_flat_results.csv"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fieldnames = ["timestamp", "data_type", "label", "chars", "bytes", "lines", "tokens_est", "error"]

    file_exists = os.path.isfile(output_file)
    with open(output_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for r in all_results:
            writer.writerow({
                "timestamp": timestamp, "data_type": r.get("data_type", ""), "label": r.get("label", ""),
                "chars": r.get("chars", ""), "bytes": r.get("bytes", ""), "lines": r.get("lines", ""),
                "tokens_est": r.get("tokens_est", ""), "error": r.get("error", ""),
            })
    print(f"\n[OK] Sonuçlar kaydedildi: {output_file}")

def main():
    print("\n" + "#" * 60)
    print("  NESTED vs FLAT — FORMAT KARŞILAŞTIRMA TESTİ")
    print("  (Ollama gerekmez — boyut ve token tahmini analizi)")
    print("#" * 60)

    all_results = []
    flat_results = test_flat()
    nested_results = test_nested()
    test_flat_vs_nested_json()

    all_results.extend(flat_results)
    all_results.extend(nested_results)
    save_results(all_results)

    print("\n" + "=" * 60)
    print("  GENEL SONUÇ")
    print("=" * 60)
    print("  ✅ Flat veride  : TOON, JSON'dan daha az token harcıyor.")
    print("  ❌ Nested veride: TOON dönüşümü başarısız — JSON ve XML destekliyor.")

if __name__ == "__main__":
    main()