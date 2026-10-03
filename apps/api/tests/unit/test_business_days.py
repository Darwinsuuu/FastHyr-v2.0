"""MSG-003: business-day delays and email times in the workspace's time zone; SCREEN-003:
interview links that stay open to the end of their last day there."""

from datetime import UTC, datetime

from app.core.business_days import add_business_days, end_of_day_after, format_local, zone_of
from app.services.candidate_emails import names

MANILA = zone_of("Asia/Manila")
NEW_YORK = zone_of("America/New_York")


def test_friday_screening_gets_a_tuesday_email() -> None:
    friday = datetime(2026, 10, 2, 10, 0, tzinfo=MANILA)  # Fri 10:00 in Manila

    sent = add_business_days(friday, 2, MANILA)

    assert sent.astimezone(MANILA) == datetime(2026, 10, 6, 10, 0, tzinfo=MANILA)  # Tue 10:00
    assert sent.tzinfo == UTC


def test_business_days_are_counted_in_the_workspace_time_zone() -> None:
    # Friday 20:00 UTC is already Saturday 04:00 in Manila, so two business days is Tuesday.
    friday_utc = datetime(2026, 10, 2, 20, 0, tzinfo=UTC)

    assert add_business_days(friday_utc, 2, MANILA).astimezone(MANILA).date().isoformat() == (
        "2026-10-06"
    )
    assert add_business_days(friday_utc, 2, zone_of("UTC")).date().isoformat() == "2026-10-06"
    # Wednesday + 3 is Monday.
    wednesday = datetime(2026, 10, 7, 9, 0, tzinfo=MANILA)
    assert add_business_days(wednesday, 3, MANILA).astimezone(MANILA).weekday() == 0


def test_weekend_starts_count_from_monday() -> None:
    saturday = datetime(2026, 10, 3, 15, 0, tzinfo=MANILA)
    sunday = datetime(2026, 10, 4, 15, 0, tzinfo=MANILA)

    assert add_business_days(saturday, 1, MANILA).astimezone(MANILA).day == 5  # Monday
    assert add_business_days(sunday, 2, MANILA).astimezone(MANILA).day == 6  # Tuesday


def test_a_daylight_saving_change_keeps_the_local_hour() -> None:
    # US clocks go back on Sunday 1 November 2026.
    friday = datetime(2026, 10, 30, 9, 0, tzinfo=NEW_YORK)

    sent = add_business_days(friday, 2, NEW_YORK)

    assert sent.astimezone(NEW_YORK).hour == 9
    assert sent == datetime(2026, 11, 3, 14, 0, tzinfo=UTC)  # EST is UTC-5


def test_unknown_time_zones_fall_back_to_utc() -> None:
    assert zone_of("Mars/Olympus_Mons").key == "UTC"
    assert zone_of(None).key == "UTC"


def test_email_times_read_in_the_workspace_time_zone() -> None:
    expiry = datetime(2026, 10, 3, 15, 59, tzinfo=UTC)

    assert format_local(expiry, MANILA) == "Sat, 3 Oct 2026, 11:59 PM PST"
    assert format_local(expiry, zone_of("Asia/Singapore")) == "Sat, 3 Oct 2026, 11:59 PM GMT+8"
    assert format_local(expiry, zone_of("Asia/Kolkata")) == "Sat, 3 Oct 2026, 9:29 PM IST"
    assert format_local(expiry, zone_of("Asia/Kathmandu")).endswith("GMT+5:45")


def test_candidate_names_split_into_first_and_last() -> None:
    assert names("Maria Clara Santos") == ("Maria", "Santos")
    assert names("  Paolo  ") == ("Paolo", "Paolo")
    assert names("") == ("", "")


def test_an_interview_link_stays_open_to_the_end_of_its_last_local_day() -> None:
    # Saturday 3 Oct 2026, 20:00 UTC is already Sunday 04:00 in Manila: 5 days is Friday.
    invited = datetime(2026, 10, 3, 20, 0, tzinfo=UTC)

    expires = end_of_day_after(invited, 5, MANILA)

    assert expires.astimezone(MANILA) == datetime(2026, 10, 9, 23, 59, 59, tzinfo=MANILA)
    assert expires.tzinfo == UTC
    assert format_local(expires, MANILA) == "Fri, 9 Oct 2026, 11:59 PM PST"
