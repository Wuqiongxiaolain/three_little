"""
数据加载模块
负责从 /data/附件/ 目录中读取所有原始 Excel 文件，并返回 Pandas DataFrame。
"""
import pandas as pd
from pathlib import Path

def load_all_data(base_path: Path) -> dict[str, pd.DataFrame]:
    """
    加载所有 Excel 数据文件。

    Args:
        base_path (Path): '附件' 文件夹的路径。

    Returns:
        dict[str, pd.DataFrame]: 一个字典，键是文件名（不含扩展名），值是对应的 DataFrame。
    """
    file_paths = {
        "customer_info": base_path / "客户坐标信息.xlsx",
        "time_windows": base_path / "时间窗.xlsx",
        "orders": base_path / "订单信息.xlsx",
        "distance_matrix": base_path / "距离矩阵.xlsx",
    }

    data_frames = {}
    for name, path in file_paths.items():
        if not path.exists():
            raise FileNotFoundError(f"数据文件未找到: {path}")
        # 距离矩阵的第一列是索引
        if name == "distance_matrix":
            data_frames[name] = pd.read_excel(path, index_col=0)
        else:
            data_frames[name] = pd.read_excel(path)
    
    return data_frames

if __name__ == '__main__':
    # 测试加载功能
    try:
        project_root = Path(__file__).resolve().parents[2]
        data_path = project_root / "data" / "附件"
        
        all_data = load_all_data(data_path)
        
        print("成功加载以下数据文件:")
        for name, df in all_data.items():
            print(f"- {name}: shape={df.shape}")
            print(df.head(2).to_string())
            print("-" * 30)

    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(f"加载数据时发生未知错误: {e}")
