import os
import argparse
import curses
import dataclasses
import enum
import random
import time
import typing


KEY_H = ord('h')
KEY_J = ord('j')
KEY_K = ord('k')
KEY_L = ord('l')

TIC = 1 / 6
TIC_PER_BODY = 0.1
BORDER = 0


@enum.unique
class Color(enum.Enum):
    BLACK = enum.auto()
    RED = enum.auto()
    GREEN = enum.auto()
    YELLOW = enum.auto()
    BLUE = enum.auto()
    MAGENTA = enum.auto()
    CYAN = enum.auto()
    WHITE = enum.auto()


Window = curses.window


def init_colors() -> None:
    bg_color = curses.A_NORMAL
    color_pairs = (
        (Color.RED, curses.COLOR_RED),
        (Color.GREEN, curses.COLOR_GREEN),
        (Color.YELLOW, curses.COLOR_YELLOW),
        (Color.BLUE, curses.COLOR_BLUE),
        (Color.CYAN, curses.COLOR_CYAN),
        (Color.WHITE, curses.COLOR_WHITE),
        (Color.MAGENTA, curses.COLOR_MAGENTA),
    )
    curses.start_color()
    for enum_color, fg_color in color_pairs:
        curses.init_pair(enum_color.value, fg_color, bg_color)


def init_window() -> Window:
    window = curses.initscr()
    window.keypad(True)
    window.nodelay(True)
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)
    return window


def get_window_max_yx(window: Window) -> tuple[int, int]:
    max_y, max_x = window.getmaxyx()
    return max_y - 1, max_x - 1


@enum.unique
class Direction(enum.Enum):
    UP = enum.auto()
    DOWN = enum.auto()
    LEFT = enum.auto()
    RIGHT = enum.auto()

    @classmethod
    def horizontal(cls) -> set['Direction']:
        return {cls.LEFT, cls.RIGHT}

    @classmethod
    def vertical(cls) -> set['Direction']:
        return {cls.UP, cls.DOWN}

    def is_opposite(self, other: 'Direction') -> bool:
        if not isinstance(other, Direction):
            raise TypeError(
                f'Expected type: {self.__class__!r}, '
                f'not {other.__class__!r}'
            )
        return any([
            self == Direction.UP and other == Direction.DOWN,
            self == Direction.DOWN and other == Direction.UP,
            self == Direction.LEFT and other == Direction.RIGHT,
            self == Direction.RIGHT and other == Direction.LEFT,
        ])


@dataclasses.dataclass(slots=True, eq=True, repr=False)
class Coord():
    y: int
    x: int

    def __add__(self, other: 'Coord') -> 'Coord':
        return Coord(self.y + other.y, self.x + other.x)

    def __sub__(self, other: 'Coord') -> 'Coord':
        return Coord(self.y - other.y, self.x - other.x)

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, Coord):
            raise TypeError(
                f'Expected type: {self.__class__!r}, '
                f'not {other.__class__!r}'
            )
        return self.y == other.y and self.x == other.x

    def __repr__(self) -> str:
        return f'<{self.y}, {self.x}>'

    def __bool__(self) -> bool:
        return self.y != 0 and self.x != 0

    def copy(self) -> 'Coord':
        return Coord(self.y, self.x)

    @classmethod
    def random_inside_window(
            cls,
            window: Window,
            border: int = BORDER,
    ) -> 'Coord':
        max_y, max_x = get_window_max_yx(window)
        y = random.randint(border, max_y - border)
        x = random.randint(border, max_x - border)
        return cls(y, x)

    @classmethod
    def from_direction(cls, direction: Direction) -> 'Coord':
        coord = cls(0, 0)
        if direction == Direction.UP:
            coord.y -= 1
        elif direction == Direction.DOWN:
            coord.y += 1
        elif direction == Direction.LEFT:
            coord.x -= 1
        elif direction == Direction.RIGHT:
            coord.x += 1
        return coord


Snake = list[Coord]


@dataclasses.dataclass(slots=True, eq=True, repr=False)
class Food():
    image: str
    coord: Coord
    color: Color

    @staticmethod
    def random_outside_snake(window: Window, snake: Snake) -> Coord:
        border = 5
        while True:
            coord = Coord.random_inside_window(window, border)
            if coord in snake:
                continue
            return coord

    @classmethod
    def create_random_food(cls, window: Window, snake: Snake) -> 'Food':
        image = random.choice('%$#№8')
        color = random.choice([
            Color.RED,
            Color.YELLOW,
            Color.GREEN,
            Color.WHITE,
        ])
        return cls(
            image=image,
            coord=cls.random_outside_snake(window, snake),
            color=color,
        )


