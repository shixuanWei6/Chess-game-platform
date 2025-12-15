from abc import ABC, abstractmethod
import copy
import pickle
from exceptions import *

# Board 类保持不变
class Board:
    def __init__(self, size):
        self.size = size
        self.grid = [[0 for _ in range(size)] for _ in range(size)]
    
    def is_valid(self, x, y):
        return 0 <= x < self.size and 0 <= y < self.size
    
    def count_stones(self):
        black = sum(row.count(1) for row in self.grid)
        white = sum(row.count(2) for row in self.grid)
        return black, white

class GameBase(ABC):
    def __init__(self, size=15):
        if not (8 <= size <= 19):
            raise ValueError("棋盘大小必须在 8-19 之间")
        self.board = Board(size)
        self.current_player = 1 
        self.history = [] 

    @abstractmethod
    def check_rules(self, x, y, player):
        pass

    @abstractmethod
    def check_winner(self):
        pass

    # 为 AI 提供合法落子接口
    def get_valid_moves(self):
        moves = []
        for r in range(self.board.size):
            for c in range(self.board.size):
                if self.board.grid[r][c] == 0:
                    try:
                        # 模拟检查，不同游戏规则不同
                        # 注意：Othello 会重写此方法以提高效率
                        self.check_rules(r, c, self.current_player)
                        moves.append((r, c))
                    except GameError:
                        continue
        return moves

    def make_move(self, x, y):
        # [修改] 增加对 Othello 的兼容性（Othello 可能在规则检查中就需要改变棋盘）
        # 这里保持通用逻辑
        if not self.board.is_valid(x, y):
            raise InvalidMoveError("坐标超出棋盘范围")
        if self.board.grid[x][y] != 0:
            raise InvalidMoveError("此处已有棋子")
        
        self.check_rules(x, y, self.current_player)
        self.history.append(copy.deepcopy(self.board.grid))
        self.board.grid[x][y] = self.current_player
        self.current_player = 3 - self.current_player

    def undo(self): 
        if not self.history:
            raise GameStateError("无棋可悔")
        prev_grid = self.history.pop()
        self.board.grid = prev_grid
        self.current_player = 3 - self.current_player

    def save_game(self, filepath):
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(self, f)
        except Exception as e:
            raise GameStateError(f"保存失败: {str(e)}")

# GomokuGame 和 GoGame 保持原样 (请保留原有代码)
class GomokuGame(GameBase):
    def check_rules(self, x, y, player):
        pass
    def check_winner(self):
        # ... (保留原代码)
        grid = self.board.grid
        size = self.board.size
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for r in range(size):
            for c in range(size):
                p = grid[r][c]
                if p == 0: continue
                for dr, dc in directions:
                    count = 1
                    tr, tc = r + dr, c + dc
                    while 0 <= tr < size and 0 <= tc < size and grid[tr][tc] == p:
                        count += 1
                        tr += dr
                        tc += dc
                    if count >= 5: return p
        for row in grid:
            if 0 in row: return 0
        return 3

class GoGame(GameBase):
    def __init__(self, size=19):
        super().__init__(size)

    def check_rules(self, x, y, player):
        # 围棋的规则检查比较复杂，通常结合在 make_move 里做（涉及提子后才能判断禁入点）
        pass

    def check_winner(self):
        # 简单数子规则：黑子多于白子为胜（未考虑贴目，仅做基础逻辑）
        black, white = self.board.count_stones()
        # 只有在双方停着（pass）后通常才算结束，这里仅返回当前状态
        return 1 if black > white else (2 if white > black else 0)

    def make_move(self, x, y):
        # 1. 基础检查
        if not self.board.is_valid(x, y):
            raise InvalidMoveError("坐标超出棋盘范围")
        if self.board.grid[x][y] != 0:
            raise InvalidMoveError("此处已有棋子")

        # 2. 模拟落子 (为了检查提子和自杀)
        # 先保存状态，如果这一步是非法的（如自杀），则回滚
        self.history.append(copy.deepcopy(self.board.grid))
        self.board.grid[x][y] = self.current_player
        
        opponent = 3 - self.current_player
        captured_any = False
        
        # 3. 检查四周的对手棋子是否被提吃
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dr, dc in directions:
            nr, nc = x + dr, y + dc
            if self.board.is_valid(nr, nc) and self.board.grid[nr][nc] == opponent:
                # 检查这一块对手棋是否还有气
                if not self._has_liberty(nr, nc):
                    self._capture_group(nr, nc)
                    captured_any = True
        
        # 4. 检查是否有气 (禁入点/自杀规则)
        # 规则：如果没提吃对方子，且自己落子后没气，则为禁入点
        if not captured_any and not self._has_liberty(x, y):
            # 还原棋盘
            self.board.grid = self.history.pop()
            raise InvalidMoveError("禁入点 (气尽禁入)")

        # 5. 劫争检查 (Ko Rule) - 简易版
        # 如果落子后局面和上一步完全一样（通常指上上一步），则为打劫
        # 注意：这里需要历史记录里至少有两步才能判断全局同型，此处暂略，防止代码过于复杂

        # 6. 切换回合
        self.current_player = opponent

    def pass_turn(self):
         self.history.append(copy.deepcopy(self.board.grid))
         self.current_player = 3 - self.current_player

    # === 核心辅助函数：检查是否有气 ===
    def _has_liberty(self, r, c):
        """检查 (r, c) 所在的棋子块是否至少有一口气"""
        group = self._get_group(r, c)
        for gr, gc in group:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = gr + dr, gc + dc
                # 如果周围有空位，说明有气，活棋
                if self.board.is_valid(nr, nc) and self.board.grid[nr][nc] == 0:
                    return True
        return False

    # === 核心辅助函数：获取连通块 ===
    def _get_group(self, r, c):
        """获取与 (r, c) 同色且相连的所有棋子坐标"""
        color = self.board.grid[r][c]
        group = []
        stack = [(r, c)]
        visited = set()
        visited.add((r, c)) # 必须记录 visited 防止死循环
        
        while stack:
            curr_r, curr_c = stack.pop()
            group.append((curr_r, curr_c))
            
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = curr_r + dr, curr_c + dc
                if self.board.is_valid(nr, nc) and \
                   (nr, nc) not in visited and \
                   self.board.grid[nr][nc] == color:
                    visited.add((nr, nc)) # 标记已访问
                    stack.append((nr, nc))
        return group

    # === 核心辅助函数：提子 ===
    def _capture_group(self, r, c):
        """移除 (r, c) 所在的死棋块"""
        group = self._get_group(r, c)
        for gr, gc in group:
            self.board.grid[gr][gc] = 0


