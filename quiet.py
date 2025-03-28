from __future__ import annotations
import simpy
import random
import math
import numpy as np
from setup import setup, create_grid_roads

class FTrafficLight:
    def __init__(self, env: simpy.Environment, road: FRoad, red_time=10, green_time=10, red_amber_time=3, amber_time=3, colour="RED"):
        self.env = env
        self.road = road  # Associate the traffic light with a specific road
        self.colour = colour
        self.red_time = red_time
        self.green_time = green_time
        self.red_amber_time = red_amber_time
        self.amber_time = amber_time
        self.last_change = env.now
        self.name = road.name  # Name the light after the road it controls
        self.action = env.process(self.run())  # Start the traffic light process
        self.total_time = red_time + green_time + red_amber_time + amber_time

    def actuate_timing(self):
        """Adjust green time dynamically based on queue length."""
        queue_length = self.road.get_queue_length()  # Get the current queue length
        self.green_time = min(10 + queue_length * 2, 30)  # Increase green time proportionally to the queue

    def run(self):
        """SimPy process to manage the traffic light cycle."""
        while True:
            self.last_change = self.env.now

            # Adjust timings dynamically for GREEN light
            self.actuate_timing()

            # Traffic light state transitions
            if self.colour == "RED":
                self.colour = "RAMBER"
                
                yield self.env.timeout(self.red_amber_time)
            elif self.colour == "RAMBER":
                self.colour = "GREEN"
                
                yield self.env.timeout(self.green_time)
            elif self.colour == "GREEN":
                self.colour = "AMBER"
                
                yield self.env.timeout(self.amber_time)
            else:  # "AMBER"
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
        self.action = env.process(self.actuate_lights())  # Start the actuation process

    def add_light(self, light: 'FTrafficLight'):
        """Add a traffic light to the junction."""
        self.traffic_lights.append(light)

    def actuate_lights(self):
        """Periodically adjust traffic light timings based on road queue lengths."""
        while True:
            if self.start:
                break  # Exit if this is a starting junction
            # Identify the traffic light with the longest queue
            max_queue_light = max(self.traffic_lights, key=lambda light: light.road.get_queue_length())
            max_queue = max_queue_light.road.get_queue_length()
            

            # Adjust green time for the traffic light with the longest queue
            for light in self.traffic_lights:
                if light == max_queue_light:
                    light.green_time = min(15 + max_queue * 2, 30)  # Example: max green time is 30 seconds
                else:
                    light.green_time = 15  # Default green time for non-prioritized roads

            yield self.env.timeout(5)  # Reassess every 5 seconds


class FRoad:
    def __init__(self, name: str, speed: int, distance: int, junction_start: FJunction, junction_end: Junction, car_queue: simpy.Store):
        self.name = name
        self.speed = speed
        self.distance = distance
        self.junction_start = junction_start
        self.junction_end = junction_end
        self.traffic_light: FTrafficLight | None = None  # Assign traffic light later
        self.car_queue = car_queue

    def get_queue_length(self):
        """Retrieve the current queue length on the road."""
        return len(self.car_queue.items)

