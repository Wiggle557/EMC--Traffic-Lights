import simpy
import csv
import random
from qsetup import Fcreate_grid_roads, sample_reaction_time
from fixed import FTrafficLightFixed, FJunctionFixed
from quiet import FRoad, FCar

# Global seed for deterministic behavior
RANDOM_SEED = 42

# ------------------------------
# Import Timing Settings
# ------------------------------
def import_timings_csv(filename="final_timings.csv"):
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

# ------------------------------
# Display Statistics
# ------------------------------
def display_statistics(roads):
    """
    Computes and displays a few aggregate metrics at the end of the simulation.
    """
    total_passes = 0
    count_cars = 0
    total_wait = 0

    # Collect statistics from cars in each road's queue.
    for road in roads:
        for car in road.car_queue.items:
            total_passes += car.junction_passes
            total_wait += getattr(car, "wait_time", 0)
            count_cars += 1

    # Compute averages.
    avg_wait = total_wait / count_cars if count_cars > 0 else 0

    print("\nSimulation Statistics:")
    print("----------------------")
    print(f"Total Junction Passes: {total_passes}")
    print(f"Average Junction Passes per Car: {total_passes / count_cars if count_cars > 0 else 0:.2f}")
    print(f"Average Waiting Time per Car: {avg_wait:.2f} seconds\n")

    print("Final Traffic Signal Timings and States:")
    for road in roads:
        light = road.traffic_light
        print(f"{road.name}: RED={light.red_time} s, GREEN={light.green_time} s, AMBER={light.amber_time} s, "
              f"RED-AMBER={light.red_amber_time} s, Final Phase={light.colour}")

def generate_cars(env, num_cars, roads, base_mean, cars_data=None):
    """
    Generate cars deterministically across multiple runs.

    Parameters:
      env: simpy.Environment for simulation.
      num_cars: Total number of cars to generate.
      roads: List of FRoad objects (available roads).
      base_mean: Mean arrival interval for cars (Poisson-distributed).
      cars_data: If provided, use pre-generated car data (reaction times, road choices).
    """
    cars = []  # Always initialize or reuse cars list.
    for i in range(num_cars):
        if cars_data:
            car_data = cars_data[i]
            reaction_time = car_data["reaction_time"]
            release_time = car_data["release_time"]
            # Map the saved road object to the corresponding road in the current simulation.
            road_name = car_data["road"].name
            chosen_road = next(road for road in roads if road.name == road_name)
        else:
            # Randomly select an entrance road and reaction time.
            startable_roads = [road for road in roads if hasattr(road.junction_start, "start") and road.junction_start.start]
            weights = [1 / (len(road.car_queue.items) + 1) for road in startable_roads]
            chosen_road = random.choices(startable_roads, weights=weights)[0]
            reaction_time = sample_reaction_time(mean=1.0, std=0.2)
            release_time = random.expovariate(1 / base_mean)
            cars.append({"reaction_time": reaction_time, "road": chosen_road, "release_time": release_time})

        # Create and schedule the car in the environment.
        car = FCar(env, f"Car_{i}", chosen_road, roads, reaction_time=reaction_time)
        env.process(delayed_car_release(env, release_time, car))

    return cars

def delayed_car_release(env, release_time, car):
    """
    Release a car into the simulation after a delay (release_time).
    """
    yield env.timeout(release_time)
    yield env.process(car.run())

def fixed_main(filename="final_timings.csv", cars_data=None):
    """
    Fixed main function to run the simulation.
    Ensures reproducible timings and car generation.
    """
    random.seed(RANDOM_SEED)
    env = simpy.Environment()
    ROWS, COLS = 3, 3
    until = 600

    grid_junctions = [[FJunctionFixed(env, f"Junction_{i}_{j}", start=False, end=False, weight=1) for j in range(COLS)] for i in range(ROWS)]
    junctions = [j for row in grid_junctions for j in row]
    junc_grid = [[i * COLS + j for j in range(COLS)] for i in range(ROWS)]
    road_connections = Fcreate_grid_roads(junc_grid)

    fixed_timings = import_timings_csv(filename)
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
        rt, gt, at, rat = fixed_timings.get(road_name, (15, 15, 3, 3))
        new_road.traffic_light = FTrafficLightFixed(env, new_road, rt, gt, rat, at, initial_color)
        junctions[end_idx].add_light(new_road.traffic_light)
        roads.append(new_road)

    inroads = [FRoad(f"Road_In_Junction_{i}_0", speed=13, distance=100, junction_start=FJunctionFixed(env, f"In_Junction_{i}_0", start=True), junction_end=grid_junctions[0][i], car_queue=simpy.Store(env)) for i in range(COLS)]
    for road in inroads:
        rt, gt, at, rat = fixed_timings.get(road.name, (15, 15, 3, 3))
        road.traffic_light = FTrafficLightFixed(env, road, rt, gt, rat, at, "RED")
        road.junction_end.add_light(road.traffic_light)
    outroads = [FRoad(f"Road_Junction_{i}_2_Out", speed=13, distance=100, junction_start=grid_junctions[2][i], junction_end=FJunctionFixed(env, f"Out_Junction_{i}_2", end=True), car_queue=simpy.Store(env)) for i in range(COLS)]
    for road in outroads:
        rt, gt, at, rat = fixed_timings.get(road.name, (15, 15, 3, 3))
        road.traffic_light = FTrafficLightFixed(env, road, rt, gt, rat, at, "RED")
        road.junction_start.add_light(road.traffic_light)
    roads.extend(inroads + outroads)

    # Generate cars and run simulation
    cars_data = generate_cars(env, 100, roads, 9, cars_data)
    env.run(until=until)

    # Display statistics
    display_statistics(roads)

    return cars_data

if __name__ == "__main__":
    saved_cars = fixed_main()
    fixed_main("best_candidate_timings.csv", cars_data=saved_cars)

