"""
benchmark.py
Tüm formatları (JSON, TOON, XML) tek seferde test eden merkezi benchmark scripti.
Eklenen Özellik: Cevap Doğruluğu (Accuracy) Kontrolü.
"""

import argparse
import csv
import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime

try:
    import ollama
except ImportError:
    print("[HATA] 'ollama' paketi bulunamadı. Kurmak için: pip install ollama")
    raise

from json_to_toon import json_to_toon

DEFAULT_MODEL      = "gemma3:1b"
DEFAULT_RUNS       = 1
RESULTS_FILE       = "benchmark_results.csv"
OVERFLOW_THRESHOLD = 0.95

SYSTEM_PROMPT = (
    "You are a data analysis assistant. "
    "Answer the question using ONLY the provided data. "
    "Be concise and precise."
)

# Sorular ve beklenen cevapların içermesi gereken anahtar kelimeler (Küçük harfe duyarsız kontrol edilir)
QUESTIONS = {
    "schema": {
        "text": "How many records are in the users list and what are their field names?",
        # 100 kullanıcı var. Alan adları: id, name, role, status
        "keywords": ["100", "id", "name", "role", "status"] 
    },
    "lookup": {
        "text": "What is the capital of Country_42?",
        # JSON'da Country_42'nin başkenti tam olarak "Capital_42" olarak geçiyor.
        # Nokta atışı bir arama sorusu olduğu için hata payı sıfır.
        "keywords": ["Capital_42"] 
    },
    "aggregate": {
        "text": "How many users have the 'admin' role?",
        # Listede id'si 10'un katı olan tam 10 adet admin var.
        "keywords": ["10"] 
    }
}

def get_model_context_limit(model: str) -> int:
    try:
        info = ollama.show(model)
        model_info = info.get("modelinfo", {})
        for key, value in model_info.items():
            if "context_length" in key.lower() or ("ctx" in key.lower() and "length" in key.lower()):
                limit = int(value)
                print(f"[BİLGİ] Context limiti tespit edildi: {limit} token")
                return limit
        parameters = str(info.get("parameters", ""))
        for line in parameters.splitlines():
            if "num_ctx" in line.lower():
                parts = line.split()
                if parts:
                    limit = int(parts[-1])
                    print(f"[BİLGİ] Context limiti parametreden okundu: {limit} token")
                    return limit
    except Exception as e:
        print(f"[UYARI] Context limiti sorgulanamadı ({e}). Varsayılan 4096 kullanılıyor.")
    return 4096

def warmup_model(model: str):
    print(f"\n[BİLGİ] Model RAM'e yükleniyor (Warmup: {model})...")
    try:
        ollama.chat(model=model, messages=[{"role": "user", "content": "Hello"}])
        print("[BİLGİ] Warmup tamamlandı. Zaman ölçümleri artık güvenilir.")
    except Exception as e:
        print(f"[UYARI] Warmup başarısız oldu: {e}")

def dict_to_xml_minified(data: dict) -> str:
    root_el = ET.Element("root")
    for section_name, records in data.items():
        if not isinstance(records, list):
            continue
        section_el = ET.SubElement(root_el, section_name)
        for record in records:
            item_el = ET.SubElement(section_el, "item")
            for field, value in record.items():
                field_el = ET.SubElement(item_el, str(field))
                field_el.text = "" if value is None else str(value)
    return ET.tostring(root_el, encoding="unicode")

def prepare_data(data_type: str, max_records: int = None) -> dict:
    if data_type == "flat":
        with open("input.json", "r", encoding="utf-8") as f:
            raw = json.load(f)
    elif data_type == "nested":
        with open("nested_input.json", "r", encoding="utf-8") as f:
            raw = json.load(f)
    else:
        raise ValueError(f"Bilinmeyen veri tipi: '{data_type}'")

    if max_records is not None:
        raw = {k: (v[:max_records] if isinstance(v, list) else v) for k, v in raw.items()}
        actual = sum(len(v) for v in raw.values() if isinstance(v, list))
        print(f"[BİLGİ] Veri {actual} kayıtla sınırlandırıldı (--records {max_records}).")

    json_str = json.dumps(raw, separators=(",", ":"), ensure_ascii=False)
    xml_str  = dict_to_xml_minified(raw)

    if data_type == "nested":
        try:
            toon_str = json_to_toon(raw)
        except ValueError as e:
            toon_str = None
    else:
        toon_str = json_to_toon(raw)

    return {"json": json_str, "toon": toon_str, "xml": xml_str}

