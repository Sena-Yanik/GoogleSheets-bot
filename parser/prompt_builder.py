# parser/prompt_builder.py
import json
from core.config import FIELD_TYPE_MAP, CATEGORICAL_FIELDS

# Few-shot örnekler - LLM'e format göstermek için
FEW_SHOT_EXAMPLES = """
Sorgu: "50 binden fazla borcu olan müşteriler"
JSON: {"intent":"list","filters":[{"field":"toplam_borc","operator":">","value":"50000"}],"fields":["musteri_adi","toplam_borc","odenen_tutar"],"aggregation":null,"report_type":null,"sort":null,"limit":100,"offset":0,"clarification_question":null}

Sorgu: "borcu 10000 ile 50000 arasında olanlar"
JSON: {"intent":"list","filters":[{"field":"toplam_borc","operator":">=","value":"10000"},{"field":"toplam_borc","operator":"<=","value":"50000"}],"fields":["musteri_adi","toplam_borc"],"aggregation":null,"report_type":null,"sort":null,"limit":100,"offset":0,"clarification_question":null}

Sorgu: "dava olan müşteri sayısı"
JSON: {"intent":"count","filters":[{"field":"dava_var_mi","operator":"=","value":true}],"fields":[],"aggregation":null,"report_type":null,"sort":null,"limit":100,"offset":0,"clarification_question":null}

Sorgu: "konut kategorisindeki toplam borç"
JSON: {"intent":"sum","filters":[{"field":"kategori","operator":"=","value":"konut"}],"aggregation":{"type":"sum","field":"toplam_borc"},"fields":[],"report_type":null,"sort":null,"limit":100,"offset":0,"clarification_question":null}

Sorgu: "ortalama ödeme oranı"
JSON: {"intent":"average","filters":[],"aggregation":{"type":"avg","field":"odeme_orani"},"fields":[],"report_type":null,"sort":null,"limit":100,"offset":0,"clarification_question":null}

Sorgu: "genel rapor"
JSON: {"intent":"report","filters":[],"aggregation":null,"fields":[],"report_type":"general","sort":null,"limit":100,"offset":0,"clarification_question":null}

Sorgu: "ahmet"
JSON: {"intent":"clarification_needed","filters":[],"aggregation":null,"fields":[],"report_type":null,"sort":null,"limit":100,"offset":0,"clarification_question":"Ahmet hakkında ne öğrenmek istiyorsunuz? Borç durumu, ödeme oranı veya başka bir bilgi mi?"}
"""


def build_system_prompt() -> str:
    """Sistem promptu oluştur - sadece alan adları ve tipleri dahil edilir."""
    field_lines = "\n".join([
        f"- {name} ({'kategorik' if name in CATEGORICAL_FIELDS else (ftype.__name__ if hasattr(ftype, '__name__') else str(ftype))})"
        for name, ftype in FIELD_TYPE_MAP.items()
    ])

    return f"""Sen bir sorgu ayrıştırıcısısın. Görevin kullanıcının Türkçe sorgusunu JSON formatına çevirmektir.

YASAK:
- Hesaplama yapma
- Veri uydurma
- Yorum ekleme
- JSON dışında herhangi bir metin yazma

GEÇERLİ ALANLAR:
{field_lines}

KATEGORİK ALANLAR HAKKINDA:
kategori ve musteri_turu alanları kategoriktir.
Kullanıcının yazdığı değeri olduğu gibi value'ya koy.
Eşleştirme Python tarafında yapılacaktır.

GEÇERLİ OPERATÖRLER: = != < > <= >= contains

GEÇERLİ INTENTLER:
- list: Kayıt listeleme
- count: Kayıt sayısı
- sum: Toplam hesaplama
- average: Ortalama hesaplama
- ratio: Ödeme oranı hesaplama
- report: Rapor üretimi
- clarification_needed: Sorgu yetersiz veya belirsiz

ÇIKTI FORMATI - Sadece bu JSON, başka hiçbir şey:
{{
  "intent": "...",
  "filters": [
    {{"field": "...", "operator": "...", "value": "..."}}
  ],
  "aggregation": {{
    "type": "sum | avg | count | ratio",
    "field": "..."
  }},
  "fields": ["..."],
  "report_type": "general | performance | risk | category | null",
  "sort": {{"field": "...", "order": "asc | desc"}},
  "limit": 100,
  "offset": 0,
  "clarification_question": null
}}

ÖRNEKLER:
{FEW_SHOT_EXAMPLES}
"""


def build_refinement_messages(
    original_query: str,
    clarification_question: str,
    user_answer: str,
) -> list[dict]:
    """
    Clarification refinement: conversation history ile.
    String birleştirme yerine conversation history gönderilir.
    LLM bağlamı conversation'dan anlar.
    """
    return [
        {
            "role": "user",
            "content": original_query,
        },
        {
            "role": "assistant",
            "content": json.dumps({
                "intent": "clarification_needed",
                "clarification_question": clarification_question,
            }),
        },
        {
            "role": "user",
            "content": user_answer,
        },
    ]
