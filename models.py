import simpy
import random
import math

class TrafficLight:
    def __init__(self, env: simpy.Environment, red_time=10, green_time=10, red_amber_time = 3, amber_time = 3, colour="GREEN"):
        self.env = env
        self.colour = colour
        self.red_time = red_time
        self.green_time = green_time
        self.red_amber_time = red_amber_time
        self.amber_time = amber_time
        self.last_change = env.now
        self.name = ""
        self.action = env.process(self.run())  # Start the traffic light process

    def run(self):
        """
        SimPy process to independently manage the state of the traffic light.
        """
        while True:
            self.last_change = self.env.now
            if self.colour == "RED":
                self.colour = "RAMBER"
                print(f"Light at {self.name} turns RED AMBER at {self.env.now}")
                yield self.env.timeout(self.red_amber_time)
            elif self.colour == "GREEN":
                self.colour = "AMBER"
                print(f"Light at {self.name} turns AMBER at {self.env.now}")
                yield self.env.timeout(self.amber_time)
            elif self.colour == "RAMBER":
                self.colour = "GREEN"
                print(f"Light at {self.name} turns GREEN at {self.env.now}")
                yield self.env.timeout(self.green_time)
            else:
                self.colour = "RED"
                print(f"Light at {self.name} turns RED at {self.env.now}")
                yield self.env.timeout(self.red_time)



class Junction:
    def __init__(self, env: simpy.Environment, name: str, end: bool = False):
        self.env = env
        self.name = name
        self.traffic_lights: list[TrafficLight] = []
        self.queue = simpy.PriorityResource(env, capacity=1)
        self.end = end

    def add_light(self, light):
        """
        Add a traffic light to the junction.
        """
        self.traffic_lights.append(light)


    def run(self):
        while True:
            for light in self.traffic_lights:
                if light.colour == "RED":
                    light.colour = "GREEN"
                    print(f"Light at {light.name} turns green at {self.env.now}")
                    yield self.env.timeout(light.green_time)
                else:
                    light.colour = "RED"
                    print(f"Light at {light.name} turns red at {self.env.now}")
                    yield self.env.timeout(light.red_time)



class Road:
    def __init__(self, name: str, speed: int, distance: int, junction_start: Junction, junction_end: Junction, car_queue: simpy.Store):
        self.name = name
        self.speed = speed
        self.distance = distance
        self.junction_start = junction_start
        self.junction_end = junction_end
        self.traffic_light:TrafficLight|None = None
        self.car_queue = car_queue

class Car:
    def __init__(self, env: simpy.Environment, name: str, road: Road, roads: list[Road], reaction_time=1, acceleration = 3.5, deccelaration = -8.1, ) -> None:
        self.env = env
        self.name = name
        self.road = road
        self.reaction_time = reaction_time
        self.acceleration = acceleration
        self.decceleration = deccelaration
        self.speed = self.road.speed
        self.roads = roads
        self.junction_passes = 0

    def run(self):
        while True:
            print(f"{self.name} arriving at {self.road.junction_start.name} at {self.env.now}")
            yield self.road.car_queue.put(self)

            with self.road.junction_start.queue.request(priority=1) as request:
                yield request
                while self.road.traffic_light.colour == "RED" or self.road.car_queue.items[0] != self:
                    print(f"{self.name} waiting at red light in {self.road.junction_start.name} at {self.env.now}")
                    yield self.env.timeout(self.reaction_time)

                car = yield self.road.car_queue.get()
                if car == self:
                    print(f"{self.name} entering {self.road.junction_start.name} at {self.env.now}")
                    self.junction_passes+=1
                    if self.road.junction_end.end:
                        break
                    v_max = math.sqrt(self.speed**2+2*self.acceleration*self.road.distance)
                    if v_max <= self.road.speed:
                        total_tG = (v_max-self.speed)/self.acceleration
                        new_speed=v_max
                    else:
                        s_1 = (self.road.speed**2-self.speed**2)/(2*self.acceleration)
                        s_c = self.road.distance-s_1
                        t_1 = (self.road.speed-self.speed)/(self.acceleration)
                        t_c = s_c/self.road.speed
                        total_tG = t_1+t_c
                        new_speed = self.road.speed
                    #else:
                    final_v = 0
                    v_p = math.sqrt((self.decceleration*self.speed**2-self.acceleration*final_v**2+2*self.acceleration*self.decceleration)/(self.decceleration-self.acceleration))
                    if v_p>self.road.speed:
                        s_1 = (self.road.speed**2-self.speed**2)/(2*self.acceleration)
                        s_2 = (final_v-self.road.speed**2)/(2*self.decceleration)
                        s_c = self.road.distance-s_1-s_2
                        t_1 = (self.road.speed-self.speed)/self.acceleration
                        t_c = s_c/self.road.speed
                        t_2 = (self.road.speed-final_v)/self.decceleration
                        total_tR = t_1+t_c+t_2
                    else:
                        t_1 = (v_p-self.speed)/self.acceleration
                        t_2 = (final_v-v_p)/self.decceleration
                        total_tR = t_1+t_2
                    
                    colour = self.road.traffic_light.colour
                    t = self.env.now - self.road.traffic_light.last_change
                    while t<total_tR:
                        match colour:
                            case "RED":
                                colour="RAMBER"
                                t+=self.road.traffic_light.red_amber_time
                            case "RAMBER":
                                colour = "GREEN"
                                t+=self.road.traffic_light.green_time
                            case "GREEN":
                                colour = "AMBER"
                                t+=self.road.traffic_light.amber_time
                            case "AMBER":
                                colour = "RED"
                                t+=self.road.traffic_light.red_time

                    if colour=="RED" or colour=="RAMBER":
                        travel_time = total_tR
                        self.speed=0
                    else:
                        travel_time = total_tG
                        self.speed=new_speed


                    yield self.env.timeout(travel_time/2)
                    print(f"{self.name} driving on {self.road.name}")
                    yield self.env.timeout(travel_time/2)

                    # Update the road to the next road in the loop
                    next_junction = self.road.junction_end
                    self.road = random.choice([road for road in self.roads if road.junction_start == next_junction])
        print(f"{self.name} leaving from {self.road.junction_start.name}")


