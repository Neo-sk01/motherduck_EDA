import math

import pandas as pd

from pipeline.parse import normalize_caller_number, parse_csv_call_time, to_seconds


def test_to_seconds_parses_mm_ss_and_hh_mm_ss():
    assert to_seconds("00:09") == 9
    assert to_seconds("04:58") == 298
    assert to_seconds("1:02:03") == 3723


def test_to_seconds_treats_ms_artifact_and_bad_values_as_missing():
    assert math.isnan(to_seconds("53ms"))
    assert math.isnan(to_seconds(""))
    assert math.isnan(to_seconds(None))
    assert math.isnan(to_seconds("bad"))


def test_parse_csv_call_time_uses_sonar_format():
    parsed = parse_csv_call_time(pd.Series(["04/01/2026 8:33 am", "04/30/2026 3:40 pm"]))
    assert str(parsed.iloc[0]) == "2026-04-01 08:33:00"
    assert str(parsed.iloc[1]) == "2026-04-30 15:40:00"


def test_normalize_caller_number_does_not_aggregate_restricted():
    assert normalize_caller_number("905-283-3500") == "9052833500"
    assert normalize_caller_number("+1 (905) 283-3500") == "19052833500"
    assert normalize_caller_number("Restricted").startswith("__restricted__:")
    assert normalize_caller_number(None).startswith("__restricted__:")
    assert normalize_caller_number("Restricted") != normalize_caller_number("Restricted")
    assert normalize_caller_number(None) != normalize_caller_number(None)
    assert normalize_caller_number("Private", row_key="call-a") == "__restricted__:call-a"
    assert normalize_caller_number("Private", row_key="call-b") == "__restricted__:call-b"
