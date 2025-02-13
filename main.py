import simpy
from models import TrafficLight, Road, Junction
from setup import setup

def main():
    env = simpy.Environment()
    num_junctions = 4
    junction_names = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    junctions = []
    roads = []

    # Create junctions
    for i in range(num_junctions):
        junctions.append(Junction(env, f"Junction {junction_names[i]}"))

    # Create roads connecting junctions
    roads.append(Road("Road AB", 6, 12, junctions[0], junctions[1]))
    roads.append(Road("Road BC", 6, 12, junctions[1], junctions[2]))
    roads.append(Road("Road CA", 6, 12, junctions[2], junctions[0]))
    roads.append(Road("Road BD", 6, 12, junctions[1], junctions[3]))
    roads.append(Road("Road AC", 6, 12, junctions[0], junctions[2]))
    roads.append(Road("Road BD", 6, 12, junctions[3], junctions[2]))

    # Create and assign traffic lights to roads
    for road in roads:
        road.traffic_light = TrafficLight(env, red_time=15, green_time=15)

    car_queue = simpy.Store(env)

    # Setup environment with cars
    env.process(setup(env, 20, car_queue, roads, (1, 20)))
    env.run(until=180)

    print("Cars left in queue:")
    for car in car_queue.items:
        print(car.name)

if __name__ == "__main__":
    main()

