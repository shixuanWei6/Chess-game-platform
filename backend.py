# backend.py
from abc import ABC, abstractmethod
import copy
import pickle
from exceptions import *

class Board:
    """棋盘类：只负责存储数据"""
    def __init__(self, size):
        self.size = size
        # 0: 空, 1: 黑, 2: 白
        self.grid = [[0 for _ in range(size)] for _ in range(size)]

    def is_valid(self, x, y):
        return 0 <= x < self.size and 0 <= y < self.size

    def count_stones(self):
        black = sum(row.count(1) for row in self.grid)
        white = sum(row.count(2) for row in self.grid)
        return black, white

class GameBase(ABC):
    """抽象游戏基类"""
    def __init__(self, size=15):
        # 限制棋盘大小 
        if not (8 <= size <= 19):
            raise ValueError("棋盘大小必须在 8-19 之间")
        self.board = Board(size)
        self.current_player = 1 # 1: Black, 2: White
        self.history = [] # 存储历史快照用于悔棋和劫争判断

    @abstractmethod
    def check_rules(self, x, y, player):
        pass

    @abstractmethod
    def check_winner(self):
        """返回 0:未分胜负, 1:黑胜, 2:白胜, 3:平局"""
        pass

    def make_move(self, x, y):
        """
        通用落子逻辑 (五子棋直接使用，围棋需重写以处理提子)
        """
        # 1. 基础检查
        if not self.board.is_valid(x, y):
            raise InvalidMoveError("坐标超出棋盘范围")
        if self.board.grid[x][y] != 0:
            raise InvalidMoveError("此处已有棋子")
        
        # 2. 规则检查
        self.check_rules(x, y, self.current_player)

        # 3. 保存快照 (Deepcopy)
        self.history.append(copy.deepcopy(self.board.grid))

        # 4. 执行落子
        self.board.grid[x][y] = self.current_player
        
        # 5. 胜负已分则不切换(可选)，或者由客户端判断。此处仅切换。
        self.current_player = 3 - self.current_player

    def undo(self): 
        if not self.history:
            raise GameStateError("无棋可悔")
        
        # 恢复上一步状态
        prev_grid = self.history.pop()
        self.board.grid = prev_grid
        self.current_player = 3 - self.current_player

    def save_game(self, filepath):
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(self, f)
        except Exception as e:
            raise GameStateError(f"保存失败: {str(e)}")

class GomokuGame(GameBase):
    """五子棋逻辑实现"""
    
    def check_rules(self, x, y, player):
        # 第一阶段五子棋无需特殊规则，仅需基础合法性（已在make_move检查）
        pass

    def check_winner(self): 
        grid = self.board.grid
        size = self.board.size
        
        # 检查四个方向：横、竖、左斜、右斜
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        
        # 只需要检查当前棋盘上所有点，或者优化为只检查最后落子点(但在check_winner接口里通常检查全局)
        # 这里为了通用性，遍历全盘（稍微低效但逻辑简单稳健）
        for r in range(size):
            for c in range(size):
                p = grid[r][c]
                if p == 0: continue
                
                for dr, dc in directions:
                    count = 1
                    # 向正方向延伸
                    tr, tc = r + dr, c + dc
                    while 0 <= tr < size and 0 <= tc < size and grid[tr][tc] == p:
                        count += 1
                        tr += dr
                        tc += dc
                    
                    if count >= 5:
                        return p # 返回获胜玩家 ID

        # 检查是否平局 (棋盘满)
        for row in grid:
            if 0 in row:
                return 0 # 游戏继续
        return 3 # 平局

class GoGame(GameBase):
    """围棋逻辑实现"""

    def make_move(self, x, y):
        # 重写围棋的落子逻辑，因为涉及提子、打劫和自杀判断
        # 1. 基础检查
        if not self.board.is_valid(x, y):
            raise InvalidMoveError("坐标超出棋盘范围")
        if self.board.grid[x][y] != 0:
            raise InvalidMoveError("此处已有棋子")

        # 2. 模拟落子 (Trial)
        # 必须在真实落子前模拟，判断是否提子或自杀
        trial_grid = copy.deepcopy(self.board.grid)
        trial_grid[x][y] = self.current_player
        
        opponent = 3 - self.current_player
        captured_stones = []

        # 3. 检查邻居对手棋子是否无气 (提子逻辑 )
        neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dx, dy in neighbors:
            nx, ny = x + dx, y + dy
            if self.board.is_valid(nx, ny) and trial_grid[nx][ny] == opponent:
                # 计算该对手块的气
                group, liberties = self._get_group_liberties(trial_grid, nx, ny)
                if liberties == 0:
                    captured_stones.extend(group)
        
        # 执行提子：从模拟棋盘移除
        for cx, cy in captured_stones:
            trial_grid[cx][cy] = 0

        # 4. 检查自杀 (禁入点)：自己落下后无气，且没有提掉对手
        # 下子时不能下到不合法位置
        my_group, my_liberties = self._get_group_liberties(trial_grid, x, y)
        if my_liberties == 0:
            raise InvalidMoveError("禁入点 (自杀操作)")

        # 5. 检查全局同型 (打劫 Ko)
        if self.history and trial_grid == self.history[-1]:
            # 注意：简单的劫争规则是不能立即回到上一步。
            # 严格来说应该检查整个历史，但基本劫争通常只检查上一步。
            raise InvalidMoveError("全局同型 (打劫禁手)")

        # === 确认落子合法，应用更改 ===
        self.history.append(copy.deepcopy(self.board.grid)) # 存旧状态
        self.board.grid = trial_grid # 应用新状态
        self.current_player = opponent # 切换玩家

    def check_rules(self, x, y, player):
        # 逻辑已整合在 make_move 中
        pass
    
    def pass_turn(self): 
        """虚着：不落子，直接切换"""
        self.history.append(copy.deepcopy(self.board.grid))
        self.current_player = 3 - self.current_player

    def check_winner(self):
        """
        围棋终局判断 
        当双方虚着或无子可下时调用。
        这里实现简单的数子法（子多者胜）。
        """
        black, white = self.board.count_stones()
        # 贴目逻辑此处简化，直接比子数
        if black > white:
            return 1
        elif white > black:
            return 2
        else:
            return 3 # 平局

    def _get_group_liberties(self, grid, start_x, start_y):
        """
        辅助函数：计算某一颗棋子所在块(Group)的棋子列表和气的数量
        使用 BFS/DFS 算法
        """
        color = grid[start_x][start_y]
        if color == 0:
            return [], 0

        stack = [(start_x, start_y)]
        visited = set() # 记录已访问的同色棋子
        visited.add((start_x, start_y))
        
        liberties = set() # 记录气（空位坐标）
        group = [(start_x, start_y)]

        while stack:
            cx, cy = stack.pop()
            neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            for dx, dy in neighbors:
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < self.board.size and 0 <= ny < self.board.size):
                    continue
                
                neighbor_color = grid[nx][ny]
                if neighbor_color == 0:
                    liberties.add((nx, ny))
                elif neighbor_color == color and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    stack.append((nx, ny))
                    group.append((nx, ny))
        
        return group, len(liberties)