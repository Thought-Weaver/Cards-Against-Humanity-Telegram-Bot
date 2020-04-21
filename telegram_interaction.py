# -*- coding: utf-8 -*-
#!/usr/bin/env python3
from __future__ import unicode_literals

import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler
from telegram.error import TelegramError, Unauthorized
import logging

import os

import cah

from deck_enums import DeckEnums, DECK_NAMES

with open("api_key.txt", 'r') as f:
    TOKEN = f.read().rstrip()

PORT = int(os.environ.get("PORT", "8443"))

# Format is mmddyyyy
PATCHNUMBER = "03252020"

MIN_PLAYERS = 3


def static_handler(command):
    text = open("static_responses/{}.txt".format(command), "r").read()

    return CommandHandler(command,
        lambda bot, update: bot.send_message(chat_id=update.message.chat.id, text=text))


def reset_chat_data(chat_data):
    chat_data["is_game_pending"] = False
    chat_data["pending_players"] = {}
    chat_data["game_obj"] = None
    chat_data["decks"] = []


def check_game_existence(bot, game, chat_id):
    if game is None:
        text = open("static_responses/game_dne_failure.txt", "r").read()
        bot.send_message(chat_id=chat_id, text=text)
        return False

    return True


def send_hand(bot, chat_id, game, user_id):
    hand = game.get_players().get(user_id).get_formatted_hand()

    bot.send_message(chat_id=user_id,
                     text=hand + "\n",
                     parse_mode = telegram.ParseMode.HTML)


def send_hands(bot, chat_id, game, players):
    for user_id, nickname in players.items():
        send_hand(bot, chat_id, game, user_id)


def newgame_handler(bot, update, chat_data):
    game = chat_data.get("game_obj")
    chat_id = update.message.chat.id

    if game is None and not chat_data.get("is_game_pending", False):
        reset_chat_data(chat_data)
        chat_data["is_game_pending"] = True
        text = open("static_responses/new_game.txt", "r").read()
    elif game is not None:
        text = open("static_responses/game_ongoing.txt", "r").read()
    elif chat_data.get("is_game_pending", False):
        text = open("static_responses/game_pending.txt", "r").read()
    else:
        text = "Something has gone horribly wrong!"

    bot.send_message(chat_id=chat_id, text=text)


def is_nickname_valid(name, user_id, chat_data):
    if user_id in chat_data.get("pending_players", {}):
        if name.lower() == chat_data["pending_players"][user_id].lower():
            return True

    for id, user_name in chat_data.get("pending_players", {}).items():
        if name.lower() == user_name.lower():
            return False

    return True


def join_handler(bot, update, chat_data, args):
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id

    if not chat_data.get("is_game_pending", False):
        text = open("static_responses/join_game_not_pending.txt", "r").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    if args:
        nickname = " ".join(args)
    else:
        nickname = update.message.from_user.first_name

    if is_nickname_valid(nickname, user_id, chat_data):
        chat_data["pending_players"][user_id] = nickname
        bot.send_message(chat_id=update.message.chat_id,
                         text="Joined with nickname %s!" % nickname)
        bot.send_message(chat_id=update.message.chat_id,
                         text="Current player count: %d" % len(chat_data.get("pending_players", {})))
    else:
        text = open("static_responses/invalid_nickname.txt", "r").read()
        bot.send_message(chat_id=chat_id, text=text)


def leave_handler(bot, update, chat_data):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not chat_data.get("is_game_pending", False):
        text = open("static_responses/leave_game_not_pending_failure.txt", "r").read()
    elif user_id not in chat_data.get("pending_players", {}):
        text = open("static_responses/leave_id_missing_failure.txt", "r").read()
    else:
        text = "You have left the current game."
        del chat_data["pending_players"][update.message.from_user.id]

    bot.send_message(chat_id=chat_id, text=text)


def listplayers_handler(bot, update, chat_data):
    chat_id = update.message.chat_id
    text = "List of players: \n"
    game = chat_data.get("game_obj")

    if chat_data.get("is_game_pending", False):
        for user_id, name in chat_data.get("pending_players", {}).items():
            text += "%s\n" % name
    elif game is not None:
        for player in game.get_players().values():
            text += "%s\n" % player.get_name()
    else:
        text = open("static_responses/listplayers_failure.txt", "r").read()

    bot.send_message(chat_id=chat_id, text=text)


def feedback_handler(bot, update, args):
    if args and len(args) > 0:
        feedback = open("feedback.txt\n", "a+")
        feedback.write(update.message.from_user.first_name + "\n")
        feedback.write(str(update.message.from_user.id) + "\n")
        feedback.write(" ".join(args) + "\n")
        feedback.close()
        bot.send_message(chat_id=update.message.chat_id, text="Thanks for the feedback!")
    else:
        bot.send_message(chat_id=update.message.chat_id, text="Usage: /feedback [feedback]")


