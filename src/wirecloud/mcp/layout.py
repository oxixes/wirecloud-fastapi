"""Deterministic wiring editor placement, independent of the MCP transport."""
from __future__ import annotations

from heapq import heapify, heappop, heappush

from fastapi import HTTPException


def component_nodes(status, valid_nodes, moves):
    """Include operators, displayed widgets, connected widgets, and explicit moves."""
    nodes = {("operator", key) for key in status.operators}
    nodes.update((kind, key) for kind in ("widget", "operator")
                 for key in getattr(status.visualdescription.components, kind))
    nodes.update((endpoint.type.value, endpoint.id) for connection in status.connections
                 for endpoint in (connection.source, connection.target))
    seen = set()
    for move in moves:
        node = (move.type, move.id)
        if node not in valid_nodes:
            raise HTTPException(404, "Wiring component not found")
        if node in seen:
            raise HTTPException(422, "Supply each component position only once")
        seen.add(node)
        nodes.add(node)
    return nodes & valid_nodes


def graph_layers(nodes, connections):
    """Lay out acyclic edges left to right; break feedback cycles deterministically."""
    edges = {node: set() for node in nodes}
    incoming = dict.fromkeys(nodes, 0)
    for connection in connections:
        source = (connection.source.type.value, connection.source.id)
        target = (connection.target.type.value, connection.target.id)
        if source != target and source in nodes and target in nodes and target not in edges[source]:
            edges[source].add(target)
            incoming[target] += 1
    layers = dict.fromkeys(nodes, 0)
    pending = {node for node in nodes}
    ready = [node for node in nodes if incoming[node] == 0]
    heapify(ready)
    while pending:
        if not ready:
            heappush(ready, min(pending))
        source = heappop(ready)
        pending.remove(source)
        for target in sorted(edges[source] & pending):
            layers[target] = max(layers[target], layers[source] + 1)
            incoming[target] -= 1
            if incoming[target] == 0:
                heappush(ready, target)
    return layers


def placement_patches(status, nodes, heights, moves=(), preserve_existing=True):
    """Patch only positions, preserving collapsed state, endpoint order and other views."""
    components = status.visualdescription.components
    existing = {node: getattr(components, node[0]).get(node[1]) for node in nodes}
    manual = {(move.type, move.id): {"x": move.x, "y": move.y} for move in moves}
    placed = {node: component.position.model_dump() for node, component in existing.items()
              if preserve_existing and component is not None and component.position is not None}
    placed.update(manual)
    layers = graph_layers(nodes, status.connections)

    def height(node):
        component = existing[node]
        return 90 if component is not None and component.collapsed else heights.get(node, 240)

    for node in sorted(nodes - placed.keys(), key=lambda node: (layers[node], node)):
        # Reserve an initial column for widget sources when adding isolated operators.
        column = layers[node] + (1 if node[0] == "operator" and not status.connections else 0)
        x, y = 20 + column * 420, 10
        while True:
            blockers = [other for other, position in placed.items()
                        if abs(position["x"] - x) < 380
                        and y < position["y"] + height(other) + 40
                        and position["y"] < y + height(node) + 40]
            if not blockers:
                break
            y = max(placed[other]["y"] + height(other) + 40 for other in blockers)
        placed[node] = {"x": x, "y": y}

    patches = []
    for node in sorted(nodes):
        component = existing[node]
        position = placed[node]
        if component is not None and component.position is not None and component.position.model_dump() == position:
            continue
        kind, identifier = node
        escaped = identifier.replace("~", "~0").replace("/", "~1")
        path = f"/visualdescription/components/{kind}/{escaped}"
        patches.append({"op": "add", "path": path + "/position" if component is not None else path,
                        "value": position if component is not None else {"position": position}})
    return patches
