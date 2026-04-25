"""
使用节约算法 (Savings Algorithm) 构建初始解。
"""
import numpy as np

def clarke_wright_savings(data: dict, policy_active: bool = False):
    """
    实现Clarke & Wright节约算法来生成初始VRP解。

    Args:
        data (dict): 预处理后的数据。
        policy_active (bool): 是否考虑绿色区域政策。

    Returns:
        dict: 一个初始解，包含 'routes', 'arrivals', 'vehicle_map'。
    """
    customers_df = data['customers_df'].set_index('ID')
    dist_matrix = data['distance_matrix']
    depot_id = 0

    # 1. 计算节约值
    savings = []
    customer_ids = customers_df.index[customers_df.index != depot_id]
    for i in customer_ids:
        for j in customer_ids:
            if i >= j:
                continue
            saving_value = dist_matrix[depot_id, i] + dist_matrix[depot_id, j] - dist_matrix[i, j]
            savings.append((saving_value, i, j))
    
    # 按节约值降序排序
    savings.sort(key=lambda x: x[0], reverse=True)

    # 2. 初始化每个客户为一条单独的路径
    routes = {cid: [depot_id, cid, depot_id] for cid in customer_ids}
    
    # 3. 合并路径
    for _, i, j in savings:
        route_i, route_j = None, None
        key_i, key_j = -1, -1

        # 找到包含 i 和 j 的路径
        for key, route in routes.items():
            if i in route:
                route_i = route
                key_i = key
            if j in route:
                route_j = route
                key_j = key
        
        # 如果 i 和 j 已经在同一路径中，则跳过
        if key_i == key_j:
            continue

        # 检查合并的可行性
        # 条件1: i 是路径的末尾客户，j 是路径的开头客户
        if route_i[-2] == i and route_j[1] == j:
            merged_route = route_i[:-1] + route_j[1:]
            
            # 检查容量约束
            total_w = sum(customers_df.loc[c, 'total_weight'] for c in merged_route[1:-1])
            total_v = sum(customers_df.loc[c, 'total_volume'] for c in merged_route[1:-1])
            
            # 简单起见，这里我们只用最大的一种车型来检查，实际应更复杂
            # TODO: 改进为考虑多种车型
            vehicle_ok = False
            for v_info in data['vehicle_types'].values():
                if total_w <= v_info['capacity_w'] and total_v <= v_info['capacity_v']:
                    vehicle_ok = True
                    break
            
            if vehicle_ok:
                routes[key_i] = merged_route
                del routes[key_j]

    # 4. 格式化输出
    final_routes = list(routes.values())
    
    # TODO: 分配具体车辆，计算到达时间
    # 这里只是一个非常简化的实现
    solution = {
        'routes': {idx: route for idx, route in enumerate(final_routes)},
        'arrivals': {}, # 到达时间需要单独计算
        'vehicle_map': {} # 车辆类型映射需要单独分配
    }
    
    print(f"节约算法生成了 {len(final_routes)} 条初始路径。")
    
    return solution


if __name__ == '__main__':
    from pathlib import Path
    from src.data.loader import load_all_data
    from src.data.preprocess import preprocess_data

    try:
        project_root = Path(__file__).resolve().parents[2]
        data_path = project_root / "data" / "附件"
        
        raw_data = load_all_data(data_path)
        processed_data = preprocess_data(raw_data)
        
        initial_solution = clarke_wright_savings(processed_data)
        
        print("\n生成的初始路径示例 (前5条):")
        for i, route in enumerate(initial_solution['routes'].values()):
            if i >= 5:
                break
            print(f"- {route}")

    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(f"测试节约算法时发生错误: {e}")
