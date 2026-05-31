import enum
import pathlib

BASE_PATH = pathlib.Path(__file__).resolve().parent

LORA_TARGET_UPDATES = 400
LORA_MIN_EPOCHS = 1
LORA_MAX_EPOCHS = 3
LORA_BATCH_SIZE = 4
LORA_LAYERS = 8
LORA_LR = 2e-5
LORA_MAX_SEQ_LENGTH = 512

IMITATION_TOP_P = 0.85
IMITATION_MIN_P = 0.05
IMITATION_REPETITION_PENALTY = 1.15
IMITATION_REPETITION_CONTEXT_SIZE = 20


class AvailableModel(enum.StrEnum):
    QWEN_3_5_9B = "QWEN_3_5_9B"
    QWEN_3_5_4B = "QWEN_3_5_4B"
    QWEN_2_5_3B = "QWEN_2_5_3B"
    QWEN_2_5_1_5B = "QWEN_2_5_1_5B"
    LLAMA_3_2_3B = "LLAMA_3_2_3B"

    def is_qwen(self) -> bool:
        return self.value in {
            AvailableModel.QWEN_3_5_9B.value,
            AvailableModel.QWEN_3_5_4B.value,
            AvailableModel.QWEN_2_5_3B.value,
            AvailableModel.QWEN_2_5_1_5B.value,
        }
