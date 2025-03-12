# Controller.py

import pygame
import math
from pygame.math import Vector2

# ------------------ Main Boat 控制相關參數 ------------------
SPEED_STEP = 0.5
MAX_SPEED = 2.0
SPEED_APPROACH_RATE = 0.1
TURN_ANGLE_STEP = 0.5

# ------------------ (STEP 1) 新增：隊形模式參數 ------------------
formation_mode = 0  # 0=無隊形、1=V字、2=一字、3=十字

# ------------------ 各種隊形 OFFSET ------------------
# 先把三種隊形的 offset 都準備好：V字、一字、十字
# 以下示範可自行調整距離與分佈
FORMATION_OFFSETS_V = [
    (0, 0),
    (-80,  50),
    (-80, -50),
    (-160,  100),
    (-160, -100),
]

FORMATION_OFFSETS_LINE = [
    (0, 0),
    (-80, 0),
    (-160, 0),
    (-240, 0),
    (-320, 0),
]

FORMATION_OFFSETS_CROSS = [
    (50, 0),
    (0, 0),   # 後方
    (0, -50),   # 上方
    (0, 50),   # 下方
    (-50,  0),   # 前方 (或你想讓它都在後方就自行調整)
]


def handle_event(boat, event):
    """監聽鍵盤事件，調整 main_boat 的 target_speed 或轉向，也監聽 0/1/2/3 切換隊形"""
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_w:
            boat.target_speed = min(boat.target_speed + SPEED_STEP, MAX_SPEED)
        elif event.key == pygame.K_s:
            boat.target_speed = max(boat.target_speed - SPEED_STEP, 0)
        elif event.key == pygame.K_d:
            boat.turning_right = True
        elif event.key == pygame.K_a:
            boat.turning_left = True

        # ------------------ (STEP 2) 新增 0/1/2/3 切換隊形 ------------------
        elif event.key == pygame.K_0:
            print("切換到 0 = 無隊形")
            global formation_mode
            formation_mode = 0
        elif event.key == pygame.K_1:
            print("切換到 1 = V 字隊形")
            formation_mode = 1
        elif event.key == pygame.K_2:
            print("切換到 2 = 一字隊形")
            formation_mode = 2
        elif event.key == pygame.K_3:
            print("切換到 3 = 十字隊形")
            formation_mode = 3

    elif event.type == pygame.KEYUP:
        if event.key == pygame.K_d:
            boat.turning_right = False
        elif event.key == pygame.K_a:
            boat.turning_left = False

def change_mode(mode):
    global formation_mode
    formation_mode = mode
    return


def update_mainboat(boat, grid_map):
    """每禎都呼叫，讓 main_boat 的 speed 慢慢追近 target_speed，並根據按鍵持續轉向"""
    speed_diff = boat.target_speed - boat.speed
    boat.speed += SPEED_APPROACH_RATE * speed_diff

    # 轉向邏輯
    if boat.turning_left:
        boat.angle += TURN_ANGLE_STEP
    if boat.turning_right:
        boat.angle -= TURN_ANGLE_STEP

    # 更新 velocity
    rad_angle = math.radians(-boat.angle)
    boat.velocity = Vector2(math.cos(rad_angle), math.sin(rad_angle)) * boat.speed
    boat.collide(grid_map)
    # 最後讓船前進
    boat.go_forward()

def update_formation(main_boat, other_boats, grid_map):
    global formation_mode

    # (STEP 3-1) 若 mode=0 => 其他船不移動，但 speed 一樣跟領頭船
    if formation_mode == 0:
        for b in other_boats:
            b.speed = main_boat.speed  # 雖然設定了 speed
            b.velocity = Vector2(0, 0) # 但實際上不前進
        return

    # (STEP 3-2) 判斷 mode=1/2/3 決定 offset
    if formation_mode == 1:
        offsets = FORMATION_OFFSETS_V
    elif formation_mode == 2:
        offsets = FORMATION_OFFSETS_LINE
    elif formation_mode == 3:
        offsets = FORMATION_OFFSETS_CROSS
    else:
        # 當作預設 V字
        offsets = FORMATION_OFFSETS_V

    # 取得主船位置與角度
    main_pos = main_boat.position
    main_angle_deg = main_boat.angle
    theta = math.radians(-main_angle_deg)

    for i, boat in enumerate(other_boats):
        idx = i + 1
        if idx >= len(offsets):
            idx = len(offsets) - 1
        local_offset = Vector2(offsets[idx])

        cosA = math.cos(theta)
        sinA = math.sin(theta)
        world_offset = Vector2(
            local_offset.x * cosA - local_offset.y * sinA,
            local_offset.x * sinA + local_offset.y * cosA
        )

        desired_pos = main_pos + world_offset

        # (STEP 3-3) 讓該船用 move_towards_formation(...) 去「緩慢」移動到 desired_pos
        boat.move_towards_formation(desired_pos, main_boat, formation_mode, grid_map)


