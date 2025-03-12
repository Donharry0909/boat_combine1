# other_object.py

"""
這個檔案存儲除了一般船隻外物件
包括敵人船隻，和障礙物gridmap
"""

import pygame
from pygame.math import Vector2
import config
import math

# --------------------------------------- 敵人船隻物件 ------------------------------------------------

class EnemyBoat:
    def __init__(self, image_path, position, boat_id):
        self.image = pygame.image.load(image_path).convert_alpha()
        self.image = pygame.transform.scale(self.image, (30, 30))  # 縮小船的大小
        self.original_image = self.image
        self.rect = self.image.get_rect(center=position)

        self.position = Vector2(position)
        self.velocity = Vector2(0, 0)
        self.speed = config.ENEMY_SPEED  # 領頭船速度

        self.collision_radius = config.ENEMY_RADIUS  # 圓形防撞泡泡
        self.around_radius = config.ENEMY_RADIUS * 5
        self.alg_radius = config.ENEMY_RADIUS * 10

        self.id = config.ENEMY_ID
        self.moving_up = False
        self.moving_down = False
        self.moving_left = False
        self.moving_right = False

    def handle_keydown(self, key):
        """當按下方向鍵時，開始移動"""
        if key == pygame.K_UP:
            self.moving_up = True
        elif key == pygame.K_DOWN:
            self.moving_down = True
        elif key == pygame.K_LEFT:
            self.moving_left = True
        elif key == pygame.K_RIGHT:
            self.moving_right = True

    def handle_keyup(self, key):
        """當放開方向鍵時，停止移動"""
        if key == pygame.K_UP:
            self.moving_up = False
        elif key == pygame.K_DOWN:
            self.moving_down = False
        elif key == pygame.K_LEFT:
            self.moving_left = False
        elif key == pygame.K_RIGHT:
            self.moving_right = False

    def update(self, grid_map):
        """
        持續更新敵船的位置，但在移動前先檢查「新位置是否會跟普通船重疊」。
        如果會重疊，就不允許移動。
        """
        dx, dy = 0, 0
        if self.moving_up:
            dy -= self.speed
        if self.moving_down:
            dy += self.speed
        if self.moving_left:
            dx -= self.speed
        if self.moving_right:
            dx += self.speed

        # 預計的新位置
        new_x = self.position.x + grid_map.grid_size + dx
        new_y = self.position.y + grid_map.grid_size + dy

        # 檢查新位置是否可以移動
        if self.can_move_to(new_x, new_y, grid_map):
            # 可以移動才更新位置
            self.position.x = self.position.x + dx
            self.position.y = self.position.y + dy
            self.rect.center = (int(self.position.x), int(self.position.y))
        else:
            # 不可移動 -> 保持原地 (dx=0,dy=0)
            pass

    def can_move_to(self, cx, cy, grid_map):
        """
        檢查 (cx, cy) 為中心時，擴大一格的防撞半徑所覆蓋的格子裏，
        是否有普通船隻 (grid != 0 且 != 自己的ID)。
        有 -> false (不能移動)
        無 -> true (可以移動)
        """
        # 保險起見 多1格
        expanded_radius = self.collision_radius + grid_map.grid_size

        # 找到grid範圍
        col_center, row_center = grid_map.get_grid_coords(cx, cy)
        
        # 大約估計能涵蓋 expanded_radius 的網格範圍
        grid_rad = int( math.ceil(expanded_radius / grid_map.grid_size ) )

        for col in range(col_center - grid_rad, col_center + grid_rad + 1):
            for row in range(row_center - grid_rad, row_center + grid_rad + 1):
                if not grid_map.is_valid_cell(col, row):
                    continue  # 在地圖外就無需檢查
                # 轉換成像素中心
                px, py = grid_map.get_pixel_coords(col, row)
                dist = math.hypot(px - cx, py - cy)
                if dist <= expanded_radius:
                    cell_value = grid_map.grid[col][row]
                    # 如果該格是普通船隻(  != 0  且  != self.id )，代表重疊，無法移動
                    if cell_value != 0 and cell_value != self.id:
                        return False
        # 全部都沒碰到船 -> 可以移動
        return True

    def draw(self, surface, font):
        """繪製敵船與圓形防撞泡泡"""
        surface.blit(self.image, self.rect)
        pygame.draw.circle(surface, (0, 255, 0), (int(self.position.x), int(self.position.y)), self.collision_radius, 2)
        # 畫「開始演算法」泡泡，顏色可自行調整（例如紅色），半徑為 collision_radius * 3
        pygame.draw.circle(surface, (255, 0, 0), (int(self.position.x), int(self.position.y)), self.alg_radius , 2)
        enemy_text = font.render(str("ENEMY"), True, (0, 0, 0))
        enemy_rect = enemy_text.get_rect(center=(self.position.x, self.position.y - 30))
        surface.blit(enemy_text,  enemy_rect)

# ------------------------------------ 障礙物GridMap(在二維方格陣標記哪些點是障礙物) --------------------------------------------------

