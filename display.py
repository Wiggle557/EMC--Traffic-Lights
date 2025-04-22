# display.py
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.animation import FuncAnimation
from functools import partial
from math import sqrt
import matplotlib.patches as mpatches

def build_graph(roads):
    """
    Constructs a NetworkX MultiDiGraph from the list of road objects.
    Each road's junction_start and junction_end must have a 'name' attribute.
    Each edge stores:
      - traffic_state: the current color of the traffic light,
      - queue: the number of cars waiting,
      - key: the road's unique name.
    """
    G = nx.MultiDiGraph()
    for road in roads:
        start = road.junction_start.name
        end = road.junction_end.name
        G.add_node(start)
        G.add_node(end)
        queue_val = len(road.car_queue.items) if hasattr(road.car_queue, 'items') else 0
        G.add_edge(start, end, traffic_state=road.traffic_light.colour, queue=queue_val, key=road.name)
    return G

def get_node_positions(grid_rows, grid_cols):
    """
    Returns a dictionary mapping node names to positions.
    Base nodes are at (j, -i). Side nodes (Top, Bottom, Left, Right)
    are given a small offset; external nodes are more offset.
    """
    positions = {}
    for i in range(grid_rows):
        for j in range(grid_cols):
            base = f"Junction_{i}_{j}"
            positions[base] = (j, -i)
            positions[f"Top_{base}"] = (j, -i + 0.2)
            positions[f"Bottom_{base}"] = (j, -i - 0.2)
            positions[f"Left_{base}"] = (j - 0.2, -i)
            positions[f"Right_{base}"] = (j + 0.2, -i)
            positions[f"Connector_Top_{base}"] = (j, -i + 0.2)
            positions[f"Connector_Bottom_{base}"] = (j, -i - 0.2)
            positions[f"Connector_Left_{base}"] = (j - 0.2, -i)
            positions[f"Connector_Right_{base}"] = (j + 0.2, -i)
            positions[f"Ext_Top_{base}"] = (j, -i + 0.8)
            positions[f"Ext_Bottom_{base}"] = (j, -i - 0.8)
            positions[f"Ext_Left_{base}"] = (j - 0.8, -i)
            positions[f"Ext_Right_{base}"] = (j + 0.8, -i)
    return positions

def update(frame, env_time, roads, pos, ax):
    """
    Update function for FuncAnimation.
    Draws nodes, edges, and their labels using unique keys for each directed edge.
    Also adds a legend and a dynamic title with the current simulation time.
    """
    ax.clear()
    G = build_graph(roads)
    
    # Draw nodes and labels.
    nx.draw_networkx_nodes(G, pos, node_size=400, node_color="lightblue", ax=ax)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=8)
    
    seen = {}
    edge_labels = {}
    custom_label_positions = {}
    for u, v, key, data in G.edges(keys=True, data=True):
        # Use the triple (u, v, key) for uniqueness.
        count = seen.get((u, v, key), 0)
        rad = 0.1 * ((count // 2) + 1) * (1 if count % 2 == 0 else -1)
        seen[(u, v, key)] = count + 1
        
        state = data.get("traffic_state", "RED")
        color = "green" if state.upper() == "GREEN" else "red"
        queue_val = data.get("queue", 0)
        width = 1 + 0.5 * queue_val
        
        nx.draw_networkx_edges(G, pos, edgelist=[(u, v)],
                                arrowstyle='->', arrowsize=15,
                                edge_color=color, width=width,
                                connectionstyle=f"arc3, rad={rad}",
                                ax=ax)
        
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1
        length = sqrt(dx**2 + dy**2)
        perp = (0, 0) if length == 0 else (-dy / length, dx / length)
        offset = rad * 1.5
        lx, ly = mx + perp[0] * offset, my + perp[1] * offset
        custom_label_positions[(u, v, key)] = (lx, ly)
        
        if queue_val:
            edge_labels[(u, v, key)] = str(queue_val)
    
    for (u, v, key), label in edge_labels.items():
        lx, ly = custom_label_positions[(u, v, key)]
        ax.text(lx, ly, label, fontsize=7, color='blue', horizontalalignment='center', verticalalignment='center')
    
    # Add a legend.
    red_patch = mpatches.Patch(color='red', label='RED Light')
    green_patch = mpatches.Patch(color='green', label='GREEN Light')
    blue_patch = mpatches.Patch(color='blue', label='Queue Count')
    ax.legend(handles=[red_patch, green_patch, blue_patch], loc='upper right', fontsize='small')
    
    ax.set_title(f"Simulation Time: {env_time()} seconds", fontsize=10)
    ax.set_axis_off()

def animate_network(env, roads, grid_rows, grid_cols, update_interval=1, save_to_file=None):
    """
    Sets up and runs the animation using FuncAnimation.
    If save_to_file is provided (such as "simulation.mp4"), the animation is saved using FFmpeg or ImageMagick.
    """
    pos = get_node_positions(grid_rows, grid_cols)
    fig, ax = plt.subplots(figsize=(8, 8))
    env_time = partial(lambda: int(env.now))
    ani = FuncAnimation(fig, update, fargs=(env_time, roads, pos, ax),
                        interval=update_interval * 1000,
                        cache_frame_data=False, save_count=200)
    if save_to_file:
        writer = 'ffmpeg' if save_to_file.endswith('.mp4') else 'imagemagick'
        ani.save(save_to_file, fps=int(1/update_interval), writer=writer)
        print(f"Animation saved to {save_to_file}")
    else:
        plt.show()
    return ani

def display_statistics(roads):
    """
    Computes simulation statistics from the road object list and prints them.
      - Total junction passes
      - Average junction passes per car
      - Average waiting time per car
    """
    total_passes = 0
    total_wait = 0
    count = 0
    for road in roads:
        for car in road.car_queue.items:
            total_passes += car.junction_passes
            total_wait += getattr(car, "wait_time", 0)
            count += 1
    avg_wait = total_wait / count if count else 0
    print("Simulation Statistics:")
    print("----------------------")
    print("Total Junction Passes:", total_passes)
    print("Average Junction Passes per Car:", total_passes / count if count else 0)
    print("Average Waiting Time per Car:", avg_wait)

