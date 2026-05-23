import enum
import pathlib

BASE_PATH = pathlib.Path(__file__).resolve().parent

MAX_TOKENS_IMITATION = 150
TEMP_IMITATION = 0.7

LORA_ITERS = 3
LORA_BATCH_SIZE = 4
LORA_LAYERS = 16
LORA_LR = 2e-5
LORA_MAX_SEQ_LENGTH = 512


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
