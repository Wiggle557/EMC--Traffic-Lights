from models import Car, TrafficLight
import simpy
import random

def setup(env: simpy.Environment, num_cars: int, light: TrafficLight, car_queue: simpy.Store, junction: simpy.PriorityResource, interval: tuple[int, int]):
    """
    Sets up the junction and runs cars through the junction

    Parameters:
    env (simpy.Environment): Environment of the junction
    num_cars (int): The maximum number of cars that can go through the junction
    light (TrafficLight): The traffic light at the junction
    car_queue (simpy.Store): The queue of cars at the junction
    junction (simpy.PriorityResource): The junction resource
    interval (tuple[int, int]): Range of times between when new cars approach the junction
    """
    for i in range(num_cars):
        car = Car(env, f'Car {i}', junction, light, car_queue, random.randint(1, 6))
        env.process(car.run())
        yield env.timeout(random.randint(*interval))


