import simpy
from models import TrafficLight
from setup import setup

def main():
    env = simpy.Environment()
    traffic_light = TrafficLight(env, green_time=30, red_time=30)
    junction = simpy.PriorityResource(env, capacity=1)
    car_queue = simpy.Store(env)
    env.process(setup(env, 20, traffic_light, car_queue, junction, (1, 20)))
    env.run(until=180)

    print("Cars left in queue:")
    for car in car_queue.items:
        print(car.name)

if __name__ == "__main__":
    main()

