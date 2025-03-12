# main.py

import pygame
import sys
import math
import heapq
import random
from pygame.locals import *
from boat import *
from My_FCC_Astar import *
import config
from other_object import *
from ship_navigation_v1 import multi_ship_planning  # 多艘船規劃函式

# -----------------------------------【新加入】 import threading
import threading
import Controller

pygame.init()

# ------------------------------------ 參數設定 ----------------------------------------
SCREEN_WIDTH = config.SCREEN_WIDTH
SCREEN_HEIGHT = config.SCREEN_HEIGHT
GRID_SIZE = config.GRID_SIZE

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Boat Navigation System")

WHITE = config.WHITE
BUTTON_COLOR = config.BUTTON_COLOR
TEXT_COLOR = config.TEXT_COLOR
DESTINATION_MARKER_COLOR = config.DESTINATION_MARKER_COLOR
NUMBER_COLOR = config.NUMBER_COLOR

BUTTON_WIDTH = config.BUTTON_WIDTH
BUTTON_HEIGHT = config.BUTTON_HEIGHT
BUTTON_MARGIN = config.BUTTON_MARGIN

start_button_x = BUTTON_MARGIN
reset_button_x = SCREEN_WIDTH - BUTTON_WIDTH - BUTTON_MARGIN
start_button_rect = pygame.Rect(
    (start_button_x, SCREEN_HEIGHT - BUTTON_HEIGHT * 1.5), (BUTTON_WIDTH, BUTTON_HEIGHT)
)
reset_button_rect = pygame.Rect(
    (reset_button_x, SCREEN_HEIGHT - BUTTON_HEIGHT * 1.5), (BUTTON_WIDTH, BUTTON_HEIGHT)
)

font_size = 25
font = pygame.font.SysFont(None, font_size)

# 【新加入】 全域變數：背景計算狀態
planning_thread = None            # Thread物件 (或None)
planning_thread_busy = False      # 是否正在後臺計算
planning_results = None           # 暫存「背景計算完」的路徑規劃結果

