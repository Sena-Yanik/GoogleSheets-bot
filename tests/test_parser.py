# tests/test_parser.py
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.llm_parser import LLMParser, LLMParseError
from parser.prompt_builder import (
    build_system_prompt,
    build_refinement_messages,
    FEW_SHOT_EXAMPLES,
)


def test_system_prompt_contains_fields():
    prompt = build_system_prompt()
    assert "musteri_adi" in prompt
    assert "toplam_borc" in prompt
    assert "odenen_tutar" in prompt
    assert "kategori" in prompt
    assert "dava_var_mi" in prompt


def test_system_prompt_contains_intents():
    prompt = build_system_prompt()
    assert "list" in prompt
    assert "count" in prompt
    assert "sum" in prompt
    assert "average" in prompt
    assert "ratio" in prompt
    assert "report" in prompt
    assert "clarification_needed" in prompt


def test_system_prompt_contains_operators():
    prompt = build_system_prompt()
    assert "contains" in prompt


def test_system_prompt_no_enum_values():
    prompt = build_system_prompt()
    # Prompt'ta kategorik alan adları var ama değerleri yok
    assert "kategorik" in prompt


def test_few_shot_examples_valid_json():
    import json
    for line in FEW_SHOT_EXAMPLES.strip().split("\n"):
        if line.startswith("JSON:"):
            json_str = line[5:].strip()
            parsed = json.loads(json_str)
            assert "intent" in parsed


def test_refinement_messages_structure():
    messages = build_refinement_messages(
        original_query="ahmet",
        clarification_question="Borç mu ödeme mi?",
        user_answer="borç durumu",
    )
    assert len(messages) == 3
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "ahmet"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"] == "borç durumu"


def test_refinement_messages_assistant_is_json():
    import json
    messages = build_refinement_messages(
        original_query="test",
        clarification_question="Soru?",
        user_answer="cevap",
    )
    parsed = json.loads(messages[1]["content"])
    assert parsed["intent"] == "clarification_needed"
    assert parsed["clarification_question"] == "Soru?"


@pytest.mark.asyncio
async def test_retry_on_parse_error(mocker):
    mocker.patch.object(
        LLMParser,
        "_call_with_retry",
        side_effect=LLMParseError("test error"),
    )
    parser = LLMParser.__new__(LLMParser)
    with pytest.raises(LLMParseError):
        await parser.parse("test query", "system prompt")
