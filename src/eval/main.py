import asyncio
import json
from pathlib import Path

import constants
from eval.disentanglement_evaluator import DisentanglementEvaluator
from eval.load_dataset import load_irc_dataset_to_memory
from data_preparation.application.features.process_chat_threads import Command, CommandHandler
from data_preparation.infrastructure.in_memory.uow import InMemoryUnitOfWork
from infrastructure.llm.mlx_engine import MLXInferenceEngine


async def main(
        dataset_path: Path,
        cache_path: Path,
        base_model: constants.AvailableModel,
) -> None:
    uow = InMemoryUnitOfWork()

    eval_data = load_irc_dataset_to_memory(
        json_filepath=dataset_path,
        uow=uow,
    )

    ground_truth = eval_data.ground_truth

    chat_exports = uow.chat_export.get_all()
    if not chat_exports:
        print("Error: No chat exports found in the database!")
        return

    target_chat_export = chat_exports[0]
    all_messages = uow.parsed_message.get_all()
    print(f"Loaded messages: {len(all_messages)}")

    predictions = {}

    if cache_path.exists():
        print(f"\nCache found ({cache_path.name})! Skipping LLM inference...")
        with open(cache_path, "r", encoding="utf-8") as f:
            predictions = json.load(f)
    else:
        print("\nCache not found. Running CommandHandler with MLXInferenceEngine...")
        engine = MLXInferenceEngine(base_model)
        handler = CommandHandler(uow=uow, inference_engine=engine)

        command = Command(chat_export_id=target_chat_export.chat_id)

        await handler.handle(command)
        print("Inference completed! Collecting predictions...")

        try:
            for msg in all_messages:
                mid = msg.external_id.value
                predictions[mid] = str(msg.thread_id.value) if msg.thread_id else None

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(predictions, f, indent=4, ensure_ascii=False)
            print("Cache successfully saved!")
        except Exception as e:
            print(f"Error saving cache: {e}")

    evaluator = DisentanglementEvaluator(
        ground_truth=ground_truth,
        predictions=predictions,
    )

    evaluator.print_report()


if __name__ == "__main__":
    dataset_path = Path(__file__).parent / "CODI" / "validation_uk.json"
    cache_path = Path(__file__).parent / "cache" / "validation_predictions" / "llama3.2_ukrainian_best_settup.json"
    base_model = constants.AvailableModel.LLAMA_3_2_3B

    asyncio.run(main(
        dataset_path=dataset_path,
        cache_path=cache_path,
        base_model=base_model,
    ))
