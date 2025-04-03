import simpy
from quiet import FTrafficLight, FRoad, FJunction
from qsetup import Fsetup, Fcreate_grid_roads
import math
import random

import csv

def export_timings_csv(timings, filename="final_timings.csv"):
    """
    Exports the final timing values to a CSV file.
    
    timings: dict mapping road name -> [red_time, green_time, amber_time, red_amber_time]
    filename: Name of the CSV file.
    """
    fieldnames = ["road", "red_time", "green_time", "amber_time", "red_amber_time"]
    with open(filename, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for road, values in timings.items():
            writer.writerow({
                "road": road,
                "red_time": values[0],
                "green_time": values[1],
                "amber_time": values[2],
                "red_amber_time": values[3]
            })

# Example usage after your run loop:
# ---------------------------
# Helper: Compute weight from POI(s)
# ---------------------------
def compute_weight(i, j, poi_list):
    """
    For a junction at grid coordinates (i, j),
    return a weight that is highest when the junction is near one of the POIs.
    This example uses Manhattan distance and computes:
      weight = max_{poi in poi_list} (1/(d+1))
    where d is the Manhattan distance between (i,j) and the POI.
    """
    if not poi_list:
        return 1.0  # default weight if no POIs specified
    weights = []
    for (pi, pj) in poi_list:
        d = abs(i - pi) + abs(j - pj)
        weights.append(1 / (d + 1))
    return max(weights)

# ---------------------------
# Main Simulation Setup
# ---------------------------
def quiet_main():
    env = simpy.Environment()

    # Grid dimensions.
    ROWS = 3
    COLS = 3
    until = 400

    # Specify one or more POI positions (row, col) in grid coordinates.
    # For example, if you want the center to be a POI:
    poi_list = [(1, 1)]
    
    # Create grid junctions (inside the grid). We use nested loops so that we know each 
    # junction's (i,j) coordinate. Also, set the weight based on proximity to a POI.
    grid_junctions = []
    for i in range(ROWS):
        row_junc = []
        for j in range(COLS):
            # In this example, junctions on the top row (i == 0) are not only within the grid
            # but will later receive an inroad; junctions on bottom row (i==ROWS-1) will receive an outroad.
            start_flag = False
            end_flag   = False
            # We'll mark them as grid junctions even though the actual entry
            # and exit functions will be implemented via inroads/outroads.
            # (They are the terminals for the internal network.)
            row_junc.append(FJunction(env, f"Junction_{i}_{j}", start=start_flag, end=end_flag, 
                                       weight=compute_weight(i, j, poi_list)))
        grid_junctions.append(row_junc)

    # Flatten the grid junction list into one list (preserving order)
    junctions = [junc for row in grid_junctions for junc in row]

    # Create the grid structure (a 2D list of indices) to feed into Fcreate_grid_roads.
    # Here, the index corresponds to the position in 'junctions'.
    junc_grid = []
    for i in range(ROWS):
        row = []
        for j in range(COLS):
            row.append(i * COLS + j)
        junc_grid.append(row)

    # Generate road connections inside the grid, e.g., connecting adjacent junctions.
    road_connections = Fcreate_grid_roads(junc_grid)

    # Create the internal roads and assign traffic lights.
    roads = []
    for connection in road_connections:
        start_idx, end_idx, initial_color = connection
        new_road = FRoad(f"Road_{junctions[start_idx].name}_{junctions[end_idx].name}",
                         speed=13, distance=150,
                         junction_start=junctions[start_idx],
                         junction_end=junctions[end_idx],
                         car_queue=simpy.Store(env))
        new_road.traffic_light = FTrafficLight(env, new_road, red_time=15, green_time=15, 
                                               amber_time=3, red_amber_time=3, colour=initial_color)
        # Add the light to the end junction.
        junctions[end_idx].add_light(new_road.traffic_light)
        roads.append(new_road)
        
    # -------------------------------------------------
    # Create inroads (entrances) on the top edge of the grid.
    # For each junction in the top row (i==0), create an inroad.
    # -------------------------------------------------
    inroads = []
    for j in range(COLS):
        grid_idx = j  # top row: i=0 so index = j.
        # Create a new junction that acts as the entry point.
        entrance_junc = FJunction(env, f"In_Junction_{grid_junctions[0][j].name}", start=True)
        # Create an FRoad from the entrance junction to the corresponding grid junction.
        road_in = FRoad(f"Road_{entrance_junc.name}_{grid_junctions[0][j].name}",
                        speed=13, distance=100,
                        junction_start=entrance_junc,
                        junction_end=grid_junctions[0][j],
                        car_queue=simpy.Store(env))
        road_in.traffic_light = FTrafficLight(env, road_in, red_time=15, green_time=15,
                                               amber_time=3, red_amber_time=3, colour="RED")
        # Add the traffic light to the terminated (internal) junction.
        grid_junctions[0][j].add_light(road_in.traffic_light)
        inroads.append(road_in)
        
    # -------------------------------------------------
    # Create outroads (exits) on the bottom edge of the grid.
    # For each junction in the bottom row (i==ROWS-1), create an outroad.
    # -------------------------------------------------
    outroads = []
    for j in range(COLS):
        grid_idx = (ROWS - 1) * COLS + j
        exit_junc = FJunction(env, f"Out_Junction_{grid_junctions[ROWS-1][j].name}", end=True)
        road_out = FRoad(f"Road_{grid_junctions[ROWS-1][j].name}_{exit_junc.name}",
                         speed=13, distance=100,
                         junction_start=grid_junctions[ROWS-1][j],
                         junction_end=exit_junc,
                         car_queue=simpy.Store(env))
        road_out.traffic_light = FTrafficLight(env, road_out, red_time=15, green_time=15,
                                               amber_time=3, red_amber_time=3, colour="RED")
        # Add the traffic light to the exit junction.
        exit_junc.add_light(road_out.traffic_light)
        outroads.append(road_out)
    
    # Add the inroads and outroads to the main road list.
    roads.extend(inroads)
    roads.extend(outroads)
    
    # Add the new entrance and exit junctions to the overall junction list.
    for road in inroads:
        junctions.append(road.junction_start)
    for road in outroads:
        junctions.append(road.junction_end)
    
    # Initialize the car setup.
    env.process(Fsetup(env, 200, roads, base_mean=9))

    # Run the simulation.
    env.run(until=until)

    # Collect statistics.
    timings = {}
    total_passes = 0
    for road in roads:
        timings[road.name] = [road.traffic_light.red_time,
                              road.traffic_light.green_time,
                              road.traffic_light.amber_time,
                              road.traffic_light.red_amber_time]
        for car in road.car_queue.items:
            total_passes += car.junction_passes
    return total_passes, timings


if __name__ == "__main__":
    total_runs = 200
    total_passes = 0
    timings = {}
    for _ in range(total_runs):
        passes, timing = quiet_main()
        total_passes += passes
        for key, values in timing.items():
            if key not in timings:
                timings[key] = [0] * len(values)
            for j, val in enumerate(values):
                timings[key][j] += val
    for key, values in timings.items():
        timings[key] = [val / total_runs for val in values]
    export_timings_csv(timings, filename="final_timings.csv")
    
    print(f"Average Timings: {timings}")
    print(f"Average Junction Passes: {total_passes / total_runs}")
