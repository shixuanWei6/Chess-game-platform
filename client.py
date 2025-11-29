
import sys
import os
import pickle
from exceptions import *
from view import *
from backend import *

class GameClient:
    def __init__(self):
        self.game = None 
        self.ui_builder = ConsoleUIBuilder()
        self.last_message = "欢迎来到对战平台！请输入 start 或 load 指令开始。"
        self.show_hints = True # 控制提示显示
        # 记录连续虚着次数，用于围棋终局判断
        self.pass_count = 0 

    def start(self):
        # 游戏启动入口：负责初始化配置
        while True:
            # 渲染简易的启动界面
            self._clear_screen()
            print("=== 棋类对战平台 ===")
            print("1. 新游戏: start <type> <size> (例如: start gomoku 15 或 start go 19)")
            print("2. 读存档: load <filepath>     (例如: load save.dat)")
            print("3. 退出:   quit")
            print("-" * 30)
            print(f"系统提示: {self.last_message}")
            
            # 获取输入
            try:
                user_input = input("\n请输入指令 > ").strip().split()
                if not user_input: continue
                
                cmd = user_input[0].lower()

                if cmd == 'start':
                    if len(user_input) != 3:
                        raise InvalidCommandError("参数错误。格式: start <game_type> <size>")
                    
                    g_type = user_input[1]
                    try:
                        size = int(user_input[2])
                    except ValueError:
                        raise InvalidCommandError("棋盘大小必须是整数")

                    if g_type == 'gomoku':
                        self.game = GomokuGame(size)
                    elif g_type == 'go':
                        self.game = GoGame(size)
                    else:
                        raise InvalidCommandError("未知游戏类型，请输入 gomoku 或 go")
                    
                    self.last_message = "游戏开始！"
                    self.pass_count = 0
                    self.game_loop() # 进入游戏循环

                elif cmd == 'load': 
                    if len(user_input) != 2:
                        raise InvalidCommandError("参数错误。格式: load <filepath>")
                    self.load_game(user_input[1])
                    self.game_loop()

                elif cmd == 'quit':
                    print("再见！")
                    sys.exit()
                else:
                    self.last_message = "无效指令，请参考上方菜单。"

            except Exception as e:
                self.last_message = f"错误: {str(e)}"

    def game_loop(self):
        # 游戏主循环
        while True:
            # 渲染界面 
            self.ui_builder\
                .add_board(self.game.board.grid)\
                .add_info(self.game.current_player, self.last_message)
            
            if self.show_hints: # 可选显示提示
                self.ui_builder.add_help()
            
            self.ui_builder.build_and_show()

            # 检查胜负状态 (在渲染后检查，确保用户看到最后一步)
            winner = self.check_game_over()
            if winner is not None:
                print(f"\n=== 游戏结束! {winner} ===")
                input("按回车键返回主菜单...")
                return # 退出该函数，返回 start() 的循环

            # 获取并处理指令
            user_input = input("指令 > ").strip().lower()
            try:
                self.handle_input(user_input)
                # 如果没报错，说明操作成功（除了一些特定指令外，重置消息）
                # if not self.last_message.startswith("操作成功"):
                #    self.last_message = "操作成功"
            except StopIteration:
                return # 真正退出 game_loop，返回到 start() 的菜单循环
            except GameError as e:
                self.last_message = f"非法操作: {str(e)}" # 
            except Exception as e:
                self.last_message = f"未知错误: {str(e)}"

    def handle_input(self, user_input):
        parts = user_input.split()
        if not parts: return
        cmd = parts[0]

        # 落子指令
        if cmd == 'move': 
            if len(parts) != 3:
                raise InvalidCommandError("格式错误。应为: move <row> <col>")
            try:
                x, y = int(parts[1]), int(parts[2])
            except ValueError:
                raise InvalidCommandError("坐标必须为整数")
            
            self.game.make_move(x, y)
            self.pass_count = 0 # 落子后重置虚着计数
            self.last_message = "落子成功"

        # 围棋虚着
        elif cmd == 'pass': 
            if isinstance(self.game, GoGame):
                self.game.pass_turn()
                self.pass_count += 1
                self.last_message = "当前玩家选择虚着 (Pass)"
            else:
                raise InvalidCommandError("只有围棋可以虚着")

        # 悔棋
        elif cmd == 'undo': 
            self.game.undo()
            self.pass_count = 0 # 悔棋可能会破坏连续虚着状态，简单起见重置
            self.last_message = "悔棋成功"

        # 认负
        elif cmd == 'resign': 
            # 认负直接判对方胜
            winner_id = 3 - self.game.current_player
            winner_str = "黑方" if winner_id == 1 else "白方"
            
            # 构建胜负消息
            self.last_message = f"{winner_str} 获胜 (对方认负)"
            
            # 显示最终结果
            print(f"\n=== {self.last_message} ===")
            input("按回车键返回主菜单...")
            
            # 使用 StopIteration 跳出 game_loop
            raise StopIteration("游戏结束")

        # 存档
        elif cmd == 'save': 
            if len(parts) != 2:
                raise InvalidCommandError("格式: save <filename>")
            self.game.save_game(parts[1])
            self.last_message = f"游戏已保存至 {parts[1]}"

        # 重新开始
        elif cmd == 'restart': 
            # 保留原配置重新开局
            size = self.game.board.size
            game_type = type(self.game)
            self.game = game_type(size)
            self.pass_count = 0
            self.last_message = "游戏已重置"

        # 界面控制
        elif cmd == 'hint': 
            self.show_hints = not self.show_hints
            self.last_message = f"提示已{'显示' if self.show_hints else '隐藏'}"

        elif cmd == 'quit': 
            # 这里是返回主菜单
            self.last_message = "已返回主菜单"
            raise StopIteration("返回主菜单") # 借用异常跳出

        else:
            raise InvalidCommandError("未知指令，输入 hint 查看帮助")

    def check_game_over(self):
        # 检查游戏是否结束
        winner_id = 0
        
        # 情况1: 五子棋连珠 (每次落子后 backend 可能会计算，或者在这里调用)
        # 情况2: 围棋双虚着
        
        if isinstance(self.game, GoGame):
            # 双方均决定不落子(连续两次Pass)时判胜负
            if self.pass_count >= 2:
                winner_id = self.game.check_winner()
        else:
            # 五子棋每次落子都检查
            winner_id = self.game.check_winner()

        if winner_id == 0:
            return None # 游戏继续
        elif winner_id == 1:
            return "黑方获胜"
        elif winner_id == 2:
            return "白方获胜"
        elif winner_id == 3:
            return "平局" 
        return None

    def load_game(self, filepath):
        # 读取存档逻辑
        try:
            with open(filepath, 'rb') as f:
                loaded_game = pickle.load(f)
                if not isinstance(loaded_game, GameBase):
                    raise ValueError("文件内容损坏或不是有效的游戏存档")
                self.game = loaded_game
                self.pass_count = 0
                self.last_message = "存档读取成功"
        except FileNotFoundError:
            raise GameStateError("找不到指定的存档文件")
        except Exception as e:
            raise GameStateError(f"读取失败: {str(e)}")

    def _clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
if __name__ == "__main__":
    try:
        client = GameClient()
        client.start()
    except KeyboardInterrupt:
        print("\n强制退出")