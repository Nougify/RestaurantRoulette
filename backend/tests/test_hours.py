from datetime import UTC, datetime

import pytest

from roulette.hours import LOCAL_TIMEZONE, is_open, local_now

# 2026-10-02 is a Friday.
FRIDAY_EVENING = datetime(2026, 10, 2, 19, 30)
SATURDAY_1AM = datetime(2026, 10, 3, 1, 0)


@pytest.mark.parametrize(
    "opening_hours, at, expected",
    [
        ("Mo-Fr 11:00-22:00", FRIDAY_EVENING, True),
        ("Mo-Fr 11:00-22:00", SATURDAY_1AM, False),
        ("Mo-Th 11:00-22:00", FRIDAY_EVENING, False),
        ("24/7", SATURDAY_1AM, True),
        ("Fr 18:00-02:00", SATURDAY_1AM, True),
        ("Mo-Su 11:00-22:00; Fr off", FRIDAY_EVENING, False),
        ("Mo-Fr 11:00-14:00,17:00-22:00", FRIDAY_EVENING, True),
    ],
    ids=[
        "inside hours",
        "outside hours",
        "wrong day",
        "always open",
        "past midnight",
        "day off",
        "second sitting",
    ],
)
def test_is_open(opening_hours, at, expected):
    assert is_open(opening_hours, at) is expected


def test_missing_hours_count_as_closed():
    assert is_open(None, FRIDAY_EVENING) is False


@pytest.mark.parametrize("text", ["Mo-Fr05:30-20:00", "whenever we feel like it", ""])
def test_unreadable_hours_count_as_closed(text):
    assert is_open(text, FRIDAY_EVENING) is False


def test_aware_time_is_converted_to_vancouver_time():
    # 02:30 UTC on Saturday is 19:30 on Friday in Vancouver (UTC-7 in October).
    saturday_utc = datetime(2026, 10, 3, 2, 30, tzinfo=UTC)
    assert is_open("Fr 11:00-22:00", saturday_utc) is True
    assert is_open("Sa 00:00-06:00", saturday_utc) is False


def test_local_now_is_in_vancouver_time():
    assert local_now().tzinfo is LOCAL_TIMEZONE
