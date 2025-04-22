# main.py
from controller import run_fixed  # Assumes run_fixed runs the fixed simulation.
from genetic_algorithm import run_genetic_algorithm
import actuated_model
from config import RANDOM_SEED

def main():
    choice = input("Enter 'sim' for fixed simulation, 'act' for actuated simulation, or 'ga' for genetic algorithm: ").strip().lower()
    if choice == "sim":
        run_fixed()
    elif choice == "act":
        print("Running actuated simulation...")
        actuated_model.actuated_main()
    elif choice == "ga":
        run_genetic_algorithm()
    else:
        print("Invalid option.")

if __name__ == "__main__":
    main()

