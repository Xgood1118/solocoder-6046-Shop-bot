from aiogram.dispatcher.filters.state import StatesGroup, State

class SearchState(StatesGroup):
    keyword = State()

class ReviewState(StatesGroup):
    rating = State()
    comment = State()
