import simpy
from models import TrafficLight, Road, Junction
from setup import setup
from display import display

def main():
    env = simpy.Environment()
    num_junctions = 4
    junction_names = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    junctions:list[Junction] = []
    roads = []

    # Create junctions
    for i in range(num_junctions):
        junctions.append(Junction(env, f"{junction_names[i]}"))

    # Create roads connecting junctions
    road_names = [[0,1],[1,2],[2,0],[1,3],[0,2],[3,0]]
    for name in road_names:
        new_road = Road(f"Road {junctions[name[0]].name}{junctions[name[1]].name}",6,12,junctions[name[0]],junctions[name[1]],simpy.Store(env))
        roads.append(new_road)

    # Create and assign traffic lights to roads
    for road in roads:
        road.traffic_light = TrafficLight(env, red_time=15, green_time=15)
        road.traffic_light.name = road.name
        road.junction_end.add_light(road.traffic_light)

    # Setup environment with cars
    display(junctions,roads)
    env.process(setup(env, 20, roads, (1, 20)))
    env.run(until=180)

    print("Cars left in queue:")
    for road in roads:
        print(road.name)
        for car in road.car_queue.items:
            print(car.name)

if __name__ == "__main__":
    main()

