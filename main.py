import simpy
from models import TrafficLight, Road, Junction
from setup import setup

def main():
    env = simpy.Environment()

    # Create junctions
    junction_a = Junction(env, "Junction A")
    junction_b = Junction(env, "Junction B")
    junction_c = Junction(env, "Junction C")

    # Create traffic lights
    traffic_light_a = TrafficLight(env, red_time=20, green_time=20)
    traffic_light_b = TrafficLight(env, red_time=15, green_time=15)
    traffic_light_c = TrafficLight(env, red_time=10, green_time=10)

    # Assign traffic lights to junctions
    junction_a.set_traffic_light(traffic_light_a)
    junction_b.set_traffic_light(traffic_light_b)
    junction_c.set_traffic_light(traffic_light_c)

    # Create roads connecting junctions
    road_ab = Road("Road AB", 60, 10, junction_a, junction_b)
    road_bc = Road("Road BC", 50, 15, junction_b, junction_c)
    road_ca = Road("Road CA", 70, 20, junction_c, junction_a)

    car_queue = simpy.Store(env)

    # Setup environment with cars
    env.process(setup(env, 20, car_queue, [road_ab, road_bc, road_ca], (1, 20)))
    env.run(until=180)

    print("Cars left in queue:")
    for car in car_queue.items:
        print(car.name)

if __name__ == "__main__":
    main()

