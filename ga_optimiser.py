# ga_optimisation.py
import simpy
import csv
import random
import numpy as np
from scipy.stats import truncnorm

# Import shared setup and helper functions
from qsetup import Fsetup, Fcreate_grid_roads, sample_arrival_interval, sample_reaction_time
from fixed import FTrafficLightFixed, FJunctionFixed
from quiet import FRoad, FCar

def import_timings_csv(filename="final_timings.csv"):
    """
    Imports timing settings from a CSV file.
    The CSV file is expected to have columns:
      road, red_time, green_time, amber_time, red_amber_time.
    Returns a dictionary mapping road names to a tuple of timings.
    """
    timings = {}
    with open(filename, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            road_name = row["road"]
            timings[road_name] = (
                float(row["red_time"]),
                float(row["green_time"]),
                float(row["amber_time"]),
                float(row["red_amber_time"])
            )
    return timings

def simulate_fixed(candidate, num_cars=50, sim_duration=600):
    """
    Runs a fixed-timing simulation using candidate timings.
    
    candidate: dict with keys "red", "green", "amber", "red_amber"
    num_cars: number of cars to generate.
    sim_duration: simulation running time (in seconds)
    
    Returns a tuple (fitness, roads) where:
      fitness = negative average wait time (lower wait is fitter),
      roads = list of road objects created during the simulation.
    """
    env = simpy.Environment()
    ROWS = 3
    COLS = 3

    # Create grid junctions using naming "Junction_i_j"
    grid_junctions = []
    for i in range(ROWS):
        row = []
        for j in range(COLS):
            row.append(FJunctionFixed(env, f"Junction_{i}_{j}", start=False, end=False, weight=1))
        grid_junctions.append(row)
    # Flatten the grid list.
    junctions = [j for row in grid_junctions for j in row]
    
    # Build grid indices for road connection creation.
    junc_grid = []
    for i in range(ROWS):
        row_indices = [i * COLS + j for j in range(COLS)]
        junc_grid.append(row_indices)
    
    # Create internal road connections.
    road_connections = Fcreate_grid_roads(junc_grid)
    roads = []
    for connection in road_connections:
        start_idx, end_idx, initial_color = connection
        road_name = f"Road_{junctions[start_idx].name}_{junctions[end_idx].name}"
        new_road = FRoad(
            road_name,
            speed=13,
            distance=100,
            junction_start=junctions[start_idx],
            junction_end=junctions[end_idx],
            car_queue=simpy.Store(env)
        )
        new_road.traffic_light = FTrafficLightFixed(
            env,
            new_road,
            red_time=candidate["red"],
            green_time=candidate["green"],
            red_amber_time=candidate["red_amber"],
            amber_time=candidate["amber"],
            colour=initial_color
        )
        # Attach the traffic light to the end junction.
        junctions[end_idx].add_light(new_road.traffic_light)
        roads.append(new_road)
        
    # Create inroads (entrances) along the top row.
    inroads = []
    for j in range(COLS):
        target_junc = grid_junctions[0][j]
        entrance = FJunctionFixed(env, f"In_{target_junc.name}", start=True)
        road_name = f"Road_{entrance.name}_{target_junc.name}"
        road_in = FRoad(
            road_name,
            speed=13,
            distance=100,
            junction_start=entrance,
            junction_end=target_junc,
            car_queue=simpy.Store(env)
        )
        road_in.traffic_light = FTrafficLightFixed(
            env,
            road_in,
            red_time=candidate["red"],
            green_time=candidate["green"],
            red_amber_time=candidate["red_amber"],
            amber_time=candidate["amber"],
            colour="RED"
        )
        target_junc.add_light(road_in.traffic_light)
        inroads.append(road_in)
    
    # Create outroads (exits) along the bottom row.
    outroads = []
    for j in range(COLS):
        target_junc = grid_junctions[ROWS-1][j]
        exit_junc = FJunctionFixed(env, f"Out_{target_junc.name}", end=True)
        road_name = f"Road_{target_junc.name}_{exit_junc.name}"
        road_out = FRoad(
            road_name,
            speed=13,
            distance=100,
            junction_start=target_junc,
            junction_end=exit_junc,
            car_queue=simpy.Store(env)
        )
        road_out.traffic_light = FTrafficLightFixed(
            env,
            road_out,
            red_time=candidate["red"],
            green_time=candidate["green"],
            red_amber_time=candidate["red_amber"],
            amber_time=candidate["amber"],
            colour="RED"
        )
        exit_junc.add_light(road_out.traffic_light)
        outroads.append(road_out)
    
    # Combine all roads.
    roads.extend(inroads)
    roads.extend(outroads)
    
    # Optionally add inroad/outroad junctions to the junction list.
    for rd in inroads:
        junctions.append(rd.junction_start)
    for rd in outroads:
        junctions.append(rd.junction_end)
    
    # Launch the car-generation process.
    env.process(generate_cars(env, num_cars, roads, base_mean=9))
    env.run(until=sim_duration)
    
    # Gather simulation statistics.
    total_wait = 0
    total_cars = 0
    for road in roads:
        for car in road.car_queue.items:
            total_wait += getattr(car, "wait_time", 0)
            total_cars += 1

    avg_wait = total_wait / total_cars if total_cars > 0 else float('inf')
    fitness = -avg_wait  # Lower wait times yield higher fitness.
    return fitness, roads

def generate_cars(env, num_cars, roads, base_mean):
    """
    Simplified car-generation process.
    """
    i = 0
    while i < num_cars:
        # Only choose roads whose starting junction is marked as an entry.
        startable_roads = [road for road in roads if hasattr(road.junction_start, "start") and road.junction_start.start]
        if not startable_roads:
            break
        weights = [1 / (len(road.car_queue.items) + 1) for road in startable_roads]
        chosen_road = random.choices(startable_roads, weights=weights)[0]
        reaction_time = sample_reaction_time(mean=1.0, std=0.2)
        # Import FCar from the actuated module.
        from quiet import FCar
        car = FCar(env, f"Car_{i}", chosen_road, roads, reaction_time=reaction_time)
        env.process(car.run())
        i += 1
        interval = sample_arrival_interval(base_mean)
        yield env.timeout(interval)

# -------------------------------
# Genetic Algorithm Functions
# -------------------------------

def initialize_population(pop_size):
    """
    Initialize a population of candidate timing solutions.
    """
    population = []
    for _ in range(pop_size):
        red = random.uniform(10, 20)
        amber = random.uniform(2, 5)
        red_amber = amber  # Assuming symmetry
        max_green = red - (amber + red_amber) if red > (amber + red_amber) else 10
        green = random.uniform(10, max_green)
        
        candidate = {
            "red": red,
            "green": green,
            "amber": amber,
            "red_amber": red_amber
        }
        population.append(candidate)
    return population


def evaluate_population(population):
    """
    Evaluate each candidate by running the simulation.
    Returns a list of tuples: (candidate, fitness).
    """
    evaluated = []
    for candidate in population:
        fitness, _ = simulate_fixed(candidate)
        evaluated.append((candidate, fitness))
    return evaluated

def select_parents(evaluated, num_parents):
    """
    Tournament selection of parent candidates.
    """
    selected = []
    tournament_size = 3
    for _ in range(num_parents):
        tournament = random.sample(evaluated, tournament_size)
        best = max(tournament, key=lambda x: x[1])
        selected.append(best[0])
    return selected

def crossover(parent1, parent2):
    """
    Create an offspring candidate by averaging parent parameters.
    """
    offspring = {
        "red": (parent1["red"] + parent2["red"]) / 2,
        "green": (parent1["green"] + parent2["green"]) / 2,
        "amber": (parent1["amber"] + parent2["amber"]) / 2,
        "red_amber": (parent1["red_amber"] + parent2["red_amber"]) / 2,
    }
    return offspring

def mutate(candidate, mutation_rate=0.1):
    if random.random() < mutation_rate:
        candidate["red"] += random.uniform(-1, 1)
    if random.random() < mutation_rate:
        candidate["green"] += random.uniform(-2, 2)
    if random.random() < mutation_rate:
        candidate["amber"] += random.uniform(-0.5, 0.5)
    if random.random() < mutation_rate:
        candidate["red_amber"] += random.uniform(-0.5, 0.5)
    
    # Enforce symmetry for intermediary phases
    candidate["red_amber"] = candidate["amber"]
    
    # Enforce green time limit
    amber_total = candidate["amber"] + candidate["red_amber"]
    max_green = candidate["red"] - amber_total if candidate["red"] > amber_total else 10
    candidate["green"] = max(10, min(max_green, candidate["green"]))
    
    # Ensure parameters remain within bounds
    candidate["red"] = max(10, min(20, candidate["red"]))
    candidate["green"] = max(10, min(40, candidate["green"]))
    candidate["amber"] = max(2, min(5, candidate["amber"]))
    candidate["red_amber"] = candidate["amber"]
    return candidate


def genetic_algorithm(pop_size=10, generations=5):
    """
    Run the genetic algorithm:
      1. Initialize a population.
      2. For a number of generations, evaluate each candidate, select parents,
         perform crossover and mutation to form a new population.
      3. Return the best candidate found.
    """
    population = initialize_population(pop_size)
    
    best_candidate = None
    best_fitness = -float('inf')
    
    for gen in range(generations):
        print(f"Generation {gen}:")
        evaluated = evaluate_population(population)
        for candidate, fitness in evaluated:
            print(f"Candidate: {candidate} -> Fitness: {fitness}")
            if fitness > best_fitness:
                best_fitness = fitness
                best_candidate = candidate
        parents = select_parents(evaluated, pop_size // 2)
        offspring = []
        while len(offspring) < pop_size - len(parents):
            parent1, parent2 = random.sample(parents, 2)
            child = crossover(parent1, parent2)
            child = mutate(child)
            offspring.append(child)
        population = parents + offspring
    
    print("\nBest Candidate:", best_candidate)
    print("Best Fitness:", best_fitness)
    return best_candidate

def export_best_candidate_timings(candidate, roads, filename="best_candidate_timings.csv"):
    """
    Exports the best candidate timings to a CSV file.
    Each road is assigned the candidate timings.
    """
    fieldnames = ["road", "red_time", "green_time", "amber_time", "red_amber_time"]
    
    with open(filename, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for road in roads:
            writer.writerow({
                "road": road.name,
                "red_time": candidate["red"],
                "green_time": candidate["green"],
                "amber_time": candidate["amber"],
                "red_amber_time": candidate["red_amber"]
            })

if __name__ == "__main__":
    best_candidate = genetic_algorithm(pop_size=100, generations=100)
    best_fitness, roads = simulate_fixed(best_candidate)
    export_best_candidate_timings(best_candidate, roads)

