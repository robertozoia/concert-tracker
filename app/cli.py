from __future__ import annotations

import argparse
import getpass
import logging
import sys


def _cmd_hash_password(_args: argparse.Namespace) -> int:
    from .auth import hash_password

    pw1 = getpass.getpass("Password: ")
    pw2 = getpass.getpass("Confirm: ")
    if pw1 != pw2:
        print("Passwords do not match", file=sys.stderr)
        return 1
    if not pw1:
        print("Empty password", file=sys.stderr)
        return 1
    print(hash_password(pw1))
    return 0


def _cmd_scrape(_args: argparse.Namespace) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    from .db import init_db
    from .scraper import scrape_all

    init_db()
    stats = scrape_all()
    print(stats.to_dict())
    return 0


def _cmd_init_db(_args: argparse.Namespace) -> int:
    from .db import init_db

    init_db()
    print("Database initialized.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="concert-tracker")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("hash-password", help="Generate bcrypt hash for APP_PASSWORD_HASH")
    sub.add_parser("scrape", help="Run the scraper once")
    sub.add_parser("init-db", help="Create database tables")

    args = parser.parse_args(argv)
    if args.cmd == "hash-password":
        return _cmd_hash_password(args)
    if args.cmd == "scrape":
        return _cmd_scrape(args)
    if args.cmd == "init-db":
        return _cmd_init_db(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
