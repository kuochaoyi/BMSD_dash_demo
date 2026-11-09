"""建立三個分頁及其搜尋控制項、圖表容器與狀態儲存元件。"""

from dash import dcc, html

from .components import app_dropdown, metric_card
from .data import CITY_OPTIONS, CUISINE_OPTIONS, DATA_UPDATE_TIME, PLANNER_DEFAULT_CITY
from .time_utils import format_update_time


def build_layout():
    """產生完整 Dash 頁面配置。"""
    return html.Div(
        [
            html.Header(
                [
                    html.Div(
                        [
                            html.P("RESTAURANT DATA DEMO", className="eyebrow"),
                            html.H1("台灣餐廳資料探索"),
                            html.P("用排行榜、地圖與複合條件快速瀏覽專案資料集。", className="subtitle"),
                        ]
                    ),
                    html.Div(
                        [
                            html.Span("資料更新時間"),
                            html.Strong(format_update_time(DATA_UPDATE_TIME)),
                        ],
                        className="data-time",
                    ),
                ],
                className="page-header",
            ),
            html.Main(
                [
                    # 以分頁切換資料總覽與單店探索，兩區內容會保留在頁面中，
                    # 因此切換時不需要重新載入資料或重建圖表元件。
                    dcc.Tabs(
                        id="view-tabs",
                        value="overview",
                        children=[
                            dcc.Tab(label="資料總覽", value="overview"),
                            dcc.Tab(label="店家探索", value="explorer"),
                            dcc.Tab(label="餐廳規劃", value="planner"),
                            dcc.Tab(label="D3 視覺化分析", value="d3-analytics"),
                        ],
                        className="view-tabs",
                    ),
                    # 暫存第三頁選取的店家，供第二頁載入對應縣市與詳細資料。
                    dcc.Store(id="navigate-restaurant-store"),
                    html.Div(
                        [
                    html.Section(
                        [
                            html.Div(
                                [
                                    html.Label("關鍵字", htmlFor="keyword"),
                                    dcc.Input(
                                        id="keyword",
                                        type="search",
                                        placeholder="搜尋店名、地址或簡介",
                                        debounce=True,
                                    ),
                                ],
                                className="field field-wide",
                            ),
                            html.Div(
                                [
                                    html.Label("縣市", htmlFor="city"),
                                    app_dropdown(
                                        "city",
                                        options=[{"label": city, "value": city} for city in CITY_OPTIONS],
                                        placeholder="全部縣市",
                                        clearable=True,
                                        search_placeholder="搜尋縣市名稱...",
                                    ),
                                ],
                                className="field",
                            ),
                            html.Div(
                                [
                                    html.Label("營業狀態", htmlFor="status"),
                                    app_dropdown(
                                        "status",
                                        options=[
                                            {"label": "營業中", "value": "營業中"},
                                            {"label": "非營業中", "value": "非營業中"},
                                        ],
                                        placeholder="全部狀態",
                                        clearable=True,
                                        searchable=False,
                                    ),
                                ],
                                className="field",
                            ),
                            html.Div(
                                [
                                    html.Label("資料條件"),
                                    dcc.Checklist(
                                        id="extras",
                                        options=[
                                            {"label": "有營業時間", "value": "has_hours"},
                                            {"label": "有官方網站", "value": "has_website"},
                                        ],
                                        value=[],
                                        className="check-list",
                                    ),
                                ],
                                className="field extras-field",
                            ),
                            html.Button("清除條件", id="reset", n_clicks=0, className="reset-button"),
                        ],
                        className="filter-panel",
                        **{"aria-label": "餐廳搜尋條件"},
                    ),
                    html.Section(
                        [
                            metric_card("符合條件", "metric-count"),
                            metric_card("涵蓋縣市", "metric-cities"),
                            metric_card("有營業時間", "metric-hours"),
                        ],
                        className="metric-grid",
                        **{"aria-label": "搜尋摘要"},
                    ),
                    html.Section(
                        [
                            html.Article(
                                [
                                    html.Div(
                                        [html.H2("縣市餐廳數量排行榜"), html.P("依目前搜尋條件即時重新計算")],
                                        className="section-heading",
                                    ),
                                    dcc.Loading(dcc.Graph(id="ranking", config={"displayModeBar": False})),
                                ],
                                className="panel ranking-panel",
                            ),
                            html.Article(
                                [
                                    html.Div(
                                        [
                                            html.H2("菜色類型比例"),
                                            html.P("依目前搜尋結果的分類標記統計"),
                                        ],
                                        className="section-heading",
                                    ),
                                    dcc.Loading(
                                        dcc.Graph(
                                            id="overview-cuisine-pie",
                                            config={"displayModeBar": False},
                                        )
                                    ),
                                ],
                                className="panel overview-pie-panel",
                            ),
                            html.Article(
                                [
                                    html.Div(
                                        [html.H2("台灣餐廳分布地圖"), html.P("滑過標記可查看店家資訊")],
                                        className="section-heading",
                                    ),
                                    dcc.Loading(dcc.Graph(id="restaurant-map", config={"displayModeBar": False})),
                                ],
                                className="panel map-panel overview-map-panel",
                            ),
                        ],
                        className="visual-grid",
                    ),
                    html.Section(
                        [
                            html.Div(
                                [
                                    html.Div([html.H2("搜尋結果"), html.P(id="result-summary")]),
                                    html.Div(
                                        [
                                            html.Button("上一頁", id="previous-page", n_clicks=0),
                                            html.Span(id="page-indicator"),
                                            html.Button("下一頁", id="next-page", n_clicks=0),
                                        ],
                                        className="pagination",
                                    ),
                                ],
                                className="section-heading result-heading",
                            ),
                            dcc.Store(id="current-page", data=1),
                            html.Div(id="result-list", className="result-list"),
                        ],
                        className="panel results-panel",
                    ),
                        ],
                        id="overview-tab-content",
                    ),
                    html.Div(
                        [
                            html.Section(
                                [
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Label("縣市", htmlFor="explorer-city"),
                                                    app_dropdown(
                                                        "explorer-city",
                                                        options=[
                                                            {"label": city, "value": city}
                                                            for city in CITY_OPTIONS
                                                        ],
                                                        placeholder="全部縣市",
                                                        clearable=True,
                                                        search_placeholder="搜尋縣市名稱...",
                                                    ),
                                                ],
                                                className="field",
                                            ),
                                            html.Div(
                                                [
                                                    html.Label("店名／簡介關鍵字", htmlFor="explorer-keyword"),
                                                    dcc.Input(
                                                        id="explorer-keyword",
                                                        type="search",
                                                        placeholder="例如：客家、海鮮、景觀",
                                                        debounce=True,
                                                        className="text-input",
                                                    ),
                                                ],
                                                className="field",
                                            ),
                                            html.Div(
                                                [
                                                    html.Label("菜色類型（可複選）", htmlFor="explorer-cuisines"),
                                                    app_dropdown(
                                                        "explorer-cuisines",
                                                        options=CUISINE_OPTIONS,
                                                        value=[],
                                                        placeholder="全部類型",
                                                        multi=True,
                                                        clearable=True,
                                                        search_placeholder="搜尋菜色類型...",
                                                    ),
                                                ],
                                                className="field",
                                            ),
                                            html.Div(
                                                [
                                                    html.Label("選擇店家", htmlFor="restaurant-picker"),
                                                    app_dropdown(
                                                        "restaurant-picker",
                                                        options=[],
                                                        value=None,
                                                        placeholder="請先使用搜尋條件",
                                                        clearable=False,
                                                        searchable=True,
                                                        disabled=True,
                                                        search_placeholder="搜尋店名或地區...",
                                                    ),
                                                ],
                                                className="field",
                                            ),
                                            html.P(
                                                [
                                                    "設定縣市、關鍵字或菜色類型後，才會載入符合條件的店家資料。",
                                                    html.Br(),
                                                    "當前並未進行任何篩選，請使用者透過上方欄位搜尋即可開始瀏覽店家。",
                                                ],
                                                id="explorer-search-hint",
                                                className="picker-hint",
                                            ),
                                            html.Div(
                                                [
                                                    html.Strong("查不到符合條件的店家"),
                                                    html.P("請調整縣市、關鍵字或菜色類型後再試一次。"),
                                                ],
                                                id="explorer-no-results",
                                                className="explorer-no-results",
                                                style={"display": "none"},
                                            ),
                                        ],
                                        className="explorer-picker",
                                    )
                                ],
                                className="panel explorer-toolbar",
                            ),
                            html.Section(
                                [
                                    html.Article(
                                        [
                                            dcc.Loading(
                                                html.Div(id="restaurant-detail"),
                                                type="circle",
                                            )
                                        ],
                                        className="panel detail-panel",
                                    ),
                                    html.Article(
                                        [
                                            html.Div(
                                                [html.H2("店家位置"), html.P("地圖已聚焦至目前選定的店家")],
                                                className="section-heading",
                                            ),
                                            dcc.Loading(
                                                dcc.Graph(
                                                    id="detail-map",
                                                    config={"displayModeBar": False},
                                                )
                                            ),
                                        ],
                                        className="panel detail-map-panel",
                                    ),
                                ],
                                className="explorer-grid",
                                id="explorer-details",
                                style={"display": "none"},
                            ),
                        ],
                        id="explorer-tab-content",
                        style={"display": "none"},
                    ),
                    html.Div(
                        [
                            html.Section(
                                [
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.Label("預計用餐時間"),
                                                            html.Strong(id="planner-time-label"),
                                                        ],
                                                        className="slider-heading",
                                                    ),
                                                    dcc.RangeSlider(
                                                        id="planner-time",
                                                        min=0,
                                                        max=23.5,
                                                        step=0.5,
                                                        value=[11.5, 13.5],
                                                        marks={
                                                            0: "00:00",
                                                            6: "06:00",
                                                            12: "12:00",
                                                            18: "18:00",
                                                            23.5: "23:30",
                                                        },
                                                        tooltip={
                                                            "placement": "bottom",
                                                            "always_visible": False,
                                                        },
                                                        allowCross=False,
                                                        pushable=0.5,
                                                    ),
                                                    html.P(
                                                        "拖曳兩端選擇用餐區間；營業時段需完整涵蓋所選範圍。",
                                                        className="planner-hint",
                                                    ),
                                                ],
                                                className="planner-slider",
                                            ),
                                            html.Div(
                                                [
                                                    html.Label("縣市", htmlFor="planner-city"),
                                                    app_dropdown(
                                                        "planner-city",
                                                        options=[
                                                            {"label": city, "value": city}
                                                            for city in CITY_OPTIONS
                                                        ],
                                                        value=PLANNER_DEFAULT_CITY,
                                                        placeholder="請選擇縣市",
                                                        clearable=False,
                                                        search_placeholder="搜尋縣市名稱...",
                                                    ),
                                                ],
                                                className="field",
                                            ),
                                            html.Div(
                                                [
                                                    html.Label("菜色類型（可複選）", htmlFor="planner-cuisines"),
                                                    app_dropdown(
                                                        "planner-cuisines",
                                                        options=CUISINE_OPTIONS,
                                                        value=[],
                                                        placeholder="全部類型",
                                                        multi=True,
                                                        clearable=True,
                                                        search_placeholder="搜尋菜色類型...",
                                                    ),
                                                    html.P(
                                                        "選擇多種類型時，符合任一類型即可列入結果。",
                                                        className="planner-hint",
                                                    ),
                                                ],
                                                className="field",
                                            ),
                                        ],
                                        className="planner-controls",
                                    )
                                ],
                                className="panel planner-toolbar",
                            ),
                            html.Section(
                                [
                                    html.Div(
                                        [html.H2("符合規劃的餐廳"), html.P(id="planner-summary")],
                                        className="section-heading",
                                    ),
                                    html.Div(
                                        [
                                            html.Div(
                                                dcc.Loading(
                                                    dcc.Graph(
                                                        id="planner-map",
                                                        config={"displayModeBar": False},
                                                    )
                                                ),
                                                className="planner-map-wrap",
                                            ),
                                        ],
                                        className="planner-output-grid",
                                    ),
                                    html.Div(
                                        [
                                            html.H3("全部符合條件的店家"),
                                            html.P("所有結果完整展開，不限制顯示筆數。"),
                                        ],
                                        className="planner-list-heading",
                                    ),
                                    html.Div(id="planner-results", className="planner-results"),
                                ],
                                className="panel planner-results-panel",
                            ),
                        ],
                        id="planner-tab-content",
                        style={"display": "none"},
                    ),
                    html.Div(
                        [
                            dcc.Store(id="d3-data-store"),
                            dcc.Store(id="d3-render-status"),
                            html.Section(
                                [
                                    html.Div(
                                        [
                                            html.Label("關鍵字搜尋", htmlFor="d3-keyword"),
                                            dcc.Input(
                                                id="d3-keyword",
                                                type="search",
                                                placeholder="搜尋店名、地址或餐廳簡介",
                                                debounce=True,
                                                className="text-input",
                                            ),
                                        ],
                                        className="field",
                                    ),
                                    html.Div(
                                        [
                                            html.Label("鎖定縣市（或點擊左側長條）", htmlFor="d3-city-filter"),
                                            app_dropdown(
                                                "d3-city-filter",
                                                options=[
                                                    {"label": city, "value": city}
                                                    for city in CITY_OPTIONS
                                                ],
                                                placeholder="全部縣市",
                                                clearable=True,
                                                search_placeholder="搜尋縣市名稱...",
                                            ),
                                        ],
                                        className="field",
                                    ),
                                    html.Div(
                                        [
                                            html.Label("鎖定菜色（或點擊右側圓餅）", htmlFor="d3-cuisine-filter"),
                                            app_dropdown(
                                                "d3-cuisine-filter",
                                                options=CUISINE_OPTIONS,
                                                placeholder="全部菜色類型",
                                                clearable=True,
                                                search_placeholder="搜尋菜色類型...",
                                            ),
                                        ],
                                        className="field",
                                    ),
                                    html.Div(
                                        [
                                            html.Label("營業狀態", htmlFor="d3-status"),
                                            app_dropdown(
                                                "d3-status",
                                                options=[
                                                    {"label": "營業中", "value": "營業中"},
                                                    {"label": "非營業中", "value": "非營業中"},
                                                ],
                                                placeholder="全部狀態",
                                                clearable=True,
                                                searchable=False,
                                            ),
                                        ],
                                        className="field",
                                    ),
                                    html.Div(
                                        [
                                            html.Label("資料完整度"),
                                            dcc.Checklist(
                                                id="d3-extras",
                                                options=[
                                                    {"label": "有營業時間", "value": "has_hours"},
                                                    {"label": "有官方網站", "value": "has_website"},
                                                ],
                                                value=[],
                                                className="check-list",
                                            ),
                                        ],
                                        className="field extras-field",
                                    ),
                                    html.Button(
                                        "重設全部條件",
                                        id="d3-reset",
                                        n_clicks=0,
                                        className="reset-button",
                                    ),
                                ],
                                className="filter-panel d3-filter-panel",
                                **{"aria-label": "D3 視覺化篩選條件"},
                            ),
                            html.Div(
                                id="d3-active-badges",
                                className="d3-active-bar",
                            ),
                            html.Section(
                                [
                                    metric_card("符合餐廳總數", "d3-metric-count"),
                                    metric_card("涵蓋縣市數", "d3-metric-cities"),
                                    metric_card("營業中比例", "d3-metric-open"),
                                    metric_card("最大宗菜色", "d3-metric-top-cuisine"),
                                ],
                                className="metric-grid d3-metric-grid",
                                **{"aria-label": "D3 視覺化統計摘要"},
                            ),
                            html.Section(
                                [
                                    html.Article(
                                        [
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.Span("D3.JS INTERACTIVE RANKING", className="d3-panel-tag"),
                                                            html.H2("縣市餐廳數量排行榜"),
                                                            html.P(id="d3-ranking-subtitle"),
                                                        ]
                                                    ),
                                                    html.Div(
                                                        [
                                                            dcc.RadioItems(
                                                                id="d3-ranking-mode",
                                                                options=[
                                                                    {"label": "全部縣市", "value": "all"},
                                                                    {"label": "Top 10", "value": "top10"},
                                                                ],
                                                                value="all",
                                                                className="d3-segmented-control",
                                                                 inline=True,
                                                            ),
                                                            dcc.RadioItems(
                                                                id="d3-ranking-sort",
                                                                options=[
                                                                    {"label": "依數量", "value": "count"},
                                                                    {"label": "依營業率", "value": "open_rate"},
                                                                ],
                                                                value="count",
                                                                className="d3-segmented-control",
                                                                inline=True,
                                                            ),
                                                        ],
                                                        className="d3-chart-controls",
                                                    ),
                                                ],
                                                className="section-heading d3-section-heading",
                                            ),
                                            html.Div(
                                                id="d3-ranking-chart",
                                                className="d3-chart-canvas d3-ranking-canvas",
                                            ),
                                        ],
                                        className="panel d3-panel",
                                    ),
                                    html.Article(
                                        [
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.Span("D3.JS DONUT & BREAKDOWN", className="d3-panel-tag"),
                                                            html.H2("菜色類型比例"),
                                                            html.P(id="d3-cuisine-subtitle"),
                                                        ]
                                                    ),
                                                ],
                                                className="section-heading d3-section-heading",
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                id="d3-cuisine-chart",
                                                                className="d3-donut-canvas",
                                                            ),
                                                            html.P(
                                                                "滑過扇區檢視占比，點擊扇區或右側排行項目可雙向篩選左側縣市",
                                                                className="d3-donut-caption",
                                                            ),
                                                        ],
                                                        className="d3-donut-column",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                [
                                                                    html.Span("完整菜色分類排行"),
                                                                    html.Span("點擊項目可鎖定篩選", className="d3-legend-hint"),
                                                                ],
                                                                className="d3-legend-header",
                                                            ),
                                                            html.Div(
                                                                id="d3-cuisine-legend",
                                                                className="d3-cuisine-legend",
                                                            ),
                                                        ],
                                                        className="d3-legend-column",
                                                    ),
                                                ],
                                                className="d3-cuisine-split",
                                            ),
                                        ],
                                        className="panel d3-panel",
                                    ),
                                ],
                                className="d3-visual-grid",
                            ),
                        ],
                        id="d3-tab-content",
                        style={"display": "none"},
                    ),
                ]
            ),
            html.Footer("資料來源：專案 datasets/RestaurantList.json｜本頁僅供功能展示"),
        ],
        className="app-shell",
    )
