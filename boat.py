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

    def update2(self, boats, grid_map):
        """
        目前用於mode2演算法生效執行的函式
        """
        if not self.is_moving:
            return
        
        # 若路徑還沒走完
        if self.path_index < len(self.path):
            # 取得目前應該前往的中繼點資訊
            px, py, step_t, hdg = self.path[self.path_index]
            self.temp_destin = Vector2(px, py)

            # 更新橢圓大小
            self.semima = max(1, SEMI_MAJOR_AXIS * self.spadjust)
            self.semimi = max(0.5, SEMI_MINOR_AXIS * self.spadjust)

            # ----------- 基本朝目標(中繼點)前進的向量 -----------
            direction_to_target = self.temp_destin - self.position
            dist_to_target = direction_to_target.length()

            # 計算未來是否有船隻會相撞
            self.yield_st = will_collide_future(self, grid_map)

            # 如果會撞到，透過調整參數採取行動
            down_num = 0.015
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
            
            
        else:
            # 路徑走完了
            self.is_moving = False
            self.position = Vector2(self.destination)
            self.velocity = Vector2(0, 0)
            self.adjust_ellipse_size()
            self.path_index = 0
            self.semima = 1
            self.semimi = 0.5
            print(f"Boat {self.id} reached destination {self.destination}")

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



