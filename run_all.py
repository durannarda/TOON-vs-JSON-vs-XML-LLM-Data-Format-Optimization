import argparse
import subprocess
import sys
import os

def run_step(step_num: int, description: str, command: list) -> bool:
    print(f"\n{'='*60}\n  ADIM {step_num}: {description}\n{'='*60}")
    result = subprocess.run(command, text=True)
    if result.returncode == 0:
        print(f"\n  [✓] Adım {step_num} tamamlandı.")
        return True
    else:
        print(f"\n  [✗] Adım {step_num} başarısız oldu! (Hata kodu: {result.returncode})")
        return False

def main():
    parser = argparse.ArgumentParser(description="Tüm proje adımlarını sırayla çalıştır")
    parser.add_argument("--runs",  default=1, type=int, help="Benchmark tekrar sayısı (varsayılan: 1)")
    parser.add_argument("--model", default="gemma3:1b",  help="Ollama model adı")
    parser.add_argument("--question-type", default="all", help="Soru tipi (schema, lookup, aggregate, all)")
    parser.add_argument("--records", default=None, type=int, help="Maksimum kayıt sayısı")
    parser.add_argument("--context-limit", default=None, type=int, help="Manuel context penceresi limiti")
    args = parser.parse_args()

    python = sys.executable

    print("\n" + "#"*60)
    print("  PROJE BAŞLIYOR")
    print(f"  Model   : {args.model}")
    print(f"  Tekrar  : {args.runs}")
    print(f"  Kayıt   : {args.records if args.records else 'tümü'}")
    print(f"  Soru Tipi: {args.question_type}")
    print("#"*60)

    steps = [
        (1, "JSON → TOON dönüşümü", [python, "json_to_toon.py", "--input", "input.json", "--output", "output.toon"]),
        (2, "Flat vs Nested token analizi (Ollama gerekmez)", [python, "nested_vs_flat_test.py"]),
        (3, f"LLM Benchmark testi ({args.runs} tekrar, model: {args.model})",
            [python, "benchmark.py",
             "--runs", str(args.runs),
             "--model", args.model,
             "--question-type", args.question_type,
             "--data", "flat",
             *(["--records", str(args.records)] if args.records else []),
             *(["--context-limit", str(args.context_limit)] if args.context_limit else []),
            ]
        ),
        (4, "Özet rapor oluşturma → report.md", [python, "generate_report.py", "--output", "report.md"]),
    ]

    results = []
    for step_num, description, command in steps:
        success = run_step(step_num, description, command)
        results.append((step_num, description, success))
        if not success and step_num == 3:
            print("\n  [!] Benchmark başarısız. Ollama çalışıyor mu?")
            print("      Raporlama adımı yine de çalıştırılıyor...\n")
        elif not success and step_num == 1:
            print("\n  [!] Dönüşüm başarısız, devam edilemiyor.")
            break

    print("\n" + "="*60 + "\n  ÖZET\n" + "="*60)
    for step_num, description, success in results:
        icon = "✓" if success else "✗"
        print(f"  [{icon}] Adım {step_num}: {description}")

    if all(s for _, _, s in results):
        print("\n  Tüm adımlar başarıyla tamamlandı!\n  → report.md dosyasını aç ve sonuçları incele.")
    else:
        print("\n  Bazı adımlar başarısız oldu. Hata mesajlarını kontrol et.")

if __name__ == "__main__":
    main()