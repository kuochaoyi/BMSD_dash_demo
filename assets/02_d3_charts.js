/**
 * 台灣餐廳資料探索 — D3.js v7 互動視覺化模組
 * 負責渲染「縣市餐廳數量排行榜」與「菜色類型比例」並提供雙向交叉篩選 (Cross-Filtering)。
 */
(function () {
  "use strict";

  const PALETTE = [
    "#1d4ed8", // 皇家藍
    "#0f766e", // 青松綠
    "#0284c7", // 天空藍
    "#059669", // 翡翠綠
    "#2563eb", // 亮鈷藍
    "#d97706", // 琥珀金
    "#4f46e5", // 靛青藍
    "#0d9488", // 湖水綠
    "#ea580c", // 暖陽橘
    "#64748b", // 中性岩灰 (其他分類)
  ];

  let latestPayload = null;
  let resizeObserverInitialized = false;
  let resizeTimer = null;

  /**
   * 取得或建立全域浮動 Tooltip 元件
   */
  function getTooltip() {
    let tip = d3.select("#d3-floating-tooltip");
    if (tip.empty()) {
      tip = d3
        .select("body")
        .append("div")
        .attr("id", "d3-floating-tooltip")
        .attr("class", "d3-tooltip")
        .style("opacity", 0)
        .style("pointer-events", "none");
    }
    return tip;
  }

  function moveTooltip(event) {
    const tipNode = document.getElementById("d3-floating-tooltip");
    if (!tipNode) return;
    const pad = 16;
    const rect = tipNode.getBoundingClientRect();
    let left = event.clientX + pad;
    let top = event.clientY + pad;

    if (left + rect.width > window.innerWidth - 12) {
      left = event.clientX - rect.width - pad;
    }
    if (top + rect.height > window.innerHeight - 12) {
      top = Math.max(12, window.innerHeight - rect.height - 12);
    }
    d3.select(tipNode)
      .style("left", `${left}px`)
      .style("top", `${top}px`);
  }

  function hideTooltip() {
    d3.select("#d3-floating-tooltip").style("opacity", 0);
  }

  /**
   * 透過 Dash 內建 set_props 觸發雙向交叉篩選
   */
  function toggleCitySelection(cityName, currentSelectedCity) {
    if (!window.dash_clientside || !window.dash_clientside.set_props) return;
    const nextValue = currentSelectedCity === cityName ? null : cityName;
    hideTooltip();
    window.dash_clientside.set_props("d3-city-filter", { value: nextValue });
  }

  function toggleCuisineSelection(cuisineCode, currentSelectedCuisine) {
    if (cuisineCode === -1) return; // 「其他菜色」彙整群組不直接鎖定單一代碼
    if (!window.dash_clientside || !window.dash_clientside.set_props) return;
    const nextValue =
      currentSelectedCuisine !== null &&
      currentSelectedCuisine !== undefined &&
      Number(currentSelectedCuisine) === Number(cuisineCode)
        ? null
        : Number(cuisineCode);
    hideTooltip();
    window.dash_clientside.set_props("d3-cuisine-filter", { value: nextValue });
  }

  /**
   * 綁定頂部篩選膠囊點擊移除事件
   */
  function bindFilterPills(filters) {
    const cityPill = document.querySelector(".d3-pill-city");
    if (cityPill) {
      cityPill.title = "點擊移除縣市篩選";
      cityPill.onclick = function () {
        toggleCitySelection(filters.selected_city, filters.selected_city);
      };
    }
    const cuisinePill = document.querySelector(".d3-pill-cuisine");
    if (cuisinePill) {
      cuisinePill.title = "點擊移除菜色篩選";
      cuisinePill.onclick = function () {
        toggleCuisineSelection(
          filters.selected_cuisine,
          filters.selected_cuisine
        );
      };
    }
  }

  /**
   * 1. 渲染「縣市餐廳數量排行榜」D3 水平長條圖
   */
  function renderCityRanking(payload) {
    const container = document.getElementById("d3-ranking-chart");
    if (!container) return;

    const cities = payload.cities || [];
    const filters = payload.filters || {};
    const summary = payload.summary || {};
    const sortBy = filters.ranking_sort || "count";
    const selectedCity = filters.selected_city || null;

    const root = d3.select(container);

    if (!cities.length) {
      root.selectAll("*").remove();
      root
        .append("div")
        .attr("class", "d3-empty-state")
        .html(
          "<strong>目前篩選條件下沒有可排行的縣市資料</strong><p>請嘗試放寬關鍵字、營業狀態或點擊「重設全部條件」。</p>"
        );
      return;
    }

    root.selectAll(".d3-empty-state").remove();

    const containerWidth = Math.max(container.clientWidth || 560, 340);
    const margin = { top: 34, right: 128, bottom: 26, left: 108 };
    const rowHeight = 36;
    const height = margin.top + margin.bottom + cities.length * rowHeight;
    const innerWidth = Math.max(160, containerWidth - margin.left - margin.right);
    const innerHeight = cities.length * rowHeight;

    let svg = root.select("svg.d3-ranking-svg");
    if (svg.empty()) {
      svg = root
        .append("svg")
        .attr("class", "d3-ranking-svg")
        .style("width", "100%")
        .style("display", "block");

      const defs = svg.append("defs");
      const gradPrimary = defs
        .append("linearGradient")
        .attr("id", "d3-bar-grad-primary")
        .attr("x1", "0%")
        .attr("y1", "0%")
        .attr("x2", "100%")
        .attr("y2", "0%");
      gradPrimary.append("stop").attr("offset", "0%").attr("stop-color", "#2563eb");
      gradPrimary.append("stop").attr("offset", "100%").attr("stop-color", "#1d4ed8");

      const gradTop = defs
        .append("linearGradient")
        .attr("id", "d3-bar-grad-top")
        .attr("x1", "0%")
        .attr("y1", "0%")
        .attr("x2", "100%")
        .attr("y2", "0%");
      gradTop.append("stop").attr("offset", "0%").attr("stop-color", "#1d4ed8");
      gradTop.append("stop").attr("offset", "100%").attr("stop-color", "#0f766e");

      const gradSelected = defs
        .append("linearGradient")
        .attr("id", "d3-bar-grad-selected")
        .attr("x1", "0%")
        .attr("y1", "0%")
        .attr("x2", "100%")
        .attr("y2", "0%");
      gradSelected.append("stop").attr("offset", "0%").attr("stop-color", "#0f766e");
      gradSelected.append("stop").attr("offset", "100%").attr("stop-color", "#0d9488");

      svg.append("g").attr("class", "d3-grid-layer");
      svg.append("g").attr("class", "d3-track-layer");
      svg.append("g").attr("class", "d3-bars-layer");
      svg.append("g").attr("class", "d3-avg-layer");
      svg.append("g").attr("class", "d3-labels-layer");
    }

    svg
      .attr("viewBox", `0 0 ${containerWidth} ${height}`)
      .attr("height", height);

    const maxMetric =
      sortBy === "open_rate"
        ? 100
        : d3.max(cities, (d) => d.count) || 1;

    const xScale = d3
      .scaleLinear()
      .domain([0, maxMetric * (sortBy === "open_rate" ? 1 : 1.04)])
      .range([0, innerWidth]);

    const yScale = d3
      .scaleBand()
      .domain(cities.map((d) => d.city))
      .range([0, innerHeight])
      .paddingInner(0.26)
      .paddingOuter(0.12);

    const t = svg.transition().duration(600).ease(d3.easeCubicOut);

    // 繪製背景垂直參考網格線
    const gridLayer = svg
      .select(".d3-grid-layer")
      .attr("transform", `translate(${margin.left}, ${margin.top})`);

    const ticks = xScale.ticks(5);
    const gridLines = gridLayer.selectAll("g.d3-grid-tick").data(ticks, (d) => d);

    const gridEnter = gridLines
      .enter()
      .append("g")
      .attr("class", "d3-grid-tick")
      .attr("transform", (d) => `translate(${xScale(d)}, 0)`);

    gridEnter
      .append("line")
      .attr("y1", 0)
      .attr("y2", innerHeight)
      .attr("stroke", "#e2e8f0")
      .attr("stroke-dasharray", "3,3");

    gridEnter
      .append("text")
      .attr("y", -10)
      .attr("text-anchor", "middle")
      .attr("fill", "#64748b")
      .attr("font-size", "11px")
      .text((d) => (sortBy === "open_rate" ? `${d}%` : d3.format(",")(d)));

    const gridMerge = gridEnter.merge(gridLines);
    gridMerge
      .transition(t)
      .attr("transform", (d) => `translate(${xScale(d)}, 0)`);
    gridMerge.select("line").transition(t).attr("y2", innerHeight);
    gridMerge
      .select("text")
      .text((d) => (sortBy === "open_rate" ? `${d}%` : d3.format(",")(d)));

    gridLines.exit().remove();

    // 繪製長條底軌 (Track)
    const trackLayer = svg
      .select(".d3-track-layer")
      .attr("transform", `translate(${margin.left}, ${margin.top})`);

    const tracks = trackLayer.selectAll("rect.d3-bar-track").data(cities, (d) => d.city);
    tracks
      .enter()
      .append("rect")
      .attr("class", "d3-bar-track")
      .attr("x", 0)
      .attr("y", (d) => yScale(d.city))
      .attr("height", yScale.bandwidth())
      .attr("width", innerWidth)
      .attr("rx", 6)
      .attr("fill", "#f1f5f9")
      .merge(tracks)
      .transition(t)
      .attr("y", (d) => yScale(d.city))
      .attr("height", yScale.bandwidth())
      .attr("width", innerWidth);
    tracks.exit().remove();

    // 繪製數據長條與互動層
    const barsLayer = svg
      .select(".d3-bars-layer")
      .attr("transform", `translate(${margin.left}, ${margin.top})`);

    const rowGroups = barsLayer
      .selectAll("g.d3-bar-row")
      .data(cities, (d) => d.city);

    const rowEnter = rowGroups
      .enter()
      .append("g")
      .attr("class", "d3-bar-row")
      .attr("transform", (d) => `translate(0, ${yScale(d.city)})`)
      .style("cursor", "pointer");

    // 排名徽章
    rowEnter
      .append("rect")
      .attr("class", "d3-rank-badge")
      .attr("x", -margin.left + 6)
      .attr("y", (yScale.bandwidth() - 20) / 2)
      .attr("width", 24)
      .attr("height", 20)
      .attr("rx", 5);

    rowEnter
      .append("text")
      .attr("class", "d3-rank-num")
      .attr("x", -margin.left + 18)
      .attr("y", yScale.bandwidth() / 2)
      .attr("dy", "0.35em")
      .attr("text-anchor", "middle")
      .attr("font-size", "11px")
      .attr("font-weight", "700");

    // 縣市名稱
    rowEnter
      .append("text")
      .attr("class", "d3-city-label")
      .attr("x", -10)
      .attr("y", yScale.bandwidth() / 2)
      .attr("dy", "0.35em")
      .attr("text-anchor", "end")
      .attr("font-size", "13.5px")
      .attr("font-weight", "650");

    // 數據主長條
    rowEnter
      .append("rect")
      .attr("class", "d3-bar-rect")
      .attr("x", 0)
      .attr("y", 0)
      .attr("height", yScale.bandwidth())
      .attr("width", 0)
      .attr("rx", 6);

    // 末端數值標籤
    rowEnter
      .append("text")
      .attr("class", "d3-bar-value")
      .attr("x", 8)
      .attr("y", yScale.bandwidth() / 2)
      .attr("dy", "0.35em")
      .attr("font-size", "12.5px")
      .attr("font-weight", "700");

    const rowMerge = rowEnter.merge(rowGroups);

    rowMerge
      .transition(t)
      .attr("transform", (d) => `translate(0, ${yScale(d.city)})`)
      .style("opacity", (d) =>
        selectedCity && d.city !== selectedCity ? 0.42 : 1
      );

    rowMerge
      .select(".d3-rank-badge")
      .attr("y", (yScale.bandwidth() - 20) / 2)
      .attr("fill", (d, i) => {
        if (d.is_selected) return "#0f766e";
        if (i === 0) return "#1d4ed8";
        if (i === 1) return "#2563eb";
        if (i === 2) return "#0284c7";
        return "#e2e8f0";
      });

    rowMerge
      .select(".d3-rank-num")
      .attr("y", yScale.bandwidth() / 2)
      .attr("fill", (d, i) => (d.is_selected || i < 3 ? "#ffffff" : "#475569"))
      .text((d, i) => String(i + 1).padStart(2, "0"));

    rowMerge
      .select(".d3-city-label")
      .attr("y", yScale.bandwidth() / 2)
      .attr("fill", (d) => (d.is_selected ? "#0f766e" : "#1e293b"))
      .attr("font-weight", (d) => (d.is_selected ? "800" : "650"))
      .text((d) => d.city);

    rowMerge
      .select(".d3-bar-rect")
      .attr("height", yScale.bandwidth())
      .attr("fill", (d, i) => {
        if (d.is_selected) return "url(#d3-bar-grad-selected)";
        if (i < 3) return "url(#d3-bar-grad-top)";
        return "url(#d3-bar-grad-primary)";
      })
      .transition(t)
      .attr("width", (d) => {
        const val = sortBy === "open_rate" ? d.open_rate : d.count;
        return Math.max(4, xScale(val));
      });

    rowMerge
      .select(".d3-bar-value")
      .attr("y", yScale.bandwidth() / 2)
      .attr("fill", (d) => (d.is_selected ? "#0f766e" : "#1e293b"))
      .transition(t)
      .attr("x", (d) => {
        const val = sortBy === "open_rate" ? d.open_rate : d.count;
        return Math.max(4, xScale(val)) + 8;
      })
      .text((d) =>
        sortBy === "open_rate"
          ? `${d.open_rate}% (${d3.format(",")(d.count)} 家)`
          : `${d3.format(",")(d.count)} 家 (${d.share}%)`
      );

    // 綁定滑過 Tooltip 與點擊雙向篩選
    const tooltip = getTooltip();
    rowMerge
      .on("mouseenter", function (event, d) {
        d3.select(this)
          .select(".d3-bar-rect")
          .attr("stroke", "#0f172a")
          .attr("stroke-width", 1.5);

        const topCuisineHtml =
          d.top_cuisines && d.top_cuisines.length
            ? d.top_cuisines
                .map(
                  (c) =>
                    `<span class="d3-tip-tag">${c.label} <b>${c.count}</b></span>`
                )
                .join("")
            : `<span class="d3-tip-muted">尚無分類標記</span>`;

        tooltip
          .style("opacity", 1)
          .html(
            `
            <div class="d3-tip-header">
              <strong>${d.city}</strong>
              <span class="d3-tip-badge">${d.share}% 全台佔比</span>
            </div>
            <div class="d3-tip-Metrics">
              <div><span>餐廳總數</span><strong>${d3.format(",")(d.count)} 家</strong></div>
              <div><span>營業中比例</span><strong>${d.open_rate}% (${d3.format(",")(d.open_count)} 家)</strong></div>
              <div><span>具營業時間</span><strong>${d.hours_rate}%</strong></div>
            </div>
            <div class="d3-tip-section">
              <div class="d3-tip-subtitle">熱門菜色前三名</div>
              <div class="d3-tip-tags">${topCuisineHtml}</div>
            </div>
            <div class="d3-tip-footer">
              ${
                d.is_selected
                  ? "⚡ 目前已鎖定此縣市，再次點擊可取消篩選"
                  : "👆 點擊長條以連動篩選右側「菜色類型比例」"
              }
            </div>
          `
          );
        moveTooltip(event);
      })
      .on("mousemove", function (event) {
        moveTooltip(event);
      })
      .on("mouseleave", function () {
        d3.select(this)
          .select(".d3-bar-rect")
          .attr("stroke", "none");
        hideTooltip();
      })
      .on("click", function (_event, d) {
        toggleCitySelection(d.city, selectedCity);
      });

    rowGroups.exit().remove();

    // 繪製平均參考虛線 (僅在依店家數排序時顯示)
    const avgLayer = svg
      .select(".d3-avg-layer")
      .attr("transform", `translate(${margin.left}, ${margin.top})`);

    const avgVal = summary.avg_city_count || 0;
    const showAvg = sortBy === "count" && avgVal > 0 && xScale(avgVal) <= innerWidth;
    const avgData = showAvg ? [avgVal] : [];

    const avgGroup = avgLayer.selectAll("g.d3-avg-line").data(avgData);
    const avgEnter = avgGroup
      .enter()
      .append("g")
      .attr("class", "d3-avg-line")
      .attr("transform", (d) => `translate(${xScale(d)}, 0)`);

    avgEnter
      .append("line")
      .attr("y1", -4)
      .attr("y2", innerHeight)
      .attr("stroke", "#0f766e")
      .attr("stroke-width", 1.5)
      .attr("stroke-dasharray", "5,4");

    avgEnter
      .append("rect")
      .attr("x", -44)
      .attr("y", -28)
      .attr("width", 88)
      .attr("height", 18)
      .attr("rx", 9)
      .attr("fill", "#ccfbf1")
      .attr("stroke", "#0f766e")
      .attr("stroke-width", 1);

    avgEnter
      .append("text")
      .attr("y", -16)
      .attr("text-anchor", "middle")
      .attr("fill", "#0f766e")
      .attr("font-size", "10.5px")
      .attr("font-weight", "750");

    const avgMerge = avgEnter.merge(avgGroup);
    avgMerge
      .transition(t)
      .attr("transform", (d) => `translate(${xScale(d)}, 0)`);
    avgMerge.select("line").transition(t).attr("y2", innerHeight);
    avgMerge
      .select("text")
      .text((d) => `平均 ${d3.format(",.1f")(d)} 家`);

    avgGroup.exit().remove();
  }

  /**
   * 2. 渲染「菜色類型比例」D3 互動環形圖 + 排行明細圖例
   */
  function renderCuisineDistribution(payload) {
    const chartContainer = document.getElementById("d3-cuisine-chart");
    const legendContainer = document.getElementById("d3-cuisine-legend");
    if (!chartContainer || !legendContainer) return;

    const slices = payload.donut_slices || [];
    const allCuisines = payload.cuisines || [];
    const summary = payload.summary || {};
    const filters = payload.filters || {};
    const selectedCuisine =
      filters.selected_cuisine !== undefined ? filters.selected_cuisine : null;

    const chartRoot = d3.select(chartContainer);
    const legendRoot = d3.select(legendContainer);

    if (!slices.length) {
      chartRoot.selectAll("*").remove();
      legendRoot.selectAll("*").remove();
      chartRoot
        .append("div")
        .attr("class", "d3-empty-state")
        .html(
          "<strong>目前篩選條件下沒有可統計的菜色類型</strong><p>部分餐廳未提供分類標記，請嘗試切換其他縣市或放寬條件。</p>"
        );
      return;
    }

    chartRoot.selectAll(".d3-empty-state").remove();

    const size = Math.min(Math.max(chartContainer.clientWidth || 340, 280), 370);
    const outerRadius = Math.floor(size / 2) - 18;
    const innerRadius = Math.floor(outerRadius * 0.62);

    let svg = chartRoot.select("svg.d3-donut-svg");
    if (svg.empty()) {
      svg = chartRoot
        .append("svg")
        .attr("class", "d3-donut-svg")
        .style("width", "100%")
        .style("max-width", `${size}px`)
        .style("margin", "0 auto")
        .style("display", "block");

      const g = svg.append("g").attr("class", "d3-donut-center");
      g.append("g").attr("class", "d3-arcs-layer");

      const centerGroup = g
        .append("g")
        .attr("class", "d3-center-hub")
        .style("pointer-events", "none");

      centerGroup
        .append("text")
        .attr("class", "d3-hub-eyebrow")
        .attr("y", -28)
        .attr("text-anchor", "middle")
        .attr("fill", "#64748b")
        .attr("font-size", "11.5px")
        .attr("font-weight", "700");

      centerGroup
        .append("text")
        .attr("class", "d3-hub-title")
        .attr("y", -4)
        .attr("text-anchor", "middle")
        .attr("fill", "#172554")
        .attr("font-size", "15px")
        .attr("font-weight", "800");

      centerGroup
        .append("text")
        .attr("class", "d3-hub-value")
        .attr("y", 24)
        .attr("text-anchor", "middle")
        .attr("fill", "#0f766e")
        .attr("font-size", "22px")
        .attr("font-weight", "800");

      centerGroup
        .append("text")
        .attr("class", "d3-hub-sub")
        .attr("y", 45)
        .attr("text-anchor", "middle")
        .attr("fill", "#64748b")
        .attr("font-size", "11.5px")
        .attr("font-weight", "600");
    }

    svg.attr("viewBox", `0 0 ${size} ${size}`).attr("height", size);

    const gCenter = svg
      .select(".d3-donut-center")
      .attr("transform", `translate(${size / 2}, ${size / 2})`);

    const colorMap = new Map();
    slices.forEach((s, idx) => {
      colorMap.set(
        s.code,
        s.is_other_group ? "#94a3b8" : PALETTE[idx % (PALETTE.length - 1)]
      );
    });

    const pie = d3
      .pie()
      .value((d) => d.count)
      .sort(null)
      .padAngle(0.018);

    const arcNormal = d3
      .arc()
      .innerRadius(innerRadius)
      .outerRadius(outerRadius)
      .cornerRadius(5);

    const arcActive = d3
      .arc()
      .innerRadius(innerRadius - 2)
      .outerRadius(outerRadius + 9)
      .cornerRadius(6);

    // 更新環形圖中央 KPI Hub 的輔助函式
    function updateCenterHub(activeItem) {
      const hub = gCenter.select(".d3-center-hub");
      if (activeItem) {
        const shortLabel =
          activeItem.label.length > 9
            ? activeItem.label.slice(0, 9) + "…"
            : activeItem.label;
        hub
          .select(".d3-hub-eyebrow")
          .text(activeItem.is_selected ? "已鎖定菜色" : "目前檢視分類");
        hub.select(".d3-hub-title").text(shortLabel);
        hub.select(".d3-hub-value").text(`${activeItem.share}%`);
        hub
          .select(".d3-hub-sub")
          .text(`${d3.format(",")(activeItem.count)} 家標記`);
      } else {
        const lockedItem = allCuisines.find((c) => c.is_selected);
        if (lockedItem) {
          const shortLabel =
            lockedItem.label.length > 9
              ? lockedItem.label.slice(0, 9) + "…"
              : lockedItem.label;
          hub.select(".d3-hub-eyebrow").text("已鎖定菜色");
          hub.select(".d3-hub-title").text(shortLabel);
          hub.select(".d3-hub-value").text(`${lockedItem.share}%`);
          hub
            .select(".d3-hub-sub")
            .text(`${d3.format(",")(lockedItem.count)} 家標記`);
        } else {
          hub
            .select(".d3-hub-eyebrow")
            .text(filters.selected_city ? `${filters.selected_city}菜色統計` : "全台菜色總覽");
          hub
            .select(".d3-hub-title")
            .text(`共 ${summary.unique_cuisines || 0} 種分類`);
          hub
            .select(".d3-hub-value")
            .text(d3.format(",")(summary.total_cuisine_tags || 0));
          hub.select(".d3-hub-sub").text("總分類標記數");
        }
      }
    }

    updateCenterHub(null);

    const pieData = pie(slices);
    const arcsLayer = gCenter.select(".d3-arcs-layer");
    const paths = arcsLayer
      .selectAll("path.d3-donut-arc")
      .data(pieData, (d) => d.data.code);

    const pathEnter = paths
      .enter()
      .append("path")
      .attr("class", "d3-donut-arc")
      .style("cursor", (d) => (d.data.is_other_group ? "default" : "pointer"))
      .each(function (d) {
        this._current = { startAngle: d.startAngle, endAngle: d.startAngle };
      });

    const pathMerge = pathEnter.merge(paths);

    pathMerge
      .attr("fill", (d) => colorMap.get(d.data.code) || "#1d4ed8")
      .style("opacity", (d) => {
        if (selectedCuisine === null || selectedCuisine === undefined) return 1;
        return d.data.is_selected ? 1 : 0.38;
      })
      .transition()
      .duration(620)
      .ease(d3.easeCubicOut)
      .attrTween("d", function (d) {
        const interpolate = d3.interpolate(this._current || d, d);
        this._current = interpolate(1);
        const targetArc = d.data.is_selected ? arcActive : arcNormal;
        return function (tStep) {
          return targetArc(interpolate(tStep));
        };
      });

    const tooltip = getTooltip();

    pathMerge
      .on("mouseenter", function (event, d) {
        d3.select(this)
          .transition()
          .duration(180)
          .attr("d", arcActive(d))
          .style("opacity", 1);

        updateCenterHub(d.data);

        // 同步高亮右側圖例對應列
        legendRoot
          .selectAll(".d3-legend-item")
          .classed("is-hovered", (item) => item.code === d.data.code);

        const topCityHtml =
          d.data.top_cities && d.data.top_cities.length
            ? d.data.top_cities
                .map(
                  (c) =>
                    `<span class="d3-tip-tag">${c.city} <b>${c.count}</b></span>`
                )
                .join("")
            : `<span class="d3-tip-muted">包含 ${d.data.grouped_count || 0} 個細分菜色類別</span>`;

        tooltip
          .style("opacity", 1)
          .html(
            `
            <div class="d3-tip-header">
              <strong>${d.data.label}</strong>
              <span class="d3-tip-badge">${d.data.share}% 標記佔比</span>
            </div>
            <div class="d3-tip-Metrics">
              <div><span>標記店家數</span><strong>${d3.format(",")(d.data.count)} 家</strong></div>
              <div><span>餐廳涵蓋率</span><strong>${d.data.restaurant_share}%</strong></div>
              <div><span>營業中比例</span><strong>${d.data.open_rate}%</strong></div>
            </div>
            <div class="d3-tip-section">
              <div class="d3-tip-subtitle">${
                d.data.is_other_group ? "分組說明" : "主要分布縣市"
              }</div>
              <div class="d3-tip-tags">${topCityHtml}</div>
            </div>
            <div class="d3-tip-footer">
              ${
                d.data.is_other_group
                  ? "👉 請由右側完整排行清單點選特定細分菜色"
                  : d.data.is_selected
                  ? "⚡ 目前已鎖定此菜色，再次點擊可取消篩選"
                  : "👆 點擊扇區以連動篩選左側「縣市餐廳排行榜」"
              }
            </div>
          `
          );
        moveTooltip(event);
      })
      .on("mousemove", function (event) {
        moveTooltip(event);
      })
      .on("mouseleave", function (_event, d) {
        d3.select(this)
          .transition()
          .duration(200)
          .attr("d", ( d.data.is_selected ? arcActive : arcNormal )(d))
          .style("opacity", () => {
            if (selectedCuisine === null || selectedCuisine === undefined) return 1;
            return d.data.is_selected ? 1 : 0.38;
          });

        updateCenterHub(null);
        legendRoot.selectAll(".d3-legend-item").classed("is-hovered", false);
        hideTooltip();
      })
      .on("click", function (_event, d) {
        if (!d.data.is_other_group) {
          toggleCuisineSelection(d.data.code, selectedCuisine);
        }
      });

    paths.exit().remove();

    // 渲染右側互動式完整菜色排行清單 (#d3-cuisine-legend)
    const maxCuisineCount = d3.max(allCuisines, (d) => d.count) || 1;
    const legendItems = legendRoot
      .selectAll("div.d3-legend-item")
      .data(allCuisines, (d) => d.code);

    const itemEnter = legendItems
      .enter()
      .append("div")
      .attr("class", "d3-legend-item");

    const topRow = itemEnter.append("div").attr("class", "d3-legend-top");
    const leftMeta = topRow.append("div").attr("class", "d3-legend-name-wrap");
    leftMeta.append("span").attr("class", "d3-legend-swatch");
    leftMeta.append("span").attr("class", "d3-legend-name");

    const rightMeta = topRow.append("div").attr("class", "d3-legend-stats");
    rightMeta.append("span").attr("class", "d3-legend-count");
    rightMeta.append("strong").attr("class", "d3-legend-share");

    const barTrack = itemEnter.append("div").attr("class", "d3-legend-bar-track");
    barTrack.append("div").attr("class", "d3-legend-bar-fill");

    const itemMerge = itemEnter.merge(legendItems);

    itemMerge
      .classed("is-selected", (d) => d.is_selected)
      .style("opacity", (d) => {
        if (selectedCuisine === null || selectedCuisine === undefined) return 1;
        return d.is_selected ? 1 : 0.55;
      });

    itemMerge
      .select(".d3-legend-swatch")
      .style("background-color", (d) => colorMap.get(d.code) || "#94a3b8");

    itemMerge
      .select(".d3-legend-name")
      .text((d, i) => `${i + 1}. ${d.label}`);

    itemMerge
      .select(".d3-legend-count")
      .text((d) => `${d3.format(",")(d.count)} 家`);

    itemMerge
      .select(".d3-legend-share")
      .text((d) => `${d.share}%`);

    itemMerge
      .select(".d3-legend-bar-fill")
      .style("background-color", (d) => colorMap.get(d.code) || "#64748b")
      .style("width", (d) => `${Math.max(3, (d.count / maxCuisineCount) * 100)}%`);

    itemMerge
      .on("mouseenter", function (_event, d) {
        updateCenterHub(d);
        arcsLayer
          .selectAll("path.d3-donut-arc")
          .filter((arcD) => arcD.data.code === d.code)
          .transition()
          .duration(180)
          .attr("d", (arcD) => arcActive(arcD))
          .style("opacity", 1);
      })
      .on("mouseleave", function () {
        updateCenterHub(null);
        arcsLayer
          .selectAll("path.d3-donut-arc")
          .transition()
          .duration(200)
          .attr("d", (arcD) =>
            (arcD.data.is_selected ? arcActive : arcNormal)(arcD)
          )
          .style("opacity", (arcD) => {
            if (selectedCuisine === null || selectedCuisine === undefined)
              return 1;
            return arcD.data.is_selected ? 1 : 0.38;
          });
      })
      .on("click", function (_event, d) {
        toggleCuisineSelection(d.code, selectedCuisine);
      });

    legendItems.exit().remove();
  }

  /**
   * 初始化 ResizeObserver，當視窗尺寸調整或切換分頁展開時自動重繪 SVG
   */
  function ensureResizeObserver() {
    if (resizeObserverInitialized || typeof ResizeObserver === "undefined") {
      return;
    }
    const target = document.getElementById("d3-ranking-chart");
    if (!target) return;

    const observer = new ResizeObserver(() => {
      if (!latestPayload) return;
      if (resizeTimer) clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        if (target.clientWidth > 0) {
          renderCityRanking(latestPayload);
          renderCuisineDistribution(latestPayload);
        }
      }, 120);
    });
    observer.observe(target);
    resizeObserverInitialized = true;
  }

  // 註冊給 Dash Clientside Callback 呼叫的入口
  window.dash_clientside = Object.assign({}, window.dash_clientside, {
    d3Charts: {
      renderAll: function (payload, activeTab) {
        if (!payload || typeof d3 === "undefined") {
          return window.dash_clientside.no_update;
        }
        latestPayload = payload;

        // 雙向篩選膠囊事件綁定
        setTimeout(() => {
          bindFilterPills(payload.filters || {});
        }, 40);

        if (activeTab !== "d3-analytics") {
          return { rendered: false, tab: activeTab };
        }

        // 確保容器已顯示 (display: block) 並取得正確寬度後繪製
        requestAnimationFrame(() => {
          ensureResizeObserver();
          renderCityRanking(payload);
          renderCuisineDistribution(payload);
        });

        return {
          rendered: true,
          timestamp: Date.now(),
          cities: (payload.cities || []).length,
          cuisines: (payload.cuisines || []).length,
        };
      },
    },
  });
})();