class FCar:
    def __init__(self, env: simpy.Environment, name: str, road: FRoad, roads: list[Road], reaction_time=1, acceleration = 3.5, deccelaration = -8.1, length = 4.9) -> None:
        self.env = env
        self.name = name
        self.road = road
        self.reaction_time = reaction_time
        self.acceleration = acceleration
        self.decceleration = deccelaration
        self.speed = self.road.speed
        self.roads = roads
        self.junction_passes = 0
        self.length = length

    def run(self):
        distance = self.road.distance
        while True:
            yield self.road.car_queue.put(self)
            with self.road.junction_start.queue.request(priority=1) as request:
                yield request
                while self.road.traffic_light.colour == "RED" or self.road.car_queue.items[0] != self or not(any([(road.junction_start == self.road.junction_end and sum(car.length for car in road.car_queue.items)+self.length<road.distance)for road in self.roads ])):
                    yield self.env.timeout(self.reaction_time)

                car = yield self.road.car_queue.get()
                if car == self:
                    
                    self.junction_passes+=1
                    if self.road.junction_end.end:
                        self.road.car_queue.put(self)
                        break
                    for i in self.road.car_queue.items:
                        distance -= i.length
                    
                    v_max = math.sqrt(self.speed**2+2*self.acceleration*distance)
                    if v_max <= self.road.speed:
                        total_tG = (v_max-self.speed)/self.acceleration
                        new_speed=v_max
                    else:
                        s_1 = (self.road.speed**2-self.speed**2)/(2*self.acceleration)
                        s_c = distance-s_1
                        t_1 = (self.road.speed-self.speed)/(self.acceleration)
                        t_c = s_c/self.road.speed
                        total_tG = t_1+t_c
                        new_speed = self.road.speed
                    final_v = 0
                    v_p = math.sqrt((self.decceleration*self.speed**2-self.acceleration*final_v**2+2*self.acceleration*self.decceleration)/(self.decceleration-self.acceleration))
                    if v_p>self.road.speed:
                        s_1 = (self.road.speed**2-self.speed**2)/(2*self.acceleration)
                        s_2 = (final_v-self.road.speed**2)/(2*self.decceleration)
                        s_c = distance-s_1-s_2
                        t_1 = (self.road.speed-self.speed)/self.acceleration
                        t_c = s_c/self.road.speed
                        t_2 = (self.road.speed-final_v)/self.decceleration
                        total_tR = t_1+t_c+t_2
                    else:
                        t_1 = (v_p-self.speed)/self.acceleration
                        t_2 = (final_v-v_p)/self.decceleration
                        total_tR = t_1+t_2
                    
                    colour = self.road.traffic_light.colour
                    t = self.env.now - self.road.traffic_light.last_change
                    while t<total_tR:
                        match colour:
                            case "RED":
                                colour="RAMBER"
                                t+=self.road.traffic_light.red_amber_time
                            case "RAMBER":
                                colour = "GREEN"
                                t+=self.road.traffic_light.green_time
                            case "GREEN":
                                colour = "AMBER"
                                t+=self.road.traffic_light.amber_time
                            case "AMBER":
                                colour = "RED"
                                t+=self.road.traffic_light.red_time

                    if colour=="RED" or colour=="RAMBER":
                        travel_time = total_tR
                        self.speed=0
                    else:
                        travel_time = total_tG
                        self.speed=new_speed


                    yield self.env.timeout(travel_time/2)
                    
                    yield self.env.timeout(travel_time/2)

                    distance = 0
                    for i in self.road.car_queue.items:
                        distance += i.length
                    # Update the road to the next road in the loop
                    next_junction = self.road.junction_end
                    possible_roads = [road for road in self.roads if road.junction_start == next_junction and sum(car.length for car in road.car_queue.items)+self.length<road.distance and not road.junction_end.start]
                    weights = [road.junction_end.weight for road in possible_roads]
                    total_weight = sum(weights)
                    probabilities = [weight / total_weight for weight in weights]
                    # Select the next road based on the weights
                    self.road = random.choices(possible_roads, probabilities)[0]
                    distance+=self.road.distance
        

