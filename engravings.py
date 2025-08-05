import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from os.path import realpath, dirname

import PIL.Image
import cv2
import numpy as np
from PIL import ImageGrab


class EngravingDetector:
    # mapping for engraving names
    mapping = ENGRAVING_MAPPING = {
        # positive engravings
        "adrenaline.png": "Adrenaline",
        "aoa.png": "All-Out Attack",
        "am.png": "Ambush Master",
        "awk.png": "Awakening",
        "barricade.png": "Barricade",
        "broken_bone.png": "Broken Bone",
        "contender.png": "Contender",
        "cris_evasion.png": "Crisis Evasion",
        "crushing_fist.png": "Crushing Fist",
        "cd.png": "Cursed Doll",
        "disrespect.png": "Disrespect",
        "divine_protection.png": "Divine Protection",
        "drops.png": "Drops of Ether",
        "emergency_rescue.png": "Emergency Rescue",
        "enhanced_shield.png": "Enhanced Shield",
        "ep.png": "Ether Predator",
        "expert.png": "Expert",
        "explosive_expert.png": "Explosive Expert",
        "fortitude.png": "Fortitude",
        "grudge.png": "Grudge",
        "ha.png": "Heavy Armor",
        "hm.png": "Hit Master",
        "kbw.png": "Keen Blunt Weapon",
        "lightning_fury.png": "Lightning Fury",
        "magick_stream.png": "Magick Stream",
        "mi.png": "Mass Increase",
        "mb.png": "Master Brawler",
        "mt.png": "Master's Tenacity",
        "max_mp.png": "Max MP Increase",
        "master_of_escape.png": "Master of Escape",
        "mpe.png": "MP Efficiency Increase",
        "necromancy.png": "Necromancy",
        "pd.png": "Precise Dagger",
        "preemptive.png": "Preemptive Strike",
        "propulsion.png": "Propulsion",
        "rc.png": "Raid Captain",
        "shield_piercing.png": "Shield Piercing",
        "sight_focus.png": "Sight Focus",
        "sa.png": "Spirit Absorption",
        "ss.png": "Stabilized Status",
        "strong_will.png": "Strong Will",
        "sc.png": "Super Charge",
        "vph.png": "Vital Point Hit",
        # negative engravings
        "negative_ap.jpg": "Atk. Power Reduction",
        "negative_as.jpg": "Atk. Speed Reduction",
        "negative_dr.jpg": "Defense Reduction",
        "negative_ms.jpg": "Move Speed Reduction",
    }

    def __init__(self, threshold: float = 0.85, max_pos: int = 2, max_neg: int = 1, num_workers: int = None):
        """
        initialize the engraving detector with the given parameters.

        :param threshold: min matchTemplate score to count as “found”
        :param max_pos: how many positives to pick
        :param max_neg: how many negatives to pick
        :param num_workers: threads to use (None = os.cpu_count())
        """
        self.img_color = None
        self.script_dir = realpath(dirname(__file__))
        self.threshold = threshold
        self.max_pos = max_pos
        self.max_neg = max_neg
        self.num_workers = num_workers or os.cpu_count()

        # preload all templates
        self.templates_pos = self._load_templates("assets/engravings/positive")
        self.templates_neg = self._load_templates("assets/engravings/negative")

    def _load_templates(self, folder: str) -> list[dict]:
        """
        load every image in folder into a list of dicts {fn, img, w, h}.

        :param folder: str: folder containing template images
        :return: list[dict]: list of templates with their properties
        """
        abs_folder = os.path.join(self.script_dir, folder)
        templates = []
        for fn in sorted(os.listdir(abs_folder)):
            if not fn.lower().endswith((".png", "jpg", "jpeg")):
                continue
            path = os.path.join(abs_folder, fn)
            tpl = cv2.imread(path)
            if tpl is None:
                continue
            h, w = tpl.shape[:2]
            templates.append({"fn": fn, "img": tpl, "w": w, "h": h})
        return templates

    def _match_one(self, tpl_dict: dict) -> dict | None:
        """
        run template-matching, return dict with match info if >= threshold.

        :param tpl_dict: dict: template dict with keys {fn, img, w, h}
        :return: dict | None: match info or None if no match found
        """
        fn = tpl_dict['fn']
        tpl = tpl_dict['img']
        h, w = tpl_dict['h'], tpl_dict['w']
        # run multi-channel matchTemplate
        res = cv2.matchTemplate(self.img_color, tpl, cv2.TM_CCOEFF_NORMED)
        _, maxv, _, maxloc = cv2.minMaxLoc(res)

        if maxv < self.threshold:
            return None

        x, y = maxloc
        return {
            'fn': fn,
            'score': maxv,
            'x': x, 'y': y,
            'w': w, 'h': h
        }

    def _collect(self, positive: bool = True) -> list[dict]:
        """
        collect all matches >= threshold from the chosen template set.

        :param positive: bool: True for positive engravings, False for negative
        :return: list[dict]: list of detected engravings with their properties
        """
        tpl_list = self.templates_pos if positive else self.templates_neg
        cands = []

        with ThreadPoolExecutor(max_workers=self.num_workers) as exe:
            futures = {exe.submit(self._match_one, tpl): tpl['fn'] for tpl in tpl_list}
            for fut in as_completed(futures):
                res = fut.result()
                if res:
                    cands.append(res)

        return cands

    def _detect(self) -> list[dict]:
        """
        return the final selected engravings as a sorted list (top -> bottom).

        :return: list[dict]: list of detected engravings with their properties
        """
        pos_cands = self._collect(positive=True)
        neg_cands = self._collect(positive=False)

        # pick top scores
        pos_sel = sorted(pos_cands, key=lambda c: c['score'], reverse=True)[:self.max_pos]
        neg_sel = sorted(neg_cands, key=lambda c: c['score'], reverse=True)[:self.max_neg]

        # sort positives by y (top first) and enumerate
        for idx, cand in enumerate(sorted(pos_sel, key=lambda c: c['y'])):
            cand['position-index'] = idx

        selected = pos_sel + neg_sel
        # sort by y-coordinate
        selected.sort(key=lambda c: c['y'])
        return selected

    def detect_from_image(self, image: str | PIL.Image.Image) -> list[dict]:
        """
        detect engravings from a given image instead of a file path.

        :param image: str or PIL.Image.Image: path to the image file or a PIL Image object
        :return: list[dict]: list of detected engravings with their properties
        """
        if isinstance(image, str):
            img = cv2.imread(image)
        else:
            img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        if img is None:
            raise FileNotFoundError(f"Cannot load image: {image}")

        self.img_color = img
        return self._detect()


