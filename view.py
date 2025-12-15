
from abc import ABC, abstractmethod

class UIComponent(ABC):
    @abstractmethod
    def render(self) -> list[str]:
        pass

class BoardComponent(UIComponent):
    def __init__(self, board_grid):
        self.grid = board_grid
    
    def render(self):
        lines = []
        # 将二维数组转换为字符图形
        lines.append("   " + " ".join([f"{i:2d}" for i in range(len(self.grid))]))
        for idx, row in enumerate(self.grid):
            row_str = " ".join([" ." if c==0 else (" X" if c==1 else " O") for c in row])
            lines.append(f"{idx:2d} {row_str}")
        return lines

class InfoComponent(UIComponent):
    def __init__(self, current_player, msg, p1_info, p2_info):
        self.current = current_player
        self.msg = msg
        self.p1 = p1_info
        self.p2 = p2_info

    def render(self):
        # 简单显示示例
        arrow_p1 = "<<" if self.current == 1 else "  "
        arrow_p2 = "<<" if self.current == 2 else "  "
        return [
            f"黑方: {self.p1} {arrow_p1}",
            f"白方: {self.p2} {arrow_p2}",
            f"系统提示: {self.msg}"
        ]

class ConsoleUIBuilder:
    # UI建造者：负责组装不同的组件
    def __init__(self):
        self.components = []

    def add_board(self, board_grid):
        self.components.append(BoardComponent(board_grid))
        return self

    # 增加 p1_info 和 p2_info 参数
    def add_info(self, player, msg, p1_info, p2_info):
        self.components.append(InfoComponent(player, msg, p1_info, p2_info))
        return self

    def build_and_show(self):
        import os
        os.system('cls' if os.name == 'nt' else 'clear') # 清屏
        for comp in self.components:
            for line in comp.render():
                print(line)
            print("-" * 20)
        self.components = [] # 重置
    def add_help(self):
        help_msg = [
            "操作指南:",
            "  move <x> <y> : 落子 (例: move 7 7)",
            "  pass         : 虚着 (仅围棋)",
            "  undo         : 悔棋",
            "  resign       : 认负",
            "  save <file>  : 存档",
            "  restart      : 重新开始",
            "  hint         : 隐藏/显示此提示",
            "  quit         : 返回主菜单"
        ]
        # 使用简单的文本组件渲染
        class HelpComponent:
            def render(self):
                return help_msg
        
        self.components.append(HelpComponent())
        return self