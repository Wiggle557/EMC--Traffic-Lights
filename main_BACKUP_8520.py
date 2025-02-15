import simpy
from models import TrafficLight, Road, Junction
from setup import setup, create_grid_roads
from display import animate_graph, display
import networkx as nx

def main():
    env = simpy.Environment()
<<<<<<< HEAD
    ROWS = 2
    COLS = 2
    num_junctions = ROWS*COLS
    junction_names = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    junctions = []
=======
    num_junctions = 4
    junction_names = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    junctions:list[Junction] = []
>>>>>>> a7419b5 (Updating to brandon's work)
    roads = []

    # Create junctions
    for i in range(num_junctions):
<<<<<<< HEAD
        junctions.append(Junction(env, f"{junction_names[i]}"))
=======
        junctions.append(Junction(env, f"Junction {junction_names[i]}"))
>>>>>>> a7419b5 (Updating to brandon's work)

    junctions.append(Junction(env, "OUT", end=True))
    # Create roads connecting junctions
<<<<<<< HEAD

    #road_names = [[0, 1], [1, 2], [2, 0], [1, 3], [0, 2], [3, 0], [0, 4], [2, 4]]
    junc_grid = []
    for i in range(ROWS):
        temp = []
        for j in range(COLS):
            temp.append(i*COLS+j)
        junc_grid.append(temp)
    print(junc_grid)
    road_names = create_grid_roads(junc_grid)
    print(road_names)
    for name in road_names:
        new_road = Road(f"Road {junctions[name[0]].name}{junctions[name[1]].name}", 13, 100, junctions[name[0]], junctions[name[1]], simpy.Store(env))
        roads.append(new_road)

    # Create and assign traffic lights to roads
    for i, road in enumerate(roads):
        road.traffic_light = TrafficLight(env, red_time=15, green_time=15, amber_time=3, red_amber_time=3, colour=road_names[i][2])
        road.traffic_light.name = road.name
        road.junction_end.add_light(road.traffic_light)

    # Add simulation processes
    env.process(setup(env, 20, roads, 9))

    # Animate the graph with environment updates
    #animate_graph(env, junctions, roads)

    # Run the simulation
    env.run(until=180)

    # Final static display of the graph
    #pos = nx.spring_layout(nx.DiGraph())
    #display(junctions, roads, pos)
=======
    roads.append(Road("Road AB", 6, 12, junctions[0], junctions[1],simpy.Store(env))
)
    roads.append(Road("Road BC", 6, 12, junctions[1], junctions[2],simpy.Store(env))
)
    roads.append(Road("Road CA", 6, 12, junctions[2], junctions[0],simpy.Store(env))
)
    roads.append(Road("Road BD", 6, 12, junctions[1], junctions[3],simpy.Store(env))
)
    roads.append(Road("Road AC", 6, 12, junctions[0], junctions[2],simpy.Store(env))
)
    roads.append(Road("Road DC", 6, 12, junctions[3], junctions[2],simpy.Store(env))
)

    # Create and assign traffic lights to roads
    for road in roads:
        road.traffic_light = TrafficLight(env, red_time=15, green_time=15)

    # Setup environment with cars
    env.process(setup(env, 20, roads, (1, 20)))
    env.run(until=180)

    print("Cars left in queue:")
    for road in roads:
        print(road.name)
        for car in road.car_queue.items:
            print(car.name)
>>>>>>> a7419b5 (Updating to brandon's work)

    print("Cars left in queue:")
    total_passes = 0
    for road in roads:
        print(road.name)
        for car in road.car_queue.items:
            print(car.name)
            total_passes += car.junction_passes
    print(total_passes)
if __name__ == "__main__":
    main()