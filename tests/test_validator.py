# tests/test_validator.py
import os
import sys
from decimal import Decimal
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validation.query_validator import QueryValidator, ValidationError


def test_valid_list_query():
    validator = QueryValidator()
    result = validator.validate({
        "intent": "list",
        "filters": [
            {"field": "toplam_borc", "operator": ">", "value": "5000"}
        ],
        "limit": 100,
        "offset": 0,
    })
    assert result.intent == "list"
    assert len(result.filters) == 1


def test_valid_count_query():
    validator = QueryValidator()
    result = validator.validate({
        "intent": "count",
        "filters": [
            {"field": "dava_var_mi", "operator": "=", "value": True}
        ],
        "limit": 100,
        "offset": 0,
    })
    assert result.intent == "count"


def test_valid_report_query():
    validator = QueryValidator()
    result = validator.validate({
        "intent": "report",
        "filters": [],
        "report_type": "general",
        "limit": 100,
        "offset": 0,
    })
    assert result.intent == "report"
    assert result.report_type == "general"


def test_unknown_field_rejected():
    validator = QueryValidator()
    with pytest.raises(ValidationError) as exc:
        validator.validate({
            "intent": "list",
            "filters": [
                {"field": "bilinmeyen", "operator": "=", "value": "x"}
            ],
            "limit": 100,
            "offset": 0,
        })
    assert exc.value.error_code == "invalid_field"


def test_invalid_intent_rejected():
    validator = QueryValidator()
    with pytest.raises(ValidationError) as exc:
        validator.validate({
            "intent": "delete",
            "filters": [],
            "limit": 100,
            "offset": 0,
        })
    assert exc.value.error_code == "invalid_intent"


def test_invalid_operator_rejected():
    validator = QueryValidator()
    with pytest.raises(ValidationError) as exc:
        validator.validate({
            "intent": "list",
            "filters": [
                {"field": "toplam_borc", "operator": "LIKE", "value": "5000"}
            ],
            "limit": 100,
            "offset": 0,
        })
    assert exc.value.error_code == "invalid_operator"


def test_type_mismatch_rejected():
    validator = QueryValidator()
    with pytest.raises(ValidationError) as exc:
        validator.validate({
            "intent": "list",
            "filters": [
                {"field": "toplam_borc", "operator": ">", "value": "abc"}
            ],
            "limit": 100,
            "offset": 0,
        })
    assert exc.value.error_code == "type_mismatch"


def test_bool_type_mismatch_rejected():
    validator = QueryValidator()
    with pytest.raises(ValidationError) as exc:
        validator.validate({
            "intent": "list",
            "filters": [
                {"field": "dava_var_mi", "operator": "=", "value": "evet"}
            ],
            "limit": 100,
            "offset": 0,
        })
    assert exc.value.error_code == "type_mismatch"


def test_conflicting_filters_rejected():
    validator = QueryValidator()
    with pytest.raises(ValidationError) as exc:
        validator.validate({
            "intent": "list",
            "filters": [
                {"field": "toplam_borc", "operator": ">", "value": "9000"},
                {"field": "toplam_borc", "operator": "<", "value": "1000"},
            ],
            "limit": 100,
            "offset": 0,
        })
    assert exc.value.error_code == "conflicting_filters"


def test_valid_range_filters_accepted():
    validator = QueryValidator()
    result = validator.validate({
        "intent": "list",
        "filters": [
            {"field": "toplam_borc", "operator": ">=", "value": "1000"},
            {"field": "toplam_borc", "operator": "<=", "value": "9000"},
        ],
        "limit": 100,
        "offset": 0,
    })
    assert len(result.filters) == 2


def test_missing_report_type_rejected():
    validator = QueryValidator()
    with pytest.raises(ValidationError) as exc:
        validator.validate({
            "intent": "report",
            "filters": [],
            "report_type": None,
            "limit": 100,
            "offset": 0,
        })
    assert exc.value.error_code == "missing_report_type"


def test_invalid_report_type_rejected():
    validator = QueryValidator()
    with pytest.raises(ValidationError) as exc:
        validator.validate({
            "intent": "report",
            "filters": [],
            "report_type": "bilinmeyen",
            "limit": 100,
            "offset": 0,
        })
    assert exc.value.error_code == "missing_report_type"


def test_invalid_aggregation_field_rejected():
    validator = QueryValidator()
    with pytest.raises(ValidationError) as exc:
        validator.validate({
            "intent": "sum",
            "filters": [],
            "aggregation": {"type": "sum", "field": "bilinmeyen_alan"},
            "limit": 100,
            "offset": 0,
        })
    assert exc.value.error_code == "invalid_field"


def test_valid_aggregation_accepted():
    validator = QueryValidator()
    result = validator.validate({
        "intent": "sum",
        "filters": [],
        "aggregation": {"type": "sum", "field": "toplam_borc"},
        "limit": 100,
        "offset": 0,
    })
    assert result.aggregation.field == "toplam_borc"


def test_clarification_needed_accepted():
    validator = QueryValidator()
    result = validator.validate({
        "intent": "clarification_needed",
        "filters": [],
        "clarification_question": "Ne öğrenmek istiyorsunuz?",
        "limit": 100,
        "offset": 0,
    })
    assert result.intent == "clarification_needed"


def test_multiple_filters_on_different_fields():
    validator = QueryValidator()
    result = validator.validate({
        "intent": "list",
        "filters": [
            {"field": "toplam_borc", "operator": ">", "value": "5000"},
            {"field": "kategori", "operator": "=", "value": "konut"},
            {"field": "dava_var_mi", "operator": "=", "value": False},
        ],
        "limit": 100,
        "offset": 0,
    })
    assert len(result.filters) == 3
