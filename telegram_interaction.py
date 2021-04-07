# -*- coding: utf-8 -*-
#!/usr/bin/env python3
from __future__ import unicode_literals

import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler
from telegram.error import TelegramError, Unauthorized
import logging

import os
import sys
import traceback
import logging
import inspect

import cah

from deck_enums import DeckEnums, DECK_NAMES

with open("api_key.txt", 'r', encoding="utf-8") as f:
    TOKEN = f.read().rstrip()

PORT = int(os.environ.get("PORT", "8443"))

# Format is mmddyyyy
PATCHNUMBER = "03252020"

MIN_PLAYERS = 3

def setup_logger(name, log_file, level=logging.INFO):
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

ERROR_LOGGER = setup_logger("error_logger", "error_logs.log")
INFO_LOGGER = setup_logger("info_logger", "info_logs.log")

bot = telegram.Bot(token=TOKEN)

def static_handler(command):
    text = open("static_responses/{}.txt".format(command), "r", encoding="utf-8").read()

    return CommandHandler(command,
        lambda update, context: bot.send_message(chat_id=update.message.chat.id, text=text))


def reset_chat_data(context):
    context.bot_data["is_game_pending"] = False
    context.bot_data["pending_players"] = {}
    context.bot_data["game_obj"] = None
    context.bot_data["decks"] = []


def check_game_existence(game, chat_id):
    if game is None:
        text = open("static_responses/game_dne_failure.txt", "r", encoding="utf-8").read()
        bot.send_message(chat_id=chat_id, text=text)
        return False

    return True


def send_hand(chat_id, game, user_id):
    hand = game.get_players().get(user_id).get_formatted_hand()

    bot.send_message(chat_id=user_id,
                     text=hand + "\n",
                     parse_mode = telegram.ParseMode.HTML)


def send_hands(chat_id, game, players):
    for user_id, nickname in players.items():
        send_hand(chat_id, game, user_id)


def newgame_handler(update, context):
    game = context.bot_data.get("game_obj")
    chat_id = update.message.chat.id

    if game is None and not context.bot_data.get("is_game_pending", False):
        reset_chat_data(context)
        context.bot_data["is_game_pending"] = True
        text = open("static_responses/new_game.txt", "r", encoding="utf-8").read()
    elif game is not None:
        text = open("static_responses/game_ongoing.txt", "r", encoding="utf-8").read()
    elif context.bot_data.get("is_game_pending", False):
        text = open("static_responses/game_pending.txt", "r", encoding="utf-8").read()
    else:
        text = "Something has gone horribly wrong!"

    bot.send_message(chat_id=chat_id, text=text)


def is_nickname_valid(name, user_id, context):
    if user_id in context.bot_data.get("pending_players", {}):
        if name.lower() == context.bot_data["pending_players"][user_id].lower():
            return True

    for id, user_name in context.bot_data.get("pending_players", {}).items():
        if name.lower() == user_name.lower():
            return False

    return True


def join_handler(update, context):
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id

    if not context.bot_data.get("is_game_pending", False):
        text = open("static_responses/join_game_not_pending.txt", "r", encoding="utf-8").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    if context.args:
        nickname = " ".join(context.args)
    else:
        nickname = update.message.from_user.first_name

    if is_nickname_valid(nickname, user_id, context):
        context.bot_data["pending_players"][user_id] = nickname
        bot.send_message(chat_id=update.message.chat_id,
                         text="Joined with nickname %s!" % nickname)
        bot.send_message(chat_id=update.message.chat_id,
                         text="Current player count: %d" % len(context.bot_data.get("pending_players", {})))
    else:
        text = open("static_responses/invalid_nickname.txt", "r", encoding="utf-8").read()
        bot.send_message(chat_id=chat_id, text=text)


def leave_handler(update, context):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id

    if not context.bot_data.get("is_game_pending", False):
        text = open("static_responses/leave_game_not_pending_failure.txt", "r", encoding="utf-8").read()
    elif user_id not in context.bot_data.get("pending_players", {}):
        text = open("static_responses/leave_id_missing_failure.txt", "r", encoding="utf-8").read()
    else:
        text = "You have left the current game."
        del context.bot_data["pending_players"][update.message.from_user.id]

    bot.send_message(chat_id=chat_id, text=text)