# [新增] 黑白棋逻辑
class OthelloGame(GameBase):
    def __init__(self, size=8):
        super().__init__(size)
        # 初始化中心 4 子
        mid = size // 2
        # 标准开局：左上白，右下白，右上黑，左下黑 (Grid: 1黑 2白)
        self.board.grid[mid-1][mid-1] = 2
        self.board.grid[mid][mid] = 2
        self.board.grid[mid-1][mid] = 1
        self.board.grid[mid][mid-1] = 1

    def make_move(self, x, y):
        # 1. 基础合法性检查
        # 注意：这里不仅要看是否在棋盘内，还得看是否符合翻转规则
        if not self.board.is_valid(x, y) or self.board.grid[x][y] != 0:
            raise InvalidMoveError("无效位置或已有棋子")

        # 获取需要翻转的棋子列表 (利用你已经写好的 _get_flipped_stones)
        flipped_stones = self._get_flipped_stones(x, y, self.current_player)
        
        # 如果没有棋子被翻转，说明这步棋不合法 (黑白棋规则：必须翻转至少一颗子)
        if not flipped_stones:
            raise InvalidMoveError("无效落子：必须能够翻转对手的棋子")

        # 2. 记录历史 (用于悔棋)
        self.history.append(copy.deepcopy(self.board.grid))

        # 3. 落子
        self.board.grid[x][y] = self.current_player

        # 4. 执行翻转 (将夹住的对手棋子变成己方颜色)
        for r, c in flipped_stones:
            self.board.grid[r][c] = self.current_player
        
        # 5. 切换回合
        self.current_player = 3 - self.current_player


  

    def check_rules(self, x, y, player):
        # 用于 get_valid_moves 的轻量级检查
        if not self._get_flipped_stones(x, y, player):
            raise InvalidMoveError("无效落子")

    def _get_flipped_stones(self, x, y, player):
        opponent = 3 - player
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), 
                      (0, 1), (1, -1), (1, 0), (1, 1)]
        flipped = []
        
        for dr, dc in directions:
            temp = []
            r, c = x + dr, y + dc
            while self.board.is_valid(r, c) and self.board.grid[r][c] == opponent:
                temp.append((r, c))
                r += dr
                c += dc
            # 如果尽头是自己的棋子，且中间有对手棋子
            if self.board.is_valid(r, c) and self.board.grid[r][c] == player:
                flipped.extend(temp)
        
        return flipped

    def get_valid_moves(self):
        # 优化：仅检查周围有棋子的空位（这里简单全遍历）
        moves = []
        for r in range(self.board.size):
            for c in range(self.board.size):
                if self.board.grid[r][c] == 0:
                    if self._get_flipped_stones(r, c, self.current_player):
                        moves.append((r, c))
        return moves

    def check_winner(self):
        # 1. 判断是否双方都无子可下，或者棋盘满
        p1_moves = self.get_valid_moves()
        # 临时切换看对手有无棋步
        self.current_player = 3 - self.current_player
        p2_moves = self.get_valid_moves()
        self.current_player = 3 - self.current_player # 切回来

        black, white = self.board.count_stones()
        
        if not p1_moves and not p2_moves:
            # 双方无棋，终局
            if black > white: return 1
            elif white > black: return 2
            else: return 3
        
        return 0 # 继续游戏
    def pass_turn(self):
        """记录一次虚着，用于历史回放"""
        self.history.append(copy.deepcopy(self.board.grid))
        self.current_player = 3 - self.current_player