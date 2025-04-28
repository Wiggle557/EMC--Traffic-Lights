# main.py
import fixed_model
import actuated_model
import genetic_algorithm

def main():
    print("Select a simulation mode:")
    print("  sim    - Fixed simulation using the fixed timing CSV")
    print("  simdef - Fixed simulation using default fixed timings (no CSV)")
    print("  act    - Actuated simulation")
    print("  ga     - Genetic algorithm")
    choice = input("Enter your choice: ").strip().lower()

    if choice == "sim":
        # Run fixed simulation using the CSV (candidate_timings remains None)
        fixed_model.fixed_main(headless=False)
    elif choice == "simdef":
        # Run fixed simulation using default timings (ignoring CSV by passing an empty dictionary)
        fixed_model.fixed_main(candidate_timings={}, headless=False)
    elif choice == "act":
        actuated_model.actuated_main(headless=False)
    elif choice == "ga":
        genetic_algorithm.run_genetic_algorithm()
    else:
        print("Invalid option selected.")

if __name__ == "__main__":
    main()