def listplayers_handler(update, context):
    chat_id = update.message.chat_id
    text = "List of players: \n"
    game = context.bot_data.get("game_obj")

    if context.bot_data.get("is_game_pending", False):
        for user_id, name in context.bot_data.get("pending_players", {}).items():
            text += "%s\n" % name
    elif game is not None:
        for player in game.get_players().values():
            text += "%s\n" % player.get_name()
    else:
        text = open("static_responses/listplayers_failure.txt", "r", encoding="utf-8").read()

    bot.send_message(chat_id=chat_id, text=text)


def feedback_handler(update, context):
    if context.args and len(context.args) > 0:
        feedback = open("feedback.txt\n", "a+", encoding="utf-8")
        feedback.write(update.message.from_user.first_name + "\n")
        feedback.write(str(update.message.from_user.id) + "\n")
        feedback.write(" ".join(context.args) + "\n")
        feedback.close()
        bot.send_message(chat_id=update.message.chat_id, text="Thanks for the feedback!")
    else:
        bot.send_message(chat_id=update.message.chat_id, text="Usage: /feedback [feedback]")


def startgame_handler(update, context):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    pending_players = context.bot_data.get("pending_players", {})

    if not context.bot_data.get("is_game_pending", False):
        text = open("static_responses/start_game_not_pending.txt", "r", encoding="utf-8").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    if user_id not in context.bot_data.get("pending_players", {}).keys():
        text = open("static_responses/start_game_id_missing_failure.txt", "r", encoding="utf-8").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    if len(pending_players) < MIN_PLAYERS:
        text = open("static_responses/start_game_min_threshold.txt", "r", encoding="utf-8").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    try:
        for user_id, nickname in pending_players.items():
            bot.send_message(chat_id=user_id, text="Trying to start game!")
    except Unauthorized as u:
        text = open("static_responses/start_game_failure.txt", "r", encoding="utf-8").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    text = open("static_responses/start_game.txt", "r", encoding="utf-8").read()
    bot.send_message(chat_id=chat_id, text=text)

    chat_id = update.message.chat_id
    pending_players = context.bot_data.get("pending_players", {})
    context.bot_data["is_game_pending"] = False
    decks = [0] if len(context.bot_data["decks"]) == 0 else context.bot_data["decks"]
    context.bot_data["game_obj"] = cah.Game(chat_id, pending_players, decks)
    game = context.bot_data["game_obj"]

    send_hands(chat_id, game, pending_players)


def endgame_handler(update, context):
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    game = context.bot_data.get("game_obj")

    if context.bot_data.get("is_game_pending", False):
        context.bot_data["is_game_pending"] = False
        text = open("static_responses/end_game.txt", "r", encoding="utf-8").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    if game is None:
        text = open("static_responses/game_dne_failure.txt", "r", encoding="utf-8").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    if user_id not in game.get_players():
        text = open("static_responses/end_game_id_missing_failure.txt", "r", encoding="utf-8").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    reset_chat_data(context)
    text = open("static_responses/end_game.txt", "r", encoding="utf-8").read()
    bot.send_message(chat_id=chat_id, text=text)


def play_handler(update, context):
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    game = context.bot_data.get("game_obj")

    if not check_game_existence(game, chat_id):
        return

    if len(context.args) < 1:
        bot.send_message(chat_id=chat_id, text="Usage: /play {card ID 1} {card ID 2} ...")
        return

    num_cards_to_submit = game.get_current_black_card()[0]
    if len(context.args) > num_cards_to_submit:
        bot.send_message(chat_id=chat_id, text="You submitted more cards that necessary (%s)!" % num_cards_to_submit)
        return

    card_ids = [int(c) for c in context.args]

    if any(card_id < 0 or card_id > game.get_deck().get_hand_size() for card_id in card_ids):
        bot.send_message(chat_id=chat_id, text="That's not a valid card ID.")
        return

    game.play(user_id, card_ids)
    send_hand(chat_id, game, user_id)


def choose_handler(update, context):
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    game = context.bot_data.get("game_obj")

    if not check_game_existence(game, chat_id):
        return

    if len(context.args) != 1:
        bot.send_message(chat_id=chat_id, text="Usage: /choose {ID}")
        return

    id = int(context.args[0])

    if game.choose(user_id, id):
        winner = game.check_for_win()
        if not winner:
            game.next_turn()
        else:
            bot.send_message(chat_id=chat_id, text="%s has won!" % winner)
            endgame_handler(update, context)


