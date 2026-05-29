__all__ = ["main"]

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import asyncio
import uuid

from common.domain.value_objects import ID
from infrastructure.celery import feature_dependencies as deps
from infrastructure.celery.scheduled_tasks import command_handlers


def _trigger_ingest(chat_id: int) -> str:
    return command_handlers.ingest_chat_export_task.apply_async(
        kwargs={"payload": {"chat_export_id": {"value": chat_id}}},
    )


def _trigger_process(chat_id: int) -> str:
    return command_handlers.process_chat_threads_task.apply_async(
        kwargs={"payload": {"chat_export_id": {"value": chat_id}}},
    )


def _trigger_build_dataset(chat_id: int) -> str:
    return command_handlers.build_imitation_dataset_task.apply_async(
        kwargs={"payload": {"chat_export_id": {"value": chat_id}}},
    )


def _trigger_train(neuroclone_id: str) -> str:
    return command_handlers.train_lora_adapter_task.apply_async(
        kwargs={"payload": {"neuroclone_id": {"value": neuroclone_id}}},
    )


def _trigger_assign(neuroclone_id: str) -> str:
    async def _load_neuroclone():
        with deps.open_model_engine_uow() as uow:
            return await uow.neuroclone.get_by_id_or_raise(
                ID(value=uuid.UUID(neuroclone_id)),
            )

    neuroclone = asyncio.run(_load_neuroclone())
    return command_handlers.assign_neuroclone_to_bot_task.apply_async(
        kwargs={"payload": {
            "owner_id": {"value": neuroclone.owner_id.value},
            "neuroclone_id": {"value": neuroclone_id},
            "reply_period": {"value": neuroclone.reply_period.value},
        }},
    )


def _trigger_run_bot(bot_id: str) -> str:
    return command_handlers.run_bot_task.apply_async(
        kwargs={"payload": {"bot_id": {"value": bot_id}}},
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="trigger",
        description="Manually trigger a pipeline step (sends a Celery task).",
    )
    sub = parser.add_subparsers(dest="step", required=True)

    p_ingest = sub.add_parser("ingest", help="Re-run ingest_chat_export for a chat export.")
    p_ingest.add_argument("chat_id", type=int)

    p_process = sub.add_parser("process", help="Re-run process_chat_threads for a chat export.")
    p_process.add_argument("chat_id", type=int)

    p_build = sub.add_parser("build-dataset", help="Re-run build_imitation_dataset for a chat export.")
    p_build.add_argument("chat_id", type=int)

    p_train = sub.add_parser("train", help="Re-run train_lora_adapter for a neuroclone.")
    p_train.add_argument("neuroclone_id", type=str)

    p_assign = sub.add_parser("assign", help="Re-run assign_neuroclone_to_bot for a neuroclone.")
    p_assign.add_argument("neuroclone_id", type=str)

    p_run = sub.add_parser("run-bot", help="Re-run run_bot for a bot id.")
    p_run.add_argument("bot_id", type=str)

    args = parser.parse_args()

    if args.step == "ingest":
        task_id = _trigger_ingest(args.chat_id)
    elif args.step == "process":
        task_id = _trigger_process(args.chat_id)
    elif args.step == "build-dataset":
        task_id = _trigger_build_dataset(args.chat_id)
    elif args.step == "train":
        task_id = _trigger_train(args.neuroclone_id)
    elif args.step == "assign":
        task_id = _trigger_assign(args.neuroclone_id)
    elif args.step == "run-bot":
        task_id = _trigger_run_bot(args.bot_id)
    else:
        parser.error(f"Unknown step: {args.step}")
        return

    print(f"Queued {args.step}: task_id={task_id}")


if __name__ == "__main__":
    main()
