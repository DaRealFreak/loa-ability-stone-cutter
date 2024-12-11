import json
import logging
import multiprocessing
import sys
import time
from os.path import realpath, dirname

import keyboard
import pyautogui

ABILITY_STONE_RELIC = 10


class Probability:
    MAX_PROBABILITY = 6

    number_of_attempts = ABILITY_STONE_RELIC
    dp = []
    sequence = []
    goal_cells = []

    def __init__(self, ability_stone: int, ability_goal_1: int, ability_goal_2: int, ability_total: int):
        """
        :param ability_stone:
        :param ability_goal_1:
        :param ability_goal_2:
        :param ability_total:
        """
        self.number_of_attempts = ability_stone
        # initialize dp table
        self.dp = [0.0] * ((self.number_of_attempts + 1) ** 6 * self.MAX_PROBABILITY)
        self.set_goal_cells_from_goal(ability_goal_1, ability_goal_2, ability_total)
        self.cal_dp()

    def idx(self, a, b, c, p, d, e, f):
        """
        returns the calculated index of the dp table
        :param a:
        :param b:
        :param c:
        :param p:
        :param d:
        :param e:
        :param f:
        :return:
        """
        na1 = self.number_of_attempts + 1
        return (((((a * na1 + b) * na1 + c) * 6 + p) * na1 + d) * na1 + e) * na1 + f

    @staticmethod
    def decode_p(p):
        return 0.25 + p * 0.1

    def cal_prob1(self, a, b, c, p, d, e, f):
        if a == 0:
            return 0
        success = self.decode_p(p) * self.dp[
            self.idx(a - 1, b, c, max(p - 1, 0), d + 1, e, f)] if d < self.number_of_attempts else 0
        fail = (1 - self.decode_p(p)) * self.dp[self.idx(a - 1, b, c, min(p + 1, self.MAX_PROBABILITY - 1), d, e, f)]
        return success + fail

    def cal_prob1_safe(self, a, b, c, p, d, e, f):
        if f < 0:
            return 0
        return self.cal_prob1(a, b, c, p, d, e, f)

    def cal_prob2(self, a, b, c, p, d, e, f):
        if b == 0:
            return 0
        success = self.decode_p(p) * self.dp[
            self.idx(a, b - 1, c, max(p - 1, 0), d, e + 1, f)] if e < self.number_of_attempts else 0
        fail = (1 - self.decode_p(p)) * self.dp[self.idx(a, b - 1, c, min(p + 1, self.MAX_PROBABILITY - 1), d, e, f)]
        return success + fail

    def cal_prob2_safe(self, a, b, c, p, d, e, f):
        if f < 0:
            return 0
        return self.cal_prob2(a, b, c, p, d, e, f)

    def cal_prob3(self, a, b, c, p, d, e, f):
        return (self.decode_p(p) * self.dp[self.idx(a, b, c - 1, max(p - 1, 0), d, e, f - 1)] if f > 0 else 0) + \
               (1 - self.decode_p(p)) * self.dp[
                   self.idx(a, b, c - 1, min(p + 1, self.MAX_PROBABILITY - 1), d, e, f)] if c > 0 else 0

    def cal_prob3_safe(self, a, b, c, p, d, e, f):
        if f < 0:
            return 0
        return self.cal_prob3(a, b, c, p, d, e, f)

    def cal_p_from_seq(self):
        p = self.MAX_PROBABILITY - 1
        for attempt in self.sequence:
            if attempt[1] == 0:
                p = min(p + 1, self.MAX_PROBABILITY - 1)
            else:
                p = max(p - 1, 0)
        return p

    def cal_idx_from_seq(self, goal, idx_of_seq):
        a = self.number_of_attempts
        d = goal
        success = 0
        for attempt in self.sequence:
            if attempt[0] == idx_of_seq:
                a -= 1
                if attempt[1] == 1:
                    d -= 1
                    success += 1
        return [a, d, success]

    def cal_dp(self):
        json_file = f"{realpath(dirname(__file__))}/tmp/dp_{self.number_of_attempts}_{self.encoded_goal_cells()}.json"
        # check if file exists
        try:
            json.load(open(json_file, "r"))
            print("loading dp from file")
            self.dp = json.load(open(json_file, "r"))
            return
        except FileNotFoundError:
            pass

        # reset previous dp
        self.dp = [0.0] * ((self.number_of_attempts + 1) ** 6 * self.MAX_PROBABILITY)

        st = time.perf_counter()
        for d in range(self.number_of_attempts, -1, -1):
            for a in range(0, self.number_of_attempts - d + 1):
                for e in range(self.number_of_attempts, -1, -1):
                    for b in range(0, self.number_of_attempts - e + 1):
                        for c in range(0, self.number_of_attempts + 1):
                            for f in range(0, self.number_of_attempts + 1):
                                for p in range(self.MAX_PROBABILITY):
                                    if self.goal_cells[d][e] == 1 and a == 0 and b == 0 and c <= f:
                                        t = 1
                                    elif c < f:
                                        t = self.dp[self.idx(a, b, c, p, d, e, c)]
                                    else:
                                        t = 0
                                        t = max(t, self.cal_prob1(a, b, c, p, d, e, f))
                                        t = max(t, self.cal_prob2(a, b, c, p, d, e, f))
                                        t = max(t, self.cal_prob3(a, b, c, p, d, e, f))

                                    self.dp[self.idx(a, b, c, p, d, e, f)] = t

        et = time.perf_counter()
        print("Probability Calculation Done! ({:.3f} seconds)".format((et - st)))
        json.dump(self.dp, open(json_file, "w"))

    def set_goal_cells_from_goal(self, ability_goal_1, ability_goal_2, ability_total):
        self.goal_cells = []
        for i in range(self.number_of_attempts + 1):
            t = []
            for j in range(self.number_of_attempts + 1):
                if i >= ability_goal_1 and j >= ability_goal_2 and i + j >= ability_total:
                    t.append(1)
                else:
                    t.append(0)
            self.goal_cells.append(t)

        if ability_total == 16:
            # remove 8/8 stone from the goal cells, because nobody would ever want that
            self.goal_cells[8][8] = 0
        if ability_total == 14:
            # remove 6/8 and 8/6 stone from the goal cells, because nobody would like it
            self.goal_cells[6][8] = 0
            self.goal_cells[8][6] = 0

    def encoded_goal_cells(self):
        return "".join([str(cell) for row in self.goal_cells for cell in row])


