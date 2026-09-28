from app.core.ids import new_id


def test_new_id_is_uuid_v7_and_time_ordered() -> None:
    ids = [new_id() for _ in range(50)]

    assert all(value.version == 7 for value in ids)
    # The first 48 bits are milliseconds, so later IDs never sort before earlier ones.
    prefixes = [value.int >> 80 for value in ids]
    assert prefixes == sorted(prefixes)
