import logging
import os
import sys
import time
from datetime import datetime
from os.path import realpath, dirname, join

import pyautogui

from probability import Probability, FAILURE_PENALTY

# stone types: number of attempts available
ABILITY_STONE_EPIC = 9
ABILITY_STONE_RELIC = 10


class Faceting:
    """
    Main driver that uses Probability to decide next move,
    plus the PyAutoGUI logic to do the actual clicks and detect success/fail.
    """
    goal1 = 0
    goal2 = 0
    goal3 = 4
    total = 16
    pref_ability = 1

    log_to_file = False
    verbose = False
    prob = None
    script_dir = None

    def __init__(self, options: dict = None):
        self.configure(options)
        self.script_dir = realpath(dirname(__file__))
        self.sequence = []
        if self.log_to_file:
            logs_dir = join(self.script_dir, "logs_faceting")
            os.makedirs(logs_dir, exist_ok=True)
            log_file_name = datetime.now().strftime("%Y%m%d_%H%M%S.log")
            log_file_path = join(logs_dir, log_file_name)
            logger = logging.getLogger()
            logger.setLevel(logging.INFO)
            file_handler = logging.FileHandler(log_file_path)
            file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            logger.addHandler(file_handler)

    def configure(self, options: dict = None):
        if options:
            self.goal1 = int(options["goal1"])
            self.goal2 = int(options["goal2"])
            self.goal3 = int(options["goal3"])
            self.total = int(options["goals"])
            self.pref_ability = int(options["pref_ability"])
            self.log_to_file = options.get("log_to_file", True)
            self.verbose = options.get("verbose", False)
            use_cache = options.get("use_file_cache", True)
        else:
            self.log_to_file = True
            self.total = int(input("Total goals: "))
            self.pref_ability = int(input("Preferred ability: "))
            self.goal1 = 0
            self.goal2 = 0
            self.goal3 = int(input("Decreased ability: "))
            use_cache = True

        self.prob = Probability(ABILITY_STONE_RELIC, self.goal1, self.goal2, self.total, self.goal3,
                                use_file_cache=use_cache)

    def log_output(self, message: str):
        """
        Helper to both print and, if enabled, log the message.
        """
        if self.verbose:
            print(message)

        if self.log_to_file:
            logging.info(message)

    def update_options(self, options: dict):
        """
        Update the faceting options based on the provided dictionary.
        Updates the probability instance if any of the goal options change.

        :param options:
        :return:
        """
        # check if any of the options are different from the current ones and update if so
        update_probability = False
        if options.get("goal1", self.goal1) != self.goal1:
            self.goal1 = int(options["goal1"])
            update_probability = True
        if options.get("goal2", self.goal2) != self.goal2:
            self.goal2 = int(options["goal2"])
            update_probability = True
        if options.get("goal3", self.goal3) != self.goal3:
            self.goal3 = int(options["goal3"])
            update_probability = True
        if options.get("goals", self.total) != self.total:
            self.total = int(options["goals"])
            update_probability = True

        if options.get("pref_ability", self.pref_ability) != self.pref_ability:
            self.pref_ability = int(options["pref_ability"])

        if options.get("log_to_file", self.log_to_file) != self.log_to_file:
            self.log_to_file = options.get("log_to_file", True)

        if options.get("verbose", self.verbose) != self.verbose:
            self.verbose = options.get("verbose", False)

        if update_probability:
            self.prob = Probability(ABILITY_STONE_RELIC, self.goal1, self.goal2, self.total, self.goal3,
                                    use_file_cache=self.prob.use_file_cache)
            self.log_output("Updated Probability instance with new options.")

    def run(self, options: dict = None):
        """
        Repeatedly check the DP result from the current state,
        pick the best option, do the PyAutoGUI clicks, until no better move is available.
        """
        if options:
            self.update_options(options)

        process_start = time.perf_counter()
        # reset sequence
        self.sequence = []
        while True:
            st = time.perf_counter()
            state = self.prob.get_current_state(self.sequence)
            a_rem, b_rem, c_rem, p, d, e, t, f, s1, s2 = state

            self.log_output("\nSequence so far: " + str(self.sequence))
            self.log_output(f"Current Probability: {self.prob.decode_probability(p) * 100:.0f}%  (p={p})")
            self.log_output(f"a_rem={a_rem}, b_rem={b_rem}, c_rem={c_rem}, d={d}, e={e}, f={f}, s1={s1}, s2={s2}")

            from_opt1 = self.prob.calc_option(1, state) if a_rem > 0 else (0, FAILURE_PENALTY, s1, s2, self.goal3 - f)
            from_opt2 = self.prob.calc_option(2, state) if b_rem > 0 else (0, FAILURE_PENALTY, s1, s2, self.goal3 - f)
            from_opt3 = self.prob.calc_option(3, state) if c_rem > 0 else (0, FAILURE_PENALTY, s1, s2, self.goal3 - f)

            self.log_output("Option1 => p={:.5f}%, r={:.5f}, E=({:.2f}/{:.2f}/{:.2f})"
                            .format(from_opt1[0] * 100, from_opt1[1], from_opt1[2], from_opt1[3], from_opt1[4]))
            self.log_output("Option2 => p={:.5f}%, r={:.5f}, E=({:.2f}/{:.2f}/{:.2f})"
                            .format(from_opt2[0] * 100, from_opt2[1], from_opt2[2], from_opt2[3], from_opt2[4]))
            self.log_output("Option3 => p={:.5f}%, r={:.5f}, E=({:.2f}/{:.2f}/{:.2f})"
                            .format(from_opt3[0] * 100, from_opt3[1], from_opt3[2], from_opt3[3], from_opt3[4]))

            # pick best
            best_opt = max([1, 2, 3],
                           key=lambda k: ((from_opt1, from_opt2, from_opt3)[k - 1][0],
                                          (from_opt1, from_opt2, from_opt3)[k - 1][1],
                                          1 if k == self.pref_ability else 0))
            best = (from_opt1, from_opt2, from_opt3)[best_opt - 1]
            if best[0] <= 0:
                self.log_output("No better option or goal not reachable. Stopping.")
                break

            self.log_output(f"Selecting option {best_opt}")
            if best_opt == 1:
                slot = self.prob.attempts - a_rem + 1
            elif best_opt == 2:
                slot = self.prob.attempts - b_rem + 1
            else:
                slot = self.prob.attempts - c_rem + 1
            slot = min(slot, self.prob.attempts)

            self.log_output(f"Faceting ability={best_opt} in slot={slot}")
            self.facet(best_opt, slot)
            et = time.perf_counter()
            self.log_output("Probability Calculation for this step done in {:.3f} seconds.".format(et - st))

        process_end = time.perf_counter()
        self.log_output("Faceting process completed in {:.3f} seconds.".format(process_end - process_start))
        self.prob.save_file_cache()

    def facet(self, ability, slot):
        """
        Do the PyAutoGUI click, then wait for the success/fail image, and record the outcome.
        """
        if ability == 1:
            y_coord = 373
            pyautogui.moveTo(x=1208, y=383)
        elif ability == 2:
            y_coord = 466
            pyautogui.moveTo(x=1208, y=472)
        else:
            y_coord = 593
            pyautogui.moveTo(x=1208, y=599)
        time.sleep(0.3)
        pyautogui.click(button='left')

        x_coord = 764 + (slot - 1) * 38
        self.log_output(f"PyAutoGUI: clicking ability={ability} at slot={slot} => x={x_coord}, y={y_coord}")

        if ability == 3:
            success_file = f"{self.script_dir}/assets/faceting/faceting_success_decrease.png"
            success_file_step = f"{self.script_dir}/assets/faceting/faceting_success_decrease_step.png"
        else:
            success_file = f"{self.script_dir}/assets/faceting/faceting_success_increase.png"
            success_file_step = f"{self.script_dir}/assets/faceting/faceting_success_increase_step.png"

        while True:
            # wait for either success or fail
            try:
                pyautogui.locateOnScreen(success_file, confidence=0.95, region=(x_coord, y_coord, 38, 40))
                self.sequence.append([ability, True])
                break
            except pyautogui.ImageNotFoundException:
                pass
            try:
                pyautogui.locateOnScreen(success_file_step, confidence=0.95, region=(x_coord, y_coord, 38, 40))
                self.sequence.append([ability, True])
                break
            except pyautogui.ImageNotFoundException:
                pass
            try:
                pyautogui.locateOnScreen(f"{self.script_dir}/assets/faceting/faceting_fail.png",
                                         confidence=0.95, region=(x_coord, y_coord, 38, 40))
                self.sequence.append([ability, False])
                break
            except pyautogui.ImageNotFoundException:
                pass


