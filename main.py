import logging
import json
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = '7065423366:AAFekBFw-3I0_HFNbIyeHt9uQ1en2OwlLfI'  # Замените на ваш API токен от BotFather
Password = '419'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

async def on_startup(dispatcher):
    global Password
    try:
        with open("password.txt", "r") as file:
            Password = file.read().strip()
    except FileNotFoundError:
        print("Файл пароля не найден, используется стандартный пароль.")
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Начать")
    await bot.send_message(5429082466, "Нажмите 'Начать', чтобы продолжить", reply_markup=keyboard)

def save_events_to_file():
    with open("events_data.json", "w", encoding='utf-8') as file:
        json.dump(events, file, ensure_ascii=False, indent=4)

def load_events_from_file():
    try:
        with open("events_data.json", "r", encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_password(password):
    with open("password.txt", "w") as file:
        file.write(password)

async def on_startup(dispatcher):
    global Password
    try:
        with open("password.txt", "r") as file:
            Password = file.read().strip()
    except FileNotFoundError:
        print("Файл пароля не найден, используется стандартный пароль.")
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Начать")
    await bot.send_message(5429082466, "Нажмите 'Начать', чтобы продолжить", reply_markup=keyboard)


events = load_events_from_file()

def save_password(password):
    with open("password.txt", "w") as file:
        file.write(password)

class EventStates(StatesGroup):
    Start = State()  # Начальное состояние
    EnterPassword = State()  # Ввод пароля для управления мероприятиями
    EventAction = State()  # Выбор действия для мероприятия
    AddEvent = State()  # Добавление нового мероприятия
    RemoveEvent = State()  # Удаление мероприятия
    RemovingMore = State()  # Состояние после удаления для решения, хочет ли пользователь удалить еще одно мероприятие
    ChangePassword = State()  # Добавляем новое состояние для смены пароля
    MaxParticipants = State()  # Состояние для ввода максимального количества записей на мероприятие


class ParticipantStates(StatesGroup):
    AwaitingStart = State()  # Добавляем новое состояние, ожидающее начала работы
    Start = State()
    ChoosingEvent = State()  # Выбор мероприятия для записи
    EnteringName = State()  # Ввод имени для записи на мероприятие
    UnsubscribeEvent = State()  # Добавлено состояние для отписки от мероприятия


@dp.message_handler(lambda message: message.text == "Начать", state="*")
async def process_start_button(message: types.Message, state: FSMContext):
    await cmd_start(message, state)

@dp.callback_query_handler(lambda c: c.data == 'back_to_start')
async def go_back_inline(callback_query: types.CallbackQuery):
    await callback_query.answer("🔙 Возвращаемся назад.")
    await EventStates.Start.set()
    await callback_query.message.edit_reply_markup()  # Удаление инлайн-клавиатуры

@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    if state is not None:
        await state.finish()  # Сбрасываем состояние FSM до начального
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["📝 Записаться на мероприятие", "👀 Посмотреть участников", "📋 Мои мероприятия", "❌ Отписаться от мероприятия"]
    if message.chat.type == "private":
        buttons.insert(1, "🛠 Управление мероприятиями")
    keyboard.add(*buttons)
    await message.answer("Выберите действие:", reply_markup=keyboard)
    await EventStates.Start.set()


@dp.message_handler(lambda message: message.text == "📋 Мои мероприятия", state="*")
async def show_my_events(message: types.Message):
    user_id = message.from_user.id
    my_events_info = []

    # Перебираем все мероприятия и ищем участие пользователя
    for event_name, participants in events.items():
        # Создаем список для хранения имен, под которыми пользователь записан на мероприятие
        names_registered = [participant['name'] for participant in participants if participant["id"] == user_id]

        if names_registered:  # Если пользователь записан на мероприятие под одним или несколькими именами
            names_str = ", ".join([f"👤 {name}" for name in names_registered])  # Добавляем эмодзи к каждому имени
            my_events_info.append(f"📅 {event_name} (как {names_str})")

    # Формируем сообщение со списком мероприятий и именами
    if my_events_info:
        response_message = "📘 Вы записаны на следующие мероприятия:\n\n" + "\n\n".join(my_events_info)
    else:
        response_message = "📭 Вы пока не записаны ни на одно мероприятие."

    await message.answer(response_message)



@dp.message_handler(lambda message: message.text == "❌ Отписаться от мероприятия", state="*")
async def unsubscribe_from_event(message: types.Message, state: FSMContext):
    await ParticipantStates.UnsubscribeEvent.set()
    user_id = message.from_user.id
    keyboard = types.InlineKeyboardMarkup()

    # Перебираем все мероприятия и ищем участие пользователя
    for event_name, participants in events.items():
        for participant in participants:
            if participant["id"] == user_id:
                callback_data = f"unsubscribe:{event_name}:{participant['name']}"
                keyboard.add(types.InlineKeyboardButton(f"{event_name} (как {participant['name']})", callback_data=callback_data))

    if keyboard.inline_keyboard:
        await message.answer("Выберите мероприятие и имя, от которых хотите отписаться:", reply_markup=keyboard)
    else:
        await message.answer("Вы не записаны ни на одно мероприятие.")
        await EventStates.Start.set()  # Возвращаемся в начальное состояние



@dp.callback_query_handler(lambda c: c.data.startswith('unsubscribe:'), state="*")
async def process_unsubscribe(callback_query: types.CallbackQuery, state: FSMContext):
    logging.info(f"Received callback query for unsubscribe: {callback_query.data}")
    try:
        _, event_name, participant_name = callback_query.data.split(':', 2)
        user_id = callback_query.from_user.id
        logging.info(f"Event name: {event_name}, Participant name: {participant_name}")
        participants = events.get(event_name, [])
        logging.info(f"Current participants: {participants}")

        new_participants = [participant for participant in participants if not (participant["id"] == user_id and participant["name"] == participant_name)]

        if len(participants) > len(new_participants):
            events[event_name] = new_participants
            save_events_to_file()
            logging.info(f"Successfully unsubscribed {user_id} from {event_name}")
            await callback_query.answer(f"Вы успешно отписаны от '{event_name}' как '{participant_name}'.")
            await callback_query.message.edit_text("Ваша отписка успешно обработана.")
        else:
            logging.warning(f"User {user_id} not found in participants for {event_name}")
            await callback_query.answer("Не удалось отписаться. Возможно, вы уже отписаны.")
    except Exception as e:
        logging.error(f"Error in process_unsubscribe: {e}")
        await callback_query.answer("Произошла ошибка при обработке вашего запроса.")

    await state.finish()
    await EventStates.Start.set()


@dp.message_handler(state=ParticipantStates.EnteringName)
async def participant_name_entered(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    event_name = user_data.get('chosen_event')
    participant_id = message.from_user.id  # Получаем ID пользователя
    participant_name = message.text  # Получаем имя пользователя

    # Проверяем, существует ли мероприятие
    if event_name not in events:
        events[event_name] = []

    # Сохраняем участника как словарь с ID и именем
    participant_info = {"id": participant_id, "name": participant_name}
    events[event_name].append(participant_info)  # Добавляем информацию об участнике

    await message.reply(f"✅ Вы записаны на мероприятие '{event_name}'. Желаете продолжить?",
                        reply_markup=continue_or_not_keyboard())
    await ParticipantStates.ChoosingEvent.set()

    async def remove_participant_from_event(event_name, user_id):
        if event_name in events:
            # Ищем участника по ID и удаляем его из списка
            events[event_name] = [participant for participant in events[event_name] if participant["id"] != user_id]


# Функция для создания инлайн-клавиатуры с кнопками "Продолжить" и "Отмена"
def continue_or_not_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("▶️ Продолжить", callback_data="continue"),
                 InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    return keyboard

# Обработка ответа на запрос продолжения
@dp.callback_query_handler(lambda c: c.data in ['continue', 'cancel'], state=ParticipantStates.ChoosingEvent)
async def continue_or_cancel(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    if callback_query.data == 'continue':
        await cmd_start(callback_query.message, state)
    else:
        await state.finish()
        await callback_query.message.reply("❌ Диалог завершен.", reply_markup=types.ReplyKeyboardRemove())


    # Обработка кнопки "Посмотреть участников"
    @dp.message_handler(lambda message: message.text == "👀 Посмотреть участников", state=EventStates.Start)
    async def show_participants_btn(message: types.Message):
        if not events:
            await message.answer("В данный момент нет доступных мероприятий.")
            return

        response_message = "📌 Список участников мероприятий:\n"
        for event_name, participants in events.items():
            response_message += f"\n📝 {event_name}:\n"
            if participants:
                # Используем только имя участника для отображения
                participant_names = [participant["name"] for participant in participants]
                response_message += "\n".join([f"👤 {name}" for name in participant_names]) + "\n"
            else:
                response_message += "Нет участников\n"
            response_message += "-----------------\n"  # Добавляем разделительную линию

        await message.answer(response_message)
        save_events_to_file()  # Сохраняем данные


# Обработка кнопки "Записаться на мероприятие"
@dp.message_handler(lambda message: message.text == "📝 Записаться на мероприятие", state=EventStates.Start)
async def join_event(message: types.Message):
    if not events:
        await message.answer("В данный момент нет доступных мероприятий.")
        return
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for event in events.keys():
        keyboard.add(event)
    keyboard.add("❌ Отмена")
    await message.answer("Выберите мероприятие:", reply_markup=keyboard)
    await ParticipantStates.ChoosingEvent.set()

# Обработка выбора мероприятия для записи
@dp.message_handler(state=ParticipantStates.ChoosingEvent)
async def process_event_choice(message: types.Message, state: FSMContext):
    if message.text not in events and message.text != "❌ Отмена":
        await message.reply("Пожалуйста, выберите мероприятие из списка.")
        return
    elif message.text == "❌ Отмена":
        await state.finish()
        await cmd_start(message, state)  # Возвращаемся к начальному состоянию
        return
    await state.update_data(chosen_event=message.text)
    await message.reply("Введите ваше имя и фамилию:", reply_markup=types.ReplyKeyboardRemove())
    await ParticipantStates.EnteringName.set()
    save_events_to_file()  # Сохраняем данные



# Обработка кнопки "Управление мероприятиями"
@dp.message_handler(lambda message: message.text == "🛠 Управление мероприятиями", state=EventStates.Start)
async def manage_events(message: types.Message):
    await message.answer("Введите пароль для доступа к управлению мероприятиями:")
    await EventStates.EnterPassword.set()

@dp.message_handler(state=EventStates.EnterPassword)
async def process_password(message: types.Message, state: FSMContext):
    if message.text == Password:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("➕ Добавить мероприятие", callback_data="add_event"))
        keyboard.add(types.InlineKeyboardButton("➖ Удалить мероприятие", callback_data="remove_event"))
        keyboard.add(types.InlineKeyboardButton("🔑 Сменить пароль", callback_data="change_password"))  # Новая кнопка
        await message.answer("Выберите действие:", reply_markup=keyboard)
        await EventStates.EventAction.set()
    else:
        await message.reply("❌ Неверный пароль.")
        await state.finish()
        await cmd_start(message, state)

@dp.callback_query_handler(lambda c: c.data == 'change_password', state=EventStates.EventAction)
async def prompt_new_password(callback_query: types.CallbackQuery):
    await EventStates.ChangePassword.set()
    await bot.send_message(callback_query.from_user.id, "Введите новый пароль:")

@dp.message_handler(state=EventStates.ChangePassword)
async def change_password(message: types.Message, state: FSMContext):
    global Password  # Используйте глобальную переменную для хранения пароля
    Password = message.text  # Обновите пароль
    save_password(Password)  # Сохраняем пароль в файл
    await message.reply("Пароль успешно изменён.")
    await state.finish()
    await cmd_start(message, state)  # Возвращение к начальному состоянию или другой логике

# Обработка callback для кнопки "Выйти" в меню управления мероприятиями
@dp.callback_query_handler(lambda c: c.data == 'exit_to_main_menu', state="*")
async def exit_to_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await EventStates.Start.set()  # Установка начального состояния
    await state.finish()  # Сброс состояния FSM
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📝 Записаться на мероприятие", "🛠 Управление мероприятиями", "👀 Посмотреть участников")
    await callback_query.message.answer('Выберите действие:', reply_markup=keyboard)

# Обработка callback для добавления мероприятия
@dp.callback_query_handler(lambda c: c.data == 'add_event', state=EventStates.EventAction)
async def process_add_event(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, "Введите название мероприятия:")
    await EventStates.AddEvent.set()

# Обработка добавления мероприятия
@dp.message_handler(state=EventStates.AddEvent)
async def add_event(message: types.Message, state: FSMContext):
    events[message.text] = []
    save_events_to_file()  # Сохраняем данные после изменения
    await message.reply(f"✅ Мероприятие '{message.text}' добавлено.")
    save_events_to_file()  # Сохраняем данные после удаления

    # Задаем вопрос о желании добавить еще мероприятие
    await message.reply("Хотите добавить еще мероприятие?", reply_markup=continue_adding_keyboard())
    await EventStates.Start.set()  # Возвращаемся в начальное состояние

    # Пример обработчика регистрации на мероприятие
    @dp.message_handler(state=ParticipantStates.EnteringName)
    async def participant_name_entered(message: types.Message, state: FSMContext):
        user_data = await state.get_data()
        event_name = user_data.get('chosen_event')
        participant_id = message.from_user.id
        participant_name = message.text

        if event_name not in events:
            events[event_name] = []

        participant_info = {"id": participant_id, "name": participant_name}
        events[event_name].append(participant_info)
        save_events_to_file()  # Сохраняем данные после изменения

        await message.reply(f"✅ Вы записаны на мероприятие '{event_name}'.")
        # Переход к следующему состоянию или завершение

# Функция для создания инлайн-клавиатуры с кнопками "Да" и "Нет" для продолжения добавления мероприятий
def continue_adding_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✅ Да", callback_data="add_more_event"),
                 InlineKeyboardButton("❌ Нет", callback_data="no_more_event"))
    return keyboard

# Обработка ответа на вопрос о продолжении добавления мероприятий
@dp.callback_query_handler(lambda c: c.data in ['add_more_event', 'no_more_event'], state="*")
async def continue_adding_event(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    if callback_query.data == 'add_more_event':
        # Если пользователь хочет добавить еще мероприятие, отправляем запрос на название нового мероприятия
        await bot.send_message(callback_query.from_user.id, "Введите название нового мероприятия:")
        await EventStates.AddEvent.set()  # Устанавливаем состояние для обработки добавления нового мероприятия
    else:
        # Если пользователь не хочет добавлять больше мероприятий, возвращаем его в начальное состояние
        await state.finish()  # Завершаем текущее состояние
        await cmd_start(callback_query.message, state)

# Обработка callback для удаления мероприятия
@dp.callback_query_handler(lambda c: c.data == 'remove_event', state=EventStates.EventAction)
async def process_remove_event(callback_query: types.CallbackQuery):
    if not events:
        await bot.send_message(callback_query.from_user.id, "❌ В данный момент нет доступных мероприятий для удаления.")
        return
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for event_name in events.keys():
        keyboard.add(event_name)
    keyboard.add("❌ Отмена")
    await bot.send_message(callback_query.from_user.id, "Выберите мероприятие для удаления:", reply_markup=keyboard)
    await EventStates.RemoveEvent.set()

# Обработка удаления мероприятия
@dp.message_handler(state=EventStates.RemoveEvent)
async def remove_event(message: types.Message, state: FSMContext):
    event_name = message.text
    if event_name not in events and event_name != "❌ Отмена":
        await message.reply("Пожалуйста, выберите мероприятие из списка.")
        return
    elif event_name == "❌ Отмена":
        await state.finish()
        await cmd_start(message, state)  # Возвращаемся к начальному состоянию
        return
    del events[event_name]
    await message.reply(f"❌ Мероприятие '{event_name}' удалено.")
    save_events_to_file()  # Сохраняем данные после удаления

    # Обработка ответа на вопрос о продолжении удаления мероприятий
    @dp.callback_query_handler(lambda c: c.data in ['remove_more_event', 'no_more_event'], state="*")
    async def continue_removing_event(callback_query: types.CallbackQuery, state: FSMContext):
        await callback_query.answer()
        if callback_query.data == 'remove_more_event':
            # Если пользователь хочет удалить еще мероприятие, отправляем его выбирать мероприятие из списка
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)  # Создаем клавиатуру
            for event_name in events.keys():
                keyboard.add(event_name)  # Добавляем кнопку для каждого мероприятия
            keyboard.add("❌ Отмена")
            await bot.send_message(callback_query.from_user.id, "Выберите мероприятие для удаления:",
                                   reply_markup=keyboard)
            await EventStates.RemoveEvent.set()  # Устанавливаем состояние для удаления мероприятия
            save_events_to_file()  # Сохраняем данные после изменения
        else:
            # Если пользователь не хочет удалять больше мероприятий, возвращаем его в начальное состояние
            await state.finish()  # Завершаем текущее состояние
            await cmd_start(callback_query.message, state)



# Функция для создания инлайн-клавиатуры с кнопками "Да" и "Нет" для продолжения удаления мероприятий
def continue_removing_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✅ Да", callback_data="remove_more_event"),
                 InlineKeyboardButton("❌ Нет", callback_data="no_more_event"))
    return keyboard

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)