def startgame_handler(bot, update, chat_data):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    pending_players = chat_data.get("pending_players", {})

    if not chat_data.get("is_game_pending", False):
        text = open("static_responses/start_game_not_pending.txt", "r").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    if user_id not in chat_data.get("pending_players", {}).keys():
        text = open("static_responses/start_game_id_missing_failure.txt", "r").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    if len(pending_players) < MIN_PLAYERS:
        text = open("static_responses/start_game_min_threshold.txt", "r").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    try:
        for user_id, nickname in pending_players.items():
            bot.send_message(chat_id=user_id, text="Trying to start game!")
    except Unauthorized as u:
        text = open("static_responses/start_game_failure.txt", "r").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    text = open("static_responses/start_game.txt", "r").read()
    bot.send_message(chat_id=chat_id, text=text)

    chat_id = update.message.chat_id
    pending_players = chat_data.get("pending_players", {})
    chat_data["is_game_pending"] = False
    decks = [0] if len(chat_data["decks"]) == 0 else chat_data["decks"]
    chat_data["game_obj"] = cah.Game(chat_id, pending_players, decks)
    game = chat_data["game_obj"]

    send_hands(bot, chat_id, game, pending_players)


def endgame_handler(bot, update, chat_data):
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    game = chat_data.get("game_obj")

    if chat_data.get("is_game_pending", False):
        chat_data["is_game_pending"] = False
        text = open("static_responses/end_game.txt", "r").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    if game is None:
        text = open("static_responses/game_dne_failure.txt", "r").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    if user_id not in game.get_players():
        text = open("static_responses/end_game_id_missing_failure.txt", "r").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    reset_chat_data(chat_data)
    text = open("static_responses/end_game.txt", "r").read()
    bot.send_message(chat_id=chat_id, text=text)


def play_handler(bot, update, chat_data, args):
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    game = chat_data.get("game_obj")

    if not check_game_existence(bot, game, chat_id):
        return

    if len(args) < 1:
        bot.send_message(chat_id=chat_id, text="Usage: /play {card ID 1} {card ID 2} ...")
        return

    num_cards_to_submit = game.get_current_black_card()[0]
    if len(args) > num_cards_to_submit:
        bot.send_message(chat_id=chat_id, text="You submitted more cards that necessary (%s)!" % num_cards_to_submit)
        return

    card_ids = [int(c) for c in args]

    if any(card_id < 0 or card_id > game.get_deck().get_hand_size() for card_id in card_ids):
        bot.send_message(chat_id=chat_id, text="That's not a valid card ID.")
        return

    game.play(user_id, card_ids)
    send_hand(bot, chat_id, game, user_id)


def choose_handler(bot, update, chat_data, args):
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    game = chat_data.get("game_obj")

    if not check_game_existence(bot, game, chat_id):
        return

    if len(args) != 1:
        bot.send_message(chat_id=chat_id, text="Usage: /choose {ID}")
        return

    id = int(args[0])

    if game.choose(user_id, id):
        winner = game.check_for_win()
        if not winner:
            game.next_turn()
        else:
            bot.send_message(chat_id=chat_id, text="%s has won!" % winner)
            endgame_handler(bot, update, chat_data)


def blame_handler(bot, update, chat_data):
    chat_id = update.message.chat_id
    game = chat_data.get("game_obj")

    if game is None:
        text = open("static_responses/game_dne_failure.txt", "r").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    if game.check_if_ready_for_choice():
        for telegram_id, player in game.get_players().items():
            if game.get_current_turn_player() == player:
                bot.send_message(chat_id=chat_id, text="[{}](tg://user?id={})".format(player.get_name(), telegram_id),
                                 parse_mode=telegram.ParseMode.MARKDOWN)
                return

    text = ""
    for telegram_id, player in game.get_players().items():
        if game.get_current_turn_player() != player and not game.player_submitted_correct_num_cards(telegram_id):
            text += "[{}](tg://user?id={})\n".format(player.get_name(), telegram_id)
    bot.send_message(chat_id=chat_id, text=text, parse_mode=telegram.ParseMode.MARKDOWN)



