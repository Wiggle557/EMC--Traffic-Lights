# config.py

# General simulation settings
GRID_ROWS = 3
GRID_COLS = 3
SIM_DURATION = 20          # seconds
DISPLAY_INTERVAL = 1         # seconds for animation updates
BASE_MEAN = 9                # mean for car release (exponential distribution)
RANDOM_SEED = 42

# Fixed model timing defaults
FIXED_TIMINGS_CSV = "final_timings.csv"
DEFAULT_RED_TIME = 15
DEFAULT_GREEN_TIME = 15
DEFAULT_AMBER_TIME = 3
DEFAULT_RED_AMBER_TIME = 3

# Actuated model timing defaults (for actuated_model.py, if needed)
ACTUATED_TIMINGS_CSV = "final_actuated_timings.csv"
DEFAULT_ACT_RED_TIME = 15
DEFAULT_ACT_GREEN_TIME = 15
DEFAULT_ACT_AMBER_TIME = 3
DEFAULT_ACT_RED_AMBER_TIME = 3

# Genetic algorithm parameters (if used)
GA_GENERATIONS = 15
GA_POPULATION_SIZE = 30
GA_MUTATION_RATE = 0.2
GA_MUTATION_STRENGTH = 1.0
GA_THRESHOLD = 5.0
GA_PENALTY_FACTOR = 1.0

