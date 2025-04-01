from __future__ import annotations
import simpy
import random
import math


class FTrafficLight:
    def __init__(self, env: simpy.Environment, road: FRoad,
                 red_time=15, green_time=15, red_amber_time=3, amber_time=3, colour="RED"):
        self.env = env
        self.road = road
        self.colour = colour
        self.red_time = red_time
        self.green_time = green_time
        self.red_amber_time = red_amber_time
        self.amber_time = amber_time
        self.last_change = env.now
        self.name = road.name
    
    def force_green(self):
        """
        Force a safe transition from the current state to GREEN 
        using intermediary phases.
        Returns a generator to be used as a process.
        """
        # If already green, do nothing.
        if self.colour == "GREEN":
            return
        # If currently RED, then we must go to RED-AMBER first.
        if self.colour == "RED":
            self.colour = "RAMBER"
            yield self.env.timeout(self.red_amber_time)
        # If in AMBER, complete the red cycle first
        elif self.colour == "AMBER":
            self.colour = "RED"
            yield self.env.timeout(self.red_time)
            self.colour = "RAMBER"
            yield self.env.timeout(self.red_amber_time)
        # Now transition to GREEN.
        self.colour = "GREEN"
        # Optionally, remain in GREEN for the allocated period.
        yield self.env.timeout(self.green_time)
    
    def force_red(self):
        """
        Force a safe transition from the current state to RED 
        using intermediary phases.
        Returns a generator to be used as a process.
        """
        if self.colour == "RED":
            return
        # If currently GREEN, go through AMBER.
        if self.colour == "GREEN":
            self.colour = "AMBER"
            yield self.env.timeout(self.amber_time)
        # If in RAMBER, complete transition by going full cycle.
        elif self.colour == "RAMBER":
            self.colour = "GREEN"
            yield self.env.timeout(self.green_time)
            self.colour = "AMBER"
            yield self.env.timeout(self.amber_time)
        # Now set to RED.
        self.colour = "RED"
        yield self.env.timeout(self.red_time)

class FJunction:
    def __init__(self, env: simpy.Environment, name: str, end: bool = False, start: bool = False, weight=1):
        self.env = env
        self.name = name
        self.traffic_lights: list[FTrafficLight] = []
        self.queue = simpy.PriorityResource(env, capacity=1)
        self.end = end
        self.start = start
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
        """
        Every few seconds, calculate pressures over the conflict groups,
        then force the designated group to transition to green (and others to red)
        using safe intermediary phases.
        """
        while True:
            if self.start:
                yield self.env.timeout(5)
                continue
            if self.conflict_groups:
                # Calculate each conflict group's pressure by summing queue lengths.
                pressures = [sum(light.road.get_queue_length() for light in group)
                             for group in self.conflict_groups]
                best_group_index = pressures.index(max(pressures))
                # For the best group, force lights to green.
                for idx, group in enumerate(self.conflict_groups):
                    if idx == best_group_index:
                        for light in group:
                            if light.colour != "GREEN":
                                self.env.process(light.force_green())
                    else:
                        # For non-selected groups, force them to transition to red.
                        for light in group:
                            if light.colour != "RED":
                                self.env.process(light.force_red())
            else:
                # Fallback: if no conflict groups exist, select the single light with highest queue.
                if self.traffic_lights:
                    best = max(self.traffic_lights, key=lambda l: l.road.get_queue_length())
                    for light in self.traffic_lights:
                        if light == best:
                            if light.colour != "GREEN":
                                self.env.process(light.force_green())
                        else:
                            if light.colour != "RED":
                                self.env.process(light.force_red())
            yield self.env.timeout(5)

class FRoad:
    def __init__(self, name: str, speed: int, distance: int,
                 junction_start: FJunction, junction_end: FJunction, car_queue: simpy.Store):
        self.name = name
        self.speed = speed
        self.distance = distance
        self.junction_start = junction_start
        self.junction_end = junction_end
        self.traffic_light: FTrafficLight | None = None
        self.car_queue = car_queue

    def get_queue_length(self):
        """Returns the number of cars waiting on this road."""
        return len(self.car_queue.items)


