import logging
import os
import pickle
import sys
import time
from datetime import datetime
from os.path import realpath, dirname, join

import pyautogui

# Stone types: number of attempts available
ABILITY_STONE_EPIC = 9
ABILITY_STONE_RELIC = 10

# Probability index range 0..5 => 25..75%
MAX_PROBABILITY = 6

# Constant for penalizing states that do not meet milestone conditions (in total mode)
# or do not meet the individual goals (in individual mode).
# set to 0 by default; can be changed if you want a big penalty for failing.
FAILURE_PENALTY = 0


class Probability:
    """
    DP class for computing (P, R, E1, E2, E3) from a given state.
    P: probability of eventually meeting the user's goal (individual or total).
    R: expected "reward" in total mode, 0 in individual mode.
    E1, E2: expected successes for abilities 1,2
    E3: expected negative successes for ability 3
    """

    def __init__(self, ability_stone: int, goal1: int, goal2: int, total: int, goal3: int, use_file_cache=True):
        """
        Initialize the Probability instance.

        :param ability_stone: Number of attempts per ability.
        :param goal1: Required successes for ability 1 (0 for total mode).
        :param goal2: Required successes for ability 2 (0 for total mode).
        :param total: Total required successes (used in total mode).
        :param goal3: Maximum allowed failures (for ability 3).
        :param use_file_cache: If True, attempt to load/save the DP cache from/to file.
        """
        self.attempts = ability_stone
        self.goal1 = goal1
        self.goal2 = goal2
        self.total = total
        self.goal3 = goal3
        self.total_mode = (goal1 + goal2 == 0)
        self.dp_cache = {}
        self.use_file_cache = use_file_cache
        if self.use_file_cache:
            self.load_file_cache()

    @staticmethod
    def decode_probability(p):
        """
        Convert p in [0..5] => [25..75]%
        p=0 => 25%, p=5 => 75%.
        """
        return 0.25 + 0.1 * p

    @staticmethod
    def positive_reward(s):
        """
        Cumulative positive reward for s successes (in total mode).
        Example milestones:
          s<6   => 0.0
          s=6   => 0.0256
          s=7   => 0.0321
          s=9   => 0.0449
          s>=10 => 0.0513
        """
        if s >= 10:
            return 0.0513
        elif s >= 9:
            return 0.0449
        elif s >= 7:
            return 0.0321
        elif s >= 6:
            return 0.0256
        else:
            return 0.0

    def bonus_for_positive(self, current, new):
        """Incremental bonus crossing a milestone from current to new."""
        return self.positive_reward(new) - self.positive_reward(current)

    @staticmethod
    def negative_reward(s):
        """
        Cumulative negative penalty for s successes on ability 3 (in total mode).
          s<5 => 0.0
          s=5 => -0.02
          s=7 => -0.04
          s>=10 => -0.06
        """
        if s >= 10:
            return -0.06
        elif s >= 7:
            return -0.04
        elif s >= 5:
            return -0.02
        else:
            return 0.0

    def penalty_for_negative(self, current, new):
        """Incremental penalty from current->new for negative successes."""
        return self.negative_reward(new) - self.negative_reward(current)

    def _cache_file_name(self):
        """
        Return the file name (with path) to use for caching the dp_cache.
        """
        tmp_dir = join(realpath(dirname(__file__)), "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        # Use .pkl extension for pickle file.
        return join(tmp_dir, f"dp_{self.attempts}_{self.goal1}_{self.goal2}_{self.total}_{self.goal3}.pkl")

    def load_file_cache(self):
        """
        Attempt to load the DP cache from a pickle file.
        """
        cache_file = self._cache_file_name()
        st = time.perf_counter()
        try:
            with open(cache_file, "rb") as f:
                self.dp_cache = pickle.load(f)
            et = time.perf_counter()
            print("Loaded DP cache from file in {:.3f} seconds.".format(et - st))
        except FileNotFoundError:
            print("No DP cache file found. Will compute and save later.")
        except Exception as e:
            print("Error loading cache:", e)

    def save_file_cache(self):
        """
        Save the DP cache to a pickle file.
        """
        if not self.use_file_cache:
            return
        cache_file = self._cache_file_name()

        # Return if the cache file exists already
        if os.path.exists(cache_file):
            return

        st = time.perf_counter()
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(self.dp_cache, f, protocol=pickle.HIGHEST_PROTOCOL)
            et = time.perf_counter()
            print("Saved DP cache to file in {:.3f} seconds.".format(et - st))
        except Exception as e:
            print("Error saving cache:", e)

    def dp_tuple(self, a, b, c, p, d, e, t, f, s1, s2):
        """
        Recursively compute the expected probability and reward (tuple (p, r))
        for the given state using dynamic programming.

        :param a: Remaining attempts for ability 1.
        :param b: Remaining attempts for ability 2.
        :param c: Remaining attempts for ability 3.
        :param p: Current probability index.
        :param d: Remaining successes needed for ability 1 (individual mode).
        :param e: Remaining successes needed for ability 2 (individual mode).
        :param t: Remaining total successes needed (total mode).
        :param f: Remaining allowed failures for ability 3.
        :param s1: Successes so far on ability 1.
        :param s2: Successes so far on ability 2.
        :return: Tuple (probability, reward, expected_success_1, expected_success_2, expected_success_3).
        """
        key = (a, b, c, p, d, e, t, f, s1, s2)
        if key in self.dp_cache:
            return self.dp_cache[key]

        # Stop conditions for total mode.
        if self.total_mode:
            # In total mode, stop if no attempts remain => check milestone
            if a + b + c == 0:
                s3 = self.goal3 - f
                if self.total == 16:
                    # Must not end 8/8
                    if ((s1 >= 9 and s2 >= 7) or (s1 >= 7 and s2 >= 9) or
                        (s1 >= 10 and s2 >= 6) or (s1 >= 6 and s2 >= 10)) and not (s1 == 8 and s2 == 8):
                        val = (1.0,
                               self.positive_reward(min(s1, self.attempts)) +
                               self.positive_reward(min(s2, self.attempts)) +
                               self.negative_reward(s3),
                               min(s1, self.attempts), min(s2, self.attempts), s3)
                    else:
                        val = (0.0, FAILURE_PENALTY,
                               min(s1, self.attempts), min(s2, self.attempts), s3)
                elif self.total == 14:
                    s3 = self.goal3 - f
                    if (s1 + s2 >= 14) and ((min(s1, s2) >= 7) or (min(s1, s2) == 6 and max(s1, s2) >= 9)):
                        val = (1.0,
                               self.positive_reward(min(s1, self.attempts)) +
                               self.positive_reward(min(s2, self.attempts)) +
                               self.negative_reward(s3),
                               min(s1, self.attempts), min(s2, self.attempts), s3)
                    else:
                        val = (0.0, FAILURE_PENALTY,
                               min(s1, self.attempts), min(s2, self.attempts), s3)
                else:
                    # Default for totals other than 14 or 16:
                    # Only succeed if the combined successes meet the total goal.
                    s3 = self.goal3 - f
                    if s1 + s2 >= self.total:
                        val = (1.0,
                               self.positive_reward(min(s1, self.attempts)) +
                               self.positive_reward(min(s2, self.attempts)) +
                               self.negative_reward(s3),
                               min(s1, self.attempts), min(s2, self.attempts), s3)
                    else:
                        val = (0.0, FAILURE_PENALTY,
                               min(s1, self.attempts), min(s2, self.attempts), s3)
                self.dp_cache[key] = val
                return val
        else:
            # Individual mode => success if d<=0 & e<=0
            if d <= 0 and e <= 0:
                s3 = self.goal3 - f
                val = (1.0, 0.0, s1, s2, s3)
                self.dp_cache[key] = val
                return val
            if a + b + c == 0:
                # no attempts left => fail
                s3 = self.goal3 - f
                val = (0.0, FAILURE_PENALTY, s1, s2, s3)
                self.dp_cache[key] = val
                return val

        # Negative tolerance exceeded => fail
        if f < 0:
            val = (0.0, 0.0, s1, s2, self.goal3 - f)
            self.dp_cache[key] = val
            return val

        # -- Optional: skip synergy usage in individual mode if you want fewer negative successes:
        # if (not self.total_mode) and (a+b>0):
        #     # only use ability1 or ability2
        #     best = (-1.0, -1000, 0,0,0)
        #     if a>0:
        #         candidate= self.calc_option(1, (a,b,c,p,d,e,t,f,s1,s2))
        #         if candidate>best:
        #             best= candidate
        #     if b>0:
        #         candidate= self.calc_option(2, (a,b,c,p,d,e,t,f,s1,s2))
        #         if candidate>best:
        #             best= candidate
        #     self.dp_cache[key]= best
        #     return best

        # Otherwise do normal branching
        best = (-1.0, -1000, 0, 0, 0)
        if a > 0:
            candidate = self.calc_option(1, (a, b, c, p, d, e, t, f, s1, s2))
            if candidate > best:
                best = candidate
        if b > 0:
            candidate = self.calc_option(2, (a, b, c, p, d, e, t, f, s1, s2))
            if candidate > best:
                best = candidate
        if c > 0:
            candidate = self.calc_option(3, (a, b, c, p, d, e, t, f, s1, s2))
            if candidate > best:
                best = candidate

        self.dp_cache[key] = best
        return best

    def calc_option(self, option: int, state: tuple):
        """
        Evaluate a single click on ability=option, returning (probability, reward, e1, e2, e3).
        Weighted by success/fail with decode_probability(p).

        :param option: Integer (1, 2, or 3) representing the ability choice.
        :param state: Tuple (a, b, c, p, d, e, t, f, s1, s2) representing the current state.
        :return: Tuple (probability, reward, expected_success_1, expected_success_2, expected_success_3).
        """
        a, b, c, p, d, e, t, f, s1, s2 = state
        dec = self.decode_probability(p)

        if option == 1 and a > 0:
            new_s1 = min(s1 + 1, self.attempts)
            # success branch
            if self.total_mode:
                child_succ = self.dp_tuple(a - 1, b, c, max(p - 1, 0), 0, 0, t - 1, f, new_s1, s2)
                child_fail = self.dp_tuple(a - 1, b, c, min(p + 1, MAX_PROBABILITY - 1), 0, 0, t, f, s1, s2)
            else:
                child_succ = self.dp_tuple(a - 1, b, c, max(p - 1, 0), d - 1, e, t, f, new_s1, s2)
                child_fail = self.dp_tuple(a - 1, b, c, min(p + 1, MAX_PROBABILITY - 1), d, e, t, f, s1, s2)

            bonus = self.bonus_for_positive(s1, new_s1)
            probability = dec * child_succ[0] + (1 - dec) * child_fail[0]
            reward = dec * (child_succ[1] + bonus) + (1 - dec) * child_fail[1]
            e1 = dec * child_succ[2] + (1 - dec) * child_fail[2]
            e2 = dec * child_succ[3] + (1 - dec) * child_fail[3]
            e3 = dec * child_succ[4] + (1 - dec) * child_fail[4]
            return probability, reward, e1, e2, e3

        elif option == 2 and b > 0:
            new_s2 = min(s2 + 1, self.attempts)
            if self.total_mode:
                child_succ = self.dp_tuple(a, b - 1, c, max(p - 1, 0), 0, 0, t - 1, f, s1, new_s2)
                child_fail = self.dp_tuple(a, b - 1, c, min(p + 1, MAX_PROBABILITY - 1), 0, 0, t, f, s1, s2)
            else:
                child_succ = self.dp_tuple(a, b - 1, c, max(p - 1, 0), d, e - 1, t, f, s1, new_s2)
                child_fail = self.dp_tuple(a, b - 1, c, min(p + 1, MAX_PROBABILITY - 1), d, e, t, f, s1, s2)

            bonus = self.bonus_for_positive(s2, new_s2)
            probability = dec * child_succ[0] + (1 - dec) * child_fail[0]
            reward = dec * (child_succ[1] + bonus) + (1 - dec) * child_fail[1]
            e1 = dec * child_succ[2] + (1 - dec) * child_fail[2]
            e2 = dec * child_succ[3] + (1 - dec) * child_fail[3]
            e3 = dec * child_succ[4] + (1 - dec) * child_fail[4]
            return probability, reward, e1, e2, e3

        elif option == 3 and c > 0:
            s3 = self.goal3 - f
            child_succ = self.dp_tuple(a, b, c - 1, max(p - 1, 0), d, e, t, f - 1, s1, s2)
            child_fail = self.dp_tuple(a, b, c - 1, min(p + 1, MAX_PROBABILITY - 1), d, e, t, f, s1, s2)
            bonus_neg = self.penalty_for_negative(s3, s3 + 1)
            probability = dec * child_succ[0] + (1 - dec) * child_fail[0]
            reward = dec * (child_succ[1] + bonus_neg) + (1 - dec) * child_fail[1]
            e1 = dec * child_succ[2] + (1 - dec) * child_fail[2]
            e2 = dec * child_succ[3] + (1 - dec) * child_fail[3]
            e3 = dec * child_succ[4] + (1 - dec) * child_fail[4]
            return probability, reward, e1, e2, e3

        return -1.0, -1000, 0, 0, 0

    @staticmethod
    def cal_p_from_seq(sequence):
        """
        Compute the current probability index from a sequence of clicks.

        :param sequence: List of [ability, outcome] records.
        :return: Current probability index (integer).
        """
        p = MAX_PROBABILITY - 1  # start at 75%
        for att in sequence:
            if att[1]:
                p = max(p - 1, 0)
            else:
                p = min(p + 1, MAX_PROBABILITY - 1)
        return p

    def get_current_state(self, sequence):
        """
        Compute the full DP state from the faceting sequence.

        :param sequence: List of [ability, outcome] records.
        :return: Tuple (a_rem, b_rem, c_rem, p, d, e, t, f, s1, s2) where:
                 - a_rem, b_rem, c_rem: Remaining attempts for abilities 1, 2, 3.
                 - p: Current probability index.
                 - In total mode:
                      t = total - (# successes on abilities 1 and 2),
                      d = e = 0,
                      s1, s2 = successes on abilities 1 and 2.
                 - In individual mode:
                      d = goal1 - (# successes on ability 1),
                      e = goal2 - (# successes on ability 2),
                      t = 0,
                      s1, s2 = successes on abilities 1 and 2.
                 - f = goal3 - (# successes on ability 3).
        """
        a_used = sum(1 for att in sequence if att[0] == 1)
        b_used = sum(1 for att in sequence if att[0] == 2)
        c_used = sum(1 for att in sequence if att[0] == 3)
        a_rem = self.attempts - a_used
        b_rem = self.attempts - b_used
        c_rem = self.attempts - c_used
        p = self.cal_p_from_seq(sequence)
        s1 = sum(1 for att in sequence if att[0] == 1 and att[1])
        s2 = sum(1 for att in sequence if att[0] == 2 and att[1])
        s3 = sum(1 for att in sequence if att[0] == 3 and att[1])  # for debug

        f = self.goal3 - s3

        if self.total_mode:
            t = self.total - (s1 + s2)
            d = 0
            e = 0
        else:
            t = 0
            d = self.goal1 - s1
            e = self.goal2 - s2

        return a_rem, b_rem, c_rem, p, d, e, t, f, s1, s2


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
            # Wait for either success or fail
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
    # Let's check a 9/7 stone (goal1=9, goal2=7, total=0, goal3=10) from an empty sequence:
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
