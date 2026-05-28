__all__ = ["router"]

import json
from io import BytesIO
from typing import Any, Optional

from aiogram import Bot as AiogramBot, F, Router
from aiogram.filters import Command as TgCommand
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dishka.integrations.aiogram import FromDishka, inject

from bot_operations.application.features import (
    CreateBotCommand,
    CreateBotCommandHandler,
)
from bot_operations.domain.entities import Bot
from common.domain.value_objects import UserName, OwnerTelegramID
from common.exceptions.client.malformed_request import MissingUserException
from data_preparation.application.features import (
    CreateChatExportCommand,
    CreateChatExportCommandHandler,
)

_CALLBACK_TARGET_USER_PREFIX: str = "create_bot:target_user:"
_FSM_KEY_BOT_NAME: str = "bot_name"
_FSM_KEY_BOT_TOKEN: str = "bot_token"
_FSM_KEY_TARGET_CANDIDATES: str = "target_candidates"
_FSM_KEY_CHAT_EXPORT_ID: str = "chat_export_id"


class CreateBotStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_token = State()
    waiting_for_chat_export = State()
    waiting_for_target_user = State()


router = Router(name="create_bot")


@router.message(TgCommand("create_bot"))
async def handle_create_bot_start(
        message: Message,
        state: FSMContext,
) -> None:
    if message.from_user is None:
        raise MissingUserException()

    await state.clear()
    await state.set_state(CreateBotStates.waiting_for_name)
    await message.answer("Step 1/4. Send the name of the bot:")


@router.message(CreateBotStates.waiting_for_name, F.text)
async def handle_bot_name(
        message: Message,
        state: FSMContext,
) -> None:
    bot_name: Optional[str] = message.text
    if not bot_name or not bot_name.strip():
        await message.answer("Name cannot be empty. Please send the name of the bot again:")
        return

    await state.update_data({_FSM_KEY_BOT_NAME: bot_name.strip()})
    await state.set_state(CreateBotStates.waiting_for_token)
    await message.answer("Step 2/4. Send the bot token (you can get it from @BotFather):")


@router.message(CreateBotStates.waiting_for_token, F.text)
async def handle_bot_token(
        message: Message,
        state: FSMContext,
) -> None:
    bot_token: Optional[str] = message.text
    if not bot_token or not bot_token.strip():
        await message.answer("Token cannot be empty. Please send the bot token again:")
        return

    await state.update_data({_FSM_KEY_BOT_TOKEN: bot_token.strip()})
    await state.set_state(CreateBotStates.waiting_for_chat_export)
    await message.answer("Step 3/4. Now, please send the chat export file (JSON) that the bot will be based on")


@router.message(CreateBotStates.waiting_for_chat_export, F.document)
@inject
async def handle_chat_export_file(
        message: Message,
        state: FSMContext,
        aiogram_bot: AiogramBot,
) -> None:
    message_document = message.document
    if message.from_user is None:
        raise MissingUserException()
    if message_document is None:
        await message.answer(
            "Document is required. Please send the chat export file (JSON) that the bot will be based on:")
        return

    file_buffer: BytesIO = BytesIO()
    await aiogram_bot.download(file=message_document.file_id, destination=file_buffer)
    file_buffer.seek(0)

    raw_bytes: bytes = file_buffer.getvalue()
    parsed_data: Optional[dict[str, Any]] = _try_parse_json(raw_bytes)
    if parsed_data is None:
        await message.answer(
            "Failed to parse the file. Please make sure it's a valid JSON file exported from Telegram and send it again:")
        return

    unique_senders: list[str] = _extract_unique_senders(parsed_data)
    if not unique_senders:
        await message.answer(
            "Couldn't find any valid senders in the chat export. Please make sure the file is correct and try again:")
        return

    await state.update_data({
        _FSM_KEY_TARGET_CANDIDATES: unique_senders,
        _FSM_KEY_CHAT_EXPORT_ID: message_document.file_id,
    })

    keyboard: InlineKeyboardMarkup = _build_target_user_keyboard(unique_senders)

    await state.set_state(CreateBotStates.waiting_for_target_user)
    await message.answer(
        "Step 4/4. Please select the target user for the bot (the bot will be able to impersonate this user):",
        reply_markup=keyboard,
    )


@router.callback_query(
    CreateBotStates.waiting_for_target_user,
    F.data.startswith(_CALLBACK_TARGET_USER_PREFIX),
)
@inject
async def handle_target_user_selection(
        callback: CallbackQuery,
        state: FSMContext,
        aiogram_bot: AiogramBot,
        create_bot_handler: FromDishka[CreateBotCommandHandler],
        create_chat_export_handler: FromDishka[CreateChatExportCommandHandler],
) -> None:
    if callback.from_user is None:
        raise MissingUserException()
    if callback.data is None:
        await callback.answer("Invalid selection", show_alert=False)
        return

    state_data: dict[str, Any] = await state.get_data()
    candidates: list[str] = state_data.get(_FSM_KEY_TARGET_CANDIDATES, [])

    raw_index: str = callback.data.removeprefix(_CALLBACK_TARGET_USER_PREFIX)
    selected_index: Optional[int] = _try_parse_int(raw_index)
    if selected_index is None or selected_index < 0 or selected_index >= len(candidates):
        await callback.answer("Invalid selection", show_alert=False)
        return

    target_user_name = UserName(value=candidates[selected_index])
    bot_name: str = state_data[_FSM_KEY_BOT_NAME]
    bot_token: str = state_data[_FSM_KEY_BOT_TOKEN]
    owner_telegram_id: int = callback.from_user.id

    file_id = state_data[_FSM_KEY_CHAT_EXPORT_ID]
    file_buffer = BytesIO()
    await aiogram_bot.download(file=file_id, destination=file_buffer)
    file_buffer.seek(0)

    create_export_response = await create_chat_export_handler.handle(CreateChatExportCommand(
        owner_id=OwnerTelegramID(value=owner_telegram_id),
        file_bytes=file_buffer,
        target_user_name=target_user_name,
    ))
    if create_export_response.chat_export_id is None:
        await callback.answer(create_export_response.message)
        return

    bot_response = await create_bot_handler.handle(CreateBotCommand(
        owner_id=OwnerTelegramID(value=owner_telegram_id),
        bot_name=Bot.Name(value=bot_name),
        bot_token=Bot.Token(value=bot_token),
    ))

    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer(bot_response.message)
    await callback.answer()
    await state.clear()


def _build_target_user_keyboard(
        candidates: list[str],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=name,
                callback_data=f"{_CALLBACK_TARGET_USER_PREFIX}{index}",
            ),
        ]
        for index, name in enumerate(candidates)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _try_parse_json(
        raw_bytes: bytes,
) -> Optional[dict[str, Any]]:
    try:
        return json.loads(raw_bytes.decode("utf-8"))
    except Exception:
        return None


def _extract_unique_senders(
        data: dict[str, Any],
) -> list[str]:
    seen: set[str] = set()
    for raw in data.get("messages", []):
        sender: Any = raw.get("from") or raw.get("actor")
        if isinstance(sender, str) and sender.strip():
            seen.add(sender.strip())

    return sorted(seen)


def _try_parse_int(
        value: str,
) -> Optional[int]:
    try:
        return int(value)
    except ValueError:
        return None
