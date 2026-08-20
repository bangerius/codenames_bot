from collections.abc import Callable, Generator
from enum import StrEnum
from itertools import combinations
import os
from random import shuffle
from typing import cast

import gensim.downloader as api
from gensim.models.keyedvectors import KeyedVectors


class CellRole(StrEnum):
    SPY = "green"
    BYSTANDER = "neutral"
    ASSASSIN = "assassin"


class CellState(StrEnum):
    UNTESTED = "untested"
    INCORRECT = "incorrect"
    CORRECT = "correct"
    GAME_OVER = "game_over"


COLOR_MAP = {
    CellRole.SPY: "\033[92m",
    CellRole.BYSTANDER: "\033[93m",
    CellRole.ASSASSIN: "\033[91m",
}


class Player(StrEnum):
    PLAYER1 = "player1"
    PLAYER2 = "player2"


def main():
    width = 5
    height = 5
    word_gen = word_producer
    color_gen = color_producer
    game_board = GameBoard(width, height, word_gen, color_gen)
    game_board.print_game_board(player_perspective=Player.PLAYER1)
    # print("Correct words: " + ", ".join(game_board.get_correct_words(player_perspective=Player.PLAYER1)))
    # print("Incorrect words: " + ", ".join(game_board.get_incorrect_words(player_perspective=Player.PLAYER1)))
    # print("Assassin words: " + ", ".join(game_board.get_assassin_words(player_perspective=Player.PLAYER1)))
    bot = HintBot()
    hint = bot.get_hint(
        correct_words=game_board.get_correct_words(player_perspective=Player.PLAYER1),
        incorrect_words=game_board.get_incorrect_words(player_perspective=Player.PLAYER1),
        assassin_words=game_board.get_assassin_words(player_perspective=Player.PLAYER1),
        target_n_words=3,
    )
    print(f"Suggested hints: {hint}")


def word_producer():
    with open("word_list.txt", "r") as file:
        words = [line.strip().lower() for line in file.readlines() if " " not in line.strip()]
    shuffle(words)
    yield from words


def make_game_board(
    width: int = 5, height: int = 5, word_producer: Callable = word_producer
) -> list[list[str]]:
    game_board = []
    for i in range(height):
        row = []
        for j in range(width):
            if word_producer:
                row.append(word_producer())
            else:
                row.append(f"Word {i * width + j + 1}")
        game_board.append(row)
    return game_board


def color_producer() -> Generator[tuple[CellRole, CellRole], None, None]:
    player1_colors = (
        [CellRole.ASSASSIN]
        + [CellRole.BYSTANDER] * 5
        + [CellRole.SPY] * 9
        + [CellRole.BYSTANDER]
        + [CellRole.ASSASSIN]
        + [CellRole.BYSTANDER] * 7
        + [CellRole.ASSASSIN]
    )
    player2_colors = (
        [CellRole.SPY] * 9
        + [CellRole.BYSTANDER] * 5
        + [CellRole.ASSASSIN] * 3
        + [CellRole.BYSTANDER] * 8
    )
    joint_colors = list(zip(player1_colors, player2_colors))
    shuffle(joint_colors)
    yield from joint_colors


class GameCell:
    def __init__(self, word: str, player1_color: CellRole, player2_color: CellRole):
        self.word = word
        self.player1_color = player1_color
        self.player2_color = player2_color
        self.state = CellState.UNTESTED

    def colored_word(self, player_perspective: Player) -> str:
        if player_perspective == Player.PLAYER1:
            return f"{COLOR_MAP[self.player1_color]}{self.word}\033[0m"
        elif player_perspective == Player.PLAYER2:
            return f"{COLOR_MAP[self.player2_color]}{self.word}\033[0m"
        else:
            return self.word

    def p_color(self, player_perspective: Player) -> CellRole:
        if player_perspective == Player.PLAYER1:
            return self.player1_color
        elif player_perspective == Player.PLAYER2:
            return self.player2_color
        else:
            raise ValueError("Invalid player perspective. Must be PLAYER1 or PLAYER2.")

    def guess(self, player_perspective: Player):
        if player_perspective == Player.PLAYER1:
            if self.player1_color == CellRole.SPY:
                self.state = CellState.CORRECT
            elif self.player1_color == CellRole.ASSASSIN:
                self.state = CellState.GAME_OVER
            elif self.player1_color == CellRole.BYSTANDER:
                self.state = CellState.INCORRECT
            else:
                raise ValueError("Invalid color for player 1.")
        elif player_perspective == Player.PLAYER2:
            if self.player2_color == CellRole.SPY:
                self.state = CellState.CORRECT
            elif self.player2_color == CellRole.ASSASSIN:
                self.state = CellState.GAME_OVER
            elif self.player2_color == CellRole.BYSTANDER:
                self.state = CellState.INCORRECT
            else:
                raise ValueError("Invalid color for player 2.")
        else:
            raise ValueError("Invalid player perspective. Must be PLAYER1 or PLAYER2.")


