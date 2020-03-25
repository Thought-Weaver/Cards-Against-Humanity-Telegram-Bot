from enum import IntEnum


class DeckEnums(IntEnum):
    BASE_DECK = 0
    CALTECH_DECK = 1
    ABSURD_DECK = 2


DECK_NAMES = {
    DeckEnums.BASE_DECK : "base_deck.txt",
    DeckEnums.CALTECH_DECK : "caltech_deck.txt",
    DeckEnums.ABSURD_DECK : "absurd_deck.txt"
}