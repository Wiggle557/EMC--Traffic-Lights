import simpy
import random

class Car:
    def __init__(self, env, name, junction, light) -> None:
        self.env = env
        self.name = name
        self.junction = junction
        self.light = light

    def run(self):
        print(f"{self.name} arriving at junction at {self.env.now}")
        with self.junction.request() as request:
            yield request
            print(f"{self.name} entering junction at {self.env.now}")
            yield self.env.timeout(random.randint(3, 12))
            print(f"{self.name} leaving junction at {self.env.now}")

            while self.light.color == "RED":
                print(f"{self.name} waiting at red light at {self.env.now}")
                yield self.env.timeout(1)
            print(f"{self.name} passing the light at {self.env.now}")

class TrafficLight:
    def __init__(self, env):
        self.env = env
        self.color = "GREEN"
        self.action = env.process(self.run())

    def run(self):
        while True:
            if self.color == "GREEN":
                yield self.env.timeout(10)
                self.color = "RED"
                print(f"Light turned RED at {self.env.now}")
            else:
                yield self.env.timeout(10)
                self.color = "GREEN"
                print(f"Light turned GREEN at {self.env.now}")

def setup(env, num_cars, light):
    junction = simpy.Resource(env, capacity=1)
    for i in range(num_cars):
        car = Car(env, f'Car {i}', junction, light)
        env.process(car.run())
        yield env.timeout(random.randint(1, 4))

env = simpy.Environment()
traffic_light = TrafficLight(env)
env.process(setup(env, 10, traffic_light))
env.run(until=100)

