#!/usr/bin/env python3
"""
Visual Debugger Template for CodeHelper.

Provides a tkinter-based GUI for visualizing abstract data structures
(linked lists, binary trees, graphs, BFS/DFS traversals).

Deep-mode helper described by spec/tests.md. Generated task-specific visual
debuggers belong in ``output/<task>/tools/``; this module remains a reusable
template only.

Usage — two modes:

1. As a library (import into your debugger):
      from visual_debugger import DebugCanvas, draw_linked_list, draw_binary_tree

2. As a standalone demo:
      python visual_debugger.py

Supported visualizations:
  - Singly / Doubly linked lists (with node values and pointers)
  - Binary trees (with parent-child edges)
  - 2D grid / board state (for games like 2048)
  - BFS/DFS traversal step-by-step replay

Dependencies: tkinter (included with Python on most platforms)
"""

import tkinter as tk
import math
from dataclasses import dataclass, field
from typing import Any, Optional


# ── Color palette ──────────────────────────────────────────────────────

COLORS = {
    "bg": "#FAFAFA",
    "node": "#4A90D9",
    "node_text": "#FFFFFF",
    "node_highlight": "#E74C3C",
    "edge": "#555555",
    "grid_bg": "#CDC0B0",
    "grid_tile_2": "#EEE4DA",
    "grid_tile_4": "#EDE0C8",
    "grid_tile_8": "#F2B179",
    "grid_tile_16": "#F59563",
    "grid_tile_32": "#F67C5F",
    "grid_tile_64": "#F65E3B",
    "grid_tile_128": "#EDCF72",
    "grid_tile_256": "#EDCC61",
    "grid_tile_512": "#EDC850",
    "grid_tile_1024": "#EDC53F",
    "grid_tile_2048": "#EDC22E",
    "text_dark": "#776E65",
    "text_light": "#F9F6F2",
}


def tile_color(value: int) -> str:
    """Return background color for a 2048 tile value."""
    key = f"grid_tile_{value}"
    return COLORS.get(key, "#3C3A32")


def text_color(value: int) -> str:
    """Return text color for a 2048 tile value."""
    return COLORS["text_light"] if value > 4 else COLORS["text_dark"]


# ── Canvas wrapper ─────────────────────────────────────────────────────

@dataclass
class DebugCanvas:
    """Wraps a tkinter Canvas with helper methods for drawing structures."""

    canvas: tk.Canvas
    width: int = 800
    height: int = 600
    _tag_counter: int = 0

    def clear(self):
        """Remove all drawn elements."""
        self.canvas.delete("all")

    def _next_tag(self, prefix: str = "item") -> str:
        self._tag_counter += 1
        return f"{prefix}_{self._tag_counter}"

    # ── shapes ──────────────────────────────────────────────────────

    def draw_node(self, x: int, y: int, value: Any, radius: int = 25,
                  color: str = None, text_color: str = None) -> str:
        """Draw a circular node with text. Returns tag."""
        color = color or COLORS["node"]
        text_color = text_color or COLORS["node_text"]
        tag = self._next_tag("node")

        self.canvas.create_oval(
            x - radius, y - radius, x + radius, y + radius,
            fill=color, outline="", tags=tag,
        )
        self.canvas.create_text(
            x, y, text=str(value), fill=text_color,
            font=("Arial", 12, "bold"), tags=tag,
        )
        return tag

    def draw_arrow(self, x1: int, y1: int, x2: int, y2: int,
                   color: str = None) -> str:
        """Draw a directed arrow from (x1,y1) to (x2,y2)."""
        color = color or COLORS["edge"]
        tag = self._next_tag("arrow")
        self.canvas.create_line(
            x1, y1, x2, y2, fill=color, width=2,
            arrow=tk.LAST, arrowshape=(10, 12, 5), tags=tag,
        )
        return tag

    def draw_line(self, x1: int, y1: int, x2: int, y2: int,
                  color: str = None, width: int = 2) -> str:
        """Draw a line (undirected edge)."""
        color = color or COLORS["edge"]
        tag = self._next_tag("line")
        self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width, tags=tag)
        return tag

    def draw_rect(self, x: int, y: int, w: int, h: int,
                  fill: str = None, text: str = "", text_c: str = None) -> str:
        """Draw a rectangle with optional centered text."""
        fill = fill or COLORS["node"]
        text_c = text_c or COLORS["node_text"]
        tag = self._next_tag("rect")

        self.canvas.create_rectangle(x, y, x + w, y + h, fill=fill, outline="", tags=tag)
        if text:
            self.canvas.create_text(
                x + w // 2, y + h // 2, text=text, fill=text_c,
                font=("Arial", 12, "bold"), tags=tag,
            )
        return tag

    def draw_text(self, x: int, y: int, text: str, color: str = "#333",
                  size: int = 14, bold: bool = False) -> str:
        """Draw text at a specific position."""
        tag = self._next_tag("text")
        font_style = ("Arial", size, "bold" if bold else "normal")
        self.canvas.create_text(x, y, text=text, fill=color, font=font_style, tags=tag)
        return tag


