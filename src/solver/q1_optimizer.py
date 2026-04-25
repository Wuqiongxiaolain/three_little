"""
问题一求解器：静态环境下的混合车队配送优化（启发式）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import math
import pandas as pd

from src.utils.cost_utils import (
    FIXED_COST_PER_VEHICLE,
    calculate_energy_cost,
    calculate_total_cost,
    calculate_time_window_penalty,
    get_travel_speed,
)


@dataclass
class DeliveryTask:
    task_id: int
    customer_id: int
    weight: float
    volume: float
    tw_start: float
    tw_end: float
    service_h: float


def _build_tasks(customers_df: pd.DataFrame, vehicle_types: dict) -> List[DeliveryTask]:
    max_w = max(v["capacity_w"] for v in vehicle_types.values())
    max_v = max(v["capacity_v"] for v in vehicle_types.values())

    tasks: List[DeliveryTask] = []
    task_id = 1

    for _, row in customers_df.iterrows():
        cid = int(row["ID"])
        if cid == 0:
            continue

        total_w = float(row["total_weight"])
        total_v = float(row["total_volume"])
        if total_w <= 0 and total_v <= 0:
            continue
        tw_start = float(row["start_time_h"])
        tw_end = float(row["end_time_h"])
        service_h = float(row["s_i"])

        parts = max(1, math.ceil(total_w / max_w), math.ceil(total_v / max_v))
        base_w = total_w / parts
        base_v = total_v / parts

        for _ in range(parts):
            tasks.append(
                DeliveryTask(
                    task_id=task_id,
                    customer_id=cid,
                    weight=base_w,
                    volume=base_v,
                    tw_start=tw_start,
                    tw_end=tw_end,
                    service_h=service_h,
                )
            )
            task_id += 1

    return tasks


def _task_distance(t1: DeliveryTask, t2: DeliveryTask, dist_matrix) -> float:
    return float(dist_matrix[t1.customer_id, t2.customer_id])


def _depot_distance(t: DeliveryTask, dist_matrix) -> float:
    return float(dist_matrix[0, t.customer_id])


def _try_merge(route_a: List[int], route_b: List[int], a_tid: int, b_tid: int) -> List[int] | None:
    # 只允许端点拼接，必要时翻转路径以匹配 a 在末端、b 在开头。
    ra = route_a
    rb = route_b

    if ra[0] == a_tid:
        ra = list(reversed(ra))
    if rb[-1] == b_tid:
        rb = list(reversed(rb))

    if ra[-1] != a_tid or rb[0] != b_tid:
        return None

    merged = ra + rb
    return merged


def _route_demand(route: List[int], task_map: Dict[int, DeliveryTask]) -> Tuple[float, float]:
    w = sum(task_map[tid].weight for tid in route)
    v = sum(task_map[tid].volume for tid in route)
    return w, v


def _build_routes_by_savings(tasks: List[DeliveryTask], dist_matrix, vehicle_types: dict) -> List[List[int]]:
    if not tasks:
        return []

    max_w = max(v["capacity_w"] for v in vehicle_types.values())
    max_v = max(v["capacity_v"] for v in vehicle_types.values())

    task_map = {t.task_id: t for t in tasks}
    route_of_task = {t.task_id: t.task_id for t in tasks}
    routes: Dict[int, List[int]] = {t.task_id: [t.task_id] for t in tasks}

    savings: List[Tuple[float, int, int]] = []
    for i in range(len(tasks)):
        ti = tasks[i]
        for j in range(i + 1, len(tasks)):
            tj = tasks[j]
            s = _depot_distance(ti, dist_matrix) + _depot_distance(tj, dist_matrix) - _task_distance(ti, tj, dist_matrix)
            savings.append((s, ti.task_id, tj.task_id))

    savings.sort(key=lambda x: x[0], reverse=True)

    for _, tid_i, tid_j in savings:
        rid_i = route_of_task[tid_i]
        rid_j = route_of_task[tid_j]
        if rid_i == rid_j:
            continue

        route_i = routes[rid_i]
        route_j = routes[rid_j]
        merged = _try_merge(route_i, route_j, tid_i, tid_j)
        if merged is None:
            merged = _try_merge(route_j, route_i, tid_j, tid_i)
        if merged is None:
            continue

        total_w, total_v = _route_demand(merged, task_map)
        if total_w > max_w or total_v > max_v:
            continue

        new_rid = min(rid_i, rid_j)
        old_rid = max(rid_i, rid_j)
        routes[new_rid] = merged
        del routes[old_rid]

        for tid in merged:
            route_of_task[tid] = new_rid

    return list(routes.values())


def _route_distance(route: List[int], task_map: Dict[int, DeliveryTask], dist_matrix) -> float:
    if not route:
        return 0.0
    dist = float(dist_matrix[0, task_map[route[0]].customer_id])
    for i in range(len(route) - 1):
        c1 = task_map[route[i]].customer_id
        c2 = task_map[route[i + 1]].customer_id
        dist += float(dist_matrix[c1, c2])
    dist += float(dist_matrix[task_map[route[-1]].customer_id, 0])
    return dist


def _two_opt_route(route: List[int], task_map: Dict[int, DeliveryTask], dist_matrix) -> List[int]:
    if len(route) < 4:
        return route

    best = route[:]
    best_cost = _route_distance(best, task_map, dist_matrix)
    improved = True

    while improved:
        improved = False
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best) - 1):
                candidate = best[:i] + list(reversed(best[i:j + 1])) + best[j + 1:]
                cand_cost = _route_distance(candidate, task_map, dist_matrix)
                if cand_cost + 1e-9 < best_cost:
                    best = candidate
                    best_cost = cand_cost
                    improved = True

    return best


def _simulate_route(
    route: List[int],
    task_map: Dict[int, DeliveryTask],
    dist_matrix,
    vehicle_type_info: dict,
    start_time_h: float = 8.0,
):
    v_type = vehicle_type_info["type"]
    cap_w = float(vehicle_type_info["capacity_w"])

    customer_route = [0]
    arrivals = [start_time_h]
    delivered_w = [0.0]
    delivered_v = [0.0]

    current_time = start_time_h
    current_load_w = sum(task_map[tid].weight for tid in route)
    prev_customer = 0

    travel_cost = 0.0
    emission_cost = 0.0
    penalty_cost = 0.0

    for tid in route:
        task = task_map[tid]
        dist = float(dist_matrix[prev_customer, task.customer_id])
        speed = get_travel_speed(current_time)
        travel_t = dist / speed if speed > 0 else 0.0
        arrival = current_time + travel_t

        load_ratio = current_load_w / cap_w if cap_w > 0 else 0.0
        ecost, ccost = calculate_energy_cost(v_type, speed, dist, load_ratio)
        travel_cost += ecost
        emission_cost += ccost
        penalty_cost += calculate_time_window_penalty(arrival, task.tw_start, task.tw_end)

        service_begin = max(arrival, task.tw_start)
        current_time = service_begin + task.service_h

        customer_route.append(task.customer_id)
        arrivals.append(arrival)
        delivered_w.append(task.weight)
        delivered_v.append(task.volume)

        current_load_w -= task.weight
        prev_customer = task.customer_id

    # 返回配送中心
    dist_back = float(dist_matrix[prev_customer, 0])
    speed_back = get_travel_speed(current_time)
    travel_back_t = dist_back / speed_back if speed_back > 0 else 0.0
    arrival_back = current_time + travel_back_t
    load_ratio_back = current_load_w / cap_w if cap_w > 0 else 0.0
    ecost_back, ccost_back = calculate_energy_cost(v_type, speed_back, dist_back, load_ratio_back)

    travel_cost += ecost_back
    emission_cost += ccost_back

    customer_route.append(0)
    arrivals.append(arrival_back)
    delivered_w.append(0.0)
    delivered_v.append(0.0)

    return {
        "customer_route": customer_route,
        "arrivals": arrivals,
        "delivered_w": delivered_w,
        "delivered_v": delivered_v,
        "travel_cost": travel_cost,
        "emission_cost": emission_cost,
        "penalty_cost": penalty_cost,
        "distance": _route_distance(route, task_map, dist_matrix),
        "end_time": arrival_back,
    }


def _assign_vehicles(routes: List[List[int]], tasks: List[DeliveryTask], data: dict, start_time_h: float = 8.0):
    task_map = {t.task_id: t for t in tasks}
    dist_matrix = data["distance_matrix"]
    vehicle_types = data["vehicle_types"]

    available = {k: int(v["count"]) for k, v in vehicle_types.items()}

    # 先处理长路径，优先分配车辆，降低可用数量冲突。
    routes_sorted = sorted(routes, key=lambda r: _route_distance(r, task_map, dist_matrix), reverse=True)

    chosen: List[dict] = []
    for r in routes_sorted:
        route_w = sum(task_map[tid].weight for tid in r)
        route_v = sum(task_map[tid].volume for tid in r)

        candidates = []
        for v_name, info in vehicle_types.items():
            if available[v_name] <= 0:
                continue
            if route_w <= info["capacity_w"] and route_v <= info["capacity_v"]:
                sim = _simulate_route(r, task_map, dist_matrix, info, start_time_h)
                total = FIXED_COST_PER_VEHICLE + sim["travel_cost"] + sim["emission_cost"] + sim["penalty_cost"]
                candidates.append((total, v_name, sim))

        if not candidates:
            # 兜底：忽略数量上限，至少选一个可承载车型，确保解可构造。
            for v_name, info in vehicle_types.items():
                if route_w <= info["capacity_w"] and route_v <= info["capacity_v"]:
                    sim = _simulate_route(r, task_map, dist_matrix, info, start_time_h)
                    total = FIXED_COST_PER_VEHICLE + sim["travel_cost"] + sim["emission_cost"] + sim["penalty_cost"]
                    candidates.append((total, v_name, sim))

        if not candidates:
            raise RuntimeError("存在无法由任何车型承载的路径，请检查需求拆分逻辑。")

        candidates.sort(key=lambda x: x[0])
        _, best_v, best_sim = candidates[0]
        if available.get(best_v, 0) > 0:
            available[best_v] -= 1

        chosen.append(
            {
                "raw_route": r,
                "vehicle_type": best_v,
                "sim": best_sim,
                "route_weight": route_w,
                "route_volume": route_v,
            }
        )

    return chosen


def _export_dispatch_files(solution: dict, costs: dict, data: dict, output_dir: str):
    customers_df = data["customers_df"].set_index("ID")

    route_rows = []
    stop_rows = []

    for vid, route in solution["routes"].items():
        arrivals = solution["arrivals"][vid]
        delivered_w = solution["delivery_weight_map"][vid]
        delivered_v = solution["delivery_volume_map"][vid]
        vname = solution["vehicle_map"][vid]

        route_weight = float(sum(delivered_w[1:-1]))
        route_volume = float(sum(delivered_v[1:-1]))
        distance = 0.0
        for i in range(len(route) - 1):
            distance += float(data["distance_matrix"][route[i], route[i + 1]])

        route_rows.append(
            {
                "vehicle_id": vid,
                "vehicle_type": vname,
                "stops": len(route) - 2,
                "route_weight": round(route_weight, 4),
                "route_volume": round(route_volume, 4),
                "route_distance_km": round(distance, 4),
                "start_time_h": round(arrivals[0], 4),
                "end_time_h": round(arrivals[-1], 4),
                "route_nodes": "->".join(str(x) for x in route),
            }
        )

        for idx in range(1, len(route) - 1):
            cid = route[idx]
            arr = arrivals[idx]
            tw_start = float(customers_df.loc[cid, "start_time_h"])
            tw_end = float(customers_df.loc[cid, "end_time_h"])
            stop_rows.append(
                {
                    "vehicle_id": vid,
                    "vehicle_type": vname,
                    "stop_seq": idx,
                    "customer_id": cid,
                    "arrival_h": round(arr, 4),
                    "tw_start_h": round(tw_start, 4),
                    "tw_end_h": round(tw_end, 4),
                    "delivered_weight": round(float(delivered_w[idx]), 4),
                    "delivered_volume": round(float(delivered_v[idx]), 4),
                    "penalty": round(calculate_time_window_penalty(arr, tw_start, tw_end), 4),
                }
            )

    route_df = pd.DataFrame(route_rows).sort_values("vehicle_id")
    stop_df = pd.DataFrame(stop_rows).sort_values(["vehicle_id", "stop_seq"])

    cost_df = pd.DataFrame(
        [
            {
                "total_cost": costs["total_cost"],
                "fixed_cost": costs["fixed_cost"],
                "travel_cost": costs["travel_cost"],
                "emission_cost": costs["emission_cost"],
                "penalty_cost": costs["penalty_cost"],
                "route_count": len(solution["routes"]),
                "served_stop_count": int((stop_df.shape[0])),
            }
        ]
    )

    vehicle_stat_df = route_df.groupby("vehicle_type", as_index=False).agg(
        vehicles_used=("vehicle_id", "count"),
        total_weight=("route_weight", "sum"),
        total_distance_km=("route_distance_km", "sum"),
    )

    import os

    routes_dir = os.path.join(output_dir, "routes")
    tables_dir = os.path.join(output_dir, "tables")
    os.makedirs(routes_dir, exist_ok=True)
    os.makedirs(tables_dir, exist_ok=True)

    route_xlsx = os.path.join(routes_dir, "q1_dispatch_plan.xlsx")
    with pd.ExcelWriter(route_xlsx, engine="openpyxl") as writer:
        route_df.to_excel(writer, index=False, sheet_name="route_summary")
        stop_df.to_excel(writer, index=False, sheet_name="stop_details")

    route_df.to_csv(os.path.join(routes_dir, "q1_route_summary.csv"), index=False, encoding="utf-8-sig")
    stop_df.to_csv(os.path.join(routes_dir, "q1_stop_details.csv"), index=False, encoding="utf-8-sig")

    table_xlsx = os.path.join(tables_dir, "q1_result_tables.xlsx")
    with pd.ExcelWriter(table_xlsx, engine="openpyxl") as writer:
        cost_df.to_excel(writer, index=False, sheet_name="cost_summary")
        vehicle_stat_df.to_excel(writer, index=False, sheet_name="vehicle_summary")

    cost_df.to_csv(os.path.join(tables_dir, "q1_cost_summary.csv"), index=False, encoding="utf-8-sig")
    vehicle_stat_df.to_csv(os.path.join(tables_dir, "q1_vehicle_summary.csv"), index=False, encoding="utf-8-sig")


def optimize_question1(data: dict, output_dir: str, start_time_h: float = 8.0):
    customers_df = data["customers_df"]
    tasks = _build_tasks(customers_df, data["vehicle_types"])
    task_map = {t.task_id: t for t in tasks}

    routes = _build_routes_by_savings(tasks, data["distance_matrix"], data["vehicle_types"])
    routes = [_two_opt_route(r, task_map, data["distance_matrix"]) for r in routes]

    assigned = _assign_vehicles(routes, tasks, data, start_time_h=start_time_h)

    solution = {
        "routes": {},
        "arrivals": {},
        "vehicle_map": {},
        "delivery_weight_map": {},
        "delivery_volume_map": {},
    }

    for vid, info in enumerate(assigned):
        sim = info["sim"]
        solution["routes"][vid] = sim["customer_route"]
        solution["arrivals"][vid] = sim["arrivals"]
        solution["vehicle_map"][vid] = info["vehicle_type"]
        solution["delivery_weight_map"][vid] = sim["delivered_w"]
        solution["delivery_volume_map"][vid] = sim["delivered_v"]

    costs = calculate_total_cost(solution, data)
    _export_dispatch_files(solution, costs, data, output_dir)

    meta = {
        "task_count": len(tasks),
        "route_count": len(solution["routes"]),
    }
    return solution, costs, meta