def blame_handler(update, context):
    chat_id = update.message.chat_id
    game = context.bot_data.get("game_obj")

    if game is None:
        text = open("static_responses/game_dne_failure.txt", "r", encoding="utf-8").read()
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



def add_deck_handler(update, context):
    chat_id = update.message.chat_id

    if not context.bot_data.get("is_game_pending", False):
        text = open("static_responses/add_deck_not_pending.txt", "r", encoding="utf-8").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    if len(context.args) < 1:
        bot.send_message(chat_id=chat_id, text="Usage: /ad {deck IDs from /decks}")
        return

    try:
        decks = [int(d) for d in context.args]
    except ValueError:
        bot.send_message(chat_id=chat_id, text="That is not a valid integer.")
        return

    max_deck = max(list(map(int, DeckEnums)))
    if any(deck < 0 or deck > max_deck for deck in decks):
        bot.send_message(chat_id=chat_id, text="That deck is not in the range [0, %s]!" % max_deck)
        return

    if context.bot_data.get("decks") is None:
        context.bot_data["decks"] = decks
    else:
        context.bot_data["decks"] = list(set(context.bot_data["decks"]).union(set(decks)))
    bot.send_message(chat_id=chat_id, text="Added deck(s) %s!" % decks)


def remove_deck_handler(update, context):
    chat_id = update.message.chat_id

    if not context.bot_data.get("is_game_pending", False):
        text = open("static_responses/remove_deck_not_pending.txt", "r", encoding="utf-8").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    if len(context.args) != 1:
        bot.send_message(chat_id=chat_id, text="Usage: /rd {deck ID from /decks}")
        return

    try:
        deck = int(context.args[0])
    except ValueError:
        bot.send_message(chat_id=chat_id, text="That is not a valid integer.")
        return

    max_deck = max(list(map(int, DeckEnums)))
    if deck < 0 or deck > max_deck:
        bot.send_message(chat_id=chat_id, text="That deck is not in the range [0, %s]!" % max_deck)
        return

    if context.bot_data.get("decks") is None:
        bot.send_message(chat_id=chat_id, text="No decks have been added yet! You can't remove one.")
        return
    else:
        if deck not in context.bot_data["decks"]:
            bot.send_message(chat_id=chat_id, text="That deck has not been added!")
            return
        context.bot_data["decks"].remove(deck)
    bot.send_message(chat_id=chat_id, text="Removed deck %s!" % deck)


def current_decks_handler(update, context):
    chat_id = update.message.chat_id
    game = context.bot_data.get("game_obj")

    if not context.bot_data.get("is_game_pending", False) and game is None:
        text = open("static_responses/current_decks_not_pending.txt", "r", encoding="utf-8").read()
        bot.send_message(chat_id=chat_id, text=text)
        return

    text = "Current Decks:\n\n"
    for i in context.bot_data["decks"]:
        text += "(%s) %s\n" % (i, DECK_NAMES[i])
    bot.send_message(chat_id=chat_id, text=text)


def log_action(update, func_name):
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id

    INFO_LOGGER.info("%s called %s in %s.", user_id, func_name, chat_id)


def handle_error(update, context):
    trace = "".join(traceback.format_tb(sys.exc_info()[2]))
    ERROR_LOGGER.warning("Telegram Error! %s with context error %s caused by this update: %s", trace, context.error, update)


if __name__ == "__main__":
    # Set up the bot
    updater = Updater(token=TOKEN, use_context=True)
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

    commands = [("feedback", feedback_aliases),
                ("newgame", newgame_aliases),
                ("join", join_aliases),
                ("leave", leave_aliases),
                ("listplayers", listplayers_aliases),
                ("startgame", startgame_aliases),
                ("endgame", endgame_aliases),
                ("play", play_aliases),
                ("choose", choose_aliases),
                ("add_deck", add_deck_aliases),
                ("remove_deck", remove_deck_aliases),
                ("blame", blame_aliases),
                ("current_decks", current_decks_aliases)]
    for base_name, aliases in commands:
        func = locals()[base_name + "_handler"]
        dispatcher.add_handler(CommandHandler(aliases, func))
    
    # Error handlers

    dispatcher.add_error_handler(handle_error)

    updater.start_polling()
    updater.idle()