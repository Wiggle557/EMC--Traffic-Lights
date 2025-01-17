import simpy
from models import TrafficLight
from setup import setup

def main():
    env = simpy.Environment()
    traffic_light = TrafficLight(env,green_time=10,red_time=10)
    env.process(setup(env, 10, traffic_light, (1,10)))
    env.run(until=100)

if __name__ == "__main__":
    main()
