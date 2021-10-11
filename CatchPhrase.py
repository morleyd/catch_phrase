#! /usr/bin/env python

import re
import threading
import time
import curses
from curses.textpad import Textbox
from random import shuffle, randint
from typing import List, Tuple

import requests
from bs4 import BeautifulSoup as bs
from fastDamerauLevenshtein import damerauLevenshtein
from gensim.models import KeyedVectors
from inflect import engine as inflection_engine
from playsound import playsound
from pronouncing import rhymes
from nltk.stem.porter import PorterStemmer

""" Sound Effect Credits:
    point.wav - LittleRobotSoundFactory
    game_over.wav - ProjectsU012
    skip - me
"""


def convert_singular(word: str) -> str:
    """
    plural.singular_noun returns the singular of the given word or None.
    This function modifies that behavior by returning the original word if already singular
    """
    if plural.singular_noun(word):
        return plural.singular_noun(word)
    else:
        return word


def bad_clue(word: str, clue_words: List[str]) -> str:
    """This function returns illegal words in clues or an empty string if it's legal"""
    word_stem = stemmer.stem(word)
    word = word.lower()
    for clue in clue_words:
        # The regex was getting grouchy if there were parentheses in the clue
        clue = re.sub('[()]', '', clue)
        clue_stem = stemmer.stem(clue)
        # Check for same roots (PorterStemmer might be too stringent, but we like a clean game)
        if word_stem == clue_stem:
            return clue
        # Check containment
        if re.search(convert_singular(clue), word) or re.search(convert_singular(word), clue):
            return clue
        # Check plurality
        if not bool(plural.compare(word, clue)):
            # Check rhyming
            if word in set(rhymes(clue)):
                return clue
    return ""


def guesser(clue: List[str]) -> List[str]:
    """This is the driving model of the game. It takes a list of words and returns the most similar"""
    return [guess for guess, _ in model.most_similar(clue, topn=50)]


def generate_guess(clue: List[str], already_guessed: List[str]) -> str:
    """Returns the computer's guess for that try."""
    for guess in guesser(clue):
        guess = guess.lower()
        if not bad_clue(guess, clue):
            if guess not in already_guessed:
                return guess
    return "I'm sorry. I don't know what else to say..."


def display_num(num: int) -> str:
    """Helper function to ensure that all times occupy the same number of character spaces"""
    out = "Time Left: "
    if num < 10:
        return out + "0" + str(num)
    else:
        return out + str(num)


