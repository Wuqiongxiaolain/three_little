import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 设置支持中文的字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

def plot_routes(solution: dict, data: dict, save_path: str = None, title: str = "车辆配送路径规划图"):
    """
    绘制车辆配送路径图
    """
    customers_df = data['customers_df']
    
    plt.figure(figsize=(10, 10))
    
    # 绘制配送中心
    depot = customers_df[customers_df['ID'] == 0]
    plt.scatter(depot['X (km)'], depot['Y (km)'], c='red', marker='s', s=200, label='配送中心', zorder=5)
    
    # 绘制客户点
    customers = customers_df[customers_df['ID'] != 0]
    plt.scatter(customers['X (km)'], customers['Y (km)'], c='blue', s=30, label='客户点', zorder=4)
    
    # 绘制绿色配送区
    center_circle = plt.Circle((0, 0), 10, color='green', alpha=0.2, label='绿色配送区')
    plt.gca().add_artist(center_circle)
    
    # 绘制路径
    colors = plt.cm.tab10(np.linspace(0, 1, 10))
    
    for v_idx, route in solution['routes'].items():
        if len(route) <= 2:
            continue
        
        c = colors[v_idx % 10]
        x_coords = []
        y_coords = []
        
        for node in route:
            node_row = customers_df[customers_df['ID'] == node].iloc[0]
            x_coords.append(node_row['X (km)'])
            y_coords.append(node_row['Y (km)'])
            
        plt.plot(x_coords, y_coords, c=c, linewidth=1.5, alpha=0.7)
        
    plt.title(title, fontsize=16)
    plt.xlabel('X (km)', fontsize=12)
    plt.ylabel('Y (km)', fontsize=12)
    plt.legend(loc='upper right')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.axis('equal')
    
    if save_path:
        import os
        import os.path as osp
        os.makedirs(osp.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()

def plot_cost_breakdown(costs: dict, save_path: str = None, title: str = "成本构成饼形图"):
    """
    绘制成本构成饼形图
    """
    labels = ['固定成本', '能耗成本', '碳排放成本', '时间窗惩罚']
    sizes = [costs['fixed_cost'], costs['travel_cost'], costs['emission_cost'], costs['penalty_cost']]
    colors = ['#ff9999','#66b3ff','#99ff99','#ffcc99']
    
    plt.figure(figsize=(8, 8))
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    plt.axis('equal')
    plt.title(title, fontsize=16)
    
    if save_path:
        import os
        import os.path as osp
        os.makedirs(osp.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()
