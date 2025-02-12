import simpy
from models import TrafficLight, Road, Junction
from setup import setup

def main():
    env = simpy.Environment()
    num_junctions = 4
    junction_names="ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    junctions:list[Junction] = []
    traffic_lights = []
    roads = []
    for i in range(num_junctions):
        junctions.append(Junction(env, f"Junction {junction_names[i]}"))
        traffic_lights.append(TrafficLight(env, red_time=15, green_time=15))
    for i in range(len(junctions)):
        junctions[i].set_traffic_light(traffic_lights[i])
        roads.append(Road(f"Road {junction_names[:num_junctions][i-1]}{junction_names[i]}",6,12,junctions[i-1],junctions[i]))
    
    car_queue = simpy.Store(env)

    # Setup environment with cars
    env.process(setup(env, 20, car_queue, roads, (1, 20)))
    env.run(until=180)


if __name__ == "__main__":
    main()