def add_deck_handler(bot, update, chat_data, args):
    chat_id = update.message.chat_id

    if not chat_data.get("is_game_pending", False):
        text = open("static_responses/add_deck_not_pending.txt", "r").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    if len(args) < 1:
        bot.send_message(chat_id=chat_id, text="Usage: /ad {deck IDs from /decks}")
        return

    try:
        decks = [int(d) for d in args]
    except ValueError:
        bot.send_message(chat_id=chat_id, text="That is not a valid integer.")
        return

    max_deck = max(list(map(int, DeckEnums)))
    if any(deck < 0 or deck > max_deck for deck in decks):
        bot.send_message(chat_id=chat_id, text="That deck is not in the range [0, %s]!" % max_deck)
        return

    if chat_data.get("decks") is None:
        chat_data["decks"] = decks
    else:
        chat_data["decks"] = list(set(chat_data["decks"]).union(set(decks)))
    bot.send_message(chat_id=chat_id, text="Added deck(s) %s!" % decks)


def remove_deck_handler(bot, update, chat_data, args):
    chat_id = update.message.chat_id

    if not chat_data.get("is_game_pending", False):
        text = open("static_responses/remove_deck_not_pending.txt", "r").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    if len(args) != 1:
        bot.send_message(chat_id=chat_id, text="Usage: /rd {deck ID from /decks}")
        return

    try:
        deck = int(args[0])
    except ValueError:
        bot.send_message(chat_id=chat_id, text="That is not a valid integer.")
        return

    max_deck = max(list(map(int, DeckEnums)))
    if deck < 0 or deck > max_deck:
        bot.send_message(chat_id=chat_id, text="That deck is not in the range [0, %s]!" % max_deck)
        return

    if chat_data.get("decks") is None:
        bot.send_message(chat_id=chat_id, text="No decks have been added yet! You can't remove one.")
        return
    else:
        if deck not in chat_data["decks"]:
            bot.send_message(chat_id=chat_id, text="That deck has not been added!")
            return
        chat_data["decks"].remove(deck)
    bot.send_message(chat_id=chat_id, text="Removed deck %s!" % deck)


def current_decks_handler(bot, update, chat_data):
    chat_id = update.message.chat_id
    game = chat_data.get("game_obj")

    if not chat_data.get("is_game_pending", False) and game is None:
        text = open("static_responses/current_decks_not_pending.txt", "r").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    text = "Current Decks:\n\n"
    for i in chat_data["decks"]:
        text += "(%s) %s\n" % (i, DECK_NAMES[i])
    bot.send_message(chat_id=chat_id, text=text)


def handle_error(bot, update, error):
    try:
        raise error
    except TelegramError:
        logging.getLogger(__name__).warning('Telegram Error! %s caused by this update: %s', error, update)


if __name__ == "__main__":
    # Set up the bot

    bot = telegram.Bot(token=TOKEN)
    updater = Updater(token=TOKEN)
    dispatcher = updater.dispatcher

    # Static command handlers

    static_commands = ["start", "rules", "help", "decks"]
    for c in static_commands:
        dispatcher.add_handler(static_handler(c))

    # Main command handlers

    join_aliases = ["join"]
    leave_aliases = ["leave", "unjoin"]
    listplayers_aliases = ["listplayers", "list"]
    play_aliases = ["play", "p"]
    choose_aliases = ["choose", "c", "pick"]
    feedback_aliases = ["feedback"]
    newgame_aliases = ["newgame"]
    startgame_aliases = ["startgame"]
    endgame_aliases = ["endgame"]
    add_deck_aliases = ["adddeck", "ad"]
    remove_deck_aliases = ["removedeck", "rd"]
    blame_aliases = ["blame", "blam"]
    current_decks_aliases = ["currentdecks", "cd"]

    commands = [("feedback", 0, feedback_aliases),
                ("newgame", 1, newgame_aliases),
                ("join", 2, join_aliases),
                ("leave", 1, leave_aliases),
                ("listplayers", 1, listplayers_aliases),
                ("startgame", 1, startgame_aliases),
                ("endgame", 1, endgame_aliases),
                ("play", 2, play_aliases),
                ("choose", 2, choose_aliases),
                ("add_deck", 2, add_deck_aliases),
                ("remove_deck", 2, remove_deck_aliases),
                ("blame", 1, blame_aliases),
                ("current_decks", 1, current_decks_aliases)]
    for c in commands:
        func = locals()[c[0] + "_handler"]
        if c[1] == 0:
            dispatcher.add_handler(CommandHandler(c[2], func, pass_args=True))
        elif c[1] == 1:
            dispatcher.add_handler(CommandHandler(c[2], func, pass_chat_data=True))
        elif c[1] == 2:
            dispatcher.add_handler(CommandHandler(c[2], func, pass_chat_data=True, pass_args=True))
        elif c[1] == 3:
            dispatcher.add_handler(CommandHandler(c[2], func, pass_chat_data=True, pass_user_data=True))

    # Error handlers

    dispatcher.add_error_handler(handle_error)

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO, filename='logging.txt', filemode='a')

    updater.start_polling()
    updater.idle()