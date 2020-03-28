# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import telegram
from telegram.error import Unauthorized, TelegramError

from collections import defaultdict

import random

from deck_enums import DECK_NAMES

with open("api_key.txt", 'r') as f:
    TOKEN = f.read().rstrip()

bot = telegram.Bot(token=TOKEN)


class Player:
    def __init__(self, name, hand):
        self.__hand = hand
        self.__name = name
        self.__score = 0

    def get_hand(self):
        return self.__hand

    def get_name(self):
        return self.__name

    def get_score(self):
        return self.__score

    def remove_card(self, id):
        if 0 <= id < len(self.__hand):
            return self.__hand.pop(id)
        return None

    def get_formatted_hand(self):
        text = "<b>Your current hand:</b>\n\n"
        for i in range(len(self.__hand)):
            text += "(" + str(i) + ") " + str(self.__hand[i]) + "\n"
        return text

    def add_card(self, c):
        self.__hand.append(c)

    def insert_card(self, c, i):
        self.__hand.insert(i, c)

    def set_hand(self, hand):
        self.__hand = hand

    def increment_score(self):
        self.__score += 1


class Deck:
    def __init__(self, decks_to_use):
        self.__white_cards = []
        self.__black_cards = []
        self.__white_cards_played = []
        self.__black_cards_played = []
        self.__HAND_SIZE = 10
        for d in decks_to_use:
            self.__white_cards += open("./static_responses/white_cards/%s" % DECK_NAMES[d]).readlines()
            bcs = open("./static_responses/black_cards/%s" % DECK_NAMES[d]).readlines()
            for bc in bcs:
                bc_split = bc.split("|")
                # Black cards are tuples of (num cards to submit, text).
                self.__black_cards.append((int(bc_split[0]), bc_split[1]))
        random.shuffle(self.__white_cards)
        random.shuffle(self.__black_cards)

    def reshuffle(self):
        if len(self.__white_cards) <= 0 < len(self.__white_cards_played):
            self.__white_cards = random.shuffle(self.__white_cards_played[:-1])
            self.__white_cards_played = self.__white_cards_played[-1]

        if len(self.__black_cards) <= 0 < len(self.__black_cards_played):
            self.__black_cards = random.shuffle(self.__black_cards_played[:-1])
            self.__black_cards_played = self.__black_cards_played[-1]

    def draw_white_card(self):
        if len(self.__white_cards) <= 0:
            self.reshuffle()
        return self.__white_cards.pop()

    def draw_black_card(self):
        if len(self.__black_cards) <= 0:
            self.reshuffle()
        return self.__black_cards.pop()

    def draw_hand(self):
        hand = []
        for i in range(self.__HAND_SIZE):
            hand.append(self.draw_white_card())
        return hand

    def discard_white_cards(self, cards):
        self.__white_cards_played += cards

    def discard_black_card(self, card):
        self.__black_cards_played.append(card)

    def get_hand_size(self):
        return self.__HAND_SIZE


