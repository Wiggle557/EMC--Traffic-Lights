# config.py

# -----------------------------
# General Simulation Settings
# -----------------------------
GRID_ROWS = 7
GRID_COLS = 7
SIM_DURATION = 600         # Total simulation time in seconds.
DISPLAY_INTERVAL = 2         # Animation update interval in seconds.
BASE_MEAN = 9                # Base mean for exponential car release.
RANDOM_SEED = 42

# -----------------------------
# Road Length Settings
# -----------------------------
HORIZONTAL_ROAD_LENGTH = 135  # Length in meters for horizontal roads.
VERTICAL_ROAD_LENGTH = 120    # Length in meters for vertical roads.

# -----------------------------
# Timing Defaults for Fixed Model
# -----------------------------
FIXED_TIMINGS_CSV = "final_timings.csv"
DEFAULT_RED_TIME = 40
DEFAULT_GREEN_TIME = 40
DEFAULT_AMBER_TIME = 3
DEFAULT_RED_AMBER_TIME = 3

# -----------------------------
# Timing Defaults for Actuated Model
# -----------------------------
ACTUATED_TIMINGS_CSV = "final_actuated_timings.csv"
DEFAULT_ACT_RED_TIME = 15
DEFAULT_ACT_GREEN_TIME = 15
DEFAULT_ACT_AMBER_TIME = 3
DEFAULT_ACT_RED_AMBER_TIME = 3

# -----------------------------
# Genetic Algorithm Parameters
# -----------------------------
GA_GENERATIONS = 30
GA_POPULATION_SIZE = 25
GA_MUTATION_RATE = 0.2
GA_MUTATION_STRENGTH = 1.0
GA_THRESHOLD = 5.0
GA_PENALTY_FACTOR = 1.0

# -----------------------------
# Points of Interest (POI)
# -----------------------------
# This dictionary maps node names (or junction identifiers) to an "attraction factor."
# Higher values indicate that more vehicles are likely to head toward these points.
POINTS_OF_INTEREST = {
    "Junction_0_6": 2.0,
    "Junction_0_5": 1.5,
    "Junction_1_6": 1.5,
    # Add additional points as required.
}

# -----------------------------
# Rush Hour Settings
# -----------------------------
# Specifies a rush hour period with a traffic multiplier.
# The simulation logic can use these values to increase the car generation rate (or volume)
# during the rush hour period.
RUSH_HOUR = {
    "start": 300,        # Rush hour begins at 300 seconds (example).
    "end": 301,          # Rush hour ends at 600 seconds.
    "multiplier": 1.5    # 50% increase in traffic during rush hour.
}