def get_direction(window: Window) -> Direction | None:
    keys2direction = {
        (curses.KEY_UP, KEY_K): Direction.UP,
        (curses.KEY_DOWN, KEY_J): Direction.DOWN,
        (curses.KEY_RIGHT, KEY_L): Direction.RIGHT,
        (curses.KEY_LEFT, KEY_H): Direction.LEFT,
    }
    key = window.getch()
    for keys, direction in keys2direction.items():
        if key in keys:
            return direction
    return None


def snake_draw(window: Window, snake: Snake) -> None:
    head, body = snake[0], snake[1:]
    for part in body:
        draw(window, part, '0', Color.BLUE)
    draw(window, head, '@', Color.BLUE)


def snake_move(snake: Snake, direction: Direction, can_grow: bool) -> None:
    head = snake[0] + Coord.from_direction(direction)
    if head == snake[0]:
        return
    snake.insert(0, head)
    if can_grow:
        return
    snake.pop(-1)


def draw(
        window: Window,
        coord: Coord,
        text: str,
        color: Color = Color.WHITE,
) -> None:
    try:
        window.addstr(coord.y, coord.x, text, curses.color_pair(color.value))
    except curses.error:
        pass


def food_draw(window: Window, food: Food) -> None:
    draw(window, food.coord, food.image, food.color)


def get_window_center(window: Window) -> Coord:
    max_y, max_x = get_window_max_yx(window)
    return Coord(max_y // 2, max_x // 2)


def can_eat_food(snake: Snake, food: Food) -> bool:
    return snake[0] == food.coord


def debug(
        window: Window,
        snake: Snake,
        food: Food,
        direction: Direction,
) -> None:
    text = f'{direction!r} {food.coord!r} {snake!r}'
    draw(window, Coord(0, 0), text, Color.MAGENTA)


def can_go_further(
        window: Window,
        snake: Snake,
        direction: Direction,
) -> bool:
    next_head_coord = snake[0] + Coord.from_direction(direction)
    max_y, max_x = get_window_max_yx(window)
    return not any([
        next_head_coord.y < BORDER,
        next_head_coord.y > max_y - BORDER,
        next_head_coord.x < BORDER,
        next_head_coord.x > max_x - BORDER,
        next_head_coord in snake,
    ])


def game_over(window: Window) -> None:
    center = get_window_center(window)
    title, title_coord = 'GAME OVER', center.copy()
    description, description_coord = 'press any key to exit', center.copy()
    title_coord.x -= (len(title) // 2)
    description_coord.x -= (len(description) // 2)
    description_coord.y += 1
    window.clear()
    window.nodelay(False)
    draw(window, title_coord, title, Color.RED)
    draw(window, description_coord, description, Color.WHITE)
    while True:
        if window.getch():
            break
        time.sleep(0.01)


def calculate_frame_timeout(snake: Snake, direction: Direction) -> float:
    """Speed up game if snake becomes longer and longer."""
    horizontal_correction = 0.5 if direction in Direction.horizontal() else 1
    # snake_size_correction = (1 / 20) * len(snake)
    snake_size_correction = 1 / (len(snake) * 2)
    return TIC * horizontal_correction + snake_size_correction


class Game:
    def __init__(
            self,
            snake: Snake,
            food: Food,
            init_direction: Direction,
            debug: bool,
    ) -> None:
        self.snake = snake
        self.food = food
        self.direction = init_direction
        self.debug = debug

    @classmethod
    def from_curses_window(cls, window: Window, debug: bool) -> 'Game':
        center_coord = get_window_center(window)
        snake: Snake = [center_coord]
        food: Food = Food.create_random_food(window, snake)
        direction: Direction = Direction.DOWN
        return cls(snake, food, direction, debug)

    def main_loop(self, window: Window) -> None:
        while True:
            # control
            # get controls
            if new_direction := get_direction(window):
                # disallow snake to go backwards
                if not new_direction.is_opposite(self.direction):
                    self.direction = new_direction

            # model
            # change state of models
            can_grow = False
            if can_eat_food(self.snake, self.food):
                can_grow = True
                self.food = Food.create_random_food(window, self.snake)

            snake_move(self.snake, self.direction, can_grow)

            if not can_go_further(window, self.snake, self.direction):
                break  # game over

            # view
            # draw all elements
            window.clear()
            window.nodelay(True)
            snake_draw(window, self.snake)
            food_draw(window, self.food)
            if self.debug:
                debug(window, self.snake, self.food, self.direction)
            window.refresh()

            timeout = calculate_frame_timeout(self.snake, self.direction)
            time.sleep(timeout)

        game_over(window)


def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='snake.py',
        description='Terminal snake game',
        epilog='Have fun!'
    )
    parser.add_argument('--debug', action='store_true')
    return parser.parse_args()


if __name__ == '__main__':
    arguments = get_arguments()
    window = init_window()
    game = Game.from_curses_window(window, arguments.debug)
    if not os.getenv('NO_COLOR'):
        init_colors()
    curses.wrapper(game.main_loop)