def run_single_test(format_name: str, data_str: str, question: str, expected_keywords: list, model: str, context_limit: int, verbose: bool = True) -> dict:
    prompt = f"You are given data in {format_name.upper()} format.\n{SYSTEM_PROMPT}\n\nDATA:\n{data_str}\n\nQUESTION:\n{question}"

    start = time.perf_counter()
    first_token_time = None
    last_chunk = None
    answer_parts = []

    for chunk in ollama.chat(model=model, messages=[{"role": "user", "content": prompt}], stream=True):
        last_chunk = chunk
        if first_token_time is None and "message" in chunk:
            first_token_time = time.perf_counter()
        if "message" in chunk:
            answer_parts.append(chunk["message"]["content"])

    end = time.perf_counter()

    ttft = round(first_token_time - start, 3) if first_token_time else None
    total_time = round(end - start, 3)
    prompt_tokens = last_chunk.get("prompt_eval_count") if last_chunk else None

    overflow = bool(prompt_tokens is not None and prompt_tokens >= context_limit * OVERFLOW_THRESHOLD)
    answer = "".join(answer_parts).strip()
    
    # Doğruluk Kontrolü: Tüm beklenen anahtar kelimeler cevapta geçiyor mu?
    answer_lower = answer.lower()
    is_correct = all(kw.lower() in answer_lower for kw in expected_keywords)

    if verbose:
        overflow_flag = "  ⚠ OVERFLOW" if overflow else ""
        correct_flag = "✅ Doğru" if is_correct else "❌ Yanlış"
        print(f"\n  Cevap : {answer[:120]}{'...' if len(answer) > 120 else ''}")
        print(f"  Durum : {correct_flag}")
        print(f"  TTFT  : {ttft}s  |  Toplam: {total_time}s  |  Token: {prompt_tokens}{overflow_flag}")

    return {
        "format": format_name,
        "prompt_tokens": prompt_tokens,
        "ttft_s": ttft,
        "total_time_s": total_time,
        "data_chars": len(data_str),
        "data_bytes": len(data_str.encode("utf-8")),
        "overflow": overflow,
        "is_correct": is_correct,
        "answer": answer,
    }

def run_format_benchmark(format_name: str, data_str: str, q_data: dict, model: str, runs: int, context_limit: int) -> dict:
    if data_str is None:
        return None

    print(f"\n{'─'*55}\n  FORMAT: {format_name.upper()}  |  {runs} tekrar\n{'─'*55}")

    results = []
    for i in range(runs):
        print(f"\n  Tekrar {i + 1}/{runs}...")
        result = run_single_test(format_name, data_str, q_data["text"], q_data["keywords"], model, context_limit)
        results.append(result)

    def avg(key):
        vals = [r[key] for r in results if r[key] is not None]
        return round(sum(vals) / len(vals), 3) if vals else None

    any_overflow = any(r["overflow"] for r in results)
    accuracy_pct = (sum(1 for r in results if r["is_correct"]) / runs) * 100

    return {
        "format": format_name,
        "runs": runs,
        "accuracy_pct": accuracy_pct,
        "avg_prompt_tokens": avg("prompt_tokens"),
        "avg_ttft_s": avg("ttft_s"),
        "avg_total_time_s": avg("total_time_s"),
        "data_chars": results[0]["data_chars"],
        "data_bytes": results[0]["data_bytes"],
        "overflow": any_overflow,
        "last_answer": results[-1]["answer"],
    }