def quiet_main():
    # Set up simulation environment
    env = simpy.Environment()

    # Grid size for junctions
    ROWS = 2
    COLS = 2
    until = 180
    num_junctions = ROWS * COLS
    junction_names = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    junctions:list[FJunction] = []
    roads = []

    weights = [[(i + j) % 2 for j in range(COLS)] for i in range(ROWS)]
    # Create junctions
    for i in range(num_junctions):
        junctions.append(FJunction(env, f"{junction_names[i]}", weight=weights[i // COLS][i % COLS]))
    
    # Generate grid structure for junctions
    junc_grid = []
    for i in range(ROWS):
        row = []
        for j in range(COLS):
            row.append(i * COLS + j)
        junc_grid.append(row)

    # Generate road connections for the grid
    road_connections = Fcreate_grid_roads(junc_grid)

    # Create roads and assign traffic lights
    for connection in road_connections:
        start, end, initial_color = connection
        new_road = FRoad(f"Road {junctions[start].name}{junctions[end].name}", 13, 100, junctions[start], junctions[end], simpy.Store(env))
        new_road.traffic_light = FTrafficLight(env, new_road, red_time=15, green_time=15, amber_time=3, red_amber_time=3, colour=initial_color)
        new_road.traffic_light.name = new_road.name
        junctions[end].add_light(new_road.traffic_light)  # Add the traffic light to the ending junction
        roads.append(new_road)

    # Adding inroads and outroads for corners
    outroads = [
        FRoad(f"Road {junctions[junc_grid[0][0]].name}OUT", 13, 100, junctions[0], FJunction(env, f"{junctions[junc_grid[0][0]].name}OUT", end=True), simpy.Store(env)),
        FRoad(f"Road {junctions[junc_grid[0][COLS - 1]].name}OUT", 13, 100, junctions[1], FJunction(env, f"{junctions[junc_grid[0][COLS - 1]].name}OUT", end=True), simpy.Store(env)),
        FRoad(f"Road {junctions[junc_grid[ROWS - 1][0]].name}OUT", 13, 100, junctions[2], FJunction(env, f"{junctions[junc_grid[ROWS - 1][0]].name}OUT", end=True), simpy.Store(env)),
        FRoad(f"Road {junctions[junc_grid[ROWS - 1][COLS - 1]].name}OUT", 13, 100, junctions[3], FJunction(env, f"{junctions[junc_grid[ROWS - 1][COLS - 1]].name}OUT", end=True), simpy.Store(env))
    ]

    inroads = [
        FRoad(f"Road {junctions[junc_grid[0][0]].name}IN", 13, 100, FJunction(env, f"{junctions[junc_grid[0][0]].name}IN", start=True), junctions[0], simpy.Store(env)),
        FRoad(f"Road {junctions[junc_grid[0][COLS - 1]].name}IN", 13, 100, FJunction(env, f"{junctions[junc_grid[0][COLS - 1]].name}IN", start=True), junctions[1], simpy.Store(env)),
        FRoad(f"Road {junctions[junc_grid[ROWS - 1][0]].name}IN", 13, 100, FJunction(env, f"{junctions[junc_grid[ROWS - 1][0]].name}IN", start=True), junctions[2], simpy.Store(env)),
        FRoad(f"Road {junctions[junc_grid[ROWS - 1][COLS - 1]].name}IN", 13, 100, FJunction(env, f"{junctions[junc_grid[ROWS - 1][COLS - 1]].name}IN", start=True), junctions[3], simpy.Store(env))
    ]

    # Assign traffic lights to inroads and outroads
    for road in inroads + outroads:
        road.traffic_light = FTrafficLight(env, road, red_time=15, green_time=15, amber_time=3, red_amber_time=3, colour="RED")
        road.traffic_light.name = road.name
        road.junction_end.add_light(road.traffic_light)

    # Extend roads list to include inroads and outroads
    roads.extend(inroads)
    roads.extend(outroads)

    # Add start/end junctions to the junction list
    for road in inroads:
        junctions.append(road.junction_start)
    for road in outroads:
        junctions.append(road.junction_end)

    # Initialize car setup
    env.process(Fsetup(env, 20, roads, 9))

    # Run the simulation
    env.run(until=until)

    # Display statistics on car queueing
    total_passes = 0
    for road in roads:
        for car in road.car_queue.items:
            total_passes += car.junction_passes
    return total_passes

def Fsetup(env: simpy.Environment, num_cars: int, roads: list[FRoad], mean: float|int):
    """
    Sets up the roads and runs cars through the roads

    Parameters:
    env (simpy.Environment): Environment of the simulation
    num_cars (int): The maximum number of cars in the simulation
    car_queue (simpy.Store): The queue of cars waiting at junctions
    roads (list[Road]): List of roads connecting the junctions
    interval (tuple[int, int]): Range of times between when new cars appear on the roads
    """
    for i in range(num_cars):
        road = random.choice([i for i in roads if i.junction_start.start])
        car = FCar(env, f'Car {i}', road, roads, random.randint(1, 6))
        env.process(car.run())
        yield env.timeout(np.random.poisson(lam=mean, size=1)[0])

def Fcreate_grid_roads(junctions: list[list[int]])->list[list[int|str]]:
    road_names:list[list[int|str]] = []
    for i, row in enumerate(junctions):
        for j, cell in enumerate(row):
            if i>0:
                road_names.append([cell,cell-len(row),"RED"])
            if i<len(row)-1:
                road_names.append([cell,cell+len(row),"RED"])
            if j>0:
                road_names.append([cell,cell-1,"GREEN"])
            if j<len(row)-1:
                road_names.append([cell,cell+1,"GREEN"])
    return road_names


            
