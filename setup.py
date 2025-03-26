from models import Car, Road
import simpy
import random

def setup(env: simpy.Environment, num_cars: int, roads: list[Road], interval: tuple[int, int]):
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
        road = random.choice([i for i in roads if not i.junction_end.end])
        car = Car(env, f'Car {i}', road, roads, random.randint(1, 6))
        env.process(car.run())
        yield env.timeout(random.randint(*interval))

def create_grid_roads(junctions: list[list[int]])->list[list[int|str]]:
    road_names:list[list[int|str]] = []
    for i, row in enumerate(junctions):
        for j, cell in enumerate(row):
            if i>0:
                road_names.append([cell,cell-len(row),"RED"])
            if i<len(row)-1:
                road_names.append([cell,cell+len(row),"RED"])
            if j>0:
                road_names.append([cell,cell-1,"GREEN"])
            if j<len(row)-1:
                road_names.append([cell,cell+1,"GREEN"])
            print(cell)
    return road_names


            
