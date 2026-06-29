from uni_intel.ingestion.parsers.qilt import parse_qilt_value


def test_parse_qilt_value_with_confidence_interval() -> None:
    assert parse_qilt_value("80.5 (79.7, 81.3)") == (80.5, 79.7, 81.3)


def test_parse_qilt_value_suppressed() -> None:
    assert parse_qilt_value("n/a") is None
