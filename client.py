import sys
import time
import os
import pickle
from exceptions import *
from view import *
from backend import *
from account import UserManager
from ai import AIPlayer

class GameClient:
    def __init__(self):
        self.game = None 
        self.ui_builder = ConsoleUIBuilder()
        self.user_manager = UserManager()
        self.last_message = "欢迎！请登录或直接开始。"
        self.show_hints = True 
        self.pass_count = 0 
        
        # 0: 人类, 1-2: AI等级
        self.player_settings = {1: 0, 2: 0} 
        self.ai_engine = None

    def start(self):
        while True:
            self._clear_screen()
            display_name = self.user_manager.get_display_name()
            print(f"=== 棋类对战平台 (当前用户: {display_name}) ===")
            print(f"当前用户: P1-[{self.user_manager.player1 or '游客'}]  P2-[{self.user_manager.player2 or '游客'}]")
            print("1. 账户: login <user> <pass> [1|2] ...")
            print("2. 游戏: start <game> <size> [mode]")
            print("   - game: gomoku (五子棋) | go (围棋) | othello (黑白棋)")
            print("   - mode: pvp (人人) | pve (人机) | eve (机机)")
            print("   例: start othello 8 pve")
            print("3. 读档: load <filepath>")
            print("4. 退出: quit")
            print("-" * 30)
            print(f"系统提示: {self.last_message}")
            
            try:
                user_input = input("\n请输入指令 > ").strip().split()
                if not user_input: continue
                
                cmd = user_input[0].lower()

                # --- 账户管理 ---
                if cmd == 'register':
                    if len(user_input) != 3: raise InvalidCommandError("格式: register <user> <pass>")
                    suc, msg = self.user_manager.register(user_input[1], user_input[2])
                    self.last_message = msg
                
                elif cmd == 'login':
                    # 允许格式: login user pass (默认P1) 或 login user pass 2
                    slot = 1
                    if len(user_input) == 4:
                        slot = int(user_input[3])
                    elif len(user_input) != 3: 
                        raise InvalidCommandError("格式: login <user> <pass> [1/2]")
                    
                    suc, msg = self.user_manager.login(user_input[1], user_input[2], slot)
                    self.last_message = msg

                elif cmd == 'logout':
                    self.user_manager.logout()
                    self.last_message = "已注销"

                # --- 游戏启动 ---
                elif cmd == 'start':
                    if len(user_input) < 3:
                        raise InvalidCommandError("格式: start <type> <size> [mode]")
                    
                    g_type = user_input[1]
                    try:
                        size = int(user_input[2])
                    except ValueError:
                        raise InvalidCommandError("棋盘大小必须为整数")
                        
                    mode = user_input[3].lower() if len(user_input) > 3 else 'pvp'

                    # 初始化 AI 配置
                    # 获取 AI 等级，默认为 1
                    ai_lvl = 1
                    if len(user_input) > 4:
                        try:
                            ai_lvl = int(user_input[4])
                        except:
                            print("AI等级无效，使用默认值 1")
                    self.player_settings = {1: 0, 2: 0}
                    if mode == 'pve':
                        self.player_settings[2] = ai_lvl # 默认白方是 Lv1 AI
                    elif mode == 'eve':
                        self.player_settings[1] = 1
                        self.player_settings[2] = 2 

                    # 初始化游戏对象
                    if g_type == 'gomoku': self.game = GomokuGame(size)
                    elif g_type == 'go': self.game = GoGame(size)
                    elif g_type == 'othello': self.game = OthelloGame(size)
                    else: raise InvalidCommandError("未知游戏类型: 请输入 gomoku, go 或 othello")
                    
                    self.ai_engine = AIPlayer(level=1)
                    self.pass_count = 0 # [Critical] 每次开始新游戏必须重置
                    self.last_message = f"游戏开始! 模式: {mode}"
                    self.game_loop()

                elif cmd == 'load': 
                    if len(user_input) != 2: raise InvalidCommandError("格式: load <filepath>")
                    self.load_game(user_input[1])
                    # 读取后询问是否回放
                    if input("是否进入回放模式? (y/n) > ").lower() == 'y':
                        self.replay_mode()
                    else:
                        self.game_loop()

                elif cmd == 'quit':
                    sys.exit()

            except Exception as e:
                self.last_message = f"错误: {str(e)}"

    def get_player_names(self):
        # 使用新写的 get_display_name 获取带战绩的完整显示名
        p1_display = self.user_manager.get_display_name(1)
        p2_display = self.user_manager.get_display_name(2)
        
        # 如果是 AI，覆盖显示名
        if self.player_settings[1] > 0:
            p1_name = f"AI-Lv{self.player_settings[1]}"
        else:
            p1_name = f"{p1_display} (黑)"
            
        if self.player_settings[2] > 0:
            p2_name = f"AI-Lv{self.player_settings[2]}"
        else:
            p2_name = f"{p2_display} (白)"

        return p1_name, p2_name

    def game_loop(self):
        while True:
            p1_name, p2_name = self.get_player_names()
            # 1. 先添加棋盘和基本信息
            self.ui_builder.add_board(self.game.board.grid)\
                        .add_info(self.game.current_player, self.last_message, p1_name, p2_name)

            # 2. 根据开关决定是否添加帮助菜单
            if self.show_hints:
                self.ui_builder.add_help()

            # 3. 最后构建并显示
            self.ui_builder.build_and_show() 
            # 检查胜负
            winner = self.check_game_over()
            if winner is not None:
                print(f"\n=== 游戏结束! {winner} ===")
                
                if winner == "平局":
                    # 平局可能只加场次不加胜场，或者不做处理，视规则而定
                    pass 
                else:

                    winner_val = self.game.check_winner() 
                    
                    # 仅在 PvP 模式下记录双方，PvE 只记录 P1
                    # 这里需要判断当前模式
                    # if self.player_settings[1] == 0 and self.player_settings[2] == 0:
                    #     # PvP: 调用双人更新
                    #     self.user_manager.update_stats_pvp(winner_val)
                    # else:
                    #     # PvE: 保持原有逻辑，只更新 P1 (如果 P1 赢了)
                    #     is_win = (winner_val == 1) # 假设玩家永远执黑(P1)
                    #     if self.user_manager.player1:
                    #         # 你可能需要保留旧的 update_stats 或手动调用 update_stats_pvp 的一部分
                    #         pass 
                    self.user_manager.update_stats_pvp(winner_val)
                
                input("按回车返回...")
                return

            # --- AI 自动行动逻辑 ---
            current_p = self.game.current_player
            if self.player_settings[current_p] > 0:
                print(f"AI ({'黑' if current_p==1 else '白'}) 正在思考...")
                time.sleep(0.5) 
                
                self.ai_engine.level = self.player_settings[current_p]
                
                # 黑白棋特殊逻辑：无路可走必须 Pass
                # 注意：backend 的 check_winner 已经处理了双方无路可走的情况
                # 这里处理单方无路可走
                valid_moves = self.game.get_valid_moves()
                if not valid_moves and isinstance(self.game, OthelloGame):
                    self.last_message = "AI 无处落子，被迫弃权"
                    self.game.pass_turn()
                    # 黑白棋的 Pass 不增加围棋的 pass_count，或者可视作逻辑上的 Pass
                    # 但为了不混淆围棋逻辑，这里不做 pass_count 操作
                    continue

                move = self.ai_engine.get_move(self.game)
                if move:
                    self.game.make_move(move[0], move[1])
                    self.pass_count = 0 
                    self.last_message = f"AI 落子于 ({move[0]}, {move[1]})"
                else:
                    # 围棋 AI 如果没返回 move (例如随机填满)，这里视为 pass
                    if isinstance(self.game, GoGame):
                        self.game.pass_turn()
                        self.pass_count += 1
                        self.last_message = "AI 此时选择虚着"
                    else:
                        self.last_message = "AI 无法移动"
                continue
            
            # --- 人类玩家逻辑 ---
            
            # 黑白棋自动检测无子可下
            if isinstance(self.game, OthelloGame):
                if not self.game.get_valid_moves():
                    input(f"玩家 {current_p} 无处落子，按回车弃权...")
                    self.game.pass_turn() 
                    self.last_message = "玩家无合法棋步，弃权"
                    continue

            user_input = input("指令 > ").strip().lower()
            try:
                self.handle_input(user_input)
                # 成功执行后，不需要重置 message，handle_input 内部会设置
            except StopIteration:
                return # 返回主菜单
            except GameError as e:
                self.last_message = f"非法操作: {str(e)}"
            except Exception as e:
                self.last_message = f"错误: {str(e)}"

    def handle_input(self, user_input):
        parts = user_input.split()
        if not parts: return
        cmd = parts[0]
        
        if cmd == 'move': 
            if len(parts) != 3: raise InvalidCommandError("格式: move r c")
            try:
                x, y = int(parts[1]), int(parts[2])
            except ValueError: raise InvalidCommandError("坐标必须为整数")
            
            self.game.make_move(x, y)
            self.pass_count = 0 # 玩家落子重置计数
            self.last_message = "落子成功"
        
        elif cmd == 'pass':
            if isinstance(self.game, GoGame):
                self.game.pass_turn()
                self.pass_count += 1
                self.last_message = "您选择了虚着"
            else:
                # 解决问题1: 明确提示
                raise InvalidCommandError("当前游戏不支持虚着 ")

        elif cmd == 'undo':
            # 解决问题2: PvE 悔棋需要回退两步
            try:
                # 先悔一步 (回退当前对手/AI的操作)
                self.game.undo() 
                msg = "悔棋成功 (已撤销一步)"
                
                # 如果是 PvE 且回退后变成了 AI 的回合，则再退一步回退到玩家回合
                current_p = self.game.current_player
                if self.player_settings[current_p] > 0:
                    try:
                        self.game.undo()
                        msg = "悔棋成功 (已撤销两步，回到您的回合)"
                    except GameStateError:
                        # 这种情况可能是开局 AI 先手，玩家无法悔到此
                        self.last_message = "无法继续悔棋 (已是开局)"
                        return

                self.pass_count = 0 # 悔棋打断虚着
                self.last_message = msg
            except GameStateError as e:
                raise GameStateError("无法悔棋: " + str(e))

        elif cmd == 'resign':
            # 解决问题3
            winner_id = 3 - self.game.current_player
            winner_str = "黑方" if winner_id == 1 else "白方"
            print(f"\n=== {winner_str} 获胜 (您认负了) ===")
            
            # === [修改前] (报错行) ===
            # self.user_manager.update_stats(is_win=False) 

            # === [修改后] 使用新接口 ===
            # 直接告诉管理器谁赢了 (winner_id)，它会自动处理 PvP 或 PvE 的战绩更新
            self.user_manager.update_stats_pvp(winner_id) 
            
            input("按回车返回...")
            raise StopIteration()

        elif cmd == 'restart':
            # 解决问题4
            size = self.game.board.size
            g_type = type(self.game)
            self.game = g_type(size)
            self.pass_count = 0
            self.last_message = "游戏已重新开始"

        elif cmd == 'save':
            if len(parts) != 2: 
                raise InvalidCommandError("格式: save <filename>")
            
            # === [修改开始] 修复 PVE 模式下错误记录玩家名字的问题 ===
            # 1. 确定黑方名字
            if self.player_settings.get(1, 0) > 0:
                p1_str = f"AI-Lv{self.player_settings[1]}"
            else:
                p1_str = self.user_manager.player1 if self.user_manager.player1 else "Guest"
            
            # 2. 确定白方名字
            if self.player_settings.get(2, 0) > 0:
                p2_str = f"AI-Lv{self.player_settings[2]}"
            else:
                p2_str = self.user_manager.player2 if self.user_manager.player2 else "Guest"
            
            # 3. 保存元数据
            self.game.player_settings_backup = self.player_settings
            self.game.players_metadata = {
                "black": p1_str,
                "white": p2_str,
                "black_account": self.user_manager.player1, # 依然保留真实账号记录用于后台查证
                "white_account": self.user_manager.player2
            }
            # === [修改结束] ===

            save_name = parts[1]

            fname_p1 = "AI" if self.player_settings[1] > 0 else (self.user_manager.player1 or "Guest")
            fname_p2 = "AI" if self.player_settings[2] > 0 else (self.user_manager.player2 or "Guest")
            filename = f"{fname_p1}_vs_{fname_p2}_{save_name}"
            
            self.game.save_game(filename)
            self.last_message = f"已保存为 {filename} (记录为: {p1_str} vs {p2_str})"
        
        elif cmd == 'hint':
            # 解决问题5
            self.show_hints = not self.show_hints
            self.last_message = "提示已隐藏" if not self.show_hints else "提示已显示"

        elif cmd == 'quit':
            # 解决问题6
            self.last_message = "返回主菜单"
            raise StopIteration()
        
        else:
            raise InvalidCommandError("未知指令，输入 hint 查看帮助")

    def check_game_over(self):
        # --- 针对围棋的特殊处理 ---
        if isinstance(self.game, GoGame):
            # 只有当累积两次虚着 (Pass) 时，才调用 check_winner 计算胜负
            if self.pass_count >= 2:
                return self._format_winner(self.game.check_winner())
            else:
                # 否则围棋一定未结束，直接返回 None，跳过后续检查
                return None
        
        # --- 其他游戏 (五子棋、黑白棋) 的常规判断 ---
        # 这些游戏的 check_winner 会自动判断是否满足结束条件 (如连珠、满盘)
        # 如果未结束，它们会返回 0
        winner_id = self.game.check_winner()
        if winner_id != 0:
            return self._format_winner(winner_id)
            
        return None

    def _format_winner(self, winner_id):
        if winner_id == 1: return "黑方获胜"
        if winner_id == 2: return "白方获胜"
        if winner_id == 3: return "平局"
        return None

    def replay_mode(self):
        # === [修改] 构造完整历史：历史记录 + 当前最终局面 ===
        # 即使 self.game.history 为空（刚开局），加上当前 grid 后就不为空了
        full_history = self.game.history + [self.game.board.grid]
        
        if not full_history:
            print("数据异常：无法获取棋局状态")
            return

        print("进入回放模式...")
        
        for idx, snapshot in enumerate(full_history):
            self._clear_screen()
            # 计算总步数显示
            total_steps = len(full_history) - 1
            print(f"=== 回放中: 第 {idx} 步 / 共 {total_steps} 步 ===")
            
            # 渲染棋盘快照
            lines = BoardComponent(snapshot).render()
            for l in lines: print(l)
            
            # 提示信息
            if idx == 0:
                print("\n[系统提示] 这是初始局面")
            elif idx == total_steps:
                print("\n[系统提示] 这是最终局面")
            
            cmd = input("\n[Enter] 下一步, [q] 退出回放 > ")
            if cmd.lower() == 'q':
                break
        
        input("回放结束，按回车返回主菜单...")

    def load_game(self, filepath):
        try:
            with open(filepath, 'rb') as f:
                self.game = pickle.load(f)
                if hasattr(self.game, 'player_settings_backup'):     
                    self.player_settings = self.game.player_settings_backup
                
                # [新增] 读取关联的账号信息并提示
                if hasattr(self.game, 'players_metadata'):
                    meta = self.game.players_metadata
                    p1 = meta.get('black', '?')
                    p2 = meta.get('white', '?')
                    print(f"对局信息 - 黑方: {p1}, 白方: {p2}")
                
                self.pass_count = 0
                self.last_message = "存档读取成功"
        except FileNotFoundError:
            raise GameStateError("文件不存在")
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