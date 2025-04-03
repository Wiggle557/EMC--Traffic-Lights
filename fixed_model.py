# fixed_model.py
import simpy
import csv
from qsetup import Fsetup, Fcreate_grid_roads, sample_arrival_interval, sample_reaction_time
from fixed import FTrafficLightFixed, FJunctionFixed  # the fixed-timing controller classes
from quiet import FRoad, FCar  # shared classes

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
        light = road.traffic_light
        print(f"{road.name}: RED={light.red_time} s, GREEN={light.green_time} s, AMBER={light.amber_time} s, "
              f"RED-AMBER={light.red_amber_time} s, Final Phase={light.colour}")



def fixed_main(filename="final_timings.csv"):
    # Create SimPy environment.
    env = simpy.Environment()
    
    # Grid configuration.
    ROWS = 3
    COLS = 3
    until = 600  # simulation duration in seconds

    # Create grid junctions using row/column nomenclature.
    grid_junctions = []
    for i in range(ROWS):
        row = []
        for j in range(COLS):
            # Use the same naming convention as main.py: "Junction_i_j"
            row.append(FJunctionFixed(env, f"Junction_{i}_{j}", start=False, end=False, weight=1))
        grid_junctions.append(row)
        
    # Flatten the grid junction list.
    junctions = [j for row in grid_junctions for j in row]
    
    # Build a grid of indices for creating road connections.
    junc_grid = []
    for i in range(ROWS):
        row_indices = []
        for j in range(COLS):
            row_indices.append(i * COLS + j)
        junc_grid.append(row_indices)
    
    # Create internal road connections using the helper function.
    road_connections = Fcreate_grid_roads(junc_grid)
    
    # Import fixed timing settings from CSV.
    fixed_timings = import_timings_csv(filename)
    
    roads = []
    # Create roads between grid junctions.
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
        # Look up timings from CSV; fall back to defaults if not found.
        if road_name in fixed_timings:
            rt, gt, at, rat = fixed_timings[road_name]
        else:
            rt, gt, at, rat = 15, 15, 3, 3
        new_road.traffic_light = FTrafficLightFixed(
            env,
            new_road,
            red_time=rt,
            green_time=gt,
            red_amber_time=rat,
            amber_time=at,
            colour=initial_color
        )
        # Attach the traffic light to the end junction.
        junctions[end_idx].add_light(new_road.traffic_light)
        roads.append(new_road)
        
    # Create inroads (entrances) along the top row.
    inroads = []
    for j in range(COLS):
        # Use the junction from the first row.
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
        if road_name in fixed_timings:
            rt, gt, at, rat = fixed_timings[road_name]
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
        if road_name in fixed_timings:
            rt, gt, at, rat = fixed_timings[road_name]
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
    
    # Add inroads and outroads to the overall list of roads.
    roads.extend(inroads)
    roads.extend(outroads)
    
    # Optionally, add the entrance and exit junctions to the junction list.
    for rd in inroads:
        junctions.append(rd.junction_start)
    for rd in outroads:
        junctions.append(rd.junction_end)
    
    # Launch the car-generation process (using the shared setup from qsetup.py).
    env.process(Fsetup(env, 100, roads, base_mean=9))
    
    # Run the simulation.
    env.run(until=until)
    
    # Collect and display statistics.
    timings = {}
    total_passes = 0
    # For each road, record its final traffic light timings and aggregate junction passes.
    for road in roads:
        timings[road.name] = [
            road.traffic_light.red_time,
            road.traffic_light.green_time,
            road.traffic_light.amber_time,
            road.traffic_light.red_amber_time
        ]
        for car in road.car_queue.items:
            total_passes += car.junction_passes
    display_statistics(roads)
    print("Average Timings:", timings)
    # Assuming 100 cars were generated.
    print("Average Junction Passes:", total_passes / 100)


if __name__ == "__main__":
    fixed_main()
    fixed_main("best_candidate_timings.csv")
