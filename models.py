import simpy

class TrafficLight:
    def __init__(self, env: simpy.Environment, red_time=10, green_time=10):
        self.env = env
        self.colour = "GREEN"
        self.action = env.process(self.run())
        self.red_time = red_time
        self.green_time = green_time

    def run(self):
        while True:
            if self.colour == "GREEN":
                yield self.env.timeout(self.green_time)
                self.colour = "RED"
                print(f"Light turned RED at {self.env.now}")
            else:
                yield self.env.timeout(self.red_time)
                self.colour = "GREEN"
                print(f"Light turned GREEN at {self.env.now}")

class Junction:
    def __init__(self, env: simpy.Environment, name: str):
        self.env = env
        self.name = name
        self.queue = simpy.PriorityResource(env, capacity=1)
        self.traffic_light = None

    def set_traffic_light(self, traffic_light: TrafficLight):
        self.traffic_light = traffic_light

class Road:
    def __init__(self, name: str, speed: int, distance: int, junction_start: Junction, junction_end: Junction):
        self.name = name
        self.speed = speed
        self.distance = distance
        self.junction_start = junction_start
        self.junction_end = junction_end

class Car:
    def __init__(self, env: simpy.Environment, name: str, car_queue: simpy.Store, road: Road, reaction_time=1) -> None:
        self.env = env
        self.name = name
        self.car_queue = car_queue
        self.road = road
        self.reaction_time = reaction_time
        env = road.junction_start.env
        # Create junctions
        junction_a = Junction(env, "Junction A")
        junction_b = Junction(env, "Junction B")
        junction_c = Junction(env, "Junction C")

        # Create traffic lights
        traffic_light_a = TrafficLight(env, red_time=20, green_time=20)
        traffic_light_b = TrafficLight(env, red_time=15, green_time=15)
        traffic_light_c = TrafficLight(env, red_time=10, green_time=10)

        # Assign traffic lights to junctions
        junction_a.set_traffic_light(traffic_light_a)
        junction_b.set_traffic_light(traffic_light_b)
        junction_c.set_traffic_light(traffic_light_c)

        # Create roads connecting junctions
        road_ab = Road("Road AB", 6, 10, junction_a, junction_b)
        road_bc = Road("Road BC", 5, 15, junction_b, junction_c)
        road_ca = Road("Road CA", 7, 20, junction_c, junction_a)
        self.roads = [road_ab,road_bc, road_ca]

    def run(self):
        while True:
            print(f"{self.name} arriving at {self.road.junction_start.name} at {self.env.now}")
            yield self.car_queue.put(self)

            with self.road.junction_start.queue.request(priority=1) as request:
                yield request
                while self.road.junction_start.traffic_light.colour == "RED" or self.car_queue.items[0] != self:
                    print(f"{self.name} waiting at red light at {self.env.now}")
                    yield self.env.timeout(self.reaction_time)
