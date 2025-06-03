# controller.py
from config import GRID_ROWS, GRID_COLS, SIM_DURATION, DISPLAY_INTERVAL, RANDOM_SEED
import fixed_model

# (You could also import your actuated model here if needed.)


def run_fixed():
    print("Running fixed simulation with composite junctions...")
    fixed_model.fixed_main(
        filename="final_timings.csv",
        sim_duration=SIM_DURATION,
        rows=GRID_ROWS,
        cols=GRID_COLS,
        display_interval=DISPLAY_INTERVAL,
        random_seed=RANDOM_SEED,
        headless=False,  # Real‐time display mode.
    )


if __name__ == "__main__":
    choice = input("Run (sim)ulation or (ga) genetic optimization? ").strip().lower()
    if choice == "sim":
        run_fixed()
    elif choice == "ga":
        import genetic_algorithm

        genetic_algorithm.run_genetic_algorithm()
    else:
        print("Invalid choice!")
