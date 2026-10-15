import osmnx as ox

G = ox.load_graphml('kpriet_graph.graphml')
campus_nodes = set([n for n, d in G.nodes(data=True) if 11.080 <= d['y'] <= 11.087 and 77.132 <= d['x'] <= 77.140])
print(f"Campus nodes count: {len(campus_nodes)}")
for u, v, k, d in G.edges(keys=True, data=True):
    if u in campus_nodes and v in campus_nodes:
        hw = d.get('highway')
        name = d.get('name')
        length = float(d.get('length', 0))
        print(f"Edge {u} -> {v}: hw={hw}, name={name}, len={length:.1f}m")
