# fixed_model.py
import simpy
import csv
from quiet import FRoad, FCar  # Reuse the other classes as needed.
from qsetup import Fsetup, Fcreate_grid_roads
from fixed import FTrafficLightFixed, FJunctionFixed  # Our new fixed-timing classes

def import_timings_csv(filename="final_timings.csv"):
    """
    Imports timing settings from a CSV file.
    The CSV file is expected to have columns: road, red_time, green_time, amber_time, red_amber_time.
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

def display_statistics(roads):
    """
    Computes and displays a few aggregate metrics at the end of the simulation.
    """
    total_passes = 0
    count_cars = 0
    total_wait = 0

    # Note: Depending on when cars are removed from queues, you may need to capture this data elsewhere.
    # Here, we assume that cars remain in the road.car_queue after completing their journey
    # and that each FCar has attributes `.junction_passes` and `.wait_time`
    for road in roads:
        for car in road.car_queue.items:
            total_passes += car.junction_passes
            total_wait += getattr(car, "wait_time", 0)
            count_cars += 1

    avg_wait = total_wait / count_cars if count_cars > 0 else 0

    print("\nSimulation Statistics:")
    print("----------------------")
    print(f"Total Junction Passes: {total_passes}")
    print(f"Average Junction Passes per Car: {total_passes / count_cars if count_cars > 0 else 0:.2f}")
    print(f"Average Waiting Time per Car: {avg_wait:.2f} seconds\n")
    
    print("Final Traffic Signal Timings and States:")
    for road in roads:
        lt = road.traffic_light
        print(f"{road.name}: RED={lt.red_time} s, GREEN={lt.green_time} s, AMBER={lt.amber_time} s, "
              f"RED-AMBER={lt.red_amber_time} s, Final Phase={lt.colour}")

def fixed_main():
    # Set up simulation environment.
    env = simpy.Environment()

    # Grid size for junctions.
    ROWS = 3
    COLS = 3
    until = 600
    num_junctions = ROWS * COLS
    junction_names = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    # Use the fixed junction variant.
    junctions: list[FJunctionFixed] = []

    # For simplicity, assign a default weight (or you could compute using your POI functions).
    weights = [[1 for j in range(COLS)] for i in range(ROWS)]
    for i in range(num_junctions):
        junctions.append(FJunctionFixed(env, f"{junction_names[i]}", weight=weights[i // COLS][i % COLS]))
    
    # Generate the grid structure.
    junc_grid = []
    for i in range(ROWS):
        row = []
        for j in range(COLS):
            row.append(i * COLS + j)
        junc_grid.append(row)
    
    # Generate internal road connections.
    road_connections = Fcreate_grid_roads(junc_grid)

    # Import fixed timings from CSV.
    fixed_timings = import_timings_csv("final_timings.csv")

    roads = []
    for connection in road_connections:
        start_idx, end_idx, initial_color = connection
        new_road = FRoad(
            f"Road_{junctions[start_idx].name}_{junctions[end_idx].name}",
            speed=13,
            distance=100,
            junction_start=junctions[start_idx],
            junction_end=junctions[end_idx],
            car_queue=simpy.Store(env)
        )
        # Look up fixed timings using the road's name.
        if new_road.name in fixed_timings:
            rt, gt, at, rat = fixed_timings[new_road.name]
        else:
            rt, gt, at, rat = 15, 15, 3, 3  # defaults if not found
        new_road.traffic_light = FTrafficLightFixed(
            env,
            new_road,
            red_time=rt,
            green_time=gt,
            red_amber_time=rat,
            amber_time=at,
            colour=initial_color
        )
        junctions[end_idx].add_light(new_road.traffic_light)
        roads.append(new_road)
    
    # -------------------------
    # Create Entrances (Inroads) on the Top Row.
    # -------------------------
    inroads = []
    for j in range(COLS):
        exit_index = j  # Top row junction index.
        entrance = FJunctionFixed(env, f"In_{junctions[exit_index].name}", start=True)
        road_in = FRoad(
            f"Road_{entrance.name}_{junctions[exit_index].name}",
            speed=13,
            distance=100,
            junction_start=entrance,
            junction_end=junctions[exit_index],
            car_queue=simpy.Store(env)
        )
        if road_in.name in fixed_timings:
            rt, gt, at, rat = fixed_timings[road_in.name]
        else:
            rt, gt, at, rat = 15, 15, 3, 3
        road_in.traffic_light = FTrafficLightFixed(
            env,
            road_in,
            red_time=rt,
            green_time=gt,
            red_amber_time=rat,
            amber_time=at,
            colour="RED"
        )
        junctions[exit_index].add_light(road_in.traffic_light)
        inroads.append(road_in)

    # -------------------------
    # Create Exits (Outroads) on the Bottom Row.
    # -------------------------
    outroads = []
    for j in range(COLS):
        exit_index = (ROWS - 1) * COLS + j  # Bottom row junction.
        exit_junc = FJunctionFixed(env, f"Out_{junctions[exit_index].name}", end=True)
        road_out = FRoad(
            f"Road_{junctions[exit_index].name}_{exit_junc.name}",
            speed=13,
            distance=100,
            junction_start=junctions[exit_index],
            junction_end=exit_junc,
            car_queue=simpy.Store(env)
        )
        if road_out.name in fixed_timings:
            rt, gt, at, rat = fixed_timings[road_out.name]
        else:
            rt, gt, at, rat = 15, 15, 3, 3
        road_out.traffic_light = FTrafficLightFixed(
            env,
            road_out,
            red_time=rt,
            green_time=gt,
            red_amber_time=rat,
            amber_time=at,
            colour="RED"
        )
        exit_junc.add_light(road_out.traffic_light)
        outroads.append(road_out)

    roads.extend(inroads)
    roads.extend(outroads)
    
    # Also add the entrance and exit junctions to the overall list.
    for road in inroads:
        junctions.append(road.junction_start)
    for road in outroads:
        junctions.append(road.junction_end)
    
    # Use the same car setup as before.
    env.process(Fsetup(env, 100, roads, base_mean=9))
    env.run(until=until)
    
    # Display statistics at the end of simulation.
    display_statistics(roads)

if __name__ == "__main__":
    fixed_main()
