# AbilityStoneCutter

AbilityStoneCutter is a Python tool for simulating and analyzing the faceting process of ability stones, commonly found
in games. It provides probability calculations, faceting simulations, and engraving management to help users optimize
their results.

## Setup
1. Install Python
   Make sure you have Python 3.13 or newer installed.  
   Download Python: https://www.python.org/downloads/

2. Create a Virtual Environment
   Open a terminal in the project directory and run:

    ```bash
    python -m venv .venv
    ```

   Activate the virtual environment:

   On Windows:
    ```bash
    .venv\Scripts\activate
   ```

   On macOS/Linux:
   ```bash
   source .venv/Scripts/activate
   ```

3. Install Requirements
   With the virtual environment activated, install dependencies:

    ```bash
    pip install -r requirements.txt 
    ```

## Configuration
Edit the `settings.py` file to set your preferences for the faceting process.  

1. priorities:  
You can adjust the priorities for different engraving types if needed (currently from average stats in sheet: https://docs.google.com/spreadsheets/d/1RTa1IWdPuYoTGg0CwD-RCXZYn8iBTNHemjaMYyeoHSs/edit?gid=0#gid=0)

2. possible_engravings:  
Probably the most important setting, here you just put all the engravings your character can use on a stone. 
Special case if you only use one engraving it'll cut all stones with that engraving, 
if you use two engravings it will cut all stones that engraving. 
Else it'll require at least two out of the listed engravings.

3. negative_engraving_max:  
Here you can configure what level you want as maximum for negative engravings.

4. faceting_options:  
Here you can configure the general options. `goals` is the combined successes for both abilities, 
16 will be either 9/7 or 7/9 stones (with 8/8 excluded). 
14 will be 7/7, 9/6, etc. with all abilities below 6 getting excluded.  
`verbose` is how talkative the script is, if you want to see all the details of the faceting process set it to True.
`goal1` and `goal2` are only relevant if you want to cut a single stone with a specific goal,

## Usage
Run the main script:

```bash
python main.py
```

There is also a PowerShell and bash script to ensure the virtualenv and run the script

On Windows:
```bash
.\bin\run.ps1
```

On macOS/Linux:
```bash
./bin/run.sh
```

## Features
 - Simulate ability stone faceting
 - Calculate probabilities for faceting outcomes
 - Log faceting sessions for later analysis

## License
