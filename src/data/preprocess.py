"""
数据预处理模块
负责将加载的原始数据转换为模型可以直接使用的格式。
"""
import pandas as pd
import numpy as np

def preprocess_data(raw_data: dict[str, pd.DataFrame]) -> dict:
    """
    对加载的原始数据进行预处理和整合。

    Args:
        raw_data (dict[str, pd.DataFrame]): 包含原始 DataFrame 的字典。

    Returns:
        dict: 包含预处理后数据的字典，可直接用于模型。
    """
    # 1. 整合订单信息到客户级别
    orders_df = raw_data["orders"]
    customer_demands = orders_df.groupby('目标客户编号').agg(
        total_weight=('重量', 'sum'),
        total_volume=('体积', 'sum')
    ).reset_index()
    customer_demands.rename(columns={'目标客户编号': 'ID'}, inplace=True)

    # 2. 合并客户信息、需求、时间窗
    customer_info_df = raw_data["customer_info"]
    time_windows_df = raw_data["time_windows"]
    
    # 将时间窗的 '客户编号' 改为 'ID' 以便合并
    time_windows_df.rename(columns={'客户编号': 'ID'}, inplace=True)

    # 合并客户坐标和需求
    customers = pd.merge(customer_info_df, customer_demands, on='ID', how='left')
    # 合并时间窗
    customers = pd.merge(customers, time_windows_df, on='ID', how='left')

    # 对无订单客户补零，避免后续求解出现 NaN。
    customers['total_weight'] = customers['total_weight'].fillna(0.0)
    customers['total_volume'] = customers['total_volume'].fillna(0.0)
    
    # 填充配送中心的需求和时间窗（如果需要）
    customers.loc[customers['ID'] == 0, ['total_weight', 'total_volume']] = 0
    customers['s_i'] = 20 / 60 # 服务时间，单位：小时

    # 3. 确定绿色配送区客户
    # 市中心坐标 (0,0)，半径 10km
    center_x, center_y, radius = 0, 0, 10
    customers['is_green_zone'] = np.sqrt(
        (customers['X (km)'] - center_x)**2 + (customers['Y (km)'] - center_y)**2
    ) <= radius
    
    # 4. 转换时间窗为小时
    def time_to_hours(t_str):
        if pd.isna(t_str):
            return 0
        h, m = map(int, t_str.split(':'))
        return h + m / 60

    customers['start_time_h'] = customers['开始时间'].apply(time_to_hours)
    customers['end_time_h'] = customers['结束时间'].apply(time_to_hours)

    # 5. 整理距离矩阵
    distance_matrix = raw_data["distance_matrix"].values

    # 6. 定义车辆类型
    vehicle_types = {
        'fuel1': {'capacity_w': 3000, 'capacity_v': 13.5, 'count': 60, 'type': 'fuel'},
        'fuel2': {'capacity_w': 1500, 'capacity_v': 10.8, 'count': 50, 'type': 'fuel'},
        'fuel3': {'capacity_w': 1250, 'capacity_v': 6.5, 'count': 50, 'type': 'fuel'},
        'electric1': {'capacity_w': 3000, 'capacity_v': 15.0, 'count': 10, 'type': 'electric'},
        'electric2': {'capacity_w': 1250, 'capacity_v': 8.5, 'count': 15, 'type': 'electric'},
    }

    return {
        "customers_df": customers,
        "distance_matrix": distance_matrix,
        "vehicle_types": vehicle_types,
        "num_customers": len(customers) -1 # 减去配送中心
    }

if __name__ == '__main__':
    from pathlib import Path
    from loader import load_all_data

    try:
        project_root = Path(__file__).resolve().parents[2]
        data_path = project_root / "data" / "附件"
        
        raw_data = load_all_data(data_path)
        processed_data = preprocess_data(raw_data)
        
        print("数据预处理完成。")
        print(f"客户数量: {processed_data['num_customers']}")
        print("\n处理后的客户信息 (前5条):")
        print(processed_data["customers_df"].head().to_string())
        
        print(f"\n距离矩阵维度: {processed_data['distance_matrix'].shape}")
        
        print("\n车辆类型信息:")
        for name, info in processed_data["vehicle_types"].items():
            print(f"- {name}: {info}")

    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(f"预处理数据时发生未知错误: {e}")
