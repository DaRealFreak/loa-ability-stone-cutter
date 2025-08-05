import os
import pickle
import time
from os.path import realpath, dirname, join

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
