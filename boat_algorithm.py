# boat_algorithm.py

"""
這個檔案含有適用於船隻的演算法，皆是從boat.py呼叫
包括調整圖片、橢圓、角度，以及計算障礙物距離
"""

import pygame
import random
import math
import config
from pygame.math import Vector2

# 定義常數
ENEMY_RADIUS = 60   # 敵船(或禁入區域)的影響半徑
ARRIVAL_TOLERANCE = 5.0  # 到達目標的容忍範圍
RATIO = 1.6

def move_to_ellipse_focus(focus, angle, semi_major, semi_minor):
    """
    計算橢圓的焦點位置

    Args:
        center: 橢圓的中心 (Vector2)。
        angle: 橢圓的旋轉角度（以度數為單位）。
        semi_major: 橢圓的半長軸。
        semi_minor: 橢圓的半短軸。
        focus_type: 焦點類型 ("front" 或 "rear")，預設為 "rear"。

    Returns:
        焦點位置 (Vector2)。
    """
    # 計算焦距 c
    c = math.sqrt(semi_major**2 - semi_minor**2)

    # 根據焦點類型決定偏移方向
    offset = Vector2(-c, 0)

    # 根據橢圓的旋轉角度旋轉偏移
    offset.rotate_ip(-angle)

    # 計算焦點的絕對位置
    center = focus - offset
    return center

def load_and_scale_image(path, max_size):
    """
     調整圖片大小
    """
    try:
        image = pygame.image.load(path).convert_alpha()
        image = pygame.transform.scale(image, max_size)
        return image
    except pygame.error as e:
        print(f"Cannot load image {path}: {e}")
        sys.exit()

def draw_rotated_ellipse(surface, position, angle, semi_major, semi_minor, color, width=1):
    """
    根據船隻的前進方向，繪製旋轉橢圓
    
    Args:
        surface: Pygame 主畫布。
        position: 橢圓中心 (x, y)。
        angle: 橢圓旋轉角度（以度數為單位，順時針方向）。
        semi_major: 橢圓的半長軸。
        semi_minor: 橢圓的半短軸。
        color: 橢圓的顏色（RGB 或 RGBA）。
        width: 線條寬度（默認為 1，填滿可設為 0）。
    """
    # 建立一個透明的 Surface 來繪製橢圓
    ellipse_width = int(semi_major * 2)
    ellipse_height = int(semi_minor * 2)
    ellipse_surface = pygame.Surface((ellipse_width, ellipse_height), pygame.SRCALPHA)

    # 在新 Surface 上畫橢圓
    pygame.draw.ellipse(
        ellipse_surface,
        color,
        (0, 0, ellipse_width, ellipse_height),
        width
    )

    # 將橢圓旋轉
    rotated_surface = pygame.transform.rotate(ellipse_surface, angle)
    rotated_rect = rotated_surface.get_rect(center=(int(position.x), int(position.y)))

    # 將旋轉後的橢圓貼到主畫布上
    surface.blit(rotated_surface, rotated_rect)

def get_obsta(f1, f2, grid_map, id):
    """
    沿著 f1 -> f2 的直線，檢查路徑上格子是否有障礙物
    """
    delta = f2 - f1
    total_dist = delta.length()
    if total_dist == 0:
        return None
    
    steps = int(total_dist / grid_map.grid_size) + 1
    step_vec = delta / steps  # 每一步要移動的向量
    
    current = f1.copy()
    for i in range(steps + 1):
        col, row = grid_map.get_grid_coords(current.x, current.y)
        grid_st = grid_map.get_cell_state(col, row)
        if not grid_map.is_valid_cell(col, row):
            return None  # 出界
        if grid_st != 0 and grid_st != config.ENEMY_ID and grid_st != id:  # 0=可走, 非0=障礙
            return current
        
        current += step_vec
    
    return None  # 代表整條線可通行，未碰到障礙


