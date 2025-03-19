from models import Road
import networkx as nx
import matplotlib.pyplot as plt

def set_node_roads(graph: nx.DiGraph, roads: list[Road]):
    """
    Add directed edges to the graph for each road, representing traffic flow and direction,
    with distinct colors for each direction.
    """
    for road in roads:
        # Assign edge colors based on traffic light states
        edge_color = "red" if road.traffic_light.colour == "RED" else "green"

        # Add a directed edge for the road with the relevant attributes
        graph.add_edge(
            road.junction_start.name,
            road.junction_end.name,
            weight=len(road.car_queue.items),  # Traffic density (queue size)
            label=road.name,  # Use road name as the unique label
            color=edge_color  # Set edge color
        )
    return graph

def update(env, graph, roads, pos, ax):
    """
    Update the graph in sync with the simulation environment's time progression.
    """
    # Clear the previous frame
    ax.clear()

    # Update edge attributes (colors, weights) based on traffic light state
    for road in roads:
        edge_color = "red" if road.traffic_light.colour == "RED" else "green"
        graph[road.junction_start.name][road.junction_end.name]["color"] = edge_color
        graph[road.junction_start.name][road.junction_end.name]["weight"] = len(road.car_queue.items)

    # Extract updated edge colors and labels
    edge_colors = [d["color"] for _, _, d in graph.edges(data=True)]
    edge_labels = dict([((u, v), d["label"]) for u, v, d in graph.edges(data=True)])

    # Identify curved edges for two-way roads
    curved_edges = []
    for u, v, d in graph.edges(data=True):
        if graph.has_edge(v, u):  # Curved edges exist if reverse direction exists
            curved_edges.append((u, v))

    # Identify straight edges (not part of two-way roads)
    straight_edges = [
        edge for edge in graph.edges() 
        if edge not in curved_edges and (edge[1], edge[0]) not in curved_edges
    ]

    # **Draw nodes**
    nx.draw_networkx_nodes(graph, pos, ax=ax, cmap=plt.get_cmap("jet"), node_size=800, node_color="lightblue")
    nx.draw_networkx_labels(graph, pos, ax=ax, font_color="black")

    # **Draw straight edges first**
    nx.draw_networkx_edges(
        graph, pos, ax=ax, edgelist=straight_edges, edge_color=edge_colors, arrowstyle="->", width=2
    )

    # **Draw curved edges on top**
    for u, v in curved_edges:
        # Curved edge for one direction
        nx.draw_networkx_edges(
            graph, pos, edgelist=[(u, v)], connectionstyle="arc3,rad=0.2",
            edge_color=graph[u][v]["color"], arrowstyle="->", arrowsize=20, width=2
        )
        # Curved edge for the reverse direction
        nx.draw_networkx_edges(
            graph, pos, edgelist=[(v, u)], connectionstyle="arc3,rad=-0.2",
            edge_color=graph[v][u]["color"], arrowstyle="->", arrowsize=20, width=2
        )

    # Draw edge labels
    nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels, ax=ax, font_size=8)

    # Update the title with the current simulation time
    ax.set_title(f"Traffic Network at Simulation Time: {env.now}")

    # Refresh the graph display
    plt.pause(0.1)
    # Draw edge labels
    nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels, ax=ax, font_size=8)

    # Update the title with the current simulation time
    ax.set_title(f"Traffic Network at Simulation Time: {env.now}")

    # Refresh the graph display
    plt.pause(0.1)  # Short pause for animation

def animate_graph(env, junctions, roads, pos=None):
    """
    Animate the graph using SimPy's environment-driven simulation time.
    """
    # Create a directed graph
    graph = nx.DiGraph()
    graph = set_node_roads(graph, roads)

    # Define node positions (create a consistent layout)
    if pos is None:
        pos = nx.spring_layout(graph, seed=42)

    # Set up the figure for live updates
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_axis_off()

    def simpy_animation():
        """
        A SimPy process that updates the graph in sync with the simulation environment.
        """
        while True:
            # Update the graph visualization with the current simulation state
            update(env, graph, roads, pos, ax)
            # Wait for the next simulation second
            yield env.timeout(1)

    # Add the animation process to the SimPy environment
    env.process(simpy_animation())

    # Start the animation (blocking call to show the plot)
    plt.show()

def display(junctions, roads, pos=None):
    """
    Display the static graph of junctions and roads with directed edges for traffic flow visualization.
    """
    # Create a directed graph
    graph = nx.DiGraph()

    # Populate the graph with nodes and edges
    graph = set_node_roads(graph, roads)

    # Define node values for coloring (optional)
    val_map = {junction.name: 1.0 for junction in junctions}
    values = [val_map.get(node, 0.45) for node in graph.nodes()]

    # Define edge colors based on attributes
    edge_colors = [d["color"] for _, _, d in graph.edges(data=True)]

    # Define edge labels (road names)
    edge_labels = dict([((u, v), d["label"]) for u, v, d in graph.edges(data=True)])

    # Use the provided layout or create a new one
    if pos is None:
        pos = nx.spring_layout(graph, seed=42)

    # Offset edges for better visualization of two-way roads
    curved_edges = []
    for u, v, d in graph.edges(data=True):
        if graph.has_edge(v, u):  # If reverse edge exists, make it curved
            curved_edges.append((u, v))

    # Draw nodes and labels
    nx.draw_networkx_nodes(graph, pos, cmap=plt.get_cmap("jet"), node_size=800, node_color="lightblue")
    nx.draw_networkx_labels(graph, pos, font_color="black")

    # Draw edges with curved lines for two-way roads
    for u, v in curved_edges:
        nx.draw_networkx_edges(
            graph, pos, edgelist=[(u, v)], connectionstyle="arc3,rad=0.2",
            edge_color=graph[u][v]["color"], arrowstyle="->", arrowsize=20, width=2
        )

    # Draw straight edges
    straight_edges = [edge for edge in graph.edges() if edge not in curved_edges and (edge[1], edge[0]) not in curved_edges]
    nx.draw_networkx_edges(graph, pos, edgelist=straight_edges, edge_color=edge_colors, arrowstyle="->", width=2)

    # Draw edge labels
    nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels, font_size=8)

    # Show the graph
    plt.title("Traffic Network with Two-Way Roads and Different Colors")
    plt.show()

    # Return the layout for reuse
    return pos