class Faceting:
    goal1 = 0
    goal2 = 0
    goal3 = 4
    goals = 16
    pref_ability = 1

    prob = None
    script_dir = None

    def __init__(self, faceting_options: dict = None):
        self.configure(faceting_options)
        self.script_dir = realpath(dirname(__file__))

    def configure(self, faceting_options: dict = None):
        # ask for input of ability 1, ability 2, and decreased ability

        if faceting_options:
            self.goal1 = int(faceting_options["goal1"])
            self.goal2 = int(faceting_options["goal2"])
            self.goal3 = int(faceting_options["goal3"])
            self.goals = int(faceting_options["goals"])
            self.pref_ability = int(faceting_options["pref_ability"])
        else:
            go_97_stone = input("9/7 stone: ")
            if go_97_stone == "y":
                use_total = input("9/7 both abilities possible: ")
                if use_total == "y":
                    self.pref_ability = int(input("Preferred ability: "))
                    self.goal1 = 0  # ability 1
                    self.goal2 = 0  # ability 2
                    self.goals = 16
                else:
                    ability = input("Which ability for 7? (your +2 engraving): ")
                    self.goals = 0
                    if ability == "1":
                        self.pref_ability = 2
                        self.goal1 = 7
                        self.goal2 = 9
                    else:
                        self.pref_ability = 1
                        self.goal1 = 9
                        self.goal2 = 7
            else:
                self.goal1 = int(input("Ability 1 (use 0 to go for total): "))
                self.goal2 = int(input("Ability 2 (use 0 to go for total): "))
                if (self.goal1 + self.goal2) == 0:
                    self.goals = min(int(input("Total: ")), 20)
                else:
                    self.goals = 0
                self.pref_ability = min(int(input("Preferred ability: ")), 10)

            self.goal3 = int(input("Decreased ability: "))

        self.prob = Probability(ABILITY_STONE_RELIC, self.goal1, self.goal2, self.goals)

    def run(self):
        current_probability = self.prob.cal_p_from_seq()
        idx1 = self.prob.cal_idx_from_seq(self.goal1, 1)
        idx2 = self.prob.cal_idx_from_seq(self.goal2, 2)
        idx3 = self.prob.cal_idx_from_seq(self.goal3, 3)
        print("current: probability: {:.0f}%".format(self.prob.decode_p(current_probability) * 100))

        prob1 = self.prob.cal_prob1_safe(idx1[0], idx2[0], idx3[0], current_probability, idx1[2], idx2[2], idx3[1])
        prob2 = self.prob.cal_prob2_safe(idx1[0], idx2[0], idx3[0], current_probability, idx1[2], idx2[2], idx3[1])
        prob3 = self.prob.cal_prob3_safe(idx1[0], idx2[0], idx3[0], current_probability, idx1[2], idx2[2], idx3[1])
        print("current probability for option 1: {:.10f}%".format(prob1 * 100))
        print("current probability for option 2: {:.10f}%".format(prob2 * 100))
        print("current probability for option 3: {:.10f}%".format(prob3 * 100))

        if prob1 + prob2 + prob3 == 0:
            print("0% probability for all options, exiting")
            return

        idx1 = self.prob.cal_idx_from_seq(self.goal1, 1)
        idx2 = self.prob.cal_idx_from_seq(self.goal2, 2)
        idx3 = self.prob.cal_idx_from_seq(self.goal3, 3)

        if prob1 > prob2 and prob1 > prob3:
            print("selecting option 1")
            ability = 1
            slot = 10 - idx1[0] + 1
        elif prob2 > prob1 and prob2 > prob3:
            print("selecting option 2")
            ability = 2
            slot = 10 - idx2[0] + 1
        elif prob1 == prob2 and prob1 > prob3:
            if self.pref_ability == 1:
                print("selecting option 1")
                ability = 1
                slot = 10 - idx1[0] + 1
            else:
                print("selecting option 2")
                ability = 2
                slot = 10 - idx2[0] + 1
        else:
            print("selecting option 3")
            ability = 3
            slot = 10 - idx3[0] + 1

        self.facet(ability, slot)
        print("sequence: ", self.prob.sequence)
        self.run()

    def facet(self, ability, slot):
        if ability == 1:
            y_coordinate = 373
            pyautogui.moveTo(x=1170, y=383)
            time.sleep(0.3)
            pyautogui.click(button='left')
        elif ability == 2:
            y_coordinate = 466
            pyautogui.moveTo(x=1170, y=472)
            time.sleep(0.3)
            pyautogui.click(button='left')
        else:
            y_coordinate = 595
            pyautogui.moveTo(x=1170, y=599)
            time.sleep(0.3)
            pyautogui.click(button='left')

        x_coordinate = 733 + (slot - 1) * 38
        print(f"Faceting ability {ability} in slot {slot} at {x_coordinate}, {y_coordinate}")

        if ability == 3:
            success_file = f"{self.script_dir}/assets/faceting/faceting_success_decrease.png"
            success_file_step = f"{self.script_dir}/assets/faceting/faceting_success_decrease_step.png"
        else:
            success_file = f"{self.script_dir}/assets/faceting/faceting_success_increase.png"
            success_file_step = f"{self.script_dir}/assets/faceting/faceting_success_increase_step.png"

        while True:
            try:
                pyautogui.locateOnScreen(
                    success_file,
                    confidence=0.95,
                    region=(x_coordinate, y_coordinate, 38, 38))
                self.prob.sequence.append([ability, True])
                break
            except pyautogui.ImageNotFoundException:
                pass

            try:
                pyautogui.locateOnScreen(
                    success_file_step,
                    confidence=0.95,
                    region=(x_coordinate, y_coordinate, 38, 38))
                self.prob.sequence.append([ability, True])
                break
            except pyautogui.ImageNotFoundException:
                pass

            try:
                pyautogui.locateOnScreen(
                    f"{self.script_dir}/assets/faceting/faceting_fail.png",
                    confidence=0.95,
                    region=(x_coordinate, y_coordinate, 38, 38))
                self.prob.sequence.append([ability, False])
                break
            except pyautogui.ImageNotFoundException:
                pass


def faceting_start_process(**kwargs):
    # Set up logging configuration in the child process
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting faceting process...")

    faceting = Faceting(**kwargs)
    faceting.run()


if __name__ == '__main__':
    # prob = Probability(ABILITY_STONE_RELIC, 9, 7, 0)
    # prob.sequence = [[2, False], [2, False]]
    #
    # current_probability = prob.cal_p_from_seq()
    # idx1 = prob.cal_idx_from_seq(0, 1)
    # idx2 = prob.cal_idx_from_seq(0, 2)
    # idx3 = prob.cal_idx_from_seq(10, 3)
    # print("current: probability: {:.0f}%".format(prob.decode_p(current_probability) * 100))
    #
    # prob1 = prob.cal_prob1_safe(idx1[0], idx2[0], idx3[0], current_probability, idx1[2], idx2[2], idx3[1])
    # prob2 = prob.cal_prob2_safe(idx1[0], idx2[0], idx3[0], current_probability, idx1[2], idx2[2], idx3[1])
    # prob3 = prob.cal_prob3_safe(idx1[0], idx2[0], idx3[0], current_probability, idx1[2], idx2[2], idx3[1])
    # print("current probability for option 1: {:.10f}%".format(prob1 * 100))
    # print("current probability for option 2: {:.10f}%".format(prob2 * 100))
    # print("current probability for option 3: {:.10f}%".format(prob3 * 100))

    if len(sys.argv) > 5:
        options = {
            "pref_ability": int(sys.argv[1]),
            "goal1": int(sys.argv[2]),
            "goal2": int(sys.argv[3]),
            "goal3": int(sys.argv[4]),
            "goals": int(sys.argv[5]),
        }
        Faceting(options).run()
    else:
        Faceting().run()

if __name__ == '__main__2':
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 5:
        faceting_kwargs = {
            'faceting_options': {
                "pref_ability": int(sys.argv[1]),
                "goal1": int(sys.argv[2]),
                "goal2": int(sys.argv[3]),
                "goal3": int(sys.argv[4]),
                "goals": int(sys.argv[5]),
            }
        }
    else:
        faceting_kwargs = {}

    # Set up process with target function `start_game_process` and pass the kwargs
    p = multiprocessing.Process(
        target=faceting_start_process(**faceting_kwargs),
        kwargs=faceting_kwargs,
        name="Faceting"
    )
    p.start()

    start_time = time.time()
    while True:
        if not p.is_alive():
            print("process has terminated")
            break

        if keyboard.is_pressed('esc'):
            print("esc key pressed, terminating process")
            p.terminate()
            break

        if time.time() - start_time > 10 * 60:
            print("10 minutes have passed, terminating process")
            p.terminate()
            break

        # sleep for 0.1 seconds to avoid 100% CPU usage
        time.sleep(0.1)
