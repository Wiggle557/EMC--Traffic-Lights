import simpy
import random
import numpy as np
from quiet import FCar, FRoad
from scipy.stats import truncnorm

def Fsetup(env: simpy.Environment, num_cars: int, roads: list[FRoad], base_mean: float | int):
    """
    Sets up the simulation by inserting cars into the network.
    Arrival intervals are drawn from a Poisson distribution, but during "rush hours"
    (e.g., between time 270 and 360 seconds) the mean interval is reduced, simulating heavier traffic.
    """
    for i in range(num_cars):
        startable_roads = [road for road in roads if road.junction_start.start]
        if not startable_roads:
            break
        weights = [1 / (len(road.car_queue.items) + 1) for road in startable_roads]
        chosen_road = random.choices(startable_roads, weights=weights)[0]
        
        reaction_time = sample_reaction_time(mean=1.0, std=0.2)
        car = FCar(env, f'Car {i}', chosen_road, roads, reaction_time=reaction_time)
        env.process(car.run())

        current_time = env.now
        if 270 <= current_time < 360:
            current_mean = base_mean * 0.5  # Rush hour: more frequent arrivals
        else:
            current_mean = base_mean
        interval = sample_arrival_interval(current_mean)
        yield env.timeout(interval)

def Fcreate_grid_roads(junctions: list[list[int]]) -> list[list[int | str]]:
    """
    Constructs a grid of roads given a 2D list of junction indices.
    Returns a list where each road is represented as [start_index, end_index, initial_colour].
    """
    road_names: list[list[int | str]] = []
    for i, row in enumerate(junctions):
        for j, cell in enumerate(row):
            if i > 0:
                road_names.append([cell, cell - len(row), "RED"])
            if i < len(junctions) - 1:
                road_names.append([cell, cell + len(row), "RED"])
            if j > 0:
                road_names.append([cell, cell - 1, "GREEN"])
            if j < len(row) - 1:
                road_names.append([cell, cell + 1, "GREEN"])
    return road_names

def sample_reaction_time(mean=1.0, std=0.2, lower=0.5, upper=1.5):
    """
    Samples a driver reaction time from a truncated normal distribution.
    """
    a, b = (lower - mean) / std, (upper - mean) / std
    return truncnorm.rvs(a, b, loc=mean, scale=std)

def sample_arrival_interval(base_mean):
    """
    Samples a car arrival interval from a Poisson distribution ensuring a minimum
    interval of 1 second.
    """
    interval = np.random.poisson(lam=base_mean, size=1)[0]
    return max(1, interval)
