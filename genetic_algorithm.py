# genetic_algorithm.py
import random, copy
from fixed_model import fixed_main
from config import (
    GRID_ROWS, GRID_COLS, RANDOM_SEED,
    GA_GENERATIONS, GA_POPULATION_SIZE, GA_MUTATION_RATE, GA_MUTATION_STRENGTH,
    GA_THRESHOLD, GA_PENALTY_FACTOR
)

# Global variable to hold the road network from a preliminary simulation run.
_global_roads = None

def get_junction_keys(rows, cols):
    """Return a list of junction keys, e.g. 'Junction_0_0', 'Junction_0_1', etc."""
    keys = []
    for i in range(rows):
        for j in range(cols):
            keys.append(f"Junction_{i}_{j}")
    return keys

def generate_random_gene():
    """Generate a random gene (tuple of timings) for a junction."""
    red = random.uniform(10, 20)
    green = random.uniform(10, 20)
    amber = random.uniform(2, 4)
    red_amber = random.uniform(2, 4)
    return (red, green, amber, red_amber)

def generate_candidate(junction_keys):
    """Generate one candidate mapping each junction key to a gene."""
    candidate = {}
    for key in junction_keys:
        candidate[key] = generate_random_gene()
    return candidate

def construct_candidate_timings(candidate, roads):
    """
    Build a dictionary mapping road names to timing tuples.
    For horizontal roads (initial GREEN) use candidate gene directly;
    for vertical roads (initial RED) swap red and green.
    """
    candidate_timings = {}
    for road in roads:
        # Determine the group key from the source's name if possible.
        if "Junction_" in road.junction_start.name:
            group_key = road.junction_start.name
        elif "Junction_" in road.junction_end.name:
            group_key = road.junction_end.name
        else:
            group_key = road.junction_start.name
        gene = candidate.get(group_key, generate_random_gene())
        init_color = getattr(road.traffic_light, "colour", "RED")
        if init_color.upper() == "GREEN":
            candidate_timings[road.name] = gene
        else:
            # Vertical roads: complementary gene (swap red and green)
            candidate_timings[road.name] = (gene[1], gene[0], gene[2], gene[3])
    return candidate_timings

def penalty_for_candidate(candidate, threshold=GA_THRESHOLD, penalty_factor=GA_PENALTY_FACTOR):
    """
    Add a penalty for each junction gene with too little difference between red and green.
    """
    penalty = 0.0
    for key, gene in candidate.items():
        diff = abs(gene[0] - gene[1])
        if diff < threshold:
            penalty += penalty_factor * (threshold - diff)
    return penalty

def evaluate_candidate(candidate):
    """
    Evaluate a candidate:
      1. Convert candidate into road-wise timings.
      2. Run the fixed model simulation in headless mode.
      3. Retrieve average wait time and add the penalty.
    Lower fitness is better.
    """
    global _global_roads
    if _global_roads is None:
        sim_result = fixed_main(
            headless=True,
            rows=GRID_ROWS,
            cols=GRID_COLS,
            sim_duration=10,
            random_seed=random.randint(1, 100000)
        )
        _global_roads = sim_result["roads"]
    candidate_timings = construct_candidate_timings(candidate, _global_roads)
    result = fixed_main(
        candidate_timings=candidate_timings,
        headless=True,
        rows=GRID_ROWS,
        cols=GRID_COLS,
        sim_duration=600,
        random_seed=random.randint(1, 100000)
    )
    avg_wait = result["stats"]["avg_wait"]
    pen = penalty_for_candidate(candidate)
    return avg_wait + pen

def crossover(parent1, parent2, junction_keys):
    """For each junction key, randomly choose gene from one of the parents."""
    child = {}
    for key in junction_keys:
        child[key] = parent1[key] if random.random() < 0.5 else parent2[key]
    return child

def mutate(candidate, mutation_rate=GA_MUTATION_RATE, mutation_strength=GA_MUTATION_STRENGTH):
    """Mutate candidate genes by adding noise."""
    new_candidate = copy.deepcopy(candidate)
    for key in candidate.keys():
        if random.random() < mutation_rate:
            red, green, amber, red_amber = candidate[key]
            red += random.uniform(-mutation_strength, mutation_strength)
            green += random.uniform(-mutation_strength, mutation_strength)
            amber += random.uniform(-mutation_strength/2, mutation_strength/2)
            red_amber += random.uniform(-mutation_strength/2, mutation_strength/2)
            new_candidate[key] = (max(5, red), max(5, green), max(1, amber), max(1, red_amber))
    return new_candidate

def run_genetic_algorithm(generations=GA_GENERATIONS, population_size=GA_POPULATION_SIZE):
    """Run the genetic algorithm over a fixed number of generations."""
    junction_keys = get_junction_keys(GRID_ROWS, GRID_COLS)
    population = [generate_candidate(junction_keys) for _ in range(population_size)]
    global _global_roads
    if _global_roads is None:
        sim_result = fixed_main(
            headless=True,
            rows=GRID_ROWS,
            cols=GRID_COLS,
            sim_duration=10,
            random_seed=random.randint(1, 100000)
        )
        _global_roads = sim_result["roads"]
    for gen in range(generations):
        scored_population = []
        for candidate in population:
            fitness = evaluate_candidate(candidate)
            scored_population.append((candidate, fitness))
        scored_population.sort(key=lambda x: x[1])
        best_candidate, best_fitness = scored_population[0]
        print(f"Generation {gen}: Best Fitness = {best_fitness}")
        new_population = [best_candidate]  # Elitism: keep best candidate.
        while len(new_population) < population_size:
            parent1 = random.choice(scored_population)[0]
            parent2 = random.choice(scored_population)[0]
            child = crossover(parent1, parent2, junction_keys)
            child = mutate(child)
            new_population.append(child)
        population = new_population
    print("Best candidate:", best_candidate)
    return best_candidate

if __name__ == "__main__":
    best = run_genetic_algorithm()
    print("Optimized candidate gene timings per junction:")
    for key, gene in best.items():
        # Horizontal timings are as-is; vertical timings swap red and green.
        print(f"{key}: Horizontal = {gene}, Vertical = ({gene[1]}, {gene[0]}, {gene[2]}, {gene[3]})")

