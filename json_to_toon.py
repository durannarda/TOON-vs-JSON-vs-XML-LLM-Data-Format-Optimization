import json
import argparse
from typing import Dict, List

# Kaçış karakteri olarak kullanılacak delimiter ve quote karakteri
DELIMITER = ","
QUOTE_CHAR = '"'


def escape_value(val: str) -> str:
    """
    Değer içinde virgül, tırnak veya newline varsa tırnak içine al.
    İçindeki tırnakları çiftleyerek escape et (CSV standardı).
    """
    if DELIMITER in val or QUOTE_CHAR in val or "\n" in val:
        escaped = val.replace(QUOTE_CHAR, QUOTE_CHAR + QUOTE_CHAR)
        return f'{QUOTE_CHAR}{escaped}{QUOTE_CHAR}'
    return val


def json_array_to_toon(name: str, records: List[Dict]) -> str:
    """Convert a JSON array of objects to TOON format."""
    if not records:
        return ""

    # Tüm kayıtların alan birleşimini al (ilk kayıt eksik alan içerebilir)
    all_keys: list = []
    seen: set = set()
    for record in records:
        for k in record.keys():
            if k not in seen:
                all_keys.append(k)
                seen.add(k)

    fields = all_keys
    lines = []

    # Header: name[count]{field1,field2,...}:
    header = f"{name}[{len(records)}]{{{','.join(fields)}}}:"
    lines.append(header)

    # Data rows
    for record in records:
        row_values = []
        for f in fields:
            val = record.get(f, "")
            # Nested veri kontrolü
            if isinstance(val, (dict, list)):
                raise ValueError(
                    f"Nested data found in field '{f}'. "
                    "TOON only supports flat tabular data."
                )
            # None -> 'null' olarak yaz (boş stringden ayırt etmek için)
            if val is None:
                val = "null"
            # bool -> küçük harf string (true/false), int/float -> str
            elif isinstance(val, bool):
                val = str(val).lower()
            else:
                val = str(val)

            row_values.append(escape_value(val))

        lines.append(DELIMITER.join(row_values))

    return "\n".join(lines)


def json_to_toon(json_data: Dict) -> str:
    """Convert JSON object to TOON format."""
    output = []
    for key, value in json_data.items():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            output.append(json_array_to_toon(key, value))
            output.append("")  # Bölümler arası boş satır
        else:
            raise ValueError(f"Unsupported JSON structure at key: '{key}'. "
                             "Expected a non-empty list of objects.")
    return "\n".join(output).strip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JSON -> TOON converter")
    parser.add_argument("--input",  default="input.json",  help="Girdi JSON dosyası")
    parser.add_argument("--output", default="output.toon", help="Çıktı TOON dosyası")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    toon = json_to_toon(data)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(toon)

    print(f"[OK] JSON -> TOON dönüşümü tamamlandı: {args.output}")
    print(f"     Dönüştürülen bölüm sayısı: {len(data)}")