class Play_game:
    def __init__(self, window, total_time: int) -> None:
        self.display = window
        self.time_limit = total_time + 2
        self.score = -1
        self.start_time = time.time()
        self.non_char = re.compile(r'[^\w ]')
        self.HEADER_SPACE = 13
        self.clues: List[str] = []

    def out_of_time(self) -> bool:
        """Helper function to check if the user is within the time limit"""
        return time.time() - self.time_limit >= self.start_time

    def clue_parser(self, clue: str) -> List[str]:
        """Takes string, splits on whitespace, removes non-letter characters, stopwords, oov words, and 'blank'"""
        return [w for w in self.non_char.sub('', clue).split() if w not in stopwords | {'blank'} and w in model.vocab]

    def generate_clues(self, word: str) -> List[str]:
        """Essentially a webscraper for BabelNet. Takes a clue word and returns a list of definitions."""
        page = requests.get(f'https://babelnet.org/search?word={word}&lang=EN').content
        base_soup = bs(page, "html.parser")
        definitions = base_soup.find_all("div", {"class": "definition"})
        clues = []
        for definition in definitions:
            clue = re.sub(word, '<blank>', definition.text.strip().lower())
            if not bad_clue(word, self.clue_parser(clue)):
                clues.append(clue)
        return clues

    def get_input(self) -> str:
        """Helper function to print message and take input from user"""
        console_message = "Your Input: "
        self.display.addstr(11, 0, console_message)
        win = curses.newwin(1, 50, 11, len(console_message))
        self.display.refresh()
        t_box = Textbox(win)
        t_box.edit()
        user_input = t_box.gather()
        return user_input.lower().strip()

    def input_parser(self) -> Tuple[str, bool, bool, bool]:
        """Function for accepting human input. Handles cases of different inputs."""
        playing, guessing, single = True, True, False
        user_input = self.get_input()
        if user_input == 'q':
            playing = False
            guessing = False
        elif user_input == 'y':
            playsound('sound/point.wav')
            self.increase_score()
            guessing = False
        elif user_input == 'n':
            playsound('sound/skip.wav')
            guessing = False
        elif user_input == 's':
            single = True
        return user_input, playing, guessing, single

    def human_give_clues(self) -> bool:
        """Driving function for the part of the game when the user is giving clues."""
        win = curses.newwin(curses.LINES - self.HEADER_SPACE, curses.COLS - 1, self.HEADER_SPACE, 0)
        win.refresh()
        playing = True
        while playing:
            win.clear()  # Important if multiple words are tried
            row = 1
            guess = ''
            all_clues: List[str] = []
            already_guessed: List[str] = []
            word = words.pop()
            win.addstr(0, 0, f'\nYour word is "{word}". Good Luck!')
            win.refresh()
            guessing = True
            while guessing:
                row += 1
                raw_clue, playing, guessing, singular = self.input_parser()
                if self.out_of_time():
                    return False
                if raw_clue == 'y':
                    return playing
                if raw_clue and playing and guessing:
                    clue = self.clue_parser(raw_clue)
                    illegal_word = bad_clue(word, clue)
                    if singular:
                        if guess:
                            all_clues.append(guess)
                            win.addstr(row, 0, f'Is "{convert_singular(guess)}" your word?')
                    elif illegal_word:
                        win.addstr(row, 0, f'Sorry, "{illegal_word}" is an illegal word for a clue. Try again.\n')
                    elif not clue:
                        win.addstr(row, 0, f'Please enter a valid clue.\n')
                    else:
                        all_clues += clue
                        guess = generate_guess(all_clues, already_guessed)
                        win.addstr(row, 0, f'Is "{guess}" your word?')
                        already_guessed.append(guess)
                if row + self.HEADER_SPACE >= curses.LINES - 2:  # Keep the guesses from extending beyond screen
                    row = 1
                    win.clear()
                    win.addstr(0, 0, f'\nYour word is "{word}". Good Luck!')
                win.refresh()
        return playing

    def clue_popper(self) -> str:
        """Helper function to give the user clues. Prevents a crash when there are no clues left (empty list)"""
        if self.clues:
            clue = self.clues.pop()
            return clue
        else:
            return "I'm out of clues!"

    def computer_give_clues(self) -> bool:
        """Driving function for the part of the game when the computer is giving clues."""
        win = curses.newwin(curses.LINES - self.HEADER_SPACE, curses.COLS - 1, self.HEADER_SPACE, 0)
        win.refresh()
        playing = True
        while playing:
            win.clear()  # Important if multiple words are tried
            row = 1
            win.addstr(0, 0, "Let me think of a clue....")
            win.refresh()
            word = words.pop()
            self.clues = self.generate_clues(word)
            clue = self.clue_popper()
            win.addstr(row, 0, clue)
            win.refresh()
            guessing = True
            while guessing:
                row += 1
                guess, playing, guessing, _ = self.input_parser()
                if self.out_of_time():
                    return False
                if not (playing and guessing):
                    message = f"The word was {word}!"
                    center_col = (curses.COLS - len(message)) // 2
                    self.display.addstr(curses.LINES - 1, center_col, message)
                else:
                    similarity = damerauLevenshtein(word, guess, True)
                    if similarity == 1:
                        playsound('sound/point.wav')
                        self.increase_score()
                        win.addstr(row, 0, "Correct!")
                        return playing
                    elif similarity >= 0.75:
                        win.addstr(row, 0, 'You are just a couple of letters off. Try Again!')
                    else:
                        win.addstr(row, 0, 'Try Again!')
                        win.refresh()
                        row += 1
                        clue = self.clue_popper()
                        win.addstr(row, 0, clue)
                if row + self.HEADER_SPACE >= curses.LINES - 2:  # Keep the guesses from extending beyond screen
                    row = 1
                    win.clear()
                win.refresh()
        return playing

    def increase_score(self):
        """Helper function to increase score on the screen"""
        self.score += 1
        self.display.addstr(10, 30, f'Score = {self.score}')

    def play_game(self) -> int:
        """Starts the game and stops it when the user is done."""
        self.increase_score()
        playing = True
        while playing:
            playing = self.human_give_clues()
            if playing:
                playing = self.computer_give_clues()
        return self.score


