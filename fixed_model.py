# fixed_model.py
import simpy, csv, random, threading, time
from quiet import FRoad, FCar, sample_reaction_time, completed_cars
from fixed import FTrafficLightFixed, FJunctionFixed  # Fixed-traffic light and junction classes
from display import animate_network, display_statistics
from config import (GRID_ROWS, GRID_COLS, SIM_DURATION, DISPLAY_INTERVAL,
                    BASE_MEAN, RANDOM_SEED, FIXED_TIMINGS_CSV, DEFAULT_RED_TIME,
                    DEFAULT_GREEN_TIME, DEFAULT_AMBER_TIME, DEFAULT_RED_AMBER_TIME,
                    HORIZONTAL_ROAD_LENGTH, VERTICAL_ROAD_LENGTH)

def create_grid_roads(grid_junctions):
    connections = []
    rows = len(grid_junctions)
    cols = len(grid_junctions[0])
    # Horizontal connections.
    for i in range(rows):
        for j in range(cols - 1):
            left_junc = grid_junctions[i][j]
            right_junc = grid_junctions[i][j+1]
            src = left_junc.base if hasattr(left_junc, "base") else left_junc
            dst = right_junc.base if hasattr(right_junc, "base") else right_junc
            connections.append((src, dst, "GREEN", HORIZONTAL_ROAD_LENGTH))
            connections.append((dst, src, "GREEN", HORIZONTAL_ROAD_LENGTH))
    # Vertical connections.
    for i in range(rows - 1):
        for j in range(cols):
            top_junc = grid_junctions[i][j]
            bottom_junc = grid_junctions[i+1][j]
            src = top_junc.base if hasattr(top_junc, "base") else top_junc
            dst = bottom_junc.base if hasattr(bottom_junc, "base") else bottom_junc
            connections.append((src, dst, "RED", VERTICAL_ROAD_LENGTH))
            connections.append((dst, src, "RED", VERTICAL_ROAD_LENGTH))
    return connections

def create_junction(env, i, j, total_rows, total_cols):
    # For simplicity, using the fixed junction class for every junction.
    return FJunctionFixed(env, f"Junction_{i}_{j}", start=True, end=True, weight=1)

def get_statistics(roads):
    total_wait = 0
    count = 0
    # Car stats from vehicles that are still in queues.
    for road in roads:
        for car in road.car_queue.items:
            total_wait += getattr(car, "wait_time", 0)
            count += 1
    # Plus statistics from cars that have finished (logged in completed_cars).
    for data in completed_cars:
        total_wait += data.get("wait_time", 0)
        count += 1
    avg_wait = total_wait / count if count > 0 else 0
    return {"avg_wait": avg_wait}

def fixed_main(filename=FIXED_TIMINGS_CSV, candidate_timings=None, sim_duration=SIM_DURATION,
               rows=GRID_ROWS, cols=GRID_COLS, display_interval=DISPLAY_INTERVAL,
               random_seed=RANDOM_SEED, headless=False):
    random.seed(random_seed)
    env = simpy.Environment()
    
    # Create grid junctions.
    grid_junctions = []
    for i in range(rows):
        row_list = []
        for j in range(cols):
            row_list.append(create_junction(env, i, j, rows, cols))
        grid_junctions.append(row_list)
    
    # Create grid roads.
    connections = create_grid_roads(grid_junctions)
    
    # Load candidate timings from CSV if candidate_timings is not provided.
    if candidate_timings is None:
        candidate_timings = {}
        try:
            with open(filename, "r") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    road_name = row["road"]
                    candidate_timings[road_name] = (float(row["red_time"]),
                                                    float(row["green_time"]),
                                                    float(row["amber_time"]),
                                                    float(row["red_amber_time"]))
        except FileNotFoundError:
            pass

    roads = []
    for source, dest, init_color, road_length in connections:
        road_name = f"Road_{source.name}_{dest.name}"
        new_road = FRoad(road_name, speed=13, distance=road_length,
                         junction_start=source,
                         junction_end=dest,
                         car_queue=simpy.Store(env))
        if road_name in candidate_timings:
            rt, gt, at, rat = candidate_timings[road_name]
        else:
            rt, gt, at, rat = DEFAULT_RED_TIME, DEFAULT_GREEN_TIME, DEFAULT_AMBER_TIME, DEFAULT_RED_AMBER_TIME
        new_road.traffic_light = FTrafficLightFixed(env, new_road,
                                                    red_time=rt,
                                                    green_time=gt,
                                                    red_amber_time=rat,
                                                    amber_time=at,
                                                    colour=init_color)
        try:
            source.add_light(new_road.traffic_light)
        except Exception:
            pass
        try:
            dest.add_light(new_road.traffic_light)
        except Exception:
            pass
        roads.append(new_road)
    
    # Generate cars.
    cars_data = []
    def delayed_car_release(env, release_time, car):
        yield env.timeout(release_time)
        yield env.process(car.run())
    for i in range(100):
        # Choose a starting road from junctions that allow entry.
        startable = [road for road in roads if hasattr(road.junction_start, "start") and road.junction_start.start]
        chosen = random.choice(startable)
        reaction_time = sample_reaction_time(mean=1.0, std=0.2)
        release_time = random.expovariate(1/BASE_MEAN)
        car = FCar(env, f"Car_{i}", chosen, roads, reaction_time=reaction_time)
        env.process(delayed_car_release(env, release_time, car))
        cars_data.append({"reaction_time": reaction_time, "road": chosen, "release_time": release_time})
    
    if not headless:
        def run_simulation():
            while env.now < sim_duration:
                env.run(until=env.now + 1)
                time.sleep(1)
        sim_thread = threading.Thread(target=run_simulation)
        sim_thread.start()
        animate_network(env, roads, grid_rows=rows, grid_cols=cols,
                        update_interval=display_interval, save_to_file="fixed_timing.mp4")
        sim_thread.join()
    else:
        env.run(until=sim_duration)
    
    stats = get_statistics(roads)
    display_statistics(roads)
    
    return {"cars_data": cars_data, "roads": roads, "stats": stats}

if __name__ == "__main__":
    fixed_main()

