import asyncio
import curses
import math
import logging
from abc import ABC, abstractmethod
import keyboard
from volcano import Volcano

import _curses

logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)

_LOGGER = logging.getLogger(__name__)

VOLCANO_MAC = 'FB:17:6B:85:5B:C2'

async def init(screen):
    k = 0
    curses.noecho()
    curses.cbreak()
    curses.use_default_colors()

    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)

    screen.nodelay()
    screen.clear()
    screen.timeout(100)
    h, w = screen.getmaxyx()

    cy = math.floor(h / 2)
    cx = math.floor(w / 2)

    screen.addstr(cy, cx - 7, 'CONNECTING...')

    screen.refresh()

    volcano = Volcano(VOLCANO_MAC)

    await volcano.connect()

    while k != ord('q'):
        screen.erase()

        if (k == curses.KEY_UP):
            volcano.target_temperature += 1
        elif (k == curses.KEY_DOWN):
            volcano.target_temperature -= 1
        elif (k == curses.KEY_LEFT):
            volcano.toggle_heater()
        elif (k == curses.KEY_RIGHT):
            volcano.toggle_pump()
    
        heater_on = 'ON' if volcano.heater_on else 'OFF'
        pump_on = 'ON' if volcano.pump_on else 'OFF'

        screen.addstr(cy - 2, cx - 7, f'Heater: ')
        screen.addstr(heater_on, curses.color_pair(1 if volcano.heater_on else 2))
        screen.addstr(cy - 1, cx - 5, f'Pump: ')
        screen.addstr(pump_on, curses.color_pair(1 if volcano.pump_on else 2))
        screen.addstr(cy, cx - 12, f'Target Temp: {volcano.target_temperature}')
        screen.addstr(cy + 1, cx - 13, f'Current Temp: {volcano.temperature}')

        screen.addstr(h - 4, 0, f'')
        screen.addstr(h - 4, 0, f'Serial number: {volcano._serial_number}')
        screen.addstr(h - 4, 0, f'Firmware version: {volcano._firmware_version}')

        screen.refresh()

        k = screen.getch()
    
    volcano.join()

def main(stdscr) -> None:
    return asyncio.run(init(stdscr))

if __name__ == '__main__':
    curses.wrapper(main)

class Display(ABC):
    def __init__(self, screen: '_curses._CursesWindow'):
        self.screen = screen
        self.done: bool = False

    @abstractmethod
    def make_display(self) -> None:
        pass

    @abstractmethod
    def handle_char(self, char: int) -> None:
        pass

    def set_exit(self) -> None:
        self.done = True

    async def run(self) -> None:
        curses.curs_set(0)
        curses.noecho()
        curses.cbreak()
        curses.use_default_colors()

        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_RED, -1)

        self.screen.nodelay()
        self.screen.clear()
        self.screen.timeout(100)

        h, w = self.screen.getmaxyx()

        cy = math.floor(h / 2)
        cx = math.floor(w / 2)

        self.screen.addstr(cy, cx - 7, 'CONNECTING...')

        self.screen.refresh()

        self.make_display()

        while not self.done:
            char = self.screen.getch()
            if char == curses.ERR:
                await asyncio.sleep(0.1)
            elif char == curses.KEY_RESIZE:
                self.make_display()
            else:
                self.handle_char(char)


class MyDisplay(Display):
    def __init__(self, screen: '_curses._CursesWindow', volcano: Volcano):
        self.volcano = volcano
        super(screen)

    def make_display(self) -> None:
        msg1 = "Resize at will"
        msg2 = "Press 'q' to exit"

        h, w = self.screen.getmaxyx()

        cy = math.floor(h / 2)
        cx = math.floor(w / 2)

        self.screen.erase()

        heater_on = 'ON' if self.volcano.heater_on else 'OFF'
        pump_on = 'ON' if self.volcano.pump_on else 'OFF'

        self.screen.addstr(cy - 2, cx - 7, f'Heater: ')
        self.screen.addstr(heater_on, curses.color_pair(1 if self.volcano.heater_on else 2))
        self.screen.addstr(cy - 1, cx - 5, f'Pump: ')
        self.screen.addstr(pump_on, curses.color_pair(1 if self.volcano.pump_on else 2))
        self.screen.addstr(cy, cx - 12, f'Target Temp: {self.volcano.target_temperature}')
        self.screen.addstr(cy + 1, cx - 13, f'Current Temp: {self.volcano.current_temperature}')

        self.screen.addstr(h - 4, 0, f'')
        self.screen.addstr(h - 4, 0, f'Serial number: {self.volcano._serial_number}')
        self.screen.addstr(h - 4, 0, f'Firmware version: {self.volcano._firmware_version}')

        self.screen.refresh()

    def handle_char(self, char: int) -> None:
        if chr(char) == "q":
            self.set_exit()
        if chr(char) == curses.KEY_UP:
            self.volcano.target_temperature += 1
        elif chr(char) == curses.KEY_DOWN:
            self.volcano.target_temperature -= 1
        elif chr(char) == curses.KEY_LEFT:
            self.volcano.toggle_heater()
        elif chr(char) == curses.KEY_RIGHT:
            self.volcano.toggle_pump()


async def display_main(screen):
    display = MyDisplay(screen)
    await display.run()


def main(stdscr) -> None:
    return asyncio.run(display_main(stdscr))


if __name__ == "__main__":
    curses.wrapper(main)
