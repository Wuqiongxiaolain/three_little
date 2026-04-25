"""
主程序入口
"""
from pathlib import Path
from src.data.loader import load_all_data
from src.data.preprocess import preprocess_data
from src.solver.q1_optimizer import optimize_question1
from src.visualization.route_plot import plot_routes, plot_cost_breakdown

def main():
    """
    主函数，执行整个VRP求解流程。
    """
    try:
        # 1. 加载和预处理数据
        print("--- 1. 加载和预处理数据 ---")
        project_root = Path(__file__).resolve().parent
        data_path = project_root / "data" / "附件"
        
        raw_data = load_all_data(data_path)
        processed_data = preprocess_data(raw_data)
        print("数据加载和预处理完成。\n")

        # 2. 问题1：静态环境下的车辆调度
        print("--- 2. 求解问题1：静态VRP优化 ---")
        print("执行需求拆分、节约算法构造、2-opt路径优化、车辆类型分配与到达时刻计算...")
        solution_q1, costs_q1, meta_q1 = optimize_question1(
            processed_data,
            output_dir=str(project_root / "results"),
            start_time_h=8.0,
        )
        
        print("问题1 - 成本分析:")
        for cost_name, value in costs_q1.items():
            print(f"- {cost_name}: {value:.2f}")
        print(f"- 路径数量: {meta_q1['route_count']}")
        print(f"- 配送任务数(含拆分): {meta_q1['task_count']}")
        print("问题1调度表已输出到 results/routes 和 results/tables。")
            
        # 可视化
        print("\n生成问题1的路径图和成本构成饼图...")
        plot_routes(solution_q1, processed_data, str(project_root / "results/figures/q1_routes.png"))
        plot_cost_breakdown(costs_q1, str(project_root / "results/figures/q1_costs.png"))
        print("图表已成功保存。")

        # 3. 问题2：环保政策影响
        print("\n--- 3. 求解问题2：带政策约束的VRP ---")
        print("问题2将在问题1可行解基础上叠加绿色配送区约束。")

        # 4. 问题3：动态事件响应
        print("\n--- 4. 求解问题3：动态VRP ---")
        print("问题3将在问题1可行解基础上实现事件驱动重调度。")

    except FileNotFoundError as e:
        print(f"错误: {e}")
    except Exception as e:
        print(f"发生未知错误: {e}")

if __name__ == '__main__':
    main()
