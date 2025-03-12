# boat.py

"""
這個檔案含有船隻物件屬性，和內建方法
"""

import pygame
import math
from pygame.math import Vector2
from boat_algorithm import *
import config

SAFE_RADIUS = config.SAFE_RADIUS
ARRIVAL_TOLERANCE = config.ARRIVAL_TOLERANCE  # 到達目標的容忍範圍
SEMI_MAJOR_AXIS = config.SEMI_MAJOR_AXIS
SEMI_MINOR_AXIS = config.SEMI_MINOR_AXIS
MAX_CHANGE_ANGLE = config.MAX_CHANGE_ANGLE
MAX_CHANGE_SPEED = config.MAX_CHANGE_SPEED

# 定義顏色
WHITE = config.WHITE
DESTINATION_MARKER_COLOR = config.DESTINATION_MARKER_COLOR # 目的地標記為紅色
NUMBER_COLOR = config.NUMBER_COLOR  # 編號顏色為黑色
INTERVAL_NUM = config.INTERVAL_NUM

class Boat:
    def __init__(self, image_path, position, boat_id, max_speed):
        max_boat_size = (20, 20)
        self.original_image = load_and_scale_image(image_path, max_boat_size)
        self.image = self.original_image
        self.rect = self.image.get_rect(center=position)
        self.position = Vector2(position)
        self.angle = 0
        self.semima = 1     # 長軸長
        self.semimi = 0.5   # 短軸長

        # 目標與航行參數
        self.destination = None
        self.dest_dist = 0
        self.temp_destin = None
        self.base_speed = max_speed
        self.speed = self.base_speed
        self.velocity = Vector2(0, 0)
        self.is_moving = False
        self.target_speed = 0.0      # 目標速度(按W或S時會瞬間改變)

         # 轉向狀態
        self.turning_left = False
        self.turning_right = False
        
        # 船隻編號
        self.id = boat_id

        # 紀錄算好的路徑資訊
        self.path = []  # 用來儲存 A* 結果 [(x1,y1), (x2,y2), ...]
        self.path_index = 0  # 目前走到路徑的哪個中繼點(或終點)

        # 避讓參數
        self.collision_radius = SAFE_RADIUS  # SAFE_RADIUS
        self.yield_st = False #是否該禮讓
        self.spadjust = 1 #減速參數
        self.obst_dist = None #與距離

    def set_destination(self, dest):
        self.destination = Vector2(dest)
        print(f"Boat {self.id} destination set to {self.destination}")

    def set_semi(self):
        self.semima = SEMI_MAJOR_AXIS * self.spadjust
        self.semimi = SEMI_MINOR_AXIS * self.spadjust
    
    # 在 boat.py 裏 (最下方加上這個方法)

    def collide(self, grid_map):
        # 更新橢圓大小
        self.semima = max(1, SEMI_MAJOR_AXIS * self.spadjust)
        self.semimi = max(0.5, SEMI_MINOR_AXIS * self.spadjust)

         # 計算未來是否有船隻會相撞
        self.yield_st = will_collide_future(self, grid_map)

        # 如果會撞到，透過調整參數採取行動
        down_num = 0.1
        if self.yield_st:
            self.spadjust = max(0, self.spadjust - down_num)
        else:
            self.spadjust = min(1, self.spadjust + down_num)
        self.velocity = self.velocity  * self.spadjust
        return

    def move_towards_formation(self, desired_pos, main_boat, formation_mode, grid_map):
        """
        緩慢轉向 + 前進，貼近 desired_pos；若距離很遠，就比 main_boat 快一點。
        formation_mode: 傳進來的隊形模式(1,2,3)，可用來做不同動作
        """
        # 1) 計算我與目標位置的向量
        direction = desired_pos - self.position
        dist = direction.length()
        if dist < 1:
            # 如果已很接近(小於1像素)，就不用動了
            return

        # 2) 目標角度(以 "self.angle = -度數" 為基準)
        target_radians = math.atan2(direction.y, direction.x)
        target_degrees = math.degrees(target_radians)
        desired_angle = -target_degrees

        # 3) 與目前 self.angle 的差
        angle_diff = desired_angle - self.angle
        # 正規化到 [-180,180]
        angle_diff = (angle_diff + 180) % 360 - 180

        # 4) 最大每幀轉動角度
        MAX_TURN = 2.0
        if angle_diff > MAX_TURN:
            angle_diff = MAX_TURN
        elif angle_diff < -MAX_TURN:
            angle_diff = -MAX_TURN

        # 轉向
        self.angle += angle_diff

        # 5) 決定 speed：若跟主船距離遠，就用 (主船速度 + 一點額外補償)，
        #    但不得超過自身 base_speed。
        #    即使 main_boat.speed=0，也給自己0.5 追過去。
        main_speed = main_boat.speed
        # 額外補償
        extra = 0.2

        # 最簡單寫法：
        approach_speed = main_speed + extra
        # 若 main_boat.speed=0 => approach_speed = 0.5
        # 若 dist < 某個閾值(例如 20px) => 不需要再快
        if dist < 20:
            approach_speed = main_speed  # 如果已經很靠近，就跟主船同速
        # clip to base_speed
        if approach_speed > self.base_speed:
            approach_speed = self.base_speed

        self.speed = approach_speed

        # 6) 更新 velocity
        rad_angle = math.radians(-self.angle)
        self.velocity = Vector2(math.cos(rad_angle), math.sin(rad_angle)) * self.speed

        # 更新橢圓大小
        self.semima = max(1, SEMI_MAJOR_AXIS * self.spadjust)
        self.semimi = max(0.5, SEMI_MINOR_AXIS * self.spadjust)

         # 計算未來是否有船隻會相撞
        self.yield_st = will_collide_future(self, grid_map)

        # 如果會撞到，透過調整參數採取行動
        down_num = 0.1
        if self.yield_st:
            self.spadjust = max(0, self.spadjust - down_num)
        else:
            self.spadjust = min(1, self.spadjust + down_num)
        self.velocity = self.velocity  * self.spadjust
        # 7) 用 go_forward()
        self.go_forward()



    def go_forward(self):
        """
        目前用於mode1執行的函式
        """
        # 用velocity移動一步和決定船頭方向
        # 更新位置
        self.position += self.velocity

        # 更新船隻旋轉角度
        self.angle = -math.degrees(math.atan2(self.velocity.y, self.velocity.x))
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        self.rect = self.image.get_rect(center=self.rect.center)
        self.rect.center = (int(self.position.x), int(self.position.y))

    def mode1_sailing(self):
        # 只在有目的地時才計算方向，令船隻開始移動
        if self.destination:
            direction = self.destination - self.position
            distance = direction.length()
            self.dest_dist = distance + self.id * 0.001 # 更新初始位置與新目的地距離
            if distance > 0:
                self.speed = self.base_speed
                self.velocity = direction.normalize() * self.speed
                self.is_moving = True
                self.angle = -math.degrees(math.atan2(self.velocity.y, self.velocity.x))
                self.set_semi()
                # 讓船頭朝向前進方向
                angle = self.angle
                self.image = pygame.transform.rotate(self.original_image, angle)
                self.rect = self.image.get_rect(center=self.rect.center)

    def get_distance_to_destination(self):
        if self.destination:
            return (self.destination - self.position).length()
        return float('inf')
    def adjust_ellipse_size(self):
        """
        根據船隻當前速度動態調整橢圓的半長軸和半短軸。
        """
        speed_factor = self.velocity.length() / self.base_speed  # 速度比例 (0~1)
        self.semima = SEMI_MAJOR_AXIS * (1 + speed_factor * 0.1)  # 半長軸增長
        self.semimi = SEMI_MINOR_AXIS * (1 + speed_factor * 0.1)  # 半短軸增長
        self.collision_radius = self.semima
    
    def reset_ellipse_size(self):
        """
        根據船隻當前速度動態調整橢圓的半長軸和半短軸。
        """
        self.semima = SEMI_MAJOR_AXIS # 半長軸增長
        self.semimi = SEMI_MINOR_AXIS # 半短軸增長
        self.collision_radius = self.semima
    
    def boat_dock(self, dock_position):
        """
        停靠指定船隻在dock_position
        """
        if dock_position == None:
            print(f"Boat {self.id} : 停靠在None位置 {dock_position}")
            return
        if not isinstance(dock_position, (list, tuple, Vector2)) or len(dock_position) != 2:
            print(f"Boat {self.id} : 停靠在不合法位置 {dock_position}")
            return
        self.is_moving = False
        self.destination = None
        self.position = Vector2(dock_position)
        self.velocity = Vector2(0, 0)
        self.adjust_ellipse_size()
        self.path_index = 0
        self.semima = 1
        self.semimi = 0.5
        print(f"Boat {self.id} reached destination {dock_position}")
        return
    
    def filter_backpoints(self, boat_to_destin, target_to_destin):
        while boat_to_destin.length() < target_to_destin.length():
                self.path_index += INTERVAL_NUM
                if self.path_index >= len(self.path):
                    self.path_index = len(self.path) - 1
                    break
                px, py, step_t, hdg = self.path[self.path_index]
                self.temp_destin = Vector2(px, py)
                target_to_destin = self.destination - self.temp_destin
        return

    def update2(self, boats, grid_map):
        """
        目前用於mode2演算法生效執行的函式
        """
        if not self.is_moving:
            return
        # 若路徑還沒走完
        if self.path_index < len(self.path) and self.destination != None:
            # 取得目前應該前往的中繼點資訊
            px, py, step_t, hdg = self.path[self.path_index]
            self.temp_destin = Vector2(px, py)

            # 更新橢圓大小
            self.semima = max(1, SEMI_MAJOR_AXIS * self.spadjust)
            self.semimi = max(0.5, SEMI_MINOR_AXIS * self.spadjust)

            # ----------- 基本朝目標(中繼點)前進的向量 -----------
            boat_to_destin = self.destination - self.position
            target_to_destin = self.destination - self.temp_destin
            self.filter_backpoints(boat_to_destin, target_to_destin) # 過濾船隻後面的中繼點
            direction_to_target = self.temp_destin - self.position
            dist_to_target = direction_to_target.length()

            # 計算未來是否有船隻會相撞
            self.yield_st = will_collide_future(self, grid_map)

            # 如果會撞到，透過調整參數採取行動
            down_num = 0.007 * self.base_speed
            if self.yield_st:
                self.spadjust = max(0, self.spadjust - down_num)
            else:
                self.spadjust = min(1, self.spadjust + down_num)
            
            #檢查是否到達 temp_destin，如果已經很接近 temp_destin，換下一個點
            if self.path_index == len(self.path) - 1:
                if dist_to_target < ARRIVAL_TOLERANCE:
                    self.path_index += 1
                    return
            else:
                if dist_to_target < 1.5:  # 如果已經到了中繼點
                    self.path_index += INTERVAL_NUM  # 換下一個點
                    # 如果走完 path，代表到達最終目的地
                    if self.path_index >= len(self.path):  
                        self.path_index = len(self.path) - 1
                        # 計算前進方向
                    return

            if dist_to_target > 0:
                direction = direction_to_target.normalize()
                self.velocity = direction * self.speed * self.spadjust

            
            # 更新圖片forward
            self.go_forward()
            
            
        elif len(self.path) != 0 and self.path_index >= len(self.path):
            self.boat_dock(self.destination)
            # 路徑走完了
        else:
            self.go_forward()
    

    def draw_arrow(self, screen, color, position, angle, size):
        """
        畫一個更顯眼的箭頭，表示船的朝向
        """
        angle_rad = math.radians(angle)
        end_pos = (
            position[0] + size * math.cos(angle_rad),
            position[1] + size * math.sin(angle_rad),
        )

        # 畫黑色陰影
        pygame.draw.line(screen, (0, 0, 0), position, end_pos, 6)  # 黑色加粗
        pygame.draw.polygon(
            screen,
            (0, 0, 0),
            [
                (end_pos[0] + size * 0.4 * math.cos(angle_rad + math.pi * 0.75),
                end_pos[1] + size * 0.4 * math.sin(angle_rad + math.pi * 0.75)),
                (end_pos[0], end_pos[1]),
                (end_pos[0] + size * 0.4 * math.cos(angle_rad - math.pi * 0.75),
                end_pos[1] + size * 0.4 * math.sin(angle_rad - math.pi * 0.75))
            ]
        )  # 黑色陰影箭頭

        # 畫黃色箭頭（覆蓋黑色陰影）
        pygame.draw.line(screen, color, position, end_pos, 4)  # 黃色箭頭
        pygame.draw.polygon(
            screen,
            color,
            [
                (end_pos[0] + size * 0.3 * math.cos(angle_rad + math.pi * 0.75),
                end_pos[1] + size * 0.3 * math.sin(angle_rad + math.pi * 0.75)),
                (end_pos[0], end_pos[1]),
                (end_pos[0] + size * 0.3 * math.cos(angle_rad - math.pi * 0.75),
                end_pos[1] + size * 0.3 * math.sin(angle_rad - math.pi * 0.75))
            ]
        )  # 黃色箭頭



    def draw(self, surface, font):
        # 計算橢圓center位置
        center_position = move_to_ellipse_focus(
            focus=self.position,
            angle=self.angle,
            semi_major=self.semima,
            semi_minor=self.semimi,
        )
        self.rect = self.image.get_rect(center=(int(self.position.x), int(self.position.y)))

        # 如果有目的地，標記目的地
        if self.destination:
            pygame.draw.circle(surface, DESTINATION_MARKER_COLOR, (int(self.destination.x), int(self.destination.y)), 8)
            dest_text = font.render(str(self.id), True, DESTINATION_MARKER_COLOR)
            dest_rect = dest_text.get_rect(center=(self.destination.x, self.destination.y - 15))
            surface.blit(dest_text, dest_rect)

        # 繪製船隻圖片
        surface.blit(self.image, self.rect)

        # 使用黃色箭頭 + 黑色陰影，讓箭頭更清楚
        self.draw_arrow(surface, (255, 255, 0), self.position, -self.angle, size=25)

        # 繪製動態調整的橢圓(base on center_position)
        draw_rotated_ellipse(
            surface=surface,
            position=center_position,
            angle=self.angle,
            semi_major=self.semima,
            semi_minor=self.semimi,
            color=(0, 230, 230),  # 半透明藍色
            width=2
        )

        # 繪製船隻編號
        number_text = font.render(str(self.id), True, NUMBER_COLOR)
        number_rect = number_text.get_rect(center=(self.position.x, self.position.y - 30))
        surface.blit(number_text, number_rect)


    # def update(self, boats, enemy_positions):
    #     if not self.is_moving or not self.destination:
    #         return
    
    #     # ----------- 基本朝目標前進的向量 -----------
    #     direction_to_target = self.destination - self.position
    #     dist_to_target = direction_to_target.length()
    #     desired_dir = direction_to_target.normalize() if dist_to_target > 0 else Vector2(0, 0)
        
    #     # 動態調整橢圓大小
    #     self.adjust_ellipse_size()

    #     # 基本速度
    #     desired_speed = self.speed

    #     # 如果已經非常接近目標，就直接停止
    #     if dist_to_target < ARRIVAL_TOLERANCE:
    #         self.position = Vector2(self.destination)
    #         self.velocity = Vector2(0, 0)
    #         self.is_moving = False
    #         self.adjust_ellipse_size()
    #         print(f"Boat {self.id} reached destination {self.destination}")
    #         return

    #     # 若很接近目標，可適度減速，讓抵達時間較有機會跟其他船同步
    #     if dist_to_target < 100:
    #         desired_speed = (dist_to_target / 100.0) * self.speed

    #     # ----------- 計算避讓向量、禮讓比率-----------
    #     avoidance = calculate_avoidance_vector(self, boats, enemy_positions)
    #     yield_ratio = calculate_yield_ratio(self, boats)


    #     # 如果剛好在「同一直線且後面那艘船距離太近」，進一步減速
    #     major_ratio = calculate_major_ratio(self, boats)

    #     # ----------- 合併 -------------
    #     combined_dir = desired_dir
    #     if avoidance.length() > 0:
    #         combined_dir = (desired_dir * 1+ avoidance).normalize()

    #     # ----------- 如果一下子角度改變太多，限制角度 -------------
    #     angle = angle_between(combined_dir, self.velocity)
    #     adjust_v = self.velocity
    #     if angle > MAX_CHANGE_ANGLE:
    #         adjust_v = rotate_vector(self.velocity,MAX_CHANGE_ANGLE)
    #         combined_dir = adjust_v.normalize()
    #     elif angle < -MAX_CHANGE_ANGLE:
    #         adjust_v = rotate_vector(self.velocity,-MAX_CHANGE_ANGLE)
    #         combined_dir = adjust_v.normalize()
    #     # ----------- 如果一下子太快，限制加速 -------------
    #     velocity_pre = combined_dir * desired_speed * yield_ratio
    #     # 獲取當前速度和目標速度的長度
    #     current_speed = self.velocity.length()
    #     target_speed = velocity_pre.length()

    #     # 調整速度長度
    #     if current_speed * (1 + MAX_CHANGE_SPEED) < target_speed:
    #         self.velocity = velocity_pre.normalize() * (current_speed * (1 + MAX_CHANGE_SPEED))
    #     elif current_speed * (1 - MAX_CHANGE_SPEED) > target_speed:
    #         self.velocity = velocity_pre.normalize() * (current_speed * (1 - MAX_CHANGE_SPEED))
    #     else:
    #         self.velocity = velocity_pre
    #     # 更新位置
    #     self.position += self.velocity

    #     # 更新船隻旋轉角度
    #     self.angle = -math.degrees(math.atan2(self.velocity.y, self.velocity.x))
    #     self.image = pygame.transform.rotate(self.original_image, self.angle)
    #     self.rect = self.image.get_rect(center=self.rect.center)
    #     self.rect.center = (int(self.position.x), int(self.position.y))



