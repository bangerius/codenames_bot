from collections.abc import Callable, Generator
from enum import StrEnum
from random import shuffle


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
    print("Correct words: " + ", ".join(game_board.get_correct_words(player_perspective=Player.PLAYER1)))
    print("Incorrect words: " + ", ".join(game_board.get_incorrect_words(player_perspective=Player.PLAYER1)))
    print("Assassin words: " + ", ".join(game_board.get_assassin_words(player_perspective=Player.PLAYER1)))

def word_producer():
    with open("word_list.txt", "r") as file:
        words = [line.strip() for line in file.readlines()]
    shuffle(words)
    yield from words

def make_game_board(width: int = 5, height: int = 5, word_producer: Callable = word_producer) -> list[list[str]]:
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
    player1_colors = [CellRole.ASSASSIN] + [CellRole.BYSTANDER] * 5 + [CellRole.SPY] * 9 + [CellRole.BYSTANDER] + [CellRole.ASSASSIN] + [CellRole.BYSTANDER] * 7 + [CellRole.ASSASSIN]
    player2_colors = [CellRole.SPY] * 9 + [CellRole.BYSTANDER] * 5 + [CellRole.ASSASSIN] * 3 + [CellRole.BYSTANDER] * 8
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
    def __init__(self, width: int, height: int, word_producer: Callable = word_producer, color_producer: Callable = color_producer):
        self.width = width
        self.height = height
        self.word_producer = word_producer()
        self.color_producer = color_producer()
        self.cells = [[GameCell(next(self.word_producer), *next(self.color_producer)) for _ in range(width)] for _ in range(height)]

    def print_game_board(self, player_perspective: Player = Player.PLAYER1):
        max_widths = [max(len(game_cell.word)+2 for game_cell in column) for column in zip(*self.cells)]
        total_width = sum(max_widths) + len(max_widths) + 1
        print("-" * total_width)
        for row in self.cells:
            print("|", end="")
            for col, game_cell in enumerate(row):
                word = game_cell.word
                color = game_cell.player1_color if player_perspective == Player.PLAYER1 else game_cell.player2_color
                padding = max_widths[col]-len(word)
                to_print = " "* max(1,(padding // 2)) + game_cell.colored_word(player_perspective) + " "* max(1,(padding - padding // 2))
                print(to_print, end="|")
            print()
            print("-" * total_width)
        print()
    
    def get_correct_words(self, player_perspective: Player) -> list[str]:
        return [game_cell.word for row in self.cells for game_cell in row if game_cell.p_color(player_perspective) == CellRole.SPY]

    def get_incorrect_words(self, player_perspective: Player) -> list[str]:
        return [game_cell.word for row in self.cells for game_cell in row if game_cell.p_color(player_perspective) == CellRole.BYSTANDER]

    def get_assassin_words(self, player_perspective: Player) -> list[str]:
        return [game_cell.word for row in self.cells for game_cell in row if game_cell.p_color(player_perspective) == CellRole.ASSASSIN]


if __name__ == "__main__":
    main()
