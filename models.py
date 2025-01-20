import simpy

class TrafficLight:
    def __init__(self, env: simpy.Environment, red_time=10, green_time=10):
        self.env = env
        self.color = "GREEN"
        self.action = env.process(self.run())
        self.red_time = red_time
        self.green_time = green_time

    def run(self):
        while True:
            if self.color == "GREEN":
                yield self.env.timeout(self.green_time)
                self.color = "RED"
                print(f"Light turned RED at {self.env.now}")
            else:
                yield self.env.timeout(self.red_time)
                self.color = "GREEN"
                print(f"Light turned GREEN at {self.env.now}")

class Car:
    def __init__(self, env: simpy.Environment, name: str, junction: simpy.PriorityResource, light: TrafficLight, car_queue: simpy.Store, reaction_time=1) -> None:
        self.env = env
        self.name = name
        self.junction = junction
        self.light = light
        self.car_queue = car_queue
        self.reaction_time = reaction_time

    def run(self):
        print(f"{self.name} arriving at junction at {self.env.now}")
        yield self.car_queue.put(self)

        with self.junction.request(priority=1) as request:
            yield request
            while self.light.color == "RED" or self.car_queue.items[0] != self:
                print(f"{self.name} waiting at red light at {self.env.now}")
                yield self.env.timeout(self.reaction_time)

            car = yield self.car_queue.get()
            if car == self:
                print(f"{self.name} entering junction at {self.env.now}")
                yield self.env.timeout(self.reaction_time)
                print(f"{self.name} leaving junction at {self.env.now}")