# ------------------------------------ 船隻設定 (你原本的邏輯) ----------------------------------------
MAX_SPEED = config.MAX_SPEED
center = (SCREEN_WIDTH // 4, SCREEN_HEIGHT // 4)
radius = 100
num_boats = config.BOAT_NUM
boats = []
for i in range(num_boats):
    if i % 2 == 1:
        pos = (200 + (i // 2 + 1) * 70, 200 - (i // 2 + 1) * 70)
    else:
        pos = (200 - (i // 2) * 70, 200 - (i // 2) * 70)
    boat = Boat(f"picture/boat{i}.png", pos, i + 1, MAX_SPEED)
    boats.append(boat)

enemy_id = config.ENEMY_ID
enemy_boat = EnemyBoat(
    "picture/enemy_boat.png", (SCREEN_WIDTH // 3 * 1, SCREEN_HEIGHT // 3 * 2), enemy_id
)

grid_map = GridMap(SCREEN_WIDTH, SCREEN_HEIGHT, GRID_SIZE)

def load_and_scale_image(path, max_size):
    try:
        image = pygame.image.load(path).convert_alpha()
        image = pygame.transform.scale(image, max_size)
        return image
    except pygame.error as e:
        print(f"Cannot load image {path}: {e}")
        sys.exit()

background = load_and_scale_image("picture/sea.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
main_boat = boats[0]  # 假設第一艘船為主控
other_boats = boats[1:]


def draw_buttons(selecting_destination, current_boat, boats):
    pygame.draw.rect(screen, BUTTON_COLOR, start_button_rect)
    start_text = font.render("Start Sailing", True, TEXT_COLOR)
    text_rect = start_text.get_rect(center=start_button_rect.center)
    screen.blit(start_text, text_rect)

    pygame.draw.rect(screen, BUTTON_COLOR, reset_button_rect)
    reset_text = font.render("Reset", True, TEXT_COLOR)
    reset_rect = reset_text.get_rect(center=reset_button_rect.center)
    screen.blit(reset_text, reset_rect)

def draw_grid(screen, color=(240, 240, 240)):
    for x in range(0, SCREEN_WIDTH, GRID_SIZE):
        pygame.draw.line(screen, color, (x, 0), (x, SCREEN_HEIGHT))
    for y in range(0, SCREEN_HEIGHT, GRID_SIZE):
        pygame.draw.line(screen, color, (0, y), (SCREEN_WIDTH, y))

selecting_destination = False
reading_sailing = False
current_boat = 0
priority_queue = []
clock = pygame.time.Clock()
running = True
sailing = False
routing = False
mode = 0  # 0->初始, 1->駛向enemy, 2->進入勢力範圍
enemy_boat_position1 = None
f_enable = False
first_recal = True # 是否第一次叫出mode2_recal
finished = False

# -----------------------------------【新加入】定義「背景規劃函式」-----------------------------------

def background_multi_ship_planning(ships_info, smoothing_method="moving_average"):
    """
    此函式會在子執行緒中被呼叫：
    1. 執行多船路徑規劃 (multi_ship_planning)
    2. 計算完畢後，將結果儲存在全域變數 planning_results
    """
    global planning_results, planning_thread_busy, first_recal
    try:
        # 呼叫你在 ship_navigation_v1.py 中的多船規劃函式
        result = multi_ship_planning(ships_info, smoothing_method=smoothing_method)
        planning_results = result
    except Exception as e:
        print("[背景規劃錯誤]", e)
        planning_results = None
    finally:
        # 結束後，把 busy 旗標關閉
        planning_thread_busy = False
        first_recal = False
        print("[Background] multi_ship_planning 完成計算")

# -----------------------------------【新加入】在 mode2_recal 中：用執行緒做計算-----------------------------------

def mode2_recal():
    global planning_thread, planning_thread_busy, planning_results, first_recal

    # 如果還在算，就不要重複呼叫
    if planning_thread_busy:
        print("[mode2_recal] 仍在背景計算中，跳過本次呼叫")
        return
    

    # 這裡計算每艘船的新目標 (圍繞 enemy_boat.position)
    target_circle_radius = enemy_boat.around_radius
    N = len(boats)
    for idx, boat in enumerate(boats):
        theta = (2 * math.pi / N) * idx
        new_goal = enemy_boat.position + Vector2(
            target_circle_radius * math.cos(theta),
            target_circle_radius * math.sin(theta),
        )
        boat.destination = new_goal
        print(f"Boat {boat.id} 新目標: {new_goal}")

    # 整理 ships_info (公尺座標)
    convert_size = 25
    ships_info = []
    for boat in boats:
        if boat.destination is None:
            continue
        position = boat.position
        if first_recal:
            position = boat.position + boat.velocity * 50
        x_m  = position.x / convert_size
        y_m  = position.y / convert_size
        gx_m = boat.destination.x / convert_size
        gy_m = boat.destination.y / convert_size
        ships_info.append({"id": str(boat.id), "pos": (x_m, y_m), "goal": (gx_m, gy_m)})
    # 用 Thread 在背景計算
    planning_thread_busy = True
    planning_results = None  # 清空舊結果
    def do_planning():
        background_multi_ship_planning(ships_info, "moving_average")

    planning_thread = threading.Thread(target=do_planning)
    planning_thread.start()
    print("[mode2_recal] 已啟動背景執行緒，開始算 multi_ship_planning...")

# -----------------------------------【新加入】一個小函式：套用規劃結果到船隻-----------------------------------

def apply_planning_results_to_boats():
    """
    在主迴圈中若發現 planning_results 已經完成，
    就呼叫這個函式把路徑套用到 boats
    """
    global planning_results
    if planning_results is None:
        return  # 還沒計算好或沒有結果

    convert_size = 25
    for boat in boats:
        bid = str(boat.id)
        if bid in planning_results:
            path_data = planning_results[bid]
            path_meters = path_data["path"]
            headings = path_data.get("headings", [])

            # 組合你的 path 格式 (x, y, t, heading) (以像素為單位)
            new_path = []
            for i, (px_m, py_m) in enumerate(path_meters):
                hdg = headings[i] if i < len(headings) else 0
                px_cm = px_m * convert_size
                py_cm = py_m * convert_size
                new_path.append((px_cm, py_cm, 0, hdg))

            boat.path = new_path
            if boat.path:
                # 讓船移動
                boat.is_moving = True
                boat.path_index = 1

    # 套用完把結果清空，避免重複套用
    planning_results = None
    print("[Main] 已把背景計算結果更新到所有船隻。")

# ----------------------------------- 主要遊戲迴圈 -----------------------------------

while running:
    clock.tick(50)
    sailing_counts = sum(1 for b in boats if b.is_moving)
    sailing = sailing_counts > 0

    # 更新障礙物
    grid_map.set_obstacles_from_boats(boats, enemy_boat)

    for event in pygame.event.get():
        if event.type == QUIT:
            running = False
            break
        # # 傳遞鍵盤事件給 Controller 處理
        # if mode == 0:
        #     Controller.handle_event(main_boat, event)
        if event.type == KEYDOWN:
            if event.key in [K_UP, K_DOWN, K_LEFT, K_RIGHT]:
                enemy_boat.handle_keydown(event.key)
            elif event.key == K_f:
                if not f_enable:
                    f_enable = True
                    print("開始航行 mode=1")
                    for boat in boats:
                        boat.destination = enemy_boat.position
                        boat.speed = boat.base_speed
                        boat.velocity = Vector2(math.cos(boat.angle), math.sin(boat.angle)) * boat.speed
                        boat.mode1_sailing()
                    main_boat = boats[0]
                    for boat in boats:
                        if boat.dest_dist < main_boat.dest_dist:
                            main_boat = boat
                    for boat in boats:
                        if boat != main_boat:
                            boat.velocity = main_boat.velocity
                    mode = 1
                else:
                    f_enable = False
                    planning_results = None
                    for boat in boats:
                        boat.boat_dock(boat.position)
                    mode = 0
                    # Controller.change_mode(0)
            elif event.key == K_r:
                print("重置所有船隻")
                boats = []
                for i in range(num_boats):
                    angle = (2 * math.pi / num_boats) * i
                    if i == 0:
                        angle += math.radians(20)
                    pos = (
                        center[0] + radius * math.cos(angle),
                        center[1] + radius * math.sin(angle),
                    )
                    boat = Boat(f"picture/boat{i}.png", pos, i + 1, MAX_SPEED)
                    boats.append(boat)
                print("所有船隻已重置")

        elif event.type == KEYUP:
            if event.key in [K_UP, K_DOWN, K_LEFT, K_RIGHT]:
                enemy_boat.handle_keyup(event.key)

    # ------------------ 模式切換及邏輯 ------------------
    if mode == 0:
        pass  # 尚未啟動

    elif mode == 1:
        # 領頭船
        main_boat.mode1_sailing()
        # 所有船與領頭船方向保持一致
        for boat in boats:
            boat.velocity = main_boat.velocity
            boat.go_forward()
        
        first_recal = True
        dist_to_enemy = (main_boat.position - enemy_boat.position).length()
        if dist_to_enemy < enemy_boat.alg_radius:
            print("Main boat 進入 enemy的大泡泡, 切到 mode=2")
            enemy_boat_position1 = enemy_boat.position.copy()
            mode2_recal()  # **這裡呼叫改成開執行緒做計算**
            mode = 2

    elif mode == 2:
        # 如果敵船移動超過一定距離，就重算
        if (enemy_boat.position - enemy_boat_position1).length() > enemy_boat.speed * 3:
            print("敵船移動超過閾值，重新算")
            enemy_boat_position1 = enemy_boat.position.copy()
            mode2_recal()  # 再次呼叫執行緒

        # 讓每艘船走自己的 path
        if not first_recal:
            for boat in boats:
                boat.update2(boats, grid_map)
        else:
            for boat in boats:
                boat.go_forward()
        
    not_moving_num = 0
    for boat in boats:
        if not boat.is_moving:
            not_moving_num += 1
    if not_moving_num == 5:
        finished = False
    else:
        finised = True

        # 如果都到目標了，可切回 mode=0 (或做其他事)
        # if not_moving_num == num_boats:
        #     mode = 0

    # 【新加入】檢查背景計算結果並套用
    apply_planning_results_to_boats()

    # if mode == 0:
    #     # 1) 更新主船
    #     Controller.update_mainboat(main_boat, grid_map)
    #     # 2) 其他船跟隨隊形
    #     Controller.update_formation(main_boat, other_boats, grid_map)

    # ---------------------------------------- 繪製畫面 ------------------------------------------
    screen.blit(background, (0, 0))

    # 繪製路徑(當 mode==2 時, 你想畫箭頭或其他)
    if mode == 2 and not first_recal:
        for boat in boats:
            if boat.is_moving:
                for px, py, step_t, hdg in boat.path:
                    draw_arrow(screen, (255, 0, 0), (px, py), -hdg, size=8)

    draw_grid(screen)

    for b in boats:
        b.draw(screen, font)

    # 繪製障礙物網格
    for col in range(grid_map.cols):
        for row in range(grid_map.rows):
            if grid_map.grid[col][row] != 0 and grid_map.grid[col][row] != enemy_boat.id:
                px, py = grid_map.get_pixel_coords(col, row)
                pygame.draw.circle(screen, (255, 165, 0), (px, py), 2)

    enemy_boat.update(grid_map)
    enemy_boat.draw(screen, font)

    # if not sailing:
    #     draw_buttons(selecting_destination, current_boat, boats)

    pygame.display.flip()

pygame.quit()
sys.exit()
