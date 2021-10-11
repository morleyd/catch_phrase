# catch_phrase
## Background
A textbased videogame version of the Hasbro party game [Catch Phrase](https://en.wikipedia.org/wiki/Catch_Phrase_(game))!
In standard gameplay, the party is divided into two teams, and players take turns trying to get their team to guess a random word. Players can use any clue except those that contain:

* Words that rhyme with any target words
* Information about the first letter of the target word
* Information about the number of syllables in the target word
* Words that contain part of the target word
	
Like Hot Potato, teams get points by not being in the clue-giver role when the timer goes out. This induces pressure to provide quality clues quickly. Each player takes turns being the clue giving and clue receiving (guessing) roles. 

This work focuses on the attempts to make a computer playable opponent for CatchPhrase. This opponent imitates the different roles that humans assume while playing the game. 

## Setup
### Virtual Environment
Clone this repository, create a virtual environment, and install the Python requirements:
```
$ python -m venv catch_phrase
...
$ source catch_phrase/bin/activate
(catch_phrase) $ pip install -r requirements.txt
...
```
Note: This process is slightly altered on a Windows system. I had best results when running the project in a PowerShell based terminal where you activate the virtual environment with `.\catch_phrase\Scripts\Activate.ps1`.
### Word2Vec Download
This project is dependent on `GoogleNews-vectors-negative300.bin.gz`, a dataset of pre-trained vectors trained on part of Google News dataset (about 100 billion words). For more information and download, go to https://code.google.com/archive/p/word2vec/. Once downloaded, please place the file in the `data/` directory.

## Game Play
This repository contains two versions of the game. A light version `CatchPhrase_base.py` and the full version, `CatchPhrase.py`. The main difference between the two files is that the full version uses `curses` to create a new gameplay window within the user's terminal for added gameplay features (like sound effects!).

For either version, run `python <filename>` or `./<filename>`. Once it loads, the system will rotate back and forth between guessing and giving clues. First, the user will be given a word to get the computer to guess. Any natural language clue may be entered, but illegal clues (like those that contain the target word) will be rejected. The system remembers past entries and averages their respective word vectors to find the nearest related word. Certain keyphrases are accepted to signal information to the system:
* `q` - Press at any time to quit
* `y` - Correct word
* `n` - Skip word
* `s` - Change the form of the word to singular

These commands still apply (where relevant) for the next phase where the system gives clues. During this phase, the user's job is to enter their guess. Each incorrect guess will be rewarded with a new clue supplied by [BabelNet](https://babelnet.org/search).

Enjoy!
