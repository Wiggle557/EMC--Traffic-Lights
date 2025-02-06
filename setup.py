from models import Car, Road
import simpy
import random

def setup(env: simpy.Environment, num_cars: int, car_queue: simpy.Store, roads: list[Road], interval: tuple[int, int]):
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
        road = random.choice(roads)
        car = Car(env, f'Car {i}', car_queue, road, roads, random.randint(1, 6))
        env.process(car.run())
        yield env.timeout(random.randint(*interval))

