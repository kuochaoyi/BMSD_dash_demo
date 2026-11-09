"""D3.js 視覺化分析分頁的資料聚合、交叉篩選與客戶端渲染回呼。"""

from collections import Counter
from typing import Any

import pandas as pd
from dash import ClientsideFunction, Input, Output, ctx, html

from ..config import CUISINE_LABELS
from ..data import RESTAURANTS


def _apply_base_filters(
    df: pd.DataFrame,
    keyword: str | None,
    status: str | None,
    extras: list[str] | None,
) -> pd.DataFrame:
    """套用關鍵字、營業狀態與資料完整度等基礎篩選條件。"""
    filtered = df
    if keyword and keyword.strip():
        filtered = filtered[
            filtered["search_text"].str.contains(
                keyword.strip().lower(), regex=False, na=False
            )
        ]
    if status:
        filtered = filtered[filtered["status"] == status]

    selected_extras = extras or []
    if "has_hours" in selected_extras:
        filtered = filtered[filtered["service_time"].str.strip().ne("")]
    if "has_website" in selected_extras:
        filtered = filtered[filtered["website"].str.strip().ne("")]
    return filtered


def _build_city_ranking(
    df: pd.DataFrame,
    selected_city: str | None,
    ranking_mode: str,
    ranking_sort: str,
) -> tuple[list[dict[str, Any]], float]:
    """計算各縣市餐廳數量、佔比、營業率與前三大菜色，供 D3 長條圖渲染。"""
    if df.empty:
        return [], 0.0

    total_restaurants = len(df)
    records: list[dict[str, Any]] = []

    for city, group in df.groupby("city", sort=False):
        count = len(group)
        open_count = int((group["status"] == "營業中").sum())
        hours_count = int(group["service_time"].str.strip().ne("").sum())
        open_rate = round(open_count / count * 100, 1) if count else 0.0
        hours_rate = round(hours_count / count * 100, 1) if count else 0.0
        share = round(count / total_restaurants * 100, 1) if total_restaurants else 0.0

        cuisine_counter = Counter(
            code for codes in group["cuisine_codes"] for code in codes
        )
        top_cuisines = [
            {
                "code": int(code),
                "label": CUISINE_LABELS.get(code, f"其他類型（代碼 {code}）"),
                "count": int(c_count),
            }
            for code, c_count in cuisine_counter.most_common(3)
        ]

        records.append(
            {
                "city": str(city),
                "count": int(count),
                "share": share,
                "open_count": open_count,
                "open_rate": open_rate,
                "hours_rate": hours_rate,
                "top_cuisines": top_cuisines,
                "is_selected": bool(selected_city and city == selected_city),
            }
        )

    avg_count = round(total_restaurants / max(len(records), 1), 1)

    if ranking_sort == "open_rate":
        records.sort(key=lambda item: (item["open_rate"], item["count"]), reverse=True)
    else:
        records.sort(key=lambda item: (item["count"], item["open_rate"]), reverse=True)

    if ranking_mode == "top10":
        top_slice = records[:10]
        if selected_city and all(r["city"] != selected_city for r in top_slice):
            selected_match = [r for r in records if r["city"] == selected_city]
            if selected_match:
                top_slice = top_slice[:9] + selected_match
        records = top_slice

    return records, avg_count