# ── Structure renderers ────────────────────────────────────────────────

def draw_linked_list(canvas: DebugCanvas, values: list,
                     x: int = 50, y: int = 100,
                     node_radius: int = 25, spacing: int = 100,
                     highlight_idx: int = -1,
                     prev_pointers: bool = False) -> None:
    """Draw a singly or doubly linked list.

    Args:
        canvas: DebugCanvas wrapper.
        values: List of node values to display.
        x, y: Starting position for the first node.
        node_radius: Radius of each node circle.
        spacing: Horizontal spacing between nodes.
        highlight_idx: Index of node to highlight (-1 = none).
        prev_pointers: If True, draw back-pointers (doubly linked).
    """
    for i, val in enumerate(values):
        cx = x + i * spacing
        color = COLORS["node_highlight"] if i == highlight_idx else COLORS["node"]
        canvas.draw_node(cx, y, val, node_radius, color=color)

        # Forward arrow
        if i < len(values) - 1:
            nx = cx + node_radius
            nx2 = x + (i + 1) * spacing - node_radius
            canvas.draw_arrow(nx, y, nx2, y)

        # Back arrow (doubly linked)
        if prev_pointers and i > 0:
            px = cx - node_radius
            px2 = x + (i - 1) * spacing + node_radius
            canvas.draw_arrow(px, y + 15, px2, y + 15, color="#AAA")


