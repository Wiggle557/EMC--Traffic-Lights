# actuated_model.py
import simpy, csv, random, threading, time
from fixed import FJunctionFixed
from actuated import ATrafficLightActuated
from quiet import FRoad, FCar
from display import animate_network, display_statistics
from config import (
    GRID_ROWS, GRID_COLS, SIM_DURATION, DISPLAY_INTERVAL, BASE_MEAN, RANDOM_SEED,
    ACTUATED_TIMINGS_CSV, DEFAULT_ACT_RED_TIME, DEFAULT_ACT_GREEN_TIME,
    DEFAULT_ACT_AMBER_TIME, DEFAULT_ACT_RED_AMBER_TIME
)

# Composite Junction for Actuated Model
class CompositeJunctionActuated:
    def __init__(self, env, base_name, i, j, total_rows, total_cols):
        self.env = env
        self.base_name = base_name
        self.base = FJunctionFixed(env, base_name, start=True, end=True, weight=1)
        self.sides = {}
        if i == 0:
            self.sides["top"] = FJunctionFixed(env, f"Top_{base_name}", start=True, end=True, weight=1)
        if i == total_rows - 1:
            self.sides["bottom"] = FJunctionFixed(env, f"Bottom_{base_name}", start=True, end=True, weight=1)
        if j == 0:
            self.sides["left"] = FJunctionFixed(env, f"Left_{base_name}", start=True, end=True, weight=1)
        if j == total_cols - 1:
            self.sides["right"] = FJunctionFixed(env, f"Right_{base_name}", start=True, end=True, weight=1)
        self.connectors = {}
        for side, node in self.sides.items():
            conn_name = f"Connector_{side}_{base_name}"
            connector = FRoad(conn_name, speed=100, distance=1,
                              junction_start=node,
                              junction_end=self.base,
                              car_queue=simpy.Store(env))
            connector.traffic_light = ATrafficLightActuated(
                env, connector,
                red_time=1, green_time=1, red_amber_time=0.5, amber_time=0.5,
                initial_state="GREEN"
            )
            self.connectors[side] = connector

    def get_side(self, direction):
        return self.sides.get(direction, self.base)

    def add_light(self, light):
        self.base.add_light(light)
        for node in self.sides.values():
            node.add_light(light)

# Helper functions to create junctions and roads.
def create_junction(env, i, j, total_rows, total_cols):
    if i == 0 or i == total_rows - 1 or j == 0 or j == total_cols - 1:
        return CompositeJunctionActuated(env, f"Junction_{i}_{j}", i, j, total_rows, total_cols)
    else:
        return FJunctionFixed(env, f"Junction_{i}_{j}", start=True, end=True, weight=1)

def create_grid_roads(grid_junctions):
    connections = []
    rows = len(grid_junctions)
    cols = len(grid_junctions[0])
    # Horizontal connections (GREEN)
    for i in range(rows):
        for j in range(cols - 1):
            left_junc = grid_junctions[i][j]
            right_junc = grid_junctions[i][j+1]
            src = left_junc.base if hasattr(left_junc, "base") else left_junc
            dst = right_junc.base if hasattr(right_junc, "base") else right_junc
            connections.append((src, dst, "GREEN"))
            connections.append((dst, src, "GREEN"))
    # Vertical connections (RED)
    for i in range(rows - 1):
        for j in range(cols):
            top_junc = grid_junctions[i][j]
            bottom_junc = grid_junctions[i+1][j]
            src = top_junc.base if hasattr(top_junc, "base") else top_junc
            dst = bottom_junc.base if hasattr(bottom_junc, "base") else bottom_junc
            connections.append((src, dst, "RED"))
            connections.append((dst, src, "RED"))
    return connections

def import_timings_csv(filename=ACTUATED_TIMINGS_CSV):
    timings = {}
    try:
        with open(filename, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                road_name = row["road"]
                timings[road_name] = (float(row["red_time"]),
                                      float(row["green_time"]),
                                      float(row["amber_time"]),
                                      float(row["red_amber_time"]))
    except FileNotFoundError:
        pass
    return timings

def generate_cars(env, num_cars, roads, base_mean, cars_data=None):
    cars = cars_data if cars_data else []
    for i in range(num_cars):
        if cars_data:
            data = cars_data[i]
            reaction_time = data["reaction_time"]
            release_time = data["release_time"]
            road_name = data["road"].name
            chosen = next(road for road in roads if road.name == road_name)
        else:
            startable = [road for road in roads if (road.junction_start is None) or 
                         (hasattr(road.junction_start, "start") and road.junction_start.start)]
            weights = [1/(len(road.car_queue.items)+1) for road in startable]
            chosen = random.choices(startable, weights=weights)[0]
            reaction_time = random.uniform(0.8, 1.2)
            release_time = random.expovariate(1/base_mean)
            cars.append({"reaction_time": reaction_time, "road": chosen, "release_time": release_time})
        car = FCar(env, f"Car_{i}", chosen, roads, reaction_time=reaction_time)
        env.process(delayed_car_release(env, release_time, car))
    return cars

def delayed_car_release(env, release_time, car):
    yield env.timeout(release_time)
    yield env.process(car.run())

def get_statistics(roads):
    total_passes = 0
    total_wait = 0
    count = 0
    for road in roads:
        for car in road.car_queue.items:
            total_passes += car.junction_passes
            total_wait += getattr(car, "wait_time", 0)
            count += 1
    avg_wait = total_wait / count if count else 0
    return {"total_passes": total_passes, "avg_wait": avg_wait}

def save_timings_to_csv(roads, filename=ACTUATED_TIMINGS_CSV):
    with open(filename, "w", newline="") as csvfile:
        fieldnames = ["road", "red_time", "green_time", "amber_time", "red_amber_time"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for road in roads:
            tl = road.traffic_light
            writer.writerow({
                "road": road.name,
                "red_time": tl.red_time,
                "green_time": tl.green_time,
                "amber_time": tl.amber_time,
                "red_amber_time": tl.red_amber_time
            })

def actuated_main(filename=ACTUATED_TIMINGS_CSV, cars_data=None, sim_duration=SIM_DURATION,
                  rows=GRID_ROWS, cols=GRID_COLS, display_interval=DISPLAY_INTERVAL,
                  random_seed=RANDOM_SEED, headless=False, candidate_timings=None,
                  save_animation_to_file=None):
    random.seed(random_seed)
    env = simpy.Environment()
    grid_junctions = []
    for i in range(rows):
        row_list = []
        for j in range(cols):
            row_list.append(create_junction(env, i, j, rows, cols))
        grid_junctions.append(row_list)
    connections = create_grid_roads(grid_junctions)
    if candidate_timings is not None:
        actuated_timings = candidate_timings
    else:
        actuated_timings = import_timings_csv(filename)
    roads = []
    for source, dest, init_color in connections:
        road_name = f"Road_{source.name}_{dest.name}"
        new_road = FRoad(road_name, speed=13, distance=100,
                         junction_start=source,
                         junction_end=dest,
                         car_queue=simpy.Store(env))
        if road_name in actuated_timings:
            rt, gt, at, rat = actuated_timings[road_name]
        else:
            rt, gt, at, rat = DEFAULT_ACT_RED_TIME, DEFAULT_ACT_GREEN_TIME, DEFAULT_ACT_AMBER_TIME, DEFAULT_ACT_RED_AMBER_TIME
        new_road.traffic_light = ATrafficLightActuated(
            env, new_road,
            red_time=rt, green_time=gt,
            red_amber_time=rat, amber_time=at,
            initial_state=init_color
        )
        try:
            source.add_light(new_road.traffic_light)
        except Exception:
            pass
        try:
            dest.add_light(new_road.traffic_light)
        except Exception:
            pass
        roads.append(new_road)
        
    # External roads with two-way connections.
    # Top external connections.
    inroads = []
    for j in range(cols):
        junction = grid_junctions[0][j]
        grid_entry = junction.get_side("top") if hasattr(junction, "get_side") else junction
        ext_entry = FJunctionFixed(env, f"Ext_Top_{junction.base_name if hasattr(junction, 'base_name') else junction.name}",
                                   start=True, end=True, weight=1)
        # Road from external -> grid.
        road_name = f"Road_ExtTop_{grid_entry.name}"
        entry = FRoad(road_name, speed=13, distance=100,
                      junction_start=ext_entry, junction_end=grid_entry,
                      car_queue=simpy.Store(env))
        entry.traffic_light = ATrafficLightActuated(
            env, entry,
            red_time=DEFAULT_ACT_RED_TIME, green_time=DEFAULT_ACT_GREEN_TIME,
            red_amber_time=DEFAULT_ACT_RED_AMBER_TIME, amber_time=DEFAULT_ACT_AMBER_TIME,
            initial_state="RED"
        )
        ext_entry.add_light(entry.traffic_light)
        try:
            grid_entry.add_light(entry.traffic_light)
        except Exception:
            pass
        inroads.append(entry)
        # Reverse road (grid -> external).
        road_name_rev = f"Road_{grid_entry.name}_ExtTop_Rev"
        entry_rev = FRoad(road_name_rev, speed=13, distance=100,
                          junction_start=grid_entry, junction_end=ext_entry,
                          car_queue=simpy.Store(env))
        entry_rev.traffic_light = ATrafficLightActuated(
            env, entry_rev,
            red_time=DEFAULT_ACT_RED_TIME, green_time=DEFAULT_ACT_GREEN_TIME,
            red_amber_time=DEFAULT_ACT_RED_AMBER_TIME, amber_time=DEFAULT_ACT_AMBER_TIME,
            initial_state="RED"
        )
        try:
            grid_entry.add_light(entry_rev.traffic_light)
        except Exception:
            pass
        ext_entry.add_light(entry_rev.traffic_light)
        inroads.append(entry_rev)
        
    # Bottom external connections.
    outroads = []
    for j in range(cols):
        junction = grid_junctions[rows-1][j]
        grid_exit = junction.get_side("bottom") if hasattr(junction, "get_side") else junction
        ext_exit = FJunctionFixed(env, f"Ext_Bottom_{junction.base_name if hasattr(junction, 'base_name') else junction.name}",
                                  start=True, end=True, weight=1)
        road_name = f"Road_{grid_exit.name}_ExtBottom"
        exit_road = FRoad(road_name, speed=13, distance=100,
                          junction_start=grid_exit, junction_end=ext_exit,
                          car_queue=simpy.Store(env))
        exit_road.traffic_light = ATrafficLightActuated(
            env, exit_road,
            red_time=DEFAULT_ACT_RED_TIME, green_time=DEFAULT_ACT_GREEN_TIME,
            red_amber_time=DEFAULT_ACT_RED_AMBER_TIME, amber_time=DEFAULT_ACT_AMBER_TIME,
            initial_state="RED"
        )
        try:
            grid_exit.add_light(exit_road.traffic_light)
        except Exception:
            pass
        ext_exit.add_light(exit_road.traffic_light)
        outroads.append(exit_road)
        # Reverse road (external -> grid).
        road_name_rev = f"Road_ExtBottom_{grid_exit.name}_Rev"
        exit_road_rev = FRoad(road_name_rev, speed=13, distance=100,
                              junction_start=ext_exit, junction_end=grid_exit,
                              car_queue=simpy.Store(env))
        exit_road_rev.traffic_light = ATrafficLightActuated(
            env, exit_road_rev,
            red_time=DEFAULT_ACT_RED_TIME, green_time=DEFAULT_ACT_GREEN_TIME,
            red_amber_time=DEFAULT_ACT_RED_AMBER_TIME, amber_time=DEFAULT_ACT_AMBER_TIME,
            initial_state="RED"
        )
        ext_exit.add_light(exit_road_rev.traffic_light)
        try:
            grid_exit.add_light(exit_road_rev.traffic_light)
        except Exception:
            pass
        outroads.append(exit_road_rev)
        
    # Left external connections.
    left_inroads = []
    for i in range(rows):
        junction = grid_junctions[i][0]
        grid_left = junction.get_side("left") if hasattr(junction, "get_side") else junction
        ext_left = FJunctionFixed(env, f"Ext_Left_{junction.base_name if hasattr(junction, 'base_name') else junction.name}",
                                  start=True, end=True, weight=1)
        road_name = f"Road_ExtLeft_{grid_left.name}"
        left_road = FRoad(road_name, speed=13, distance=100,
                          junction_start=ext_left, junction_end=grid_left,
                          car_queue=simpy.Store(env))
        left_road.traffic_light = ATrafficLightActuated(
            env, left_road,
            red_time=DEFAULT_ACT_RED_TIME, green_time=DEFAULT_ACT_GREEN_TIME,
            red_amber_time=DEFAULT_ACT_RED_AMBER_TIME, amber_time=DEFAULT_ACT_AMBER_TIME,
            initial_state="RED"
        )
        ext_left.add_light(left_road.traffic_light)
        try:
            grid_left.add_light(left_road.traffic_light)
        except Exception:
            pass
        left_inroads.append(left_road)
        # Reverse road (grid -> external).
        road_name_rev = f"Road_{grid_left.name}_ExtLeft_Rev"
        left_road_rev = FRoad(road_name_rev, speed=13, distance=100,
                              junction_start=grid_left, junction_end=ext_left,
                              car_queue=simpy.Store(env))
        left_road_rev.traffic_light = ATrafficLightActuated(
            env, left_road_rev,
            red_time=DEFAULT_ACT_RED_TIME, green_time=DEFAULT_ACT_GREEN_TIME,
            red_amber_time=DEFAULT_ACT_RED_AMBER_TIME, amber_time=DEFAULT_ACT_AMBER_TIME,
            initial_state="RED"
        )
        try:
            grid_left.add_light(left_road_rev.traffic_light)
        except Exception:
            pass
        ext_left.add_light(left_road_rev.traffic_light)
        left_inroads.append(left_road_rev)
        
    # Right external connections.
    right_outroads = []
    for i in range(rows):
        junction = grid_junctions[i][cols-1]
        grid_right = junction.get_side("right") if hasattr(junction, "get_side") else junction
        ext_right = FJunctionFixed(env, f"Ext_Right_{junction.base_name if hasattr(junction, 'base_name') else junction.name}",
                                   start=True, end=True, weight=1)
        road_name = f"Road_{grid_right.name}_ExtRight"
        right_road = FRoad(road_name, speed=13, distance=100,
                           junction_start=grid_right, junction_end=ext_right,
                           car_queue=simpy.Store(env))
        right_road.traffic_light = ATrafficLightActuated(
            env, right_road,
            red_time=DEFAULT_ACT_RED_TIME, green_time=DEFAULT_ACT_GREEN_TIME,
            red_amber_time=DEFAULT_ACT_RED_AMBER_TIME, amber_time=DEFAULT_ACT_AMBER_TIME,
            initial_state="RED"
        )
        try:
            grid_right.add_light(right_road.traffic_light)
        except Exception:
            pass
        ext_right.add_light(right_road.traffic_light)
        right_outroads.append(right_road)
        # Reverse road (external -> grid).
        road_name_rev = f"Road_ExtRight_{grid_right.name}_Rev"
        right_road_rev = FRoad(road_name_rev, speed=13, distance=100,
                               junction_start=ext_right, junction_end=grid_right,
                               car_queue=simpy.Store(env))
        right_road_rev.traffic_light = ATrafficLightActuated(
            env, right_road_rev,
            red_time=DEFAULT_ACT_RED_TIME, green_time=DEFAULT_ACT_GREEN_TIME,
            red_amber_time=DEFAULT_ACT_RED_AMBER_TIME, amber_time=DEFAULT_ACT_AMBER_TIME,
            initial_state="RED"
        )
        ext_right.add_light(right_road_rev.traffic_light)
        try:
            grid_right.add_light(right_road_rev.traffic_light)
        except Exception:
            pass
        right_outroads.append(right_road_rev)
        
    roads.extend(inroads + outroads + left_inroads + right_outroads)
    
    # Add all connector roads from composite junctions.
    for row in grid_junctions:
        for junction in row:
            if hasattr(junction, "connectors"):
                for conn in junction.connectors.values():
                    roads.append(conn)
                    
    cars_data = generate_cars(env, 100, roads, BASE_MEAN, cars_data=cars_data)
    if not headless:
        def run_simulation():
            while env.now < sim_duration:
                env.run(until=env.now + 1)
                time.sleep(1)
        sim_thread = threading.Thread(target=run_simulation)
        sim_thread.start()
        # Save actuated simulation to a separate file.
        animate_network(env, roads, grid_rows=rows, grid_cols=cols, update_interval=DISPLAY_INTERVAL,
                        save_to_file="actuated_simulation.mp4")
        sim_thread.join()
    else:
        env.run(until=sim_duration)
    stats = get_statistics(roads)
    if not headless:
        display_statistics(roads)
    save_timings_to_csv(roads, filename)
    return {"cars_data": cars_data, "stats": stats, "roads": roads}

if __name__ == "__main__":
    saved = actuated_main(save_animation_to_file="actuated_simulation.mp4")
    actuated_main(ACTUATED_TIMINGS_CSV, cars_data=saved["cars_data"],
                  sim_duration=SIM_DURATION, rows=GRID_ROWS, cols=GRID_COLS,
                  display_interval=DISPLAY_INTERVAL, random_seed=RANDOM_SEED)

