from aiogram.fsm.state import StatesGroup, State


class OrderState(StatesGroup):
    table = State()
    zone = State()
    flavor = State()