import random
import copy

class AIPlayer:
    def __init__(self, level=1):
        self.level = level # 1: Random, 2: Heuristic

    def get_move(self, game):
        """根据当前游戏状态返回 (x, y)"""
        valid_moves = game.get_valid_moves()
        if not valid_moves:
            return None
        
        if self.level == 1:
            return self._random_move(valid_moves)
        else:
            return self._heuristic_move(game, valid_moves)

    def _random_move(self, moves):
        return random.choice(moves)

    def _heuristic_move(self, game, moves):
        # 简单评分 AI (针对黑白棋优化，五子棋/围棋也可通用但较弱)
        best_score = -float('inf')
        best_move = moves[0]
        
        # 简单权重矩阵 (针对 8x8 黑白棋)
        # 角落权重极高，边缘次之，C位/X位（角落旁）极低
        weights = [
            [100, -20, 10,  5,  5, 10, -20, 100],
            [-20, -50, -2, -2, -2, -2, -50, -20],
            [ 10,  -2, -1, -1, -1, -1,  -2,  10],
            [  5,  -2, -1, -1, -1, -1,  -2,   5],
            [  5,  -2, -1, -1, -1, -1,  -2,   5],
            [ 10,  -2, -1, -1, -1, -1,  -2,  10],
            [-20, -50, -2, -2, -2, -2, -50, -20],
            [100, -20, 10,  5,  5, 10, -20, 100]
        ]

        player = game.current_player
        
        # 如果不是黑白棋，退化为随机（或者实现五子棋的连珠评分）
        if type(game).__name__ != 'OthelloGame':
             return random.choice(moves)

        for r, c in moves:
            score = 0
            # [修改] 增加范围检查
            if r < len(weights) and c < len(weights[0]):
                score = weights[r][c]
            else:
                # 对于超出权值表的部分，给予一个默认的中性分
                score = 1
            
            # 添加一点随机性防止死板
            score += random.random() 
            
            if score > best_score:
                best_score = score
                best_move = (r, c)
        
        return best_move