def print_summary(results: list, baseline_format: str = "json"):
    baseline = next((r for r in results if r and r["format"] == baseline_format), None)
    
    print(f"\n{'='*82}\n  BENCHMARK SONUÇLARI — KARŞILAŞTIRMALI ÖZET\n{'='*82}")
    header = f"  {'Format':<8} {'Doğruluk':>9} {'Token':>8} {'TTFT(s)':>9} {'Süre(s)':>9} {'Byte':>8} {'Tasarruf':>10} {'Durum':>8}"
    print(header)
    print(f"  {'-'*8} {'-'*9} {'-'*8} {'-'*9} {'-'*9} {'-'*8} {'-'*10} {'-'*8}")

    for r in results:
        if r is None:
            continue
        token_savings = ""
        if baseline and r["avg_prompt_tokens"] and baseline["avg_prompt_tokens"] and r["format"] != baseline_format:
            diff = baseline["avg_prompt_tokens"] - r["avg_prompt_tokens"]
            pct  = diff / baseline["avg_prompt_tokens"] * 100
            token_savings = f"{pct:+.1f}%"

        status = "⚠ OVF" if r.get("overflow") else "✓ OK"
        accuracy_str = f"%{r['accuracy_pct']:.0f}"
        
        print(f"  {r['format']:<8} {accuracy_str:>9} {str(r['avg_prompt_tokens']):>8} {str(r['avg_ttft_s']):>9} {str(r['avg_total_time_s']):>9} {str(r['data_bytes']):>8} {token_savings:>10} {status:>8}")

    if any(r and r.get("overflow") for r in results):
        print(f"\n  ⚠ KRİTİK UYARI: Context overflow tespit edildi. Rakamlar ve doğruluk güvenilmez olabilir.")

def save_to_csv(results: list, data_type: str, model: str, question: str, max_records):
    file_exists = os.path.isfile(RESULTS_FILE)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fieldnames = ["timestamp", "model", "data_type", "max_records", "question", "format", "runs", "accuracy_pct", "avg_prompt_tokens", "avg_ttft_s", "avg_total_time_s", "data_chars", "data_bytes", "overflow", "last_answer"]

    with open(RESULTS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for r in results:
            if r is None:
                continue
            writer.writerow({
                "timestamp": timestamp, "model": model, "data_type": data_type, "max_records": max_records if max_records is not None else "all",
                "question": question, "format": r["format"], "runs": r["runs"], "accuracy_pct": r["accuracy_pct"], "avg_prompt_tokens": r["avg_prompt_tokens"],
                "avg_ttft_s": r["avg_ttft_s"], "avg_total_time_s": r["avg_total_time_s"], "data_chars": r["data_chars"],
                "data_bytes": r["data_bytes"], "overflow": r.get("overflow", False), "last_answer": r["last_answer"],
            })
    print(f"\n[OK] Sonuçlar kaydedildi: {RESULTS_FILE}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model adı")
    parser.add_argument("--runs", default=DEFAULT_RUNS, type=int, help="Her format için tekrar sayısı")
    parser.add_argument("--question-type", default="all", choices=["schema", "lookup", "aggregate", "all"], help="Sorulacak soru tipi")
    parser.add_argument("--data", default="flat", choices=["flat", "nested"], help="Veri seti")
    parser.add_argument("--records", default=None, type=int, help="Maksimum kayıt sayısı")
    parser.add_argument("--context-limit", default=None, type=int, help="Manuel context limiti")
    args = parser.parse_args()

    questions_to_run = QUESTIONS if args.question_type == "all" else {args.question_type: QUESTIONS[args.question_type]}

    print(f"\n{'#'*65}\n  BENCHMARK BAŞLIYOR\n  Model    : {args.model}\n  Veri     : {args.data}\n  Tekrar   : {args.runs}\n  Kayıt    : {args.records if args.records else 'tümü'}\n{'#'*65}")

    context_limit = args.context_limit if args.context_limit else get_model_context_limit(args.model)
    data = prepare_data(args.data, max_records=args.records)

    warmup_model(args.model)

    for q_name, q_data in questions_to_run.items():
        print(f"\n>>> SORU TİPİ: {q_name.upper()}\n>>> Soru: {q_data['text']}")
        results = []
        for fmt in ["json", "toon", "xml"]:
            result = run_format_benchmark(fmt, data[fmt], q_data, args.model, args.runs, context_limit)
            results.append(result)

        print_summary(results, baseline_format="json")
        save_to_csv(results, args.data, args.model, q_data["text"], args.records)

if __name__ == "__main__":
    main()