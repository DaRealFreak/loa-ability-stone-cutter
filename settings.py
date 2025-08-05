class Settings:
    # calculate your own engraving priorities based on your stats here: https://docs.google.com/spreadsheets/d/1RTa1IWdPuYoTGg0CwD-RCXZYn8iBTNHemjaMYyeoHSs/edit?gid=0#gid=0
    priorities = [
        # Support engravings
        "Awakening",
        "Drops of Ether",
        # 6.61%
        "Precise Dagger",
        # 5.17%
        "MP Efficiency Increase",
        # 5.16%
        "Adrenaline",
        # 5.13%
        "Cursed Doll",
        "Hit Master",
        "Master's Tenacity",
        "Stabilized Status",
        "Barricade",
        "Propulsion",
        # 5.04%
        "Mass Increase",
        # 5.03%
        "Raid Captain",
        # 5.02%
        "Ambush Master",
        "Master Brawler",
        # 4.96%
        "Grudge",
        "Super Charge",
        "All-Out Attack",
        # 4.95%
        "Ether Predator",
        # 4.71%
        "Keen Blunt Weapon",
    ]

    possible_engravings = [
        "Cursed Doll",
        "Grudge",
        "Raid Captain",
        "Adrenaline",
        "MP Efficiency Increase",
        "Precise Dagger",
        "Hit Master",
    ]

    # if only 1 single engraving is selected, it will cut all stones with that engraving
    #possible_engravings = ["Awakening"]

    # Uncomment this line to use all engravings from the mapping (for f.e. 10/x awakening stone)
    # possible_engravings = EngravingDetector.ENGRAVING_MAPPING.values()

    # caps for negative engravings
    negative_engraving_max = {
        "Atk. Power Reduction": 4,
        "Atk. Speed Reduction": 10,
        "Defense Reduction": 10,
        "Move Speed Reduction": 10,
    }

    """
    Faceting options for the engraving selection process.
    
    - goal1: The first goal engraving, either 0 for total mode or the required successful clicks
    - goal2: The second goal engraving, either 0 for total mode or the required successful clicks
    - goals: The total number of goals to achieve, 16 for 97, 14 for 77 or 0 for individual mode
    """
    faceting_options = {
        "goal1": 0,
        "goal2": 0,
        "goals": 16,
        "verbose": False,
    }
