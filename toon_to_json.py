import json
import re
import csv
import argparse
from typing import Dict, List

# Regex DFA modelimiz — TOON section header'ını yakalar
SECTION_HEADER = re.compile(
    r"(?P<name>\w+)\[(?P<count>\d+)\]\{(?P<fields>[\w,]+)\}:"
)


def parse_row(line: str) -> List[str]:
    """
    Virgüllü ve tırnaklı değerleri doğru şekilde ayrıştırır.
    csv.reader kullanarak CSV standardına uygun parse yapar.
    """
    reader = csv.reader([line])
    return next(reader)


def cast_types(values: List[str]) -> List:
    """
    String değerleri uygun Python tiplerine dönüştürür.
    Desteklenen: int, float, bool (true/false), null/none -> None, string
    """
    casted = []
    for v in values:
        v_stripped = v.strip()

        # None / null — açıkça 'null' yazılmış olanlar
        if v_stripped.lower() in ("null", "none"):
            casted.append(None)
        # Boş string — olduğu gibi koru
        elif v_stripped == "":
            casted.append("")
        # Boolean
        elif v_stripped.lower() == "true":
            casted.append(True)
        elif v_stripped.lower() == "false":
            casted.append(False)
        # Integer (negatif dahil)
        elif re.fullmatch(r"-?\d+", v_stripped):
            casted.append(int(v_stripped))
        # Float (negatif dahil)
        elif re.fullmatch(r"-?\d+\.\d+", v_stripped):
            casted.append(float(v_stripped))
        # String
        else:
            casted.append(v_stripped)

    return casted


def toon_to_json(toon_text: str) -> Dict:
    result = {}
    lines = [line.rstrip() for line in toon_text.splitlines() if line.strip()]
    i = 0

    while i < len(lines):
        match = SECTION_HEADER.match(lines[i])
        if not match:
            raise ValueError(f"Geçersiz TOON header satırı: '{lines[i]}'")

        name   = match.group("name")
        count  = int(match.group("count"))
        fields = match.group("fields").split(",")
        records = []

        # Satır sayısı yeterliliğini kontrol et
        available = len(lines) - i - 1
        if available < count:
            raise ValueError(
                f"'{name}' bölümü için {count} satır bekleniyor "
                f"ama yalnızca {available} satır mevcut."
            )

        for j in range(1, count + 1):
            raw_values = parse_row(lines[i + j])
            typed_values = cast_types(raw_values)

            # Alan sayısı uyuşmazsa uyar ama devam et
            if len(typed_values) != len(fields):
                print(
                    f"[UYARI] Satır {i + j}: "
                    f"Beklenen {len(fields)} değer, bulunan {len(typed_values)}. "
                    "Eksik alanlar None ile dolduruldu."
                )
                # Kısa listeyi None ile genişlet, uzun listeyi kes
                typed_values = (typed_values + [None] * len(fields))[:len(fields)]

            record = dict(zip(fields, typed_values))
            records.append(record)

        result[name] = records
        i += count + 1

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TOON -> JSON converter")
    parser.add_argument("--input",  default="output.toon",        help="Girdi TOON dosyası")
    parser.add_argument("--output", default="restored_output.json", help="Çıktı JSON dosyası")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        toon_text = f.read()

    json_data = toon_to_json(toon_text)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    print(f"[OK] TOON -> JSON dönüşümü tamamlandı: {args.output}")