def draw_binary_tree(canvas: DebugCanvas, root: Any = None,
                     values: list = None,
                     x: int = 400, y: int = 50,
                     h_spacing: int = 80, v_spacing: int = 80,
                     node_radius: int = 20) -> None:
    """Draw a binary tree.

    Args:
        canvas: DebugCanvas wrapper.
        root: A tree node object with .val, .left, .right attributes.
        values: Flat list representation [root, left, right, ...] (None = empty).
                Used if root is None.
        x, y: Root node position.
        h_spacing: Horizontal spacing between nodes at the same level.
        v_spacing: Vertical spacing between levels.
        node_radius: Radius of each node circle.
    """
    if root is not None:
        # Draw using node objects
        def _draw(node, cx, cy, dx):
            if node is None:
                return
            canvas.draw_node(cx, cy, node.val, node_radius)
            if node.left:
                lx = cx - dx
                ly = cy + v_spacing
                canvas.draw_line(cx + node_radius // 2, cy + node_radius,
                                 lx, ly - node_radius)
                _draw(node.left, lx, ly, dx // 2)
            if node.right:
                rx = cx + dx
                ry = cy + v_spacing
                canvas.draw_line(cx + node_radius // 2, cy + node_radius,
                                 rx, ry - node_radius)
                _draw(node.right, rx, ry, dx // 2)

        _draw(root, x, y, h_spacing)
        return

    # Fallback: draw from flat list
    if values is None:
        return

    positions = {}
    for i, val in enumerate(values):
        if val is None:
            continue
        level = int(math.log2(i + 1))
        pos_in_level = i - (2 ** level - 1)
        nodes_in_level = 2 ** level

        total_width = nodes_in_level * h_spacing
        start_x = x - total_width // 2
        cx = start_x + pos_in_level * h_spacing + h_spacing // 2
        cy = y + level * v_spacing
        positions[i] = (cx, cy)

        canvas.draw_node(cx, cy, val, node_radius)

        # Draw edge to parent
        if i > 0:
            parent_idx = (i - 1) // 2
            if parent_idx in positions:
                px, py = positions[parent_idx]
                canvas.draw_line(px, py + node_radius, cx, cy - node_radius)


def draw_grid(canvas: DebugCanvas, board: list[list[int]],
              x: int = 50, y: int = 50, tile_size: int = 80,
              gap: int = 10) -> None:
    """Draw a 2D grid (e.g., 2048 board state).

    Args:
        canvas: DebugCanvas wrapper.
        board: 2D list of tile values (0 = empty). board[0][0] is top-left.
        x, y: Top-left corner of the grid.
        tile_size: Size of each tile in pixels.
        gap: Gap between tiles.
    """
    rows, cols = len(board), len(board[0])

    # Background
    total_w = cols * (tile_size + gap) + gap
    total_h = rows * (tile_size + gap) + gap
    canvas.draw_rect(x - gap, y - gap, total_w + gap, total_h + gap,
                     fill=COLORS["grid_bg"])

    for r in range(rows):
        for c in range(cols):
            tx = x + c * (tile_size + gap) + gap
            ty = y + r * (tile_size + gap) + gap
            val = board[r][c]

            bg = tile_color(val) if val != 0 else COLORS["grid_bg"]
            tc = text_color(val) if val != 0 else COLORS["text_dark"]
            text = str(val) if val != 0 else ""

            canvas.draw_rect(tx, ty, tile_size, tile_size,
                             fill=bg, text=text, text_c=tc)


def draw_bfs_step(canvas: DebugCanvas, graph: dict, current: Any,
                  visited: set, queue: list,
                  node_positions: dict) -> None:
    """Draw one step of a BFS traversal on a graph.

    Args:
        canvas: DebugCanvas wrapper (cleared before each step).
        graph: Adjacency list {node: [neighbors]}.
        current: Currently visiting node.
        visited: Set of visited nodes.
        queue: Current BFS queue.
        node_positions: Dict of {node: (x, y)} for layout.
    """
    canvas.clear()

    # Draw edges
    for node, neighbors in graph.items():
        if node not in node_positions:
            continue
        x1, y1 = node_positions[node]
        for nb in neighbors:
            if nb not in node_positions:
                continue
            x2, y2 = node_positions[nb]
            canvas.draw_line(x1, y1, x2, y2, color="#CCC")

    # Draw nodes
    for node, (nx, ny) in node_positions.items():
        if node == current:
            color = COLORS["node_highlight"]  # currently visiting
        elif node in visited:
            color = "#27AE60"  # visited
        elif node in queue:
            color = "#F39C12"  # in queue
        else:
            color = COLORS["node"]  # unvisited
        canvas.draw_node(nx, ny, str(node), color=color)


# ── Demo ────────────────────────────────────────────────────────────────

def demo():
    """Launch a demo window showing all visualization types."""
    root = tk.Tk()
    root.title("CodeHelper Visual Debugger — Demo")
    root.geometry("900x700")

    dc = DebugCanvas(tk.Canvas(root, bg=COLORS["bg"], width=900, height=700))
    dc.canvas.pack(fill=tk.BOTH, expand=True)

    # Linked list
    draw_linked_list(dc, [1, 2, 3, 4, 5], x=30, y=30,
                     highlight_idx=2, prev_pointers=True)
    dc.draw_text(30, 10, "Doubly Linked List (node 3 highlighted)", bold=True)

    # Binary tree
    draw_binary_tree(dc, values=[10, 5, 15, 3, 7, None, 20],
                     x=400, y=90, h_spacing=50, v_spacing=60, node_radius=18)
    dc.draw_text(400, 75, "Binary Search Tree", bold=True)

    # 2048 grid
    board_2048 = [
        [2, 0, 0, 2],
        [4, 0, 0, 4],
        [8, 16, 32, 64],
        [128, 256, 512, 1024],
    ]
    draw_grid(dc, board_2048, x=30, y=280, tile_size=70, gap=8)
    dc.draw_text(30 + 4 * 78 // 2, 270, "2048 Board State", bold=True)

    # BFS step
    graph = {"A": ["B", "C"], "B": ["A", "D", "E"], "C": ["A", "F"],
             "D": ["B"], "E": ["B", "F"], "F": ["C", "E"]}
    positions = {"A": (600, 350), "B": (500, 450), "C": (700, 450),
                 "D": (430, 530), "E": (530, 530), "F": (700, 530)}
    draw_bfs_step(dc, graph, "C", {"A", "B"}, ["C", "D", "E"],
                  positions)
    dc.draw_text(600, 320, "BFS Traversal (step 3)", bold=True)

    # Legend
    dc.draw_text(750, 670, "● Visited  ● Current  ● Queued  ○ Unvisited",
                 size=10)

    root.mainloop()


if __name__ == "__main__":
    demo()
