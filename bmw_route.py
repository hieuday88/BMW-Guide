"""Finds walking routes on a map's cost grid (gold paths are cheap, forest dearer, cliffs and paper nearly blocked)."""
import heapq
import math
import zlib
from pathlib import Path

GRID = 512
MAX_EXPANSIONS = 250_000
STEPS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
         (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]

_grids = {}


def load(map_dir, image):
    """Returns the cost grid for a map image, loading it once."""
    if image not in _grids:
        path = Path(map_dir) / image.replace('.png', '.cost')
        _grids[image] = zlib.decompress(path.read_bytes()) if path.exists() else None
    return _grids[image]


def _nearest_open(grid, cell):
    """Moves a start/goal off blocked cells onto the closest walkable one."""
    x, y = cell
    if grid[y * GRID + x] < 90:
        return cell
    for radius in range(1, 12):
        for dx in range(-radius, radius + 1):
            for dy in (-radius, radius):
                for cx, cy in ((x + dx, y + dy), (x + dy, y + dx)):
                    if 0 <= cx < GRID and 0 <= cy < GRID and grid[cy * GRID + cx] < 90:
                        return cx, cy
    return cell


def find(grid, start, goal):
    """A* over the grid; returns a list of cells from start to goal, or None when nothing was found in time."""
    start, goal = _nearest_open(grid, start), _nearest_open(grid, goal)
    gx, gy = goal
    best = {start: 0.0}
    came = {}
    heap = [(math.hypot(start[0] - gx, start[1] - gy), 0.0, start)]
    expanded = 0
    while heap and expanded < MAX_EXPANSIONS:
        _, cost, cell = heapq.heappop(heap)
        if cell == goal:
            path = [cell]
            while cell in came:
                cell = came[cell]
                path.append(cell)
            return path[::-1]
        if cost > best.get(cell, math.inf):
            continue
        expanded += 1
        x, y = cell
        for dx, dy, length in STEPS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < GRID and 0 <= ny < GRID):
                continue
            step = grid[ny * GRID + nx] * length
            new = cost + step
            nxt = (nx, ny)
            if new < best.get(nxt, math.inf):
                best[nxt] = new
                came[nxt] = cell
                heapq.heappush(heap, (new + math.hypot(nx - gx, ny - gy), new, nxt))
    return None


def simplify(path, every=3):
    """Keeps every n-th cell plus the end so the drawn route stays smooth and cheap to render."""
    if not path:
        return path
    return path[::every] + ([path[-1]] if (len(path) - 1) % every else [])


if __name__ == '__main__':
    import time
    here = Path(__file__).resolve().parent / 'assets' / 'maps'
    grid = load(here, '101.png')
    t = time.time()
    route = find(grid, (150, 300), (350, 200))
    print('cells', len(route) if route else None, 'in', round(time.time() - t, 2), 's')
    assert route and route[0] and route[-1]
