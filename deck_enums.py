from enum import IntEnum


class DeckEnums(IntEnum):
    BASE_DECK = 0
    CALTECH_DECK = 1
    ABSURD_DECK = 2
    RED_BOX = 3
    BLUE_BOX = 4
    GREEN_BOX = 5
    PAX_EAST_2013 = 6
    PAX_EAST_2014 = 7
    REJECT_PACK = 8
    SCIENCE_PACK = 9
    FANTASY_PACK = 10
    SCIFI_PACK = 11
    FOOD_PACK = 12
    INTERNET_PACK = 13
    NINETIES_PACK = 14
    PEOPLE_IN_CHAT_DECK = 15


DECK_FILENAMES = {
    DeckEnums.BASE_DECK : "base_deck.txt",
    DeckEnums.CALTECH_DECK : "caltech_deck.txt",
    DeckEnums.ABSURD_DECK : "absurd_deck.txt",
    DeckEnums.RED_BOX : "red_box.txt",
    DeckEnums.BLUE_BOX : "blue_box.txt",
    DeckEnums.GREEN_BOX : "green_box.txt",
    DeckEnums.PAX_EAST_2013 : "pax_east_2013_deck.txt",
    DeckEnums.PAX_EAST_2014 : "pax_east_2014_deck.txt",
    DeckEnums.REJECT_PACK : "reject_pack.txt",
    DeckEnums.SCIENCE_PACK : "science_pack.txt",
    DeckEnums.FANTASY_PACK : "fantasy_pack.txt",
    DeckEnums.SCIFI_PACK : "scifi_pack.txt",
    DeckEnums.FOOD_PACK : "food_pack.txt",
    DeckEnums.INTERNET_PACK : "internet_pack.txt",
    DeckEnums.NINETIES_PACK : "90s_pack.txt",
    DeckEnums.PEOPLE_IN_CHAT_DECK : "people_in_chat_deck.txt"
}

DECK_NAMES = {
    DeckEnums.BASE_DECK : "Base Deck",
    DeckEnums.CALTECH_DECK : "Caltech Deck",
    DeckEnums.ABSURD_DECK : "Absurd Deck",
    DeckEnums.RED_BOX : "Red Box",
    DeckEnums.BLUE_BOX : "Blue Box",
    DeckEnums.GREEN_BOX : "Green Box",
    DeckEnums.PAX_EAST_2013 : "PAX East 2013 Deck",
    DeckEnums.PAX_EAST_2014 : "PAX East 2014 Deck",
    DeckEnums.REJECT_PACK : "Reject Pack",
    DeckEnums.SCIENCE_PACK : "Science Pack",
    DeckEnums.FANTASY_PACK : "Fantasy Pack",
    DeckEnums.SCIFI_PACK : "Sci-fi Pack",
    DeckEnums.FOOD_PACK : "Food Pack",
    DeckEnums.INTERNET_PACK : "Internet Pack",
    DeckEnums.NINETIES_PACK : "90s Pack",
    DeckEnums.PEOPLE_IN_CHAT_DECK : "People in Chat Deck"
}