class EngravingSelector(EngravingDetector):
    """
    Extended selector that filters and orders detected engravings based on:
      - possible_engravings: whitelist of engraving names to consider
      - priorities: list of engraving names in descending order of importance
      - negative_engraving_max: per-negative-engraving caps
    """

    def __init__(
            self,
            possible_engravings: list[str],
            priorities: list[str],
            negative_engraving_max: dict[str, int],
            threshold: float = 0.85,
            max_pos: int = 2,
            max_neg: int = 1,
            num_workers: int = None,
    ):
        # initialize detection parameters
        super().__init__(threshold=threshold, max_pos=max_pos, max_neg=max_neg, num_workers=num_workers)
        self.possible_engravings = possible_engravings
        self.priorities = priorities
        self.negative_engraving_max = negative_engraving_max

    def get_selection(self, results: list[dict]) -> dict:
        """
        from detect()'s results (top‐N positives + top‐N negatives):
          - prioritization: up to max_pos from all_selected, ordered by your priorities
          - negative_selection: best negative per type with cap info
          - all_selected: those same results, each tagged with is_possible

        :param results: list of detected engravings
        :return: dict containing 'prioritization', 'negative_selection', and 'all_selected'
        """
        # friendly name + possible‐flag on every entry
        named = []
        for res in results:
            name = self.mapping.get(res['fn'], res['fn'])
            res['name'] = name
            # mark if in your whitelist
            res['is_possible'] = (name in self.possible_engravings)
            named.append(res)

        # split detection‐level positives vs negatives by negative_engraving_max keys
        neg_keys = set(self.negative_engraving_max)
        det_positives = [r for r in named if r['name'] not in neg_keys]
        det_negatives = [r for r in named if r['name'] in neg_keys]

        # pick top‐N by score (these are your "selected" for cutting, etc.)
        pos_sel = sorted(det_positives, key=lambda c: c['score'], reverse=True)[:self.max_pos]
        neg_sel = sorted(det_negatives, key=lambda c: c['score'], reverse=True)[:self.max_neg]

        # build your prioritized positives in the order of self.priorities
        prioritized = []
        for pr in self.priorities:
            for r in pos_sel:
                if r['name'] == pr:
                    prioritized.append(r)
                    break
            if len(prioritized) >= self.max_pos:
                break

        # enforce per‐negative caps on neg_sel
        from collections import defaultdict
        neg_groups = defaultdict(list)
        for r in neg_sel:
            neg_groups[r['name']].append(r)

        negative_selection = []
        for name, cap in self.negative_engraving_max.items():
            if cap <= 0:
                continue
            group = neg_groups.get(name, [])
            if not group:
                continue
            best = max(group, key=lambda x: x['score'])
            best['cap'] = cap
            best['is_negative'] = True
            negative_selection.append(best)

        # all_selected = exactly pos_sel + neg_sel
        all_selected = pos_sel + neg_sel

        return {
            'prioritization': prioritized,
            'negative_selection': negative_selection,
            'all_selected': all_selected,
        }

    @staticmethod
    def could_detect_negatives(results: dict) -> bool:
        """
        check if the engraving selector could detect negative engravings.

        :param results: dict: the results from the engraving detection.
        :return: True if negative engravings are possible, False otherwise
        """
        return bool(results.get('negative_selection'))

    def should_cut(self, results: dict) -> bool:
        """
        check if the ability stone should be cut based on the results.

        :param results: dict: the results from the engraving detection.
        :return: True if the results should be cut, False otherwise
        """
        # special case: if only one possible engraving, and it's detected, always cut
        if len(self.possible_engravings) == 1:
            single = self.possible_engravings[0]
            if any(r.get('name') == single for r in results.get('all_selected', [])):
                return True

        # require full match counts
        if len(results.get('prioritization', [])) != self.max_pos or \
                len(results.get('negative_selection', [])) != self.max_neg:
            return False

        # ensure no disallowed non-whitelist positives
        for engraving in results.get('all_selected', []):
            if not engraving.get('is_possible', False) and not engraving.get('is_negative', False):
                return False

        return True

    def pretty_print_results(self, results: dict) -> None:
        """
        pretty print the results of the engraving selection.

        :param results: dict containing 'prioritization' and 'negative_selection'
        """
        selected = results.get('all_selected', [])
        prioritized = results.get('prioritization', [])
        negatives = results.get('negative_selection', [])

        print("Detected engravings (✅ = in whitelist, ⚠️ = not):")
        for c in selected:
            # either in whitelist or is an unavoidable negative and has a cap
            mark = '✅' if c['is_possible'] or c.get('is_negative', False) == True else '⚠️'
            pos = c.get('position-index', '-')
            print(f" {mark} {c['name']:20s} file={c['fn']:20s} score={c['score']:<20.3f} pos={pos}")

        if not prioritized:
            print("⚠️  No positive engravings matched the given criteria.")
        elif len(prioritized) < self.max_pos:
            print(
                f"⚠️  Only {len(prioritized)} positive engravings matched the given criteria, expected {self.max_pos}.")
            print("\nPrioritized positives:")
            for c in prioritized:
                print(f" • {c['name']:20s} file={c['fn']:20s} score={c['score']:<20.3f} pos={c['position-index']}")
        else:
            print("\nPrioritized positives (highest priority first):")
            for c in prioritized:
                print(f" • {c['name']:20s} file={c['fn']:20s} score={c['score']:<20.3f} pos={c['position-index']}")

        if not negatives:
            print("⚠️  No negative engravings detected.")
        elif len(negatives) < self.max_neg:
            print(f"⚠️  Only {len(negatives)} negative engravings matched the given criteria, expected {self.max_neg}.")
            print("\nNegative engravings:")
            for c in negatives:
                print(f" • {c['name']:20s} file={c['fn']:20s} score={c['score']:<20.3f} cap={c['cap']}")
        else:
            print("\nNegative engraving:")
            for c in negatives:
                print(f" • {c['name']:20s} file={c['fn']:20s} score={c['score']:<20.3f} cap={c['cap']}")


if __name__ == '__main__':
    from settings import Settings

    # instantiate selector
    selector = EngravingSelector(
        possible_engravings=Settings.possible_engravings,
        priorities=Settings.priorities,
        negative_engraving_max=Settings.negative_engraving_max,
        threshold=0.85,
        max_pos=2,
        max_neg=1,
        num_workers=4,
    )

    # capture screen and detect/select
    screenshot = ImageGrab.grab()
    screenshot = 'test/img_8.png'
    raw_results = selector.detect_from_image(screenshot)
    results = selector.get_selection(raw_results)

    selector.pretty_print_results(results)
    if selector.should_cut(results):
        print("\n✅  Engraving selection is complete and meets the criteria.")
    else:
        print("\n⚠️  Engraving selection does not meet the criteria, skipping.")

    if selector.could_detect_negatives(results):
        print("✅  Negative engravings were properly detected.")
    else:
        print("⚠️  Negative engravings were not detected.")
