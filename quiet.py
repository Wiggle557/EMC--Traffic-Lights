# quiet.py
from __future__ import annotations
import simpy
import random
import math
from config import POINTS_OF_INTEREST  # For POI-based routing, if needed

# Global container for completed (exited) cars statistics.
completed_cars = []  

# Safety gap (in meters) that must be available in addition to the car's own length.
SAFETY_GAP = 5

# -----------------------------
# Adaptive (Actuated) Traffic Light Class
# -----------------------------
class FTrafficLight:
    def __init__(self, env: simpy.Environment, road: FRoad,
                 red_time: float = 15, green_time: float = 15,
                 red_amber_time: float = 3, amber_time: float = 3,
                 colour: str = "RED"):
        self.env = env
        self.road = road
        self.colour = colour
        self.red_time = red_time
        self.green_time = green_time
        self.red_amber_time = red_amber_time
        self.amber_time = amber_time
        self.last_change = env.now
        self.name = road.name  # Name the light after the road.
        self.action = env.process(self.run())
    
    def actuate_timing(self):
        q_len = self.road.get_queue_length()
        # Dynamically adjust green time (capped at 30 seconds).
        self.green_time = min(15 + q_len * 2, 30)
    
    def run(self):
        while True:
            self.last_change = self.env.now
            self.actuate_timing()
            if self.colour == "RED":
                self.colour = "RAMBER"
                yield self.env.timeout(self.red_amber_time)
            elif self.colour == "RAMBER":
                self.colour = "GREEN"
                yield self.env.timeout(self.green_time)
            elif self.colour == "GREEN":
                self.colour = "AMBER"
                yield self.env.timeout(self.amber_time)
            elif self.colour == "AMBER":
                self.colour = "RED"
                yield self.env.timeout(self.red_time)

# -----------------------------
# Junction Class
# -----------------------------
class FJunction:
    def __init__(self, env: simpy.Environment, name: str,
                 end: bool = False, start: bool = False, weight: float = 1.0):
        self.env = env
        self.name = name
        self.traffic_lights: list[FTrafficLight] = []
        self.queue = simpy.PriorityResource(env, capacity=1)
        self.end = end      # True if this junction is an exit.
        self.start = start  # True if vehicles can enter here.
        self.weight = weight
        self.conflict_groups: list[list[FTrafficLight]] = []
        self.action = env.process(self.actuate_lights())
    
    def add_light(self, light: FTrafficLight, conflict_group: int | None = None):
        self.traffic_lights.append(light)
        if conflict_group is not None:
            while len(self.conflict_groups) <= conflict_group:
                self.conflict_groups.append([])
            self.conflict_groups[conflict_group].append(light)
    
    def actuate_lights(self):
        baseline_cycle_time = 60  
        max_cycle_time = 120      
        scaling_factor = 2        
        while True:
            if self.conflict_groups:
                pressures = [
                    sum(light.road.get_queue_length() for light in group)
                    for group in self.conflict_groups
                ]
                avg_pressure = sum(pressures) / len(self.conflict_groups)
                total_cycle_limit = min(max_cycle_time, baseline_cycle_time + scaling_factor * avg_pressure)
                total_green_time = sum(sum(light.green_time for light in group) for group in self.conflict_groups)
                total_fixed_time = sum(
                    sum(light.red_time + light.amber_time + light.red_amber_time for light in group)
                    for group in self.conflict_groups
                )
                if total_green_time + total_fixed_time > total_cycle_limit:
                    scale_factor = (total_cycle_limit - total_fixed_time) / total_green_time
                    for group in self.conflict_groups:
                        for light in group:
                            light.green_time *= scale_factor
                            light.green_time = max(10, light.green_time)
                for idx, group in enumerate(self.conflict_groups):
                    for light in group:
                        if idx == pressures.index(max(pressures)):
                            continue
                        else:
                            light.red_time += scale_factor * 2
                            light.red_time = max(10, min(40, light.red_time))
            yield self.env.timeout(5)

# -----------------------------
# Road Class
# -----------------------------
class FRoad:
    def __init__(self, name: str, speed: int, distance: int,
                 junction_start: FJunction, junction_end: FJunction,
                 car_queue: simpy.Store):
        self.name = name
        self.speed = speed
        self.distance = distance  # Total road length (meters).
        self.junction_start = junction_start
        self.junction_end = junction_end
        self.car_queue = car_queue
        self.traffic_light: FTrafficLight | None = None
    
    def get_queue_length(self) -> int:
        return len(self.car_queue.items)

