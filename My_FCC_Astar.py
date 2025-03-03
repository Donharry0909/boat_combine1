# My_FCC_Astar.py

"""
這個檔案含有路徑演算法
"""

import pygame
import sys
import math
import heapq
import random
import config

SCREEN_WIDTH = config.SCREEN_WIDTH
SCREEN_HEIGHT = config.SCREEN_HEIGHT
GRID_SIZE = config.GRID_SIZE
MAX_SPEED = config.MAX_SPEED

def get_blocked_cells():
    """
    回傳一個 set，裡面存了所有「不能通過」的格子 (col, row)。
    """
    blocked = set()
    # 總共有多少行、列
    cols = SCREEN_WIDTH // GRID_SIZE
    rows = SCREEN_HEIGHT // GRID_SIZE

    for c in range(cols):
        for r in range(rows):
            # 取得該格子的中心點 (像素座標)
            center_x = c * GRID_SIZE + GRID_SIZE // 2
            center_y = r * GRID_SIZE + GRID_SIZE // 2

            # 檢查是否離任一「敵方船隻中心」太近
            for enemy_pos in ENEMY_SHIPS_POS:
                dist = math.hypot(enemy_pos.x - center_x, enemy_pos.y - center_y)
                # 如果「距離敵方中心 < ENEMY_RADIUS + 額外安全距(可自己定義)」
                # 這裡示範「安全距 = 2格」，可自行調整
                # -> 將這個格子視為障礙。
                if dist < ENEMY_RADIUS + 2 * GRID_SIZE:
                    blocked.add((c, r))
                    break  # 不用再檢查其他敵方了

    return blocked

def draw_arrow(surface, color, center, angle, size=10):
    """
    center 為箭頭中心 (x, y)
    angle 為角度（0度向北，順時針增加）
    size 為箭頭長度
    """
    rad = math.radians(angle)
    tip = (center[0] + size * math.sin(rad),
           center[1] - size * math.cos(rad))
    side_angle = math.radians(150)
    left = (center[0] + (size * 0.5) * math.sin(rad + side_angle),
            center[1] - (size * 0.5) * math.cos(rad + side_angle))
    right = (center[0] + (size * 0.5) * math.sin(rad - side_angle),
             center[1] - (size * 0.5) * math.cos(rad - side_angle))
    pygame.draw.polygon(surface, color, [tip, left, right])

def smooth_heading(path_list, k=3):
    # path_list: [(px, py, t, heading), ...]
    new_path = []
    for i, (px, py, tt, hh) in enumerate(path_list):
        j = max(0, i - k)
        px0, py0, _, _ = path_list[j]
        dx = px - px0
        dy = py - py0
        if math.hypot(dx, dy) > 1e-6:
            new_h = math.degrees(math.atan2(dx, -dy)) % 360
        else:
            # 若沒位移，維持上一個 heading
            new_h = new_path[-1][3] if i > 0 else hh
        new_path.append((px, py, tt, new_h))
    return new_path


# My_FCC_Astar.py (新增 / 替換)
def a_star_search_time_heading(start_col, start_row, start_heading,
                               goal_col, goal_row, blocked):
    """
    回傳一條路徑(陣列):
    [(px1, py1, t1, heading1),
     (px2, py2, t2, heading2),
     ...
     (pxn, pyn, tn, headingn)]
    - 狀態 = (col, row, t, heading)
    - heading 先用 8 方向離散計算 (或你也可改成其他方式)
    """
    
    # 8方向 (dc, dr)
    directions = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1)
    ]
    
    # 啟發式 (斜方向距離)
    def heuristic(c1, r1, c2, r2):
        dx = abs(c1 - c2)
        dy = abs(r1 - r2)
        return (math.sqrt(2) - 1)*min(dx, dy) + max(dx, dy)
    
    # openHeap: (f_cost, (col, row, t, heading))
    start_state = (start_col, start_row, 0, start_heading)
    goal_xy = (goal_col, goal_row)
    
    g_cost = {start_state: 0}
    f_start = heuristic(start_col, start_row, goal_col, goal_row)
    openHeap = []
    heapq.heappush(openHeap, (f_start, start_state))
    parent = {}
    visited = set()

    while openHeap:
        current_f, current_state = heapq.heappop(openHeap)
        c, r, t, hdg = current_state
        
        # 是否到達目標 (col, row)
        if (c, r) == goal_xy:
            # 回溯得到完整路徑
            path_states = []
            node = current_state
            while node in parent:
                path_states.append(node)
                node = parent[node]
            path_states.append(start_state)
            path_states.reverse()
            
            # 將 (col, row, t, heading) 轉成 (px, py, t, heading)
            path_pixels = []
            for (cc, rr, tt, hh) in path_states:
                px = cc * GRID_SIZE + GRID_SIZE//2
                py = rr * GRID_SIZE + GRID_SIZE//2
                path_pixels.append((px, py, tt, hh))
            return path_pixels

        visited.add(current_state)
        
        # 擴展 8 方向
        for (dc, dr) in directions:
            nc, nr = c + dc, r + dr
            # 邊界判斷
            if not (0 <= nc < SCREEN_WIDTH//GRID_SIZE):
                continue
            if not (0 <= nr < SCREEN_HEIGHT//GRID_SIZE):
                continue
            if (nc, nr) in blocked:
                continue

            new_t = t + 1
            # 計算新的 heading：假設 0度=正北，順時針增加
            # => angle = atan2(dc, dr)
            # 假設 0度=正北，順時針增加
            new_h = math.degrees(math.atan2(dc, -dr)) % 360

            move_cost = math.sqrt(2) if dc != 0 and dr != 0 else 1
            new_g = g_cost[current_state] + move_cost
            
            neighbor_state = (nc, nr, new_t, new_h)
            
            if neighbor_state not in g_cost or new_g < g_cost[neighbor_state]:
                g_cost[neighbor_state] = new_g
                f_cost = new_g + heuristic(nc, nr, goal_col, goal_row)
                parent[neighbor_state] = current_state
                if neighbor_state not in visited:
                    heapq.heappush(openHeap, (f_cost, neighbor_state))
    
    return []  # 找不到路徑
