from models import Car, TrafficLight
import simpy
import random

def setup(env:simpy.Environment, num_cars:int, light:TrafficLight,interval:tuple[int,int]):
    """
    Sets up the junction and runs cars through the junction
    
    Parameters:
    env (simpy.Environment): Environment of the junction
    num_cars (int): The maximum number of cars that can go through the junction
    light (TrafficLight): The traffic light at the junction
    interval (tuple[int,int]): Range of times between when new cars approach the junction
    """
    junction = simpy.Resource(env, capacity=1)
    for i in range(num_cars):
        car = Car(env, f'Car {i}', junction, light,random.randint(1,6))
        env.process(car.run())
        # TODO: Add options for different types of distributions of cars.
        yield env.timeout(random.randint(*interval))

def main():
    env = simpy.Environment()
    traffic_light = TrafficLight(env, 10, 10)
    env.process(setup(env, 10, traffic_light,(1,7)))
    env.run(until=100)

if __name__=="__main__":
    main()
