import json
import os

class UserManager:
    def __init__(self, db_file="users.json"):
        self.db_file = db_file
        self.users = self._load_users()
        self.player1 = None 
        self.player2 = None

    def _load_users(self):
        if not os.path.exists(self.db_file):
            return {}
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def _save_users(self):
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, indent=4)

    def register(self, username, password):
        if username in self.users:
            return False, "用户名已存在"
        self.users[username] = {
            "password": password,
            "wins": 0,
            "total": 0
        }
        self._save_users()
        return True, "注册成功"

    def login(self, username, password, slot=1):
        if username not in self.users:
            return False, "用户不存在"
        if self.users[username]["password"] != password:
            return False, "密码错误"
        
        if slot == 1:
            self.player1 = username
            return True, f"玩家1 ({username}) 登录成功"
        elif slot == 2:
            self.player2 = username
            return True, f"玩家2 ({username}) 登录成功"
        return False, "无效的玩家槽位"

    def logout(self, slot=None):
        if slot == 1: self.player1 = None
        elif slot == 2: self.player2 = None
        else: 
            self.player1 = None
            self.player2 = None

    # 修改点：分别更新战绩
    def update_stats_pvp(self, winner_slot):
        # winner_slot: 1 表示玩家1胜，2 表示玩家2胜
        
        # 更新玩家 1
        if self.player1:
            self.users[self.player1]["total"] += 1
            if winner_slot == 1:
                self.users[self.player1]["wins"] += 1
        
        # 更新玩家 2
        if self.player2:
            self.users[self.player2]["total"] += 1
            if winner_slot == 2:
                self.users[self.player2]["wins"] += 1
        
        self._save_users()
    def get_display_name(self, slot=None):
        """
        获取显示用的玩家名称和战绩。
        :param slot: 1 表示玩家1，2 表示玩家2，None 表示获取汇总信息（用于主菜单）
        """
        # 情况A：未指定槽位，返回两个玩家的汇总信息 (适配 client.py 主菜单显示)
        if slot is None:
            p1_info = self.get_display_name(1)
            p2_info = self.get_display_name(2)
            return f"P1: {p1_info} | P2: {p2_info}"

        # 情况B：指定了槽位，获取特定玩家信息
        username = self.player1 if slot == 1 else self.player2
        
        if not username:
            return "游客"
        
        # 获取战绩
        stats = self.users.get(username, {"wins": 0, "total": 0}) 
        return f"{username} (胜率: {stats['wins']}/{stats['total']}" + (f" {stats['wins']/stats['total']*100:.2f}%" if stats['total'] else "") + ")"

