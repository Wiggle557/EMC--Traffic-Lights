import simpy
from models import TrafficLight, Road, Junction
from setup import setup, create_grid_roads
from display import animate_graph, display
import networkx as nx

def main():
    # Set up simulation environment
    env = simpy.Environment()

    # Grid size for junctions
    ROWS = 2
    COLS = 2
    num_junctions = ROWS * COLS
    junction_names = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    junctions:list[Junction] = []
    roads = []

    weights = [[(i + j) % 2 for j in range(COLS)] for i in range(ROWS)]
    # Create junctions
    for i in range(num_junctions):
        junctions.append(Junction(env, f"{junction_names[i]}", weight=weights[i // COLS][i % COLS]))
    
    # Generate grid structure for junctions
    junc_grid = []
    for i in range(ROWS):
        row = []
        for j in range(COLS):
            row.append(i * COLS + j)
        junc_grid.append(row)

    print("Junction Grid:", junc_grid)
    # Generate road connections for the grid
    road_connections = create_grid_roads(junc_grid)
    print("Road Connections:", road_connections)

    # Create roads and assign traffic lights
    for connection in road_connections:
        start, end, initial_color = connection
        new_road = Road(f"Road {junctions[start].name}{junctions[end].name}", 13, 100, junctions[start], junctions[end], simpy.Store(env))
        new_road.traffic_light = TrafficLight(env, new_road, red_time=15, green_time=15, amber_time=3, red_amber_time=3, colour=initial_color)
        new_road.traffic_light.name = new_road.name
        junctions[end].add_light(new_road.traffic_light)  # Add the traffic light to the ending junction
        roads.append(new_road)

    # Adding inroads and outroads for corners
    outroads = [
        Road(f"Road {junctions[junc_grid[0][0]].name}OUT", 13, 100, junctions[0], Junction(env, f"{junctions[junc_grid[0][0]].name}OUT", end=True), simpy.Store(env)),
        Road(f"Road {junctions[junc_grid[0][COLS - 1]].name}OUT", 13, 100, junctions[1], Junction(env, f"{junctions[junc_grid[0][COLS - 1]].name}OUT", end=True), simpy.Store(env)),
        Road(f"Road {junctions[junc_grid[ROWS - 1][0]].name}OUT", 13, 100, junctions[2], Junction(env, f"{junctions[junc_grid[ROWS - 1][0]].name}OUT", end=True), simpy.Store(env)),
        Road(f"Road {junctions[junc_grid[ROWS - 1][COLS - 1]].name}OUT", 13, 100, junctions[3], Junction(env, f"{junctions[junc_grid[ROWS - 1][COLS - 1]].name}OUT", end=True), simpy.Store(env))
    ]

    inroads = [
        Road(f"Road {junctions[junc_grid[0][0]].name}IN", 13, 100, Junction(env, f"{junctions[junc_grid[0][0]].name}IN", start=True), junctions[0], simpy.Store(env)),
        Road(f"Road {junctions[junc_grid[0][COLS - 1]].name}IN", 13, 100, Junction(env, f"{junctions[junc_grid[0][COLS - 1]].name}IN", start=True), junctions[1], simpy.Store(env)),
        Road(f"Road {junctions[junc_grid[ROWS - 1][0]].name}IN", 13, 100, Junction(env, f"{junctions[junc_grid[ROWS - 1][0]].name}IN", start=True), junctions[2], simpy.Store(env)),
        Road(f"Road {junctions[junc_grid[ROWS - 1][COLS - 1]].name}IN", 13, 100, Junction(env, f"{junctions[junc_grid[ROWS - 1][COLS - 1]].name}IN", start=True), junctions[3], simpy.Store(env))
    ]

    # Assign traffic lights to inroads and outroads
    for road in inroads + outroads:
        road.traffic_light = TrafficLight(env, road, red_time=15, green_time=15, amber_time=3, red_amber_time=3, colour="RED")
        road.traffic_light.name = road.name
        road.junction_end.add_light(road.traffic_light)

    # Extend roads list to include inroads and outroads
    roads.extend(inroads)
    roads.extend(outroads)

    # Add start/end junctions to the junction list
    for road in inroads:
        junctions.append(road.junction_start)
    for road in outroads:
        junctions.append(road.junction_end)

    # Initialize car setup
    env.process(setup(env, 20, roads, 9))

    # Animate the traffic network (optional)
    # animate_graph(env, junctions, roads)

    # Run the simulation
    env.run(until=180)

    # Display the final state of the traffic network
    pos = nx.spring_layout(nx.DiGraph())
    # display(junctions, roads, pos)

    # Display statistics on car queueing
    print("Cars left in queue:")
    total_passes = 0
    for road in roads:
        print(road.name)
        for car in road.car_queue.items:
            print(car.name)
            total_passes += car.junction_passes
    print(f"Total Junction Passes: {total_passes}")


if __name__ == "__main__":
    main()