class GridMap:
    def __init__(self, screen_width, screen_height, grid_size):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.grid_size = grid_size
        self.cols = screen_width // grid_size
        self.rows = screen_height // grid_size
        
        # 建立網格狀態 
        self.grid = [[0 for _ in range(self.rows)] for _ in range(self.cols)]            #0 -> 表示無障礙物，1表示有

    def get_grid_coords(self, x, y):
        """
        將像素座標 (x, y) 轉換為網格座標 (col, row)
        """
        col = x // self.grid_size
        row = y // self.grid_size
        return int(col), int(row)

    def get_pixel_coords(self, col, row):
        """
        將網格座標 (col, row) 轉換為像素中心點座標 (px, py)
        """
        px = col * self.grid_size + self.grid_size // 2
        py = row * self.grid_size + self.grid_size // 2
        return px, py

    def is_valid_cell(self, col, row):
        """
        檢查 (col, row) 是否在地圖範圍內
        """
        return 0 <= col < self.cols and 0 <= row < self.rows


    def set_cell_state(self, col, row, state):
        """
        設定特定網格的狀態 (例如標記為障礙物)
        """
        if self.is_valid_cell(col, row):
            self.grid[col][row] = state

    def get_cell_state(self, col, row):
        """
        取得特定網格的狀態
        """
        if self.is_valid_cell(col, row):
            return self.grid[col][row]
        return None, None  # 無效位置
    
    def reset_grid(self):
        """將整個網格重置為可行走 (0)"""
        self.grid = [[0 for _ in range(self.rows)] for _ in range(self.cols)]

    def mark_circle_as_obstacle(self, boat):
        """
        將以 (center_x, center_y) 為中心，半徑為 radius 的圓內的格子標記為障礙物
        """
        center_x = boat.position.x
        center_y = boat.position.y
        radius = boat.collision_radius
        radius += 10
        col_center, row_center = self.get_grid_coords(center_x, center_y)
        grid_radius = radius // self.grid_size  # 半徑轉換為格子單位

        for col in range(int(col_center - grid_radius), int(col_center + grid_radius) + 1):
            for row in range(int(row_center - grid_radius), int(row_center + grid_radius) + 1):
                if self.is_valid_cell(col, row):
                    px, py = self.get_pixel_coords(col, row)
                    distance = math.hypot(px - center_x, py - center_y)
                    if distance <= radius:
                        self.set_cell_state(col, row, boat.id)  # 設為障礙物

    def mark_ellipse_as_obstacle(self, boat):
        """
        假設 boat.position 是【橢圓的焦點】，而非中心。
        我們要先反推出【橢圓中心】、然後考慮 angle 旋轉，最後把符合範圍的網格標記成障礙物。
        """
        a = boat.semima  # 半長軸
        b = boat.semimi  # 半短軸
        angle_deg = boat.angle
        angle_rad = math.radians(angle_deg)  # 因為要做逆向旋轉，所以取負號

        # step 1: 從「焦點 (boat.position)」推算出「橢圓中心 center」
        # 你已經有 move_to_ellipse_focus() 來做「中心 -> 焦點」的運算，
        # 這邊我們要做反向，最簡單是自己計算 or 改寫一個「焦點 -> 中心」函式。
        # 如果直接用 move_to_ellipse_focus( focus=?, angle=?, ... )，要確定對應正確。
        # 
        # 幾何： c = sqrt(a^2 - b^2)
        # 若 boat.position 是【後焦點】，中心 = boat.position + (c, 0) (經旋轉)
        # 下方示範自己算：
        c = math.sqrt(a*a - b*b)
        # boat 是「後焦點」，則 "中心" 在焦點 + (c, 0) 方向（再依 boat.angle 旋轉）
        # 先做一個 Vector2(c, 0)
        offset = Vector2(c, 0)
        # 根據「船的 angle」旋轉 offset
        offset.rotate_ip(-boat.angle)  # 轉成對應 Pygame 座標 (要注意你 angle 定義)
        # 最後 center = 焦點 + offset
        center = boat.position + offset

        # step 2: 計算橢圓覆蓋到多少格範圍 (左右上下)
        col_center, row_center = self.get_grid_coords(center.x, center.y)
        col_range = int(a // self.grid_size) + 1
        row_range = int(a // self.grid_size) + 1  # 取 a (長軸) 即可，保證涵蓋整個橢圓

        for col in range(int(col_center - col_range), int(col_center + col_range) + 1):
            for row in range(int(row_center - row_range), int(row_center + row_range) + 1):
                if self.is_valid_cell(col, row):
                    px, py = self.get_pixel_coords(col, row)
                    
                    # step 3: 把 (px, py) 先轉到「以 center 為原點」的相對座標
                    dx = px - center.x
                    dy = py - center.y

                    # step 4: 再以 -angle 做逆向旋轉 (還原到未旋轉橢圓)
                    # x' = dx*cos(rad) - dy*sin(rad)
                    # y' = dx*sin(rad) + dy*cos(rad)
                    x_prime = dx * math.cos(angle_rad) - dy * math.sin(angle_rad)
                    y_prime = dx * math.sin(angle_rad) + dy * math.cos(angle_rad)

                    # step 5: 檢查是否落在標準橢圓方程式內
                    value = (x_prime**2) / (a*a) + (y_prime**2) / (b*b)
                    if value <= 1:
                        self.set_cell_state(col, row, boat.id)  # 設為障礙物

    def set_obstacles_from_boats(self, boats,  enemy_boat):
        """
        根據普通船隻 & 領導船的防撞泡泡，設定障礙物
        """
        self.reset_grid()  # 先清除所有障礙物

        # 設定領導船的圓形泡泡為障礙物
        # self.mark_circle_as_obstacle(enemy_boat)

        # 設定普通船的橢圓泡泡為障礙物
        for boat in boats:
            self.mark_ellipse_as_obstacle(boat)



