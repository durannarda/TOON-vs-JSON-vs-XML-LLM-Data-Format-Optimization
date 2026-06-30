"""
xml_to_toon.py
XML -> TOON ve XML -> JSON dönüştürücü.

Desteklenen XML yapısı:
    <root>
        <section_name>
            <item><field1>val</field1><field2>val</field2></item>
            <item>...</item>
        </section_name>
        <another_section>
            ...
        </another_section>
    </root>

Kullanım:
    python xml_to_toon.py                          # input.xml -> output_from_xml.toon
    python xml_to_toon.py --input data.xml --output result.toon
    python xml_to_toon.py --input data.xml --format json --output result.json
"""

import argparse
import json
from xml.etree import ElementTree as ET

from json_to_toon import json_to_toon


# ---------------------------------------------------------------------------
# XML -> Python Dict
# ---------------------------------------------------------------------------

def xml_to_dict(root: ET.Element) -> dict:
    """
    XML ağacını JSON/TOON dönüştürücülerinin beklediği sözlük yapısına çevirir.

    Beklenen yapı:
        <root>
            <section>          <- bölüm adı (ör: countries, users)
                <item>         <- tekrar eden kayıt etiketi (ör: country, user)
                    <field>value</field>
                </item>
            </section>
        </root>

    Dönüş:
        { "section_name": [ {"field1": val, "field2": val}, ... ] }
    """
    result = {}

    for section in root:
        section_name = section.tag
        items = list(section)

        if not items:
            continue  # Boş bölümü atla

        records = []
        for item in items:
            record = {}
            for field in item:
                text = (field.text or "").strip()
                record[field.tag] = _cast(text)
            records.append(record)

        result[section_name] = records

    return result


def _cast(value: str):
    """String XML değerini uygun Python tipine dönüştür."""
    if value.lower() in ("null", "none", ""):
        return None
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    # Integer
    try:
        return int(value)
    except ValueError:
        pass
    # Float
    try:
        return float(value)
    except ValueError:
        pass
    return value


# ---------------------------------------------------------------------------
# Ana dönüşüm fonksiyonları
# ---------------------------------------------------------------------------

def xml_file_to_toon(xml_path: str) -> str:
    """XML dosyasını okuyup TOON string döndürür."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    data = xml_to_dict(root)
    return json_to_toon(data)


def xml_file_to_json(xml_path: str) -> dict:
    """XML dosyasını okuyup Python sözlüğü döndürür."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    return xml_to_dict(root)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="XML -> TOON / JSON dönüştürücü")
    parser.add_argument("--input",  default="input.xml",           help="Girdi XML dosyası")
    parser.add_argument("--output", default="output_from_xml.toon",help="Çıktı dosyası")
    parser.add_argument(
        "--format",
        choices=["toon", "json"],
        default="toon",
        help="Çıktı formatı: toon (varsayılan) veya json",
    )
    args = parser.parse_args()

    if args.format == "toon":
        output_text = xml_file_to_toon(args.input)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"[OK] XML -> TOON dönüşümü tamamlandı: {args.output}")

    else:  # json
        data = xml_file_to_json(args.input)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[OK] XML -> JSON dönüşümü tamamlandı: {args.output}")