# 如果前方指定距離沒障礙物回傳零，否則回傳距離
def will_collide_future(boat, grid_map):
    """
    預測未來是否會碰撞：

    return值:
    若前方有障礙物，回傳最近的障礙物距離
    若前方沒東西，回傳0
    """
    v = boat.velocity.normalize() if boat.velocity.length() > 0 else Vector2(0, 0)
    # 預測未來的位置
    future_1 = boat.position + v * boat.semima * 1
    future_2 = boat.position + v * boat.semima * 2.5
    obsta = get_obsta(future_1, future_2, grid_map, boat.id) # 取得最近的障礙物座標
    if obsta is None:
        return 0
    return (boat.position - obsta).length()



def rotate_vector(vector, angle_degrees):
    """
    將向量順時針旋轉指定角度。

    Args:
        vector : 原始向量 (pygame.math.Vector2)
        angle_degrees (float): 順時針旋轉的角度（以度數為單位）。

    Returns:
       旋轉後的新向量 (pygame.math.Vector2)
    """
    # 將角度轉換為弧度
    angle_radians = math.radians(angle_degrees)

    # 計算旋轉後的新分量
    new_x = vector.x * math.cos(angle_radians) + vector.y * math.sin(angle_radians)
    new_y = -vector.x * math.sin(angle_radians) + vector.y * math.cos(angle_radians)

    return pygame.math.Vector2(new_x, new_y)

def angle_between(v1, v2):
    """
    計算兩個向量的夾角(能區分順時針、逆時針)
    """
    # 確保兩個向量都被正規化
    v1 = v1.normalize()
    v2 = v2.normalize()

    # 計算點積與叉積
    dot = v1.dot(v2)  # 點積
    cross = v1.x * v2.y - v1.y * v2.x  # 叉積（z 分量）

    # 計算角度（弧度），並轉換為度數
    angle = math.degrees(math.atan2(cross, dot))  # atan2 自帶符號處理
    return angle

"""
 之前用數學方法計算是否進入其他船隻橢圓半徑，現在改用根據前方是否有障礙格子判斷
"""
# def ellipse_intersects_line(p1, p2, a, b):
#     """
#     判斷線段 (p1, p2) 是否與標準橢圓 (0,0, a, b) 相交。
#     假設橢圓中心在 (0,0)，a 為長軸，b 為短軸。

#     :param p1: Vector2, 旋轉後的線段起點
#     :param p2: Vector2, 旋轉後的線段終點
#     :param a: float, 橢圓的半長軸
#     :param b: float, 橢圓的半短軸
#     :return: bool, 若線段與橢圓相交則回傳 True，否則 False
#     """

#     # 線段方程式：P(t) = p1 + t (p2 - p1)
#     dx = p2.x - p1.x
#     dy = p2.y - p1.y

#     # 橢圓方程式： (x/a)^2 + (y/b)^2 = 1
#     A = (dx**2) / (a**2) + (dy**2) / (b**2)
#     B = 2 * ((p1.x * dx) / (a**2) + (p1.y * dy) / (b**2))
#     C = (p1.x**2) / (a**2) + (p1.y**2) / (b**2) - 1

#     # 解二次方程式 At^2 + Bt + C = 0
#     discriminant = B**2 - 4*A*C

#     if discriminant < 0:
#         return False  # 無解，表示線段未與橢圓相交

#     # 計算兩個交點的 t 值
#     t1 = (-B - math.sqrt(discriminant)) / (2 * A)
#     t2 = (-B + math.sqrt(discriminant)) / (2 * A)

#     # 如果交點在 0 <= t <= 1 之間，表示線段與橢圓相交
#     return (0 <= t1 <= 1) or (0 <= t2 <= 1)

# def line_intersects_ellipse(p1, p2, boat):
#     """
#     判斷線段 (p1, p2) 是否與船隻的橢圓防撞泡泡相交。
    
#     :param p1: Vector2, 線段的起點
#     :param p2: Vector2, 線段的終點
#     :param boat: Boat, 船隻物件 (包含 position, semima, semimi, angle)
#     :return: bool, 若線段與橢圓相交則回傳 True，否則 False
#     """

#     # 取得橢圓參數
#     focus = boat.position  # 橢圓焦點 (即船的位置)
#     semi_major = boat.semima  # 半長軸
#     semi_minor = boat.semimi  # 半短軸
#     angle = math.radians(boat.angle)  # 角度轉弧度

#     # 讓兩端點轉換到「以船焦點為原點」的坐標系
#     translated_p1 = p1 - focus
#     translated_p2 = p2 - focus

