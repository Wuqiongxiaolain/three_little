"""
基础VRP模型定义
"""
from abc import ABC, abstractmethod

class BaseVRPModel(ABC):
    """
    VRP模型基类，定义了所有VRP模型应共享的接口。
    """
    def __init__(self, data: dict, policy_active: bool = False):
        """
        初始化模型。

        Args:
            data (dict): 预处理后的数据。
            policy_active (bool): 是否激活绿色配送区政策。
        """
        self.data = data
        self.policy_active = policy_active
        self.customers_df = data['customers_df']
        self.distance_matrix = data['distance_matrix']
        self.vehicle_types = data['vehicle_types']
        self.num_customers = data['num_customers']
        
        # 将客户信息转换为更易于访问的格式，例如字典
        self.customers = self.customers_df.set_index('ID').to_dict('index')

    @abstractmethod
    def solve(self):
        """
        求解VRP问题。
        子类必须实现此方法。
        """
        raise NotImplementedError

    def evaluate_solution(self, solution: dict) -> dict:
        """
        评估解决方案的成本。
        
        Args:
            solution (dict): 包含路径和时间的解决方案。

        Returns:
            dict: 包含成本明细的字典。
        """
        # 可以在这里调用 cost_utils 中的函数
        from src.utils.cost_utils import calculate_total_cost
        
        # 确保 solution 格式正确
        if 'routes' not in solution or 'arrivals' not in solution or 'vehicle_map' not in solution:
            raise ValueError("解决方案格式不正确，缺少 'routes', 'arrivals' 或 'vehicle_map'")
            
        return calculate_total_cost(solution, self.data)

    def check_constraints(self, solution: dict) -> bool:
        """
        检查解决方案是否满足所有硬约束。
        
        Args:
            solution (dict): 解决方案。

        Returns:
            bool: 如果所有约束都满足，则为 True，否则为 False。
        """
        # TODO: 实现详细的约束检查逻辑
        # 1. 容量约束 (重量和体积)
        # 2. 路径连续性 (每个客户只被访问一次)
        # 3. 绿色区域政策约束 (如果 policy_active 为 True)
        print("约束检查功能待实现。")
        return True