class Game:
    def __init__(self, chat_id, players, decks_to_use):
        self.__turn = 0
        # Players is a dict of (Telegram ID, name).
        self.__players = {}
        self.__deck = Deck(decks_to_use)
        self.__chat_id = chat_id
        self.__current_black_card = self.__deck.draw_black_card()
        # This is a dict of (Telegram ID, list of cards submitted).
        self.__cards_submitted_this_round = defaultdict(list)
        self.__randomized_ids = []
        # Whoever gets to 7 black cards won first wins!
        self.__WIN_NUM = 7

        for user_id, name in players.items():
            self.__players[user_id] = Player(name, self.__deck.draw_hand())
            self.send_message(self.__chat_id, "%s has been added to the game.\n" % name)

        self.send_state()

    def send_message(self, chat_id, text):
        try:
            bot.send_message(chat_id=chat_id, text=text, parse_mode=telegram.ParseMode.HTML)
        except TelegramError as e:
            raise e

    def get_players(self):
        return self.__players

    def get_deck(self):
        return self.__deck

    def get_current_turn_player(self):
        return self.__players[list(self.__players.keys())[self.__turn]]

    def draw(self, player):
        while len(player.get_hand()) < self.__deck.get_hand_size():
            player.add_card(self.__deck.draw_white_card())

    def send_state(self):
        current_black_card_text = "<b>Current Black Card:</b>\n\n%s" % self.__current_black_card[1]
        for telegram_id in self.__players.keys():
            self.send_message(chat_id=telegram_id, text=current_black_card_text)

        text = "<b>Current Turn:</b> <a href='tg://user?id=%s'>%s</a>\n\n" % (list(self.__players.keys())[self.__turn],
                                                                              self.get_current_turn_player().get_name())
        text += current_black_card_text
        self.send_message(chat_id=self.__chat_id, text=text)

    def next_turn(self):
        for telegram_id, white_cards in self.__cards_submitted_this_round.items():
            self.__deck.discard_white_cards(white_cards)

        self.__deck.discard_black_card(self.__current_black_card)

        self.__current_black_card = self.__deck.draw_black_card()

        self.__cards_submitted_this_round = defaultdict(list)

        self.__randomized_ids = []

        self.__turn = (self.__turn + 1) % len(self.__players)

        self.send_state()

    def check_for_win(self):
        for p in self.__players.values():
            if p.get_score() >= self.__WIN_NUM:
                return p.get_name()
        return False

    def send_white_card_options(self):
        text = "<b>Current Black Card:</b>\n\n%s\n" % self.__current_black_card[1]
        text += "<b>White Cards Submitted:</b>\n\n"

        count = 0
        for id in self.__randomized_ids:
            key = list(self.__cards_submitted_this_round.keys())[id]
            white_cards = self.__cards_submitted_this_round[key]
            text += "(%s) %s\n" % (count, "".join(white_cards))
            count += 1
        self.send_message(self.__chat_id, text)

    def player_submitted_correct_num_cards(self, telegram_id):
        return len(self.__cards_submitted_this_round[telegram_id]) == self.__current_black_card[0]

    def check_if_ready_for_choice(self):
        return len(self.__cards_submitted_this_round.keys()) == len(self.__players) - 1 and \
                all(len(cards) == self.__current_black_card[0] for cards in self.__cards_submitted_this_round.values())

    def play(self, telegram_id, card_id):
        player = self.__players[telegram_id]

        if player is None:
            self.send_message(self.__chat_id, "You don't seem to exist!")
            return

        if self.get_current_turn_player() == player:
            self.send_message(self.__chat_id, "You can't play a white card on your turn!")
            return

        if len(self.__cards_submitted_this_round[telegram_id]) == self.__current_black_card[0]:
            self.send_message(self.__chat_id, "You've already played all your white cards for this round!")
            return

        card = player.remove_card(card_id)
        self.__cards_submitted_this_round[telegram_id].append(card)
        self.send_message(telegram_id, "You submitted: %s" % card)

        # Draw back to 10 cards.
        self.draw(player)

        # Check to see that the correct number of cards have been submitted and everyone has submitted for this round.
        if self.check_if_ready_for_choice():
            self.__randomized_ids = [*range(len(self.__players) - 1)]
            random.shuffle(self.__randomized_ids)
            self.send_white_card_options()

    def send_scoreboard(self):
        text = "<b>Scoreboard:</b>\n\n"
        for p in self.__players.values():
            text += "%s: %s\n" % (p.get_name(), p.get_score())
        self.send_message(self.__chat_id, text)

    def choose(self, telegram_id, i):
        player = self.__players[telegram_id]

        if player is None:
            self.send_message(self.__chat_id, "You don't seem to exist!")
            return False

        if self.get_current_turn_player() != player:
            self.send_message(self.__chat_id, "It's not your turn to choose a winning white card!")
            return False

        if len(self.__cards_submitted_this_round.keys()) < len(self.__players) - 1:
            self.send_message(self.__chat_id, "Not all white cards have been submitted yet!")
            return False

        if i < 0 or i > len(self.__randomized_ids):
            self.send_message(self.__chat_id,
                              "That (%s) is not a valid number from 0-%s!" % (i, len(self.__randomized_ids)))

        key = list(self.__cards_submitted_this_round.keys())[self.__randomized_ids[i]]
        player_chosen = self.__players[key]
        player_chosen.increment_score()

        self.send_message(self.__chat_id, "That card belonged to %s!" % player_chosen.get_name())
        self.send_scoreboard()

        return True