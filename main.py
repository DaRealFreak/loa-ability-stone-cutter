import sys
import time

import pyautogui
from PIL import ImageGrab

from engravings import EngravingSelector
from faceting import Faceting
from settings import Settings


class AbilityStoneCutter:
    def __init__(self):
        """
        initialize the AbilityStoneCutter with necessary configurations.
        """
        # configure the engraving selector
        self.selector = EngravingSelector(
            possible_engravings=Settings.possible_engravings,
            priorities=Settings.priorities,
            negative_engraving_max=Settings.negative_engraving_max,
            threshold=0.85,
            max_pos=2,
            max_neg=1,
            num_workers=4,
        )

        # base/static faceting options from settings.py
        self.base_options = {
            "goal1": Settings.faceting_options.get('goal1', 0),
            "goal2": Settings.faceting_options.get('goal2', 0),
            "goals": Settings.faceting_options.get('goals', 16),
            "use_file_cache": True,
            "verbose": Settings.faceting_options.get('verbose', False),
            "log_to_file": True,
        }

        # we'll create this on first use, no need to cause lag on initialization
        self.faceter: Faceting | None = None

        # track absolute stone index and scrolls
        # absolute stone number
        self.abs_index = 1
        # number of times we've scrolled down by one stone
        self.scrolls = 0

        # at script start, select the first ability stone
        self._click_current()
        time.sleep(0.5)

    def _click_current(self) -> None:
        """
        click the ability stone corresponding to current abs_index and scrolls.

        :return:
        """
        visible_slot = self.abs_index - self.scrolls
        if not 1 <= visible_slot <= 12:
            raise ValueError(f"Visible slot {visible_slot} out of range 1-12")

        x = 428
        y = 165 + (visible_slot - 1) * 55
        self._click_pos(x, y)
        # click to the right to hide the tooltip of the selected stone
        self._click_pos(742, 165)
        time.sleep(0.5)

    def _scroll_down(self) -> None:
        """
        scroll the list down by one stone.

        :return:
        """
        # scroll button coordinates
        self._click_pos(636, 778)
        self.scrolls += 1

    @staticmethod
    def _click_pos(x: int, y: int, button: str = 'left') -> None:
        """
        click at a specific position on the screen.

        :param x: x-coordinate of the click position
        :param y: y-coordinate of the click position
        :param button: 'left' or 'right', default is 'left'
        :return:
        """
        pyautogui.moveTo(x=x, y=y)
        time.sleep(0.3)
        pyautogui.click(button=button)

    @staticmethod
    def get_color_hex(x: int, y: int) -> str:
        """
        get the color of a pixel at (x, y) as a hex string.

        :param x: x-coordinate of the pixel
        :param y: y-coordinate of the pixel
        :return: str: color in hex format, e.g. "0xFF0000" for red
        """
        r, g, b = pyautogui.pixel(x, y)
        return f"0x{r:02X}{g:02X}{b:02X}"

    def _detect_and_select(self) -> dict:
        """
        grab the screen, detect engravings, and return the selection dict.

        :return: dict: the results of engraving detection.
        """
        screenshot = ImageGrab.grab()
        raw = self.selector.detect_from_image(screenshot)
        results = self.selector.get_selection(raw)
        # self.selector.pretty_print_results(results)
        return results

    def _should_facet(self, results: dict) -> bool:
        """
        determine if we should facet based on the results of engraving detection.

        :param results: dict: the results from the engraving detection.
        :return: bool: True if faceting is needed, False otherwise.
        """
        return self.selector.should_cut(results)

    def _compute_dynamic_options(self, results: dict) -> dict:
        """
        compute dynamic faceting options based on the results of engraving detection.

        :param results: dict: the results from the engraving detection.
        :return: dict: options for the faceting process.
        """
        prioritized = results['prioritization']
        negatives = results['negative_selection']

        pref_ability = prioritized[0].get('position-index', 1) + 1
        goal3 = negatives[0].get('cap', 4)

        opts = dict(self.base_options)
        opts.update({
            "pref_ability": pref_ability,
            "goal3": goal3,
        })
        return opts

    def _run_faceting(self, opts: dict) -> None:
        """
        run the faceting process with the given options.

        :param opts: dict: options for the faceting process.
        :return:
        """
        if self.faceter is None:
            self.faceter = Faceting(opts)

        if self._is_in_result_screen():
            print(f"Already in result screen, decreasing abs_index to {self.abs_index - 1}.")
            self.abs_index -= 1
        else:
            print(f"Starting faceting with pref_ability={opts['pref_ability']}, goal3={opts['goal3']}")
            self.faceter.run(opts)

    def _is_in_result_screen(self) -> bool:
        """
        check if we are in the result screen of the faceting process.

        :return: bool: True if in result screen, False otherwise.
        """
        return self.get_color_hex(893, 194) == "0x1F4E6C"

    def interact_game(self, results: dict = None) -> None:
        """
        Advance to the next ability stone:
        - Increment to the next absolute stone number
        - If next stone is outside visible slots 1–12, scroll down by one and adjust

        :param results: dict: the results from the engraving detection.
        :return:
        """
        # check if we can scroll down further
        if self.abs_index > 12 and self.get_color_hex(634, 780) == "0x4C4C4C":
            print("unable to scroll down further, reached the end of the list")
            sys.exit(0)

        # check if the previous stone was fully faceted
        if self._is_in_result_screen():
            print(f"Previous stone fully faceted, moving to the next one (abs_index: {self.abs_index}).")
            self._click_pos(958, 747)
            self.scrolls = 0
            self.abs_index -= 1

        # only increase the absolute index if we have results, and we could detect negatives (in stone menu)
        if results and self.selector.could_detect_negatives(results):
            # Next stone
            self.abs_index += 1

        # Determine the slot it would appear in
        visible_slot = self.abs_index - self.scrolls
        while visible_slot > 12:
            self._scroll_down()
            # Recompute after scroll
            visible_slot = self.abs_index - self.scrolls

        # Click the stone
        self._click_current()
        print(f"Selected ability stone #{self.abs_index} at slot {visible_slot}")
        time.sleep(0.5)

    def run(self) -> None:
        """
        main loop: detect -> facet (if needed) -> select next stone -> repeat.

        :return:
        """
        while True:
            results = self._detect_and_select()
            if self._should_facet(results):
                opts = self._compute_dynamic_options(results)
                self._run_faceting(opts)
            else:
                print("No need to facet this round.")

            self.interact_game(results)


if __name__ == "__main__":
    cutter = AbilityStoneCutter()
    cutter.run()
