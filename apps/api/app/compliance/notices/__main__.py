"""`python -m app.compliance.notices lock`: releases new notice files (adds their lock lines).
`python -m app.compliance.notices check`: loads every notice and checks it against the lock."""

import sys

from app.compliance.notices import NoticeError, load_notices, lock_new_files


def main(argv: list[str]) -> int:
    command = argv[0] if argv else "check"
    try:
        if command == "lock":
            added = lock_new_files()
            print("Released: " + ", ".join(added) if added else "Nothing new to release.")
            load_notices()
        elif command == "check":
            notices = load_notices()
            print(f"{len(notices.notices)} notices match the lock.")
        else:
            print(__doc__)
            return 2
    except NoticeError as error:
        print(f"Notice error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