#     # 旋轉兩個點到「未旋轉的橢圓座標系」
#     def rotate_point(point, angle):
#         """ 旋轉點，使其回到未旋轉的橢圓座標系 """
#         x_prime = point.x * math.cos(angle) + point.y * math.sin(angle)
#         y_prime = -point.x * math.sin(angle) + point.y * math.cos(angle)
#         return Vector2(x_prime, y_prime)

#     p1_prime = rotate_point(translated_p1, angle)
#     p2_prime = rotate_point(translated_p2, angle)

#     # 檢查是否有交點
#     return ellipse_intersects_line(p1_prime, p2_prime, semi_major, semi_minor)


"""
以下是之前用「場」的方向進行避讓計算，但是太麻煩很容易出錯
"""
# def calculate_avoidance_vector(boat, boats, enemy_positions):
#     """
#     計算避讓向量，包括與其他船隻和敵方船隻的避讓。
#     """
#     avoidance = Vector2(0, 0)
    
#     # 與其他船隻的防撞避讓
#     for other in boats:
#         if other is boat:
#             continue
#         diff = boat.position - other.position
#         dist = diff.length()
#         if dist < (boat.collision_radius * RATIO + other.collision_radius * RATIO):
#             if dist > 0:
#                 overlap_ratio = 1.0 - dist / (boat.collision_radius * RATIO + other.collision_radius * RATIO)
#                 avoidance += diff.normalize() * overlap_ratio * 2.0

#     # 與敵方船隻或禁入區域的避讓
#     for enemy_pos in enemy_positions:
#         diff_enemy = boat.position - enemy_pos
#         dist_enemy = diff_enemy.length()
#         if dist_enemy < (ENEMY_RADIUS * RATIO + boat.collision_radius * RATIO):
#             if dist_enemy > 0:
#                 overlap_ratio = 1.0 - dist_enemy / (ENEMY_RADIUS * RATIO + boat.collision_radius * RATIO)
#                 avoidance += diff_enemy.normalize() * overlap_ratio * 3.0

#     return avoidance

# def calculate_yield_decision(boat, other, tolerance=10.0):
#     """
#     判斷 boat 是否要禮讓 other。 
#     """
#     if not boat.destination or not other.destination:
#         return False

#     boat_dist = (boat.position - boat.destination).length()
#     other_dist = (other.position - other.destination).length()

#     return boat_dist < other_dist

# def calculate_major_ratio(boat, others):
#     major_ratio = 1
#     for other in others:
#             if other is boat:
#                 continue
#             distance_to_other = (other.position - boat.position).length()
#             if distance_to_other < boat.semima * 2.3:
#                 # 判斷速度方向差
#                 if other.velocity.length() == 0:
#                     dot_v = 0
#                 else:
#                     dot_v = boat.velocity.normalize().dot(other.velocity.normalize())
#                 angle_diff = math.degrees(math.acos(dot_v)) if abs(dot_v) <= 1.0 else 180
#                 if angle_diff < 15:
#                     # 表示雙方大致上同方向，距離又很近 => 後面船應該減速
#                     # 先判斷誰在後面（判斷同方向時，diff 與 velocity 的投影）
#                     relative_pos = (other.position - boat.position).dot(boat.velocity.normalize())
#                     if relative_pos > 0:
#                         # other 在前面，self 在後面 => self 減速
#                         major_ratio *= 0.2
#                     else:
#                         # self 在前面，other 在後面 => 這裡自己不動作
#                         pass
#     return major_ratio

# def calculate_yield_ratio(boat, others):
#     yield_ratio = 1
#     for other in others:
#             if other is boat:
#                 continue
#             distance_to_other = (other.position - boat.position).length()
#             if distance_to_other < boat.semima  * 4:
#                 # 調用我們在 algorithm.py 中定義的禮讓函式
#                 should_yield = calculate_yield_decision(boat, other)
#                 if should_yield:
#                     # 若要禮讓，則把 desired_speed 再縮小一些
#                     yield_ratio *= 0.7
#                 else:
#                     # 不禮讓時，視需求可維持或微調加快
#                     yield_ratio *= 1.2
#     return yield_ratio
