import simpy
import random

class TrafficLight:
    def __init__(self, env: simpy.Environment, red_time=10, green_time=10, colour="GREEN"):
        self.env = env
        self.colour = colour
        self.red_time = red_time
        self.green_time = green_time
        self.name = ""
        self.action = env.process(self.run())  # Start the traffic light process

    def run(self):
        """
        SimPy process to independently manage the state of the traffic light.
        """
        while True:
            if self.colour == "RED":
                self.colour = "GREEN"
                print(f"Light at {self.name} turns GREEN at {self.env.now}")
                yield self.env.timeout(self.green_time)
            else:
                self.colour = "RED"
                print(f"Light at {self.name} turns RED at {self.env.now}")
                yield self.env.timeout(self.red_time)



class Junction:
    def __init__(self, env: simpy.Environment, name: str, end: bool = False):
        self.env = env
        self.name = name
        self.traffic_lights: list[TrafficLight] = []
        self.queue = simpy.PriorityResource(env, capacity=1)
        self.end = end

    def add_light(self, light):
        """
        Add a traffic light to the junction.
        """
        self.traffic_lights.append(light)


    def run(self):
        while True:
            for light in self.traffic_lights:
                if light.colour == "RED":
                    light.colour = "GREEN"
                    print(f"Light at {light.name} turns green at {self.env.now}")
                    yield self.env.timeout(light.green_time)
                else:
                    light.colour = "RED"
                    print(f"Light at {light.name} turns red at {self.env.now}")
                    yield self.env.timeout(light.red_time)



class Road:
    def __init__(self, name: str, speed: int, distance: int, junction_start: Junction, junction_end: Junction, car_queue: simpy.Store):
        self.name = name
        self.speed = speed
        self.distance = distance
        self.junction_start = junction_start
        self.junction_end = junction_end
        self.traffic_light = None
        self.car_queue = car_queue

class Car:
    def __init__(self, env: simpy.Environment, name: str, road: Road, roads: list[Road], reaction_time=1) -> None:
        self.env = env
        self.name = name
        self.road = road
        self.reaction_time = reaction_time
        self.roads = roads

    def run(self):
        while True:
            print(f"{self.name} arriving at {self.road.junction_start.name} at {self.env.now}")
            yield self.road.car_queue.put(self)

            with self.road.junction_start.queue.request(priority=1) as request:
                yield request
                while self.road.traffic_light.colour == "RED" or self.road.car_queue.items[0] != self:
                    print(f"{self.name} waiting at red light in {self.road.junction_start.name} at {self.env.now}")
                    yield self.env.timeout(self.reaction_time)

                car = yield self.road.car_queue.get()
                if car == self:
                    print(f"{self.name} entering {self.road.junction_start.name} at {self.env.now}")
                    if self.road.junction_end.end:
                        break

                    travel_time = self.road.distance / self.road.speed
                    yield self.env.timeout(travel_time/2)
                    print(f"{self.name} driving on {self.road.name}")
                    yield self.env.timeout(travel_time/2)

                    # Update the road to the next road in the loop
                    next_junction = self.road.junction_end
                    self.road = random.choice([road for road in self.roads if road.junction_start == next_junction])
        print(f"{self.name} leaving from {self.road.junction_start.name}")