class GameBoard:
    def __init__(
        self,
        width: int,
        height: int,
        word_producer: Callable = word_producer,
        color_producer: Callable = color_producer,
    ):
        self.width = width
        self.height = height
        self.word_producer = word_producer()
        self.color_producer = color_producer()
        self.cells = [
            [GameCell(next(self.word_producer), *next(self.color_producer)) for _ in range(width)]
            for _ in range(height)
        ]

    def print_game_board(self, player_perspective: Player = Player.PLAYER1):
        max_widths = [
            max(len(game_cell.word) + 2 for game_cell in column) for column in zip(*self.cells)
        ]
        total_width = sum(max_widths) + len(max_widths) + 1
        print("-" * total_width)
        for row in self.cells:
            print("|", end="")
            for col, game_cell in enumerate(row):
                word = game_cell.word
                padding = max_widths[col] - len(word)
                to_print = (
                    " " * max(1, (padding // 2))
                    + game_cell.colored_word(player_perspective)
                    + " " * max(1, (padding - padding // 2))
                )
                print(to_print, end="|")
            print()
            print("-" * total_width)
        print()

    def get_correct_words(self, player_perspective: Player) -> list[str]:
        return [
            game_cell.word
            for row in self.cells
            for game_cell in row
            if game_cell.p_color(player_perspective) == CellRole.SPY
        ]

    def get_incorrect_words(self, player_perspective: Player) -> list[str]:
        return [
            game_cell.word
            for row in self.cells
            for game_cell in row
            if game_cell.p_color(player_perspective) == CellRole.BYSTANDER
        ]

    def get_assassin_words(self, player_perspective: Player) -> list[str]:
        return [
            game_cell.word
            for row in self.cells
            for game_cell in row
            if game_cell.p_color(player_perspective) == CellRole.ASSASSIN
        ]


class HintBot:
    def __init__(self, model_name: str = "fasttext-wiki-news-subwords-300", settings: dict = {}):
        default_settings = {
            "debug_level": 1,  # 0 = no debug output, 1 = some debug output, 2 = verbose debug output
            "max_suggestions_from_model": 64,  # Maximum number of suggestions to retrieve from the model before giving up on finding a valid hint
            "assassin_penalty": 5,  # Penalty multiplier for assassin words when calculating the negative vector
            "correct_boost": 1.5,  # Boost multiplier for correct words when calculating the combined vector for the hint
        }
        self.settings = {**default_settings, **settings}
        binary_path = f"{model_name}.bin"
        if not os.path.exists(binary_path):
            print("Loading raw model for the first time...")
            self.model = cast(KeyedVectors, api.load(model_name))
            self.model.sort_by_descending_frequency()
            # Save as a tight binary format
            self.model.save_word2vec_format(binary_path, binary=True)
        else:
            print("Loading model from binary file...")
            self.model = KeyedVectors.load_word2vec_format(binary_path, binary=True)

    def log(self, message: str, level: int = 1):
        if self.settings["debug_level"] >= level:
            print(message)

    def get_hint(
        self,
        correct_words: list[str],
        incorrect_words: list[str],
        assassin_words: list[str],
        target_n_words: int = 3,
    ) -> str:
        target_words = self.choose_best_collection(correct_words, assassin_words, target_n_words)
        self.log(f"Chose word subset for hint: {target_words}", 1)
        hints = self.construct_hint(target_words, incorrect_words, assassin_words)
        self.log(f"Suggested hints: {hints}", 1)
        return hints[0]

    def choose_best_collection(
        self, correct_words: list[str], assassin_words: list[str], n: int
    ) -> list[str]:
        if n <= 0:
            return []
        subsets = [list(subset) for subset in combinations(correct_words, n)]
        assassin_vectors = [self.model.get_vector(b) for b in assassin_words]
        best_subset = None
        best_score = float("-inf")
        for subset in subsets:
            vectors = [self.model.get_vector(b) for b in subset]
            score = sum(
                sum(self.model.cosine_similarities(vectors[i], vectors[:i] + vectors[i + 1 :]))
                for i in range(len(vectors))
            )
            assassin_score = sum(
                sum(self.model.cosine_similarities(vectors[i], assassin_vectors))
                for i in range(len(vectors))
            )
            total_score = score - assassin_score
            if total_score > best_score:
                self.log(f"New best subset found: {subset} with score {total_score}", 2)
                best_score = total_score
                best_subset = subset

        return best_subset if best_subset is not None else subsets[0] if subsets else []

    def construct_hint(
        self,
        target_words: list[str],
        incorrect_words: list[str],
        assassin_words: list[str],
        start_top_n: int = 4,
    ) -> list[str]:
        max_n = self.settings["max_suggestions_from_model"]
        assassin_penalty = self.settings["assassin_penalty"]
        correct_boost = self.settings["correct_boost"]
        top_n = start_top_n

        options = []
        positive_vector = sum(self.model.get_vector(w) for w in target_words) / len(target_words)
        negative_vector = (
            sum(self.model.get_vector(w) for w in assassin_words) * assassin_penalty
            + sum(self.model.get_vector(w) for w in incorrect_words)
        ) / (len(assassin_words) * assassin_penalty + len(incorrect_words))
        while top_n < max_n:
            suggestions = [
                w.lower()
                for w, _ in self.model.most_similar(
                    positive=positive_vector * correct_boost, negative=negative_vector, topn=top_n
                )
            ]
            for suggestion in suggestions:
                ok = True
                for word in target_words + incorrect_words + assassin_words:
                    if word in suggestion:
                        ok = False
                        break
                if ok:
                    options.append(suggestion)
            if len(options) >= 1:
                break
            print(
                f"No valid suggestions found with topn={top_n} (suggestions: {suggestions}), increasing topn..."
            )
            top_n *= 2
        return options


if __name__ == "__main__":
    main()
