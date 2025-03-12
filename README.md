To: 許懷仁

主要看main.py 、 My_FCC_Astar.py 這兩個檔案就好

main.py 用到A*函式的地方只有 mode2_recal (line 233) 這裡而已

參數調整在config.py

可透過調整MAX_SPEED 、 ENEMY_SPEED分別控制五艘船和敵船速度



用reset重置船隻位置

用start sailing讓船隻開始包圍敵船

用上下左右可以控制enemy_ship



現在船隻如果在障礙物區域(也就是橘色點內)會整個當機

你看看能否修復這個問題

看不懂我的code也沒關係

只要新演算法能跑就ok
