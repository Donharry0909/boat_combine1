# main.py

"""
這個檔案含有主程式的運行
以決定程式進行流程
"""

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

# 初始化 Pygame
pygame.init()


# ------------------------------------ 參數設定 ----------------------------------------


# 設定螢幕尺寸
SCREEN_WIDTH = config.SCREEN_WIDTH
SCREEN_HEIGHT = config.SCREEN_HEIGHT
GRID_SIZE = config.GRID_SIZE
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Boat Navigation System")

# 顏色設定
WHITE = config.WHITE
BUTTON_COLOR = config.BUTTON_COLOR
TEXT_COLOR = config.TEXT_COLOR
DESTINATION_MARKER_COLOR = config.DESTINATION_MARKER_COLOR
NUMBER_COLOR = config.NUMBER_COLOR

# 按鈕設定
BUTTON_WIDTH = config.BUTTON_WIDTH
BUTTON_HEIGHT = config.BUTTON_HEIGHT
BUTTON_MARGIN = config.BUTTON_MARGIN
# 計算按鈕位置
start_button_x = BUTTON_MARGIN
reset_button_x = SCREEN_WIDTH - BUTTON_WIDTH - BUTTON_MARGIN
start_button_rect = pygame.Rect(
    (start_button_x, SCREEN_HEIGHT - BUTTON_HEIGHT * 1.5),
    (BUTTON_WIDTH, BUTTON_HEIGHT)
)
reset_button_rect = pygame.Rect(
    (reset_button_x, SCREEN_HEIGHT - BUTTON_HEIGHT * 1.5),
    (BUTTON_WIDTH, BUTTON_HEIGHT)
)
# 按鈕字體
font_size = 25
font = pygame.font.SysFont(None, font_size)


# ------------------------------------ 船隻設定 ----------------------------------------