class Clock(threading.Thread):
    """ Clock curses string class. Updates every second."""

    def __init__(self, window, total_time) -> None:
        """ Create the clock """
        super(Clock, self).__init__()
        self.time = total_time
        self._target = self.count_down
        self.daemon = True
        self.display = window
        self.start()

    def count_down(self) -> None:
        """The actual count down function"""
        ticker = self.time
        while ticker:
            self.display.addstr(10, 1, display_num(ticker - 1))
            self.display.refresh()
            time.sleep(1)
            ticker -= 1
        playsound('sound/game_over.wav')


def print_starter(w) -> None:
    """Function to print starter text"""
    w.addstr(0, 0, "\n  ██████╗ █████╗ ████████╗ ██████╗██╗  ██╗    ██████╗ ██╗  ██╗██████╗  █████╗ ███████╗███████╗\n")
    w.addstr(" ██╔════╝██╔══██╗╚══██╔══╝██╔════╝██║  ██║    ██╔══██╗██║  ██║██╔══██╗██╔══██╗██╔════╝██╔════╝\n")
    w.addstr(" ██║     ███████║   ██║   ██║     ███████║    ██████╔╝███████║██████╔╝███████║███████╗█████╗\n")
    w.addstr(" ██║     ██╔══██║   ██║   ██║     ██╔══██║    ██╔═══╝ ██╔══██║██╔══██╗██╔══██║╚════██║██╔══╝\n")
    w.addstr(" ╚██████╗██║  ██║   ██║   ╚██████╗██║  ██║    ██║     ██║  ██║██║  ██║██║  ██║███████║███████╗\n")
    w.addstr("  ╚═════╝╚═╝  ╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝    ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝\n")
    w.addstr('Welcome to the Catch Phrase Simulation!\n')
    w.addstr('Enter q at anytime to quit, y if the word is correct, n to get a new word, and s to convert to singular.')
    w.addstr('\n')
    w.refresh()


def continue_playing(window) -> bool:
    """Asks user if they want to continue playing and accepts their input"""
    # Clear last line and add ending text
    window.move(curses.LINES - 1, 0)
    window.clrtoeol()
    game_over = "You ran out of time. Continue Playing? (y/n)"
    center_col = (curses.COLS - len(game_over)) // 2
    window.addstr(curses.LINES - 1, center_col, game_over)
    input_message = "Your Input: "
    window.addstr(11, 0, input_message)
    win = curses.newwin(1, 50, 11, len(input_message))
    window.refresh()
    t_box = Textbox(win)
    t_box.edit()
    message = t_box.gather()
    if 'y' in message.lower():
        return True
    return False


def run(window) -> None:
    """ Main Function """
    print_starter(window)
    new_round = True
    score = 0
    while new_round:
        total_time = randint(60, 99)
        Clock(window, total_time)
        game = Play_game(window, total_time)
        score += game.play_game()
        window.refresh()
        new_round = continue_playing(window)
    print(f"\nThanks for playing! Your Score was {score}!")


if __name__ == '__main__':
    curses_window = curses.initscr()
    # Build the various models
    model = KeyedVectors.load_word2vec_format('data/GoogleNews-vectors-negative300.bin.gz', binary=True, limit=200000)
    with open("data/catchphrase_words.txt", encoding='utf8') as file:
        words = [w.strip() for w in file]
        shuffle(words)
    with open("data/stopwords.txt", encoding='utf8') as file:
        stopwords = {w.strip() for w in file}
    plural = inflection_engine()
    stemmer = PorterStemmer()
    # Start the gameplay
    curses.wrapper(run)
