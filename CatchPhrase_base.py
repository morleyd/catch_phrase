#! /usr/bin/env python

import re
import requests
import sys
from bs4 import BeautifulSoup as bs
from fastDamerauLevenshtein import damerauLevenshtein
from gensim.models import KeyedVectors
from inflect import engine as inflection_engine
from pronouncing import rhymes
from random import shuffle
from nltk.stem.porter import PorterStemmer
from typing import List, Tuple


def print_name() -> None:
    title = """
     ██████╗ █████╗ ████████╗ ██████╗██╗  ██╗    ██████╗ ██╗  ██╗██████╗  █████╗ ███████╗███████╗
    ██╔════╝██╔══██╗╚══██╔══╝██╔════╝██║  ██║    ██╔══██╗██║  ██║██╔══██╗██╔══██╗██╔════╝██╔════╝
    ██║     ███████║   ██║   ██║     ███████║    ██████╔╝███████║██████╔╝███████║███████╗█████╗  
    ██║     ██╔══██║   ██║   ██║     ██╔══██║    ██╔═══╝ ██╔══██║██╔══██╗██╔══██║╚════██║██╔══╝  
    ╚██████╗██║  ██║   ██║   ╚██████╗██║  ██║    ██║     ██║  ██║██║  ██║██║  ██║███████║███████╗
     ╚═════╝╚═╝  ╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝    ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝
    """
    print(title)
    print('Welcome to the Catch Phrase Simulation!')
    print('Enter q at anytime to quit, y/n to get a new word, and s to convert to singular.')


def convert_singular(word: str) -> str:
    """
    plural.singular_noun returns the singular of the given word or None.
    This function modifies that behavior by returning the original word if already singular
    """
    if plural.singular_noun(word):
        return plural.singular_noun(word)
    else:
        return word


def clue_parser(clue: str) -> List[str]:
    """Takes string, splits on whitespace, removes non-letter characters, stopwords, oov words, and 'blank'"""
    non_char = re.compile(r'[^\w ]')
    return [w for w in non_char.sub('', clue).split() if w not in stopwords | {'blank'} and w in model.vocab]


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
        if not bad_clue(guess, clue):
            if guess not in already_guessed:
                return guess
    return "I'm sorry. I don't know what else to say..."


def generate_clues(word: str) -> List[str]:
    """Essentially a webscraper for BabelNet. Takes a clue word and returns a list of definitions."""
    page = requests.get(f'https://babelnet.org/search?word={word}&lang=EN').content
    base_soup = bs(page, "html.parser")
    definitions = base_soup.find_all("div", {"class": "definition"})
    clues = []
    for definition in definitions:
        clue = re.sub(word, '<blank>', definition.text.strip().lower())
        if not bad_clue(word, clue_parser(clue)):
            clues.append(clue)
    return clues


def input_parser(human_guessing: bool) -> Tuple[str, bool, bool, bool]:
    """Function for accepting human input. Handles cases of different inputs."""
    playing, guessing, single = True, True, False
    if human_guessing:
        user_input = input("Please enter your clue now: ").lower()
    else:
        user_input = input("Your guess: ").lower()

    if user_input == 'q':
        playing = False
        guessing = False
    elif user_input in ('y', 'n'):
        guessing = False
    elif user_input == 's':
        single = True
    return user_input, playing, guessing, single


def human_give_clues() -> bool:
    """Driving function for the part of the game when the user is giving clues."""
    guessing = True
    playing = True
    word = words.pop()
    guess = ''
    all_clues: List[str] = []
    already_guessed: List[str] = []
    print(f'\nYour word is "{word}". Good Luck!')
    while guessing:
        raw_clue, playing, guessing, singular = input_parser(True)
        if playing and guessing:
            clue = clue_parser(raw_clue)
            illegal_word = bad_clue(word, clue)
            if illegal_word:
                print(f'Sorry, "{illegal_word}" is an illegal word for a clue. Try again.\n')
            elif singular:
                if guess:
                    all_clues.append(guess)
                    print(f'Is "{convert_singular(guess)}" your word?')
            else:
                all_clues += clue
                guess = generate_guess(all_clues, already_guessed)
                print(f'Is "{guess}" your word?')
                already_guessed.append(guess)
    return playing


def computer_give_clues() -> bool:
    """Driving function for the part of the game when the computer is giving clues."""
    guessing = True
    playing = True
    print('\nMy turn to give a clue!')
    # This fun line disappears once the first clue has been given
    sys.stdout.write("\rLet me think....")
    sys.stdout.flush()

    word = words.pop()
    clues = generate_clues(word)
    clue = clues.pop(0)
    sys.stdout.write("\r")
    sys.stdout.write(f"{clue}\n")
    while guessing:
        guess, playing, guessing, _ = input_parser(False)
        if not (playing and guessing):
            print(f"The word was {word}!")
        else:
            similarity = damerauLevenshtein(word, guess, True)
            if similarity == 1:
                guessing = False
                print("Correct!")
            elif similarity >= 0.75:
                print('You are just a couple of letters off. Try Again!')
            else:
                print('Try Again!')
                clue = clues.pop(0)
                print(clue)
    return playing


def play_game() -> None:
    print_name()
    playing = True
    while playing:
        playing = human_give_clues()
        if playing:
            playing = computer_give_clues()

    print(f"\nThanks for playing!")


if __name__ == '__main__':
    print("...wait for it...")
    # Build the various models
    model = KeyedVectors.load_word2vec_format('data/GoogleNews-vectors-negative300.bin.gz', binary=True, limit=200000)
    with open("data/catchphrase_words.txt", encoding='utf8') as file:
        words = [w.strip() for w in file]
        shuffle(words)
    with open("data/stopwords.txt", encoding='utf8') as file:
        stopwords = {w.strip() for w in file}
    plural = inflection_engine()
    stemmer = PorterStemmer()

    play_game()