def _build_cuisine_distribution(
    df: pd.DataFrame,
    selected_cuisine: int | None,
    max_donut_slices: int = 9,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    """計算菜色分類比例、各菜色熱門縣市與環形圖分組資料。"""
    if df.empty:
        return [], [], 0

    total_restaurants = len(df)
    code_counter: Counter[int] = Counter()
    city_by_code: dict[int, Counter[str]] = {}
    open_by_code: Counter[int] = Counter()

    for _, row in df.iterrows():
        codes = row["cuisine_codes"] or []
        city = str(row["city"])
        is_open = row["status"] == "營業中"
        for code in set(codes):
            code_int = int(code)
            code_counter[code_int] += 1
            if code_int not in city_by_code:
                city_by_code[code_int] = Counter()
            city_by_code[code_int][city] += 1
            if is_open:
                open_by_code[code_int] += 1

    total_tags = sum(code_counter.values())
    if not total_tags:
        return [], [], 0

    full_list: list[dict[str, Any]] = []
    for code, count in code_counter.most_common():
        label = CUISINE_LABELS.get(code, f"其他類型（代碼 {code}）")
        share_tags = round(count / total_tags * 100, 1)
        share_restaurants = (
            round(count / total_restaurants * 100, 1) if total_restaurants else 0.0
        )
        open_rate = round(open_by_code[code] / count * 100, 1) if count else 0.0
        top_cities = [
            {"city": c_name, "count": int(c_count)}
            for c_name, c_count in city_by_code[code].most_common(3)
        ]
        full_list.append(
            {
                "code": int(code),
                "label": label,
                "count": int(count),
                "share": share_tags,
                "restaurant_share": share_restaurants,
                "open_rate": open_rate,
                "top_cities": top_cities,
                "is_selected": bool(
                    selected_cuisine is not None and int(code) == int(selected_cuisine)
                ),
            }
        )

    if len(full_list) <= max_donut_slices + 1:
        donut_slices = [dict(item, is_other_group=False) for item in full_list]
    else:
        head = [dict(item, is_other_group=False) for item in full_list[:max_donut_slices]]
        tail = full_list[max_donut_slices:]
        # 若使用者選取的菜色位於長尾區間，將其保留在環形圖扇區中以便高亮顯示
        if selected_cuisine is not None:
            selected_in_tail = [
                item for item in tail if int(item["code"]) == int(selected_cuisine)
            ]
            if selected_in_tail:
                head = head[: max_donut_slices - 1] + [
                    dict(selected_in_tail[0], is_other_group=False)
                ]
                tail = [
                    item
                    for item in full_list
                    if item["code"] not in {h["code"] for h in head}
                ]

        other_count = sum(item["count"] for item in tail)
        other_share = round(other_count / total_tags * 100, 1)
        donut_slices = head + [
            {
                "code": -1,
                "label": f"其他菜色（共 {len(tail)} 類）",
                "count": int(other_count),
                "share": other_share,
                "restaurant_share": round(
                    other_count / max(total_restaurants, 1) * 100, 1
                ),
                "open_rate": round(
                    sum(item["count"] * item["open_rate"] for item in tail)
                    / max(other_count, 1),
                    1,
                ),
                "top_cities": [],
                "is_selected": False,
                "is_other_group": True,
                "grouped_count": len(tail),
            }
        ]

    return full_list, donut_slices, total_tags


def reset_d3_filters(_reset_clicks: int):
    """一鍵重設 D3 視覺化分析分頁的所有篩選與交叉選取狀態。"""
    return "", None, None, None, [], "all", "count"


def clear_single_filter(
    _clear_city_clicks: int,
    _clear_cuisine_clicks: int,
):
    """由互動篩選膠囊單獨移除縣市或菜色鎖定條件。"""
    triggered = ctx.triggered_id
    if triggered == "d3-clear-city-pill":
        return None, ctx. no_update if hasattr(ctx, "no_update") else None
    return None, None


def update_d3_analytics(
    keyword: str | None,
    selected_city: str | None,
    selected_cuisine: int | None,
    status: str | None,
    extras: list[str] | None,
    ranking_mode: str | None,
    ranking_sort: str | None,
):
    """計算 D3 圖表所需的結構化資料、頂部指標卡與篩選狀態膠囊。"""
    mode = ranking_mode or "all"
    sort_by = ranking_sort or "count"

    base_df = _apply_base_filters(RESTAURANTS, keyword, status, extras)

    # 左側「縣市排行榜」套用菜色篩選，保留全部縣市並高亮目前選取的縣市
    if selected_cuisine is not None:
        ranking_source_df = base_df[
            base_df["cuisine_codes"].apply(lambda codes: selected_cuisine in (codes or []))
        ]
    else:
        ranking_source_df = base_df

    # 右側「菜色比例」套用縣市篩選，保留該縣市下所有菜色並高亮目前選取的菜色
    if selected_city:
        cuisine_source_df = base_df[base_df["city"] == selected_city]
    else:
        cuisine_source_df = base_df

    # 完全符合目前所有交叉條件的子集（供頂部 KPI 卡計算）
    combined_df = cuisine_source_df
    if selected_cuisine is not None:
        combined_df = combined_df[
            combined_df["cuisine_codes"].apply(
                lambda codes: selected_cuisine in (codes or [])
            )
        ]

    cities_data, avg_city_count = _build_city_ranking(
        ranking_source_df, selected_city, mode, sort_by
    )
    cuisines_data, donut_slices, total_cuisine_tags = _build_cuisine_distribution(
        cuisine_source_df, selected_cuisine
    )

    total_matched = len(combined_df)
    city_count = combined_df["city"].nunique() if total_matched else 0
    open_count = int((combined_df["status"] == "營業中").sum()) if total_matched else 0
    open_ratio = round(open_count / total_matched * 100, 1) if total_matched else 0.0

    # 產生目前交叉篩選狀態提示列
    active_badges: list[Any] = []
    if selected_city:
        active_badges.append(
            html.Span(
                [
                    html.Span("鎖定縣市：", className="d3-pill-prefix"),
                    html.Strong(selected_city),
                ],
                className="d3-filter-pill d3-pill-city",
            )
        )
    if selected_cuisine is not None:
        cuisine_name = CUISINE_LABELS.get(
            int(selected_cuisine), f"代碼 {selected_cuisine}"
        )
        active_badges.append(
            html.Span(
                [
                    html.Span("鎖定菜色：", className="d3-pill-prefix"),
                    html.Strong(cuisine_name),
                ],
                className="d3-filter-pill d3-pill-cuisine",
            )
        )
    if keyword and keyword.strip():
        active_badges.append(
            html.Span(
                [
                    html.Span("關鍵字：", className="d3-pill-prefix"),
                    html.Strong(keyword.strip()),
                ],
                className="d3-filter-pill",
            )
        )
    if status:
        active_badges.append(
            html.Span(
                [
                    html.Span("狀態：", className="d3-pill-prefix"),
                    html.Strong(status),
                ],
                className="d3-filter-pill",
            )
        )

    if not active_badges:
        active_badges = [
            html.Span(
                "💡 互動提示：直接點擊下方 D3 長條圖的「縣市」或環形圖／清單的「菜色類型」，即可雙向交叉篩選資料（再次點擊可取消鎖定）。",
                className="d3-Crossfilter-tip",
            )
        ]

    ranking_subtitle = (
        f"已篩選「{CUISINE_LABELS.get(int(selected_cuisine), '指定菜色')}」｜共 {len(ranking_source_df):,} 家餐廳，平均每縣市 {avg_city_count:,} 家"
        if selected_cuisine is not None
        else f"涵蓋 {ranking_source_df['city'].nunique()} 個縣市、共 {len(ranking_source_df):,} 家餐廳｜平均每縣市 {avg_city_count:,} 家"
    )

    cuisine_subtitle = (
        f"聚焦「{selected_city}」({len(cuisine_source_df):,} 家餐廳)｜共 {total_cuisine_tags:,} 個菜色標記、{len(cuisines_data)} 種分類"
        if selected_city
        else f"全台篩選結果 ({len(cuisine_source_df):,} 家餐廳)｜共 {total_cuisine_tags:,} 個菜色標記、{len(cuisines_data)} 種分類"
    )

    payload = {
        "summary": {
            "total_restaurants": total_matched,
            "city_count": city_count,
            "open_count": open_count,
            "open_ratio": open_ratio,
            "total_cuisine_tags": total_cuisine_tags,
            "unique_cuisines": len(cuisines_data),
            "avg_city_count": avg_city_count,
            "ranking_total": len(ranking_source_df),
            "cuisine_restaurants_total": len(cuisine_source_df),
        },
        "filters": {
            "selected_city": selected_city,
            "selected_cuisine": selected_cuisine,
            "selected_cuisine_label": (
                CUISINE_LABELS.get(int(selected_cuisine), f"代碼 {selected_cuisine}")
                if selected_cuisine is not None
                else None
            ),
            "ranking_mode": mode,
            "ranking_sort": sort_by,
        },
        "cities": cities_data,
        "cuisines": cuisines_data,
        "donut_slices": donut_slices,
    }

    specific_cuisines = [c for c in cuisines_data if c["code"] != 254]
    featured_cuisine = (
        specific_cuisines[0]
        if specific_cuisines
        else (cuisines_data[0] if cuisines_data else None)
    )
    top_cuisine_metric = (
        f"{featured_cuisine['label']} ({featured_cuisine['share']}%)"
        if featured_cuisine
        else "無資料"
    )

    return (
        payload,
        f"{total_matched:,} 家",
        f"{city_count} 個",
        f"{open_ratio}%",
        top_cuisine_metric,
        active_badges,
        ranking_subtitle,
        cuisine_subtitle,
    )


def register_callbacks(app):
    """註冊 D3 視覺化分析分頁的伺服器端與客戶端回呼。"""
    app.callback(
        Output("d3-keyword", "value"),
        Output("d3-city-filter", "value"),
        Output("d3-cuisine-filter", "value"),
        Output("d3-status", "value"),
        Output("d3-extras", "value"),
        Output("d3-ranking-mode", "value"),
        Output("d3-ranking-sort", "value"),
        Input("d3-reset", "n_clicks"),
        prevent_initial_call=True,
    )(reset_d3_filters)

    app.callback(
        Output("d3-data-store", "data"),
        Output("d3-metric-count", "children"),
        Output("d3-metric-cities", "children"),
        Output("d3-metric-open", "children"),
        Output("d3-metric-top-cuisine", "children"),
        Output("d3-active-badges", "children"),
        Output("d3-ranking-subtitle", "children"),
        Output("d3-cuisine-subtitle", "children"),
        Input("d3-keyword", "value"),
        Input("d3-city-filter", "value"),
        Input("d3-cuisine-filter", "value"),
        Input("d3-status", "value"),
        Input("d3-extras", "value"),
        Input("d3-ranking-mode", "value"),
        Input("d3-ranking-sort", "value"),
    )(update_d3_analytics)

    # 當 D3 資料 Store 更新或使用者切換至 D3 分頁時，在瀏覽器端透過 D3.js 繪製並執行平滑動畫
    app.clientside_callback(
        ClientsideFunction(
            namespace="d3Charts",
            function_name="renderAll",
        ),
        Output("d3-render-status", "data"),
        Input("d3-data-store", "data"),
        Input("view-tabs", "value"),
    )