def faceting_start_process(**kwargs):
    """
    Start the faceting process with optional configuration options.
    """
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting faceting process...")
    faceting = Faceting(**kwargs)
    faceting.run()


def test_dp_options(sequence, goal1=0, goal2=0, total=16, goal3=10, use_file_cache=False):
    """
    Test function that creates a Probability instance with given parameters and prints:
      - The current state (including remaining attempts, probability index, remaining goals, etc.).
      - The expected (p, r) tuple for each option computed one step ahead.
      - The number of successful and failed clicks for each ability so far.

    :param sequence: List of [ability, outcome] records (True for success, False for failure).
    :param goal1: Individual goal for ability 1 (0 for total mode).
    :param goal2: Individual goal for ability 2 (0 for total mode).
    :param total: Total required successes (used in total mode).
    :param goal3: Maximum allowed failures (for ability 3).
    """
    prob = Probability(ABILITY_STONE_RELIC, goal1, goal2, total, goal3, use_file_cache)
    st = time.perf_counter()
    state = prob.get_current_state(sequence)
    a_rem, b_rem, c_rem, p, d, e, t, f, s1, s2 = state

    print("Sequence:", sequence)
    print("State:", state)
    print("Mode:", "total" if prob.total_mode else "individual")
    print("p={}, decode={:.0f}%".format(p, prob.decode_probability(p) * 100))
    print("Remaining attempts => a={}, b={}, c={}".format(a_rem, b_rem, c_rem))
    print("State variables => d={}, e={}, t={}, f={}, s1={}, s2={}".format(d, e, t, f, s1, s2))

    if a_rem > 0:
        r1 = prob.calc_option(1, state)
        print("Option1 => p={:.5f}%, r={:.5f}, E=({:.2f}/{:.2f}/{:.2f})"
              .format(r1[0] * 100, r1[1], r1[2], r1[3], r1[4]))
    else:
        print("Option1 => not available")

    if b_rem > 0:
        r2 = prob.calc_option(2, state)
        print("Option2 => p={:.5f}%, r={:.5f}, E=({:.2f}/{:.2f}/{:.2f})"
              .format(r2[0] * 100, r2[1], r2[2], r2[3], r2[4]))
    else:
        print("Option2 => not available")

    if c_rem > 0:
        r3 = prob.calc_option(3, state)
        print("Option3 => p={:.5f}%, r={:.5f}, E=({:.2f}/{:.2f}/{:.2f})"
              .format(r3[0] * 100, r3[1], r3[2], r3[3], r3[4]))
    else:
        print("Option3 => not available")

    et = time.perf_counter()
    print("Probability Calculation Done! ({:.3f} seconds)".format(et - st))
    if use_file_cache:
        prob.save_file_cache()


if __name__ == "__main__":
    if len(sys.argv) > 5:
        opts = {
            "pref_ability": int(sys.argv[1]),
            "goal1": int(sys.argv[2]),
            "goal2": int(sys.argv[3]),
            "goal3": int(sys.argv[4]),
            "goals": int(sys.argv[5]),
            "use_file_cache": True,
            "verbose": True,
            "log_to_file": bool(int(sys.argv[6])) if len(sys.argv) > 6 else False
        }
        Faceting(opts).run()
    else:
        Faceting().run()

if __name__ == "__test__":
    # Example usage:
    # Let's check a 9/7 stone (goal1=9, goal2=7, total=0, goal3=10) from a given sequence:
    test_sequence = [
        [1, True], [1, True], [1, True], [1, True],
        [1, True], [1, True], [1, True], [1, True],
        [1, False],
        [2, True], [2, True], [2, True], [2, True],
        [2, True], [2, True], [2, True], [2, True],
        [3, False], [3, False], [3, False], [3, False],
        [3, False], [3, False], [3, False], [3, False],
        [3, False],
    ]
    test_dp_options(test_sequence, goal1=0, goal2=0, total=16, goal3=10, use_file_cache=False)