class FCar:
    def __init__(self, env: simpy.Environment, name: str, road: FRoad,
                 roads: list[FRoad], reaction_time=1, acceleration=3.5, decceleration=-8.1, length=4.9):
        self.env = env
        self.name = name
        self.road = road
        self.reaction_time = reaction_time
        self.acceleration = acceleration
        self.decceleration = decceleration
        self.speed = self.road.speed
        self.roads = roads
        self.junction_passes = 0
        self.length = length
        # For optional statistics
        self.wait_time = 0

    def run(self):
        distance = self.road.distance
        while True:
            yield self.road.car_queue.put(self)
            with self.road.junction_start.queue.request(priority=1) as request:
                yield request
                # Apply a realistic reaction time by varying it slightly.
                current_reaction = random.uniform(0.8, 1.2) * self.reaction_time
                self.wait_time += current_reaction
                while (self.road.traffic_light.colour in ["RED", "RAMBER", "AMBER"]
                       or self.road.car_queue.items[0] != self
                       or not any(
                          (road.junction_start == self.road.junction_end and 
                           sum(car.length for car in road.car_queue.items) + self.length < road.distance)
                          for road in self.roads)):
                    yield self.env.timeout(current_reaction)
            car = yield self.road.car_queue.get()
            if car == self:
                self.junction_passes += 1
                if self.road.junction_end.end:
                    # Car reaches an exit
                    self.road.car_queue.put(self)
                    break
                # Adjust remaining distance based on cars already on the road.
                for other in self.road.car_queue.items:
                    distance -= other.length
                # Compute travel time while accelerating.
                v_max = math.sqrt(self.speed**2 + 2 * self.acceleration * distance)
                if v_max <= self.road.speed:
                    total_tG = (v_max - self.speed) / self.acceleration
                    new_speed = v_max
                else:
                    s_1 = (self.road.speed**2 - self.speed**2) / (2 * self.acceleration)
                    s_c = distance - s_1
                    t_1 = (self.road.speed - self.speed) / self.acceleration
                    t_c = s_c / self.road.speed
                    total_tG = t_1 + t_c
                    new_speed = self.road.speed
                final_v = 0
                # Compute required time if needing to decelerate.
                v_p = math.sqrt((self.decceleration * self.speed**2 - self.acceleration * final_v**2 +
                                 2 * self.acceleration * self.decceleration) /
                                (self.decceleration - self.acceleration))
                if v_p > self.road.speed:
                    s_1 = (self.road.speed**2 - self.speed**2) / (2 * self.acceleration)
                    s_2 = (final_v - self.road.speed**2) / (2 * self.decceleration)
                    s_c = distance - s_1 - s_2
                    t_1 = (self.road.speed - self.speed) / self.acceleration
                    t_c = s_c / self.road.speed
                    t_2 = (self.road.speed - final_v) / self.decceleration
                    total_tR = t_1 + t_c + t_2
                else:
                    t_1 = (v_p - self.speed) / self.acceleration
                    t_2 = (final_v - v_p) / self.decceleration
                    total_tR = t_1 + t_2
                # Determine travel time according to upcoming light state.
                colour = self.road.traffic_light.colour
                time_since_change = self.env.now - self.road.traffic_light.last_change
                t_sim = time_since_change
                while t_sim < total_tR:
                    match colour:
                        case "RED":
                            colour = "RAMBER"
                            t_sim += self.road.traffic_light.red_amber_time
                        case "RAMBER":
                            colour = "GREEN"
                            t_sim += self.road.traffic_light.green_time
                        case "GREEN":
                            colour = "AMBER"
                            t_sim += self.road.traffic_light.amber_time
                        case "AMBER":
                            colour = "RED"
                            t_sim += self.road.traffic_light.red_time
                if colour in ["RED", "RAMBER", "AMBER"]:
                    travel_time = total_tR
                    self.speed = 0
                else:
                    travel_time = total_tG
                    self.speed = new_speed
                # Simulate travel across half the distance then the other half.
                yield self.env.timeout(travel_time / 2)
                yield self.env.timeout(travel_time / 2)
                # Reset distance for the next road.
                distance = 0
                for other in self.road.car_queue.items:
                    distance += other.length
                next_junction = self.road.junction_end
                possible_roads = [road for road in self.roads if road.junction_start == next_junction and
                                  sum(car.length for car in road.car_queue.items) + self.length < road.distance and
                                  not road.junction_end.start]
                if not possible_roads:
                    break  # No valid next roads; exit the loop.
                weights = [road.junction_end.weight for road in possible_roads]
                total_weight = sum(weights)
                probabilities = [weight / total_weight for weight in weights]
                self.road = random.choices(possible_roads, probabilities)[0]
                distance += self.road.distance

