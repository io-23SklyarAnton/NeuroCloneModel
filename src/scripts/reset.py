__all__ = ["main"]

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse

from sqlalchemy import text
from sqlalchemy.orm import Session

from common.infrastructure.db.utils import get_db


def _reset_chat_export(
        session: Session,
        chat_id: int,
) -> None:
    session.execute(
        text("DELETE FROM training_datasets WHERE source_chat_export_id = :chat_id"),
        {"chat_id": chat_id},
    )
    session.execute(
        text("DELETE FROM parsed_messages WHERE chat_export_id = :chat_id"),
        {"chat_id": chat_id},
    )
    session.execute(
        text("DELETE FROM threads WHERE chat_export_id = :chat_id"),
        {"chat_id": chat_id},
    )
    session.execute(
        text("UPDATE chat_exports SET status='PENDING', n_messages=0 WHERE chat_id = :chat_id"),
        {"chat_id": chat_id},
    )
    session.commit()
    print(f"Reset chat_export {chat_id} → PENDING (cleared messages, threads, training_datasets)")


def _reset_neuroclone(
        session: Session,
        neuroclone_id: str,
) -> None:
    session.execute(
        text(
            "UPDATE neuroclones "
            "SET status='PREPARING', adapter_file_bucket=NULL, adapter_file_key=NULL "
            "WHERE id = :id"
        ),
        {"id": neuroclone_id},
    )
    session.commit()
    print(f"Reset neuroclone {neuroclone_id} → PREPARING (cleared adapter)")


def _reset_bot(
        session: Session,
        bot_id: str,
) -> None:
    session.execute(
        text(
            "UPDATE bots "
            "SET neuroclone_id=NULL, status='PENDING', reply_period=NULL "
            "WHERE id = :id"
        ),
        {"id": bot_id},
    )
    session.commit()
    print(f"Reset bot {bot_id} → PENDING (detached neuroclone, cleared reply_period)")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="reset",
        description="Reset an aggregate's state in DB so a pipeline step can be re-run.",
    )
    sub = parser.add_subparsers(dest="target", required=True)

    p_chat = sub.add_parser(
        "chat-export",
        help="Delete messages/threads/training_datasets and reset chat_export to PENDING.",
    )
    p_chat.add_argument("chat_id", type=int)

    p_neuroclone = sub.add_parser(
        "neuroclone",
        help="Clear adapter and reset neuroclone to PREPARING.",
    )
    p_neuroclone.add_argument("neuroclone_id", type=str)

    p_bot = sub.add_parser(
        "bot",
        help="Detach neuroclone and reset bot to PENDING.",
    )
    p_bot.add_argument("bot_id", type=str)

    args = parser.parse_args()

    session: Session = get_db()
    try:
        if args.target == "chat-export":
            _reset_chat_export(session, args.chat_id)
        elif args.target == "neuroclone":
            _reset_neuroclone(session, args.neuroclone_id)
        elif args.target == "bot":
            _reset_bot(session, args.bot_id)
        else:
            parser.error(f"Unknown target: {args.target}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