center = (SCREEN_WIDTH // 4, SCREEN_HEIGHT // 4)  # 圓心位於左上角附近
radius = 100  # 排列半徑，可自行調整
num_boats = config.BOAT_NUM
boats = []
for i in range(num_boats):
    # 角度分布均勻，但讓 1 號船(索引0)偏右一些，可以額外調整其角度
    if i % 2 == 1:
        pos = (200 + (i // 2 + 1) * 70, 200 - (i // 2 + 1) * 70)
    else:
        pos = (200 - (i // 2) * 70, 200 - (i // 2) * 70)
    boat = Boat(f"picture/boat{i}.png", pos, i + 1, MAX_SPEED)
    boats.append(boat)

# 創建領頭船
enemy_id = config.ENEMY_ID
enemy_boat = EnemyBoat("picture/enemy_boat.png", (SCREEN_WIDTH // 3 * 1, SCREEN_HEIGHT // 3 * 2), enemy_id)
grid_map = GridMap(SCREEN_WIDTH, SCREEN_HEIGHT, GRID_SIZE)


# ------------------------------------ 函數設定 ----------------------------------------


# 讀取背景圖片
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
background = load_and_scale_image("picture/sea.png", (SCREEN_WIDTH, SCREEN_HEIGHT))

def snap_to_grid(pos):
    """
    將一個點吸附到最近的網格中心
    支援元組和vector2輸出  
    """
    x, y = pos
    grid_x = (x // GRID_SIZE) * GRID_SIZE + GRID_SIZE // 2
    grid_y = (y // GRID_SIZE) * GRID_SIZE + GRID_SIZE // 2

    # 如果輸入是 Vector2，回傳 Vector2，否則回傳 tuple
    return pygame.math.Vector2(grid_x, grid_y) if isinstance(pos, pygame.math.Vector2) else (grid_x, grid_y)

def get_random_grid_center():
    """隨機選擇一個網格中心作為初始位置"""
    cols = SCREEN_WIDTH // GRID_SIZE
    rows = SCREEN_HEIGHT // GRID_SIZE
    col = random.randint(0, cols - 1)
    row = random.randint(0, rows - 1)
    x = col * GRID_SIZE + GRID_SIZE // 2
    y = row * GRID_SIZE + GRID_SIZE // 2
    return (x, y)

def draw_buttons(selecting_destination, current_boat, boats):
    # 畫 [Start Sailing] 按鈕
    pygame.draw.rect(screen, BUTTON_COLOR, start_button_rect)
    start_text = font.render("Start Sailing", True, TEXT_COLOR)
    text_rect = start_text.get_rect(center=start_button_rect.center)
    screen.blit(start_text, text_rect)

    # 畫 [Reset] 按鈕
    pygame.draw.rect(screen, BUTTON_COLOR, reset_button_rect)
    reset_text = font.render("Reset", True, TEXT_COLOR)
    reset_rect = reset_text.get_rect(center=reset_button_rect.center)
    screen.blit(reset_text, reset_rect)

def draw_grid(screen, color=(240, 240, 240)):
    """畫出整個地圖的網格"""
    for x in range(0, SCREEN_WIDTH, GRID_SIZE):
        pygame.draw.line(screen, color, (x, 0), (x, SCREEN_HEIGHT))  # 畫垂直線
    for y in range(0, SCREEN_HEIGHT, GRID_SIZE):
        pygame.draw.line(screen, color, (0, y), (SCREEN_WIDTH, y))  # 畫水平線

# ------------------------------------ 流程參數設定 ----------------------------------------

# 選擇目的地的狀態
selecting_destination = False
reading_sailing = False
current_boat = 0

# 優先隊列
priority_queue = []

clock = pygame.time.Clock()
running = True
sailing = False
routing = False
main_boat = None
mode = 0 # 0 -> 初始  1 -> 駛向enemy船  2 -> 進入enemyr船隻勢力裡面
enemy_boat_position1 = None

"""
進入流程主循環
"""

while running:
    clock.tick(50)
    # 檢查是否sailing
    sailing_counts = sum(1 for b in boats if b.is_moving)
    sailing = sailing_counts > 0

    #設定障礙物
    grid_map.set_obstacles_from_boats(boats, enemy_boat)


# ---------------------------- 事件判斷(鍵盤按鍵、滑鼠點擊按鈕) ------------------------------


    for event in pygame.event.get():
        # 關閉視窗 
        if event.type == QUIT:
            running = False
            break

        # 當按下鍵盤按鍵 -> 操控船隻的移動(目前是操控嫡傳移動)
        if event.type == KEYDOWN:
            enemy_boat.handle_keydown(event.key)  # 設置移動方向
        elif event.type == KEYUP:
            enemy_boat.handle_keyup(event.key)  # 停止移動

        if not sailing:
            # 按鈕事件判斷
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = event.pos

                # 按下開始建(start)
                if start_button_rect.collidepoint(mouse_pos):
                    # 五艘船開始往目標航行
                    for boat in boats:
                        boat.destination = enemy_boat.position
                        boat.mode1_sailing()
                    main_boat = boats[0]
                    for boat in boats:
                        if boat.dest_dist < main_boat.dest_dist:
                            main_boat = boat
                    for boat in boats:
                        if boat == main_boat:
                            continue
                        boat.velocity = main_boat.velocity
                    mode = 1 # 切換至 直線駛向enemy模式 (mode1)

                # 按下重置鍵(reset)
                elif reset_button_rect.collidepoint(mouse_pos):
                    boats = []
                    for i in range(num_boats):
                        # 將船隻調整回初始位置
                        angle = (2 * math.pi / num_boats) * i
                        if i == 0:
                            angle += math.radians(20)  
                        pos = (center[0] + radius * math.cos(angle),
                            center[1] + radius * math.sin(angle))
                        boat = Boat(f"picture/boat{i}.png", pos, i + 1, MAX_SPEED)
                        boats.append(boat)
                    print("所有船隻已重置")


# ---------------------------- 模式設定(鍵盤按鍵、滑鼠點擊按鈕) ------------------------------

    
    """
    mode2_recal是當mode2模式時
    若敵人船隻位置發生改變(透過上下左右鍵移動)
    需要重新計算A*路徑
    """

    def mode2_recal():
         # 設定目標圓的半徑 = 2 * enemy 的 collision_radius
        target_circle_radius = enemy_boat.around_radius
        
        # 計算排列目標的角度 (均分 360 度)
        N = len(boats)  # 假設所有船都要安排
        for idx, boat in enumerate(boats):
            # 可依 boat 的 id 或索引計算角度，這裡以均分360度為例
            theta = (2 * math.pi / N) * idx  # 每艘船的角度
            # 計算新目標點：以 enemy 為圓心
            new_goal = enemy_boat.position + Vector2(target_circle_radius * math.cos(theta),
                                                        target_circle_radius * math.sin(theta))
            boat.destination = new_goal
            print(f"Boat {boat.id} 新目的地: {new_goal}")

        # 為每艘船執行 A* 路徑搜尋
        for boat in boats:
            # 先把grid_map(紀錄障礙物格子的物件，在other_object檔案第二個) 轉成 blocked set (障礙物格子組合)
            # 反正就是將
            blocked = set()
            for col in range(grid_map.cols):
                for row in range(grid_map.rows):
                    if grid_map.grid[col][row] != 0 and grid_map.grid[col][row] != boat.id:  # 該網格是障礙物
                        blocked.add((col, row))
            if boat.destination is None:
                continue  # 沒目標就跳過
            
            start_col = int(boat.position.x // GRID_SIZE)
            start_row = int(boat.position.y // GRID_SIZE)
            start_heading = -boat.angle  # 或可用 boat.angle

            goal_col = int(boat.destination.x // GRID_SIZE)
            goal_row = int(boat.destination.y // GRID_SIZE)
            
            # 演算法呼叫
            path_res = a_star_search_time_heading(
                start_col, start_row, start_heading,
                goal_col, goal_row, blocked
            )

            if len(path_res) == 0:
                print(f"Boat {boat.id}: 找不到路徑！")
                boat.path = []
            else:
                print(f"Boat {boat.id}: 找到路徑，共 {len(path_res)} 步。")
                # path_res = [(px, py, t, heading), ...]
                # 可以進一步用 smooth_heading() 做平滑
                boat.path = smooth_heading(path_res, k=3)
                px, py, t, hh = boat.path[0]
                # 把第一個節點的 heading 設成 船隻現在的角度 (或 -angle)
                # 這樣第一幀就不會突然跳到 A* 的 heading
                boat.path[0] = (px, py, t, boat.angle)
            
            # 讓船隻開始走 path
            boat.is_moving = True
            boat.path_index = 1      # 這個變數是判斷船隻現在要往哪個中繼點移動(mode2啟用路徑演算法時)
                                     # 船隻行進過程會越來越大直到index指向目的地，用在update2

    """
    mode 0 -> 未按按鈕前的模式
    mode 1 -> 當船隻離敵船尚遠時，船隻筆直朝著敵船包圍
    mode 2 -> 當船隻接近敵船，依照算好的路徑走路線，若敵船發生移動會呼叫上面的mode2_recal

    mode1生效時，會透過boat.go_forward()更新位置
    mode2生效時，會透過boat.update2()更新位置
    """

    if mode == 0:
        NotImplemented


    elif mode == 1:
        main_boat.mode1_sailing()
        # 所有船與領頭船方向保持一致
        for boat in boats:
            boat.velocity = main_boat.velocity
            boat.go_forward()
        # 檢查 main_boat 與 enemy 的距離
        # 當 mode==1 時檢查 main_boat 與 enemy 的距離
        dist_to_enemy = (main_boat.position - enemy_boat.position).length()
        if dist_to_enemy < enemy_boat.alg_radius:  # 當進入演算法生效的圓圈區域
            print("Main boat 進入 enemy 的大泡泡範圍，切換到 mode=2")
            mode = 2  # 切換至 mode2，接下來用 A* 計算路徑
            enemy_boat_position1 = enemy_boat.position.copy()
            #boatss = boats
            mode2_recal()
            #for i in range(5):
            #    boats[i].angle = boatss[i].angle
    elif mode == 2:
        if (enemy_boat.position - enemy_boat_position1).length() > 1e-3:
            print("重算目的地")
            mode2_recal()
            enemy_boat_position1 = enemy_boat.position.copy()
        not_moving_num = 0
        for boat in boats:
            boat.update2(boats, grid_map)
            if boat.is_moving == False:
                not_moving_num += 1
        if not_moving_num == num_boats:
            mode = 0


# ------------------------------------ 繪製所有元件 ----------------------------------------


    # 繪製背景
    screen.blit(background, (0, 0))

    # 繪製路徑
    if mode == 2:
        for boat in boats:
            for (px, py, step_t, hdg) in boat.path:
                # 直接拿 hdg 當箭頭方向
                draw_arrow(screen, (255, 0, 0), (px, py), hdg, size=8)

    # 繪製網格
    draw_grid(screen)

    # 繪製所有船
    for b in boats:
        b.draw(screen, font)

    # 繪製障礙物網格 (使用橘色小點)
    for col in range(grid_map.cols):
        for row in range(grid_map.rows):
            if grid_map.grid[col][row] != 0:  # 如果該網格為障礙物
                px, py = grid_map.get_pixel_coords(col, row)
                pygame.draw.circle(screen, (255, 165, 0), (px, py), 2)  # 畫出小點

    # 繪製領頭船
    enemy_boat.update()
    enemy_boat.draw(screen, font)


    # 繪製按鈕與提示
    if not sailing:
        draw_buttons(selecting_destination, current_boat, boats)

    pygame.display.flip()

pygame.quit()
sys.exit()
