"""
成本计算工具模块
"""
import numpy as np

# --- 成本参数 ---
FIXED_COST_PER_VEHICLE = 400  # 车辆启动成本
WAITING_COST_PER_HOUR = 20    # 早到等待成本
PENALTY_COST_PER_HOUR = 50    # 晚到惩罚成本
FUEL_PRICE_PER_LITER = 7.61   # 燃油价格
ELECTRICITY_PRICE_PER_KWH = 1.64 # 电价
CARBON_COST_PER_UNIT = 0.65   # 碳排放成本

# --- 碳排放系数 ---
FUEL_EMISSION_COEFF = 2.547   # 油耗碳排放转换系数
ELEC_EMISSION_COEFF = 0.501   # 电耗碳排放转换系数

def calculate_time_window_penalty(arrival_time: float, start_time: float, end_time: float) -> float:
    """计算时间窗惩罚成本"""
    early_penalty = max(0, start_time - arrival_time) * WAITING_COST_PER_HOUR
    late_penalty = max(0, arrival_time - end_time) * PENALTY_COST_PER_HOUR
    return early_penalty + late_penalty

def get_travel_speed(depart_time: float) -> float:
    """根据出发时间获取时变速度（使用期望值）"""
    hour = depart_time % 24
    if (8 <= hour < 9) or (11.5 <= hour < 13):
        # 拥堵时段
        return 9.8
    elif (10 <= hour < 11.5) or (15 <= hour < 17):
        # 一般时段
        return 35.4
    else: # 包括 9-10, 13-15 以及其他未定义时段
        # 顺畅时段
        return 55.3

def calculate_energy_cost(vehicle_type: str, speed: float, distance: float, load_ratio: float) -> tuple[float, float]:
    """
    计算能耗成本和碳排放成本
    
    Args:
        vehicle_type (str): 车辆类型 ('fuel' or 'electric')
        speed (float): 速度 (km/h)
        distance (float): 距离 (km)
        load_ratio (float): 载重率 (0 to 1)

    Returns:
        tuple[float, float]: (能耗成本, 碳排放成本)
    """
    if vehicle_type == 'fuel':
        # 燃油车
        fpk = 0.0025 * speed**2 - 0.2554 * speed + 31.75
        if load_ratio > 0:
            fpk *= (1 + 0.4 * load_ratio)
        
        fuel_consumption = fpk * distance / 100
        fuel_cost = fuel_consumption * FUEL_PRICE_PER_LITER
        emission_cost = fuel_consumption * FUEL_EMISSION_COEFF * CARBON_COST_PER_UNIT
        return fuel_cost, emission_cost
    else: # electric
        # 新能源车
        epk = 0.0014 * speed**2 - 0.12 * speed + 36.19
        if load_ratio > 0:
            epk *= (1 + 0.35 * load_ratio)
            
        energy_consumption = epk * distance / 100
        electricity_cost = energy_consumption * ELECTRICITY_PRICE_PER_KWH
        emission_cost = energy_consumption * ELEC_EMISSION_COEFF * CARBON_COST_PER_UNIT
        return electricity_cost, emission_cost

def calculate_total_cost(solution: dict, data: dict) -> dict:
    """
    计算一个完整解决方案的总成本。
    
    Args:
        solution (dict): 包含车辆路径和到达时间的解。
                         格式: {'routes': {vehicle_id: [node1, node2, ...]}, 'arrivals': {vehicle_id: [t1, t2, ...]}}
        data (dict): 预处理后的数据。

    Returns:
        dict: 包含各项成本明细和总成本的字典。
    """
    total_fixed_cost = 0
    total_travel_cost = 0
    total_emission_cost = 0
    total_penalty_cost = 0
    
    customers_df = data['customers_df'].set_index('ID')
    dist_matrix = data['distance_matrix']
    vehicle_types = data['vehicle_types']
    
    # 假设 solution['vehicle_map'] 存储了 vehicle_id 到 vehicle_type_name 的映射
    # 例如: solution['vehicle_map'] = {0: 'fuel1', 1: 'electric2', ...}
    # 若存在 delivery_weight_map，则按每次配送重量更新载重，支持同一客户分批配送。
    delivery_weight_map = solution.get('delivery_weight_map', {})
    
    for vehicle_id, route in solution['routes'].items():
        if not route or len(route) <= 2: # 必须有配送中心->客户->配送中心
            continue
            
        total_fixed_cost += FIXED_COST_PER_VEHICLE
        
        vehicle_type_name = solution['vehicle_map'][vehicle_id]
        v_info = vehicle_types[vehicle_type_name]
        v_type = v_info['type']
        max_capacity_w = v_info['capacity_w']

        if vehicle_id in delivery_weight_map and len(delivery_weight_map[vehicle_id]) == len(route):
            current_load_w = float(sum(delivery_weight_map[vehicle_id][1:-1]))
        else:
            current_load_w = float(sum(customers_df.loc[node, 'total_weight'] for node in route[1:-1]))

        for i in range(len(route) - 1):
            from_node = route[i]
            to_node = route[i+1]
            
            distance = dist_matrix[from_node, to_node]
            depart_time = solution['arrivals'][vehicle_id][i] + (customers_df.loc[from_node, 's_i'] if from_node != 0 else 0)
            
            speed = get_travel_speed(depart_time)
            load_ratio = current_load_w / max_capacity_w if max_capacity_w > 0 else 0
            
            travel_cost, emission_cost = calculate_energy_cost(v_type, speed, distance, load_ratio)
            total_travel_cost += travel_cost
            total_emission_cost += emission_cost
            
            # 更新载重
            if to_node != 0:
                if vehicle_id in delivery_weight_map and len(delivery_weight_map[vehicle_id]) == len(route):
                    current_load_w -= float(delivery_weight_map[vehicle_id][i + 1])
                else:
                    current_load_w -= float(customers_df.loc[to_node, 'total_weight'])
            
            # 计算时间窗惩罚
            if to_node != 0:
                arrival_at_to = solution['arrivals'][vehicle_id][i+1]
                tw_start = customers_df.loc[to_node, 'start_time_h']
                tw_end = customers_df.loc[to_node, 'end_time_h']
                total_penalty_cost += calculate_time_window_penalty(arrival_at_to, tw_start, tw_end)

    total_cost = total_fixed_cost + total_travel_cost + total_emission_cost + total_penalty_cost
    
    return {
        "total_cost": total_cost,
        "fixed_cost": total_fixed_cost,
        "travel_cost": total_travel_cost,
        "emission_cost": total_emission_cost,
        "penalty_cost": total_penalty_cost,
    }
