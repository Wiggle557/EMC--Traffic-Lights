from models import Road
import networkx as nx
import matplotlib.pyplot as plt

def set_node_roads(graph: nx.DiGraph, roads: list[Road]):
    """
    Add directed edges to the graph for each road, representing traffic flow and direction,
    with distinct colors for each direction.
    """
    for road in roads:
        # Use custom logic to assign different colors to opposite edges
        if road.traffic_light.colour == "RED":
            edge_color = "red"
        else:
            edge_color = "green"

        # Add each road as a directed edge with attributes
        graph.add_edge(
            road.junction_start.name,
            road.junction_end.name,
            weight=len(road.car_queue.items),  # Traffic density (queue size)
            label=road.name,  # Use road name as the unique label
            color=edge_color  # Assign the edge color
        )
    return graph

def display(junctions, roads, pos=None):
    """
    Display the graph of junctions and roads with directed edges for traffic flow visualization.
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
        pos = nx.spring_layout(graph, seed=41)  # Use a fixed seed for consistent layouts

    # Offset edges for better visualization of two-way roads
    curved_edges = []
    for u, v, d in graph.edges(data=True):
        if graph.has_edge(v, u):
            curved_edges.append((u, v))  # Mark curved edges for two-way roads

    # Draw nodes and labels
    nx.draw_networkx_nodes(graph, pos, cmap=plt.get_cmap("jet"), node_color=values, node_size=800)
    nx.draw_networkx_labels(graph, pos, font_color="white")

    # Draw edges with curved lines for two-way roads
    for u, v in curved_edges:
        # Draw curved edge for one direction
        nx.draw_networkx_edges(
            graph, pos, edgelist=[(u, v)], connectionstyle="arc3,rad=0.2",
            edge_color=graph[u][v]["color"], arrowstyle="->", arrowsize=25, width=2
        )

    # Draw the remaining straight edges (not overlapping)
    straight_edges = [edge for edge in graph.edges() if edge not in curved_edges and (edge[1], edge[0]) not in curved_edges]
    nx.draw_networkx_edges(graph, pos, edgelist=straight_edges, arrowstyle="->", arrowsize=25, edge_color=edge_colors, width=2)

    # Draw unique edge labels for each road, offset for two-way roads
    for (u, v), label in edge_labels.items():
        if (v, u) in graph.edges():  # If a reverse edge exists
            label_pos = 0.25 if (u, v) in curved_edges else 0.75
            nx.draw_networkx_edge_labels(graph, pos, edge_labels={(u, v): label}, label_pos=label_pos)
        else:
            nx.draw_networkx_edge_labels(graph, pos, edge_labels={(u, v): label})

    # Show the graph
    plt.title("Traffic Network with Two-Way Roads and Different Colors")
    plt.show()

    # Return the layout for reuse
    return pos
