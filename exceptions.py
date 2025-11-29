# exceptions.py
class GameError(Exception):
    """游戏基础异常"""
    pass

class InvalidMoveError(GameError):
    """落子不合法 (位置占用、自杀、违反规则)"""
    pass

class InvalidCommandError(GameError):
    """指令无法解析"""
    pass

class GameStateError(GameError):
    """游戏状态错误 (如无棋可悔)"""
    pass