# -----------------------------
# Car Class (with Kinematics, POI Routing, and Debug Logging)
# -----------------------------
class FCar:
    def __init__(self, env: simpy.Environment, name: str, road: FRoad,
                 roads: list[FRoad], reaction_time: float = 1.0,
                 acceleration: float = 3.5, decceleration: float = -8.1,
                 length: float = 4.9):
        self.env = env
        self.name = name
        self.road = road                  # Current road.
        self.roads = roads                # Available roads for routing.
        self.reaction_time = reaction_time
        self.acceleration = acceleration
        self.decceleration = decceleration
        self.length = length
        self.junction_passes = 0
        self.wait_time = 0
        self.speed = road.speed
    def run(self):
        red_cycle_count = 0
        while True:
            # Enqueue into the current road's car queue.
            yield self.road.car_queue.put(self)
            # Request access from the originating junction's resource.
            with self.road.junction_start.queue.request(priority=1) as request:
                yield request
                available_distance = self.road.distance - sum(car.length for car in self.road.car_queue.items)
                while (self.road.traffic_light.colour in ["RED", "RAMBER", "AMBER"] or
                       self.road.car_queue.items[0] != self or
                       (self.road.distance - sum(car.length for car in self.road.car_queue.items)) < (self.length + SAFETY_GAP)):
                    available_distance = self.road.distance - sum(car.length for car in self.road.car_queue.items)
                    if available_distance < (self.length + SAFETY_GAP):
                        if red_cycle_count < 2:
                            red_cycle_count += 1
                            yield self.env.timeout(self.reaction_time)
                            continue
                        else:
                            print(f"[{self.env.now}] {self.name} reordering to front after {red_cycle_count} cycles.")
                            if self in self.road.car_queue.items:
                                self.road.car_queue.items.remove(self)
                                self.road.car_queue.items.insert(0, self)
                            break
                    yield self.env.timeout(self.reaction_time)
                red_cycle_count = 0
                start_delay = sample_reaction_time(mean=0.8, std=0.1, lower=0.5, upper=1.0)
                self.wait_time += start_delay
                yield self.env.timeout(start_delay)
            # Check if this road leads to an exit.
            if self.road.junction_end.end:
                if self in self.road.car_queue.items:
                    self.road.car_queue.items.remove(self)
                completed_cars.append({
                    "name": self.name,
                    "wait_time": self.wait_time,
                    "junction_passes": self.junction_passes
                })
                break  # End the car's process.
            
            # Recalculate available distance and enforce the safety gap.
            available_distance = self.road.distance - sum(car.length for car in self.road.car_queue.items)
            if available_distance < (self.length + SAFETY_GAP):
                available_distance = max(available_distance, SAFETY_GAP)
            # Compute travel kinematics.
            v_max = math.sqrt(self.speed**2 + 2 * self.acceleration * available_distance)
            if v_max <= self.road.speed:
                total_tG = (v_max - self.speed) / self.acceleration
                new_speed = v_max
            else:
                s_1 = (self.road.speed**2 - self.speed**2) / (2 * self.acceleration)
                s_c = available_distance - s_1
                t_1 = (self.road.speed - self.speed) / self.acceleration
                t_c = s_c / self.road.speed
                total_tG = t_1 + t_c
                new_speed = self.road.speed
            final_v = 0
            v_p = math.sqrt((self.decceleration * self.speed**2 - self.acceleration * final_v**2 +
                             2 * self.acceleration * self.decceleration) /
                            (self.decceleration - self.acceleration))
            if v_p > self.road.speed:
                s_1 = (self.road.speed**2 - self.speed**2) / (2 * self.acceleration)
                s_2 = (final_v - self.road.speed**2) / (2 * self.decceleration)
                s_c = available_distance - s_1 - s_2
                t_1 = (self.road.speed - self.speed) / self.acceleration
                t_c = s_c / self.road.speed
                t_2 = (self.road.speed - final_v) / abs(self.decceleration)
                total_tR = t_1 + t_c + t_2
            else:
                t_1 = (v_p - self.speed) / self.acceleration
                t_2 = (final_v - v_p) / self.decceleration
                total_tR = t_1 + t_2
            # Determine travel phase based on simulated traffic light progress.
            colour = self.road.traffic_light.colour
            t_elapsed = self.env.now - self.road.traffic_light.last_change
            while t_elapsed < total_tR:
                match colour:
                    case "RED":
                        colour = "RAMBER"
                        t_elapsed += self.road.traffic_light.red_amber_time
                    case "RAMBER":
                        colour = "GREEN"
                        t_elapsed += self.road.traffic_light.green_time
                    case "GREEN":
                        colour = "AMBER"
                        t_elapsed += self.road.traffic_light.amber_time
                    case "AMBER":
                        colour = "RED"
                        t_elapsed += self.road.traffic_light.red_time
            if colour in ["RED", "RAMBER"]:
                travel_time = total_tR
                self.speed = 0
            else:
                travel_time = total_tG
                self.speed = new_speed
            print(f"[{self.env.now}] {self.name} traveling with travel_time={travel_time:.2f}, new_speed={self.speed:.2f}.")
            # Simulate travel time (split into two halves).
            yield self.env.timeout(travel_time)
            
            # Remove self from current road's queue after traveling.
            if self in self.road.car_queue.items:
                self.road.car_queue.items.remove(self)
                print(f"[{self.env.now}] {self.name} removed from road {self.road.name} queue.")
            self.junction_passes += 1
            
            # Choose the next road from candidate roads at the destination junction.
            next_junction = self.road.junction_end
            possible_roads = [
                road for road in self.roads 
                if road.junction_start == next_junction
                   and road.junction_end != self.road.junction_start  # Exclude roads that loop back
                   and (sum(car.length for car in road.car_queue.items) + self.length < road.distance)
            ]
            weights = []
            for road in possible_roads:
                base_weight = road.junction_end.weight
                if road.junction_end.name in POINTS_OF_INTEREST:
                    base_weight *= POINTS_OF_INTEREST[road.junction_end.name]
                weights.append(base_weight)
            total_weight = sum(weights)
            if total_weight == 0 and weights:
                probabilities = [1 / len(weights)] * len(weights)
            elif total_weight == 0:
                probabilities = []
            else:
                probabilities = [w / total_weight for w in weights]
            if probabilities and possible_roads:
                chosen_road = random.choices(possible_roads, probabilities)[0]
                print(f"[{self.env.now}] {self.name} selecting next road {chosen_road.name}.")
                self.road = chosen_road
            else:
                # If no candidate road is found, remain on current road.
                print(f"[{self.env.now}] {self.name} found no candidate road; continuing on the same road.")
        # End of loop—if car exits or breaks from while, process terminates.

# -----------------------------
# Helper Function for Reaction Time Sampling
# -----------------------------
def sample_reaction_time(mean=1.0, std=0.2, lower=0.5, upper=1.5) -> float:
    return random.uniform(lower, upper)

