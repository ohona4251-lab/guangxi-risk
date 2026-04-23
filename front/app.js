(function () {
  const appData = {
    dashboard: {
      currentTime: "2026-04-23 09:36:09"
    },
    points: []
  };

  const riskClassMap = {
    "I级": "risk-i",
    "II级": "risk-ii",
    "III级": "risk-iii",
    "IV级": "risk-iv"
  };

  const inspectionTextSourceMap = {
    "BR-BY01": [
      "../data/examples/bridge_br_by01_record1.txt",
      "../data/examples/bridge_br_by01_record2.txt"
    ],
    "SP-LB13": [
      "../data/examples/bridge_sp_lb13_record1.txt",
      "../data/examples/bridge_sp_lb13_record2.txt"
    ],
    "BR-LZ02": [
      "../data/examples/bridge_br_lz02_record1.txt",
      "../data/examples/bridge_br_lz02_record2.txt"
    ],
    "BR-HZ07": [
      "../data/examples/bridge_br_hz07_record1.txt",
      "../data/examples/bridge_br_hz07_record2.txt"
    ],
    "BR-QS09": [
      "../data/examples/bridge_br_qs09_record1.txt",
      "../data/examples/bridge_br_qs09_record2.txt"
    ],
    "EX-BR-001": ["../data/examples/example2_bridge_joint.txt"],
    "SL-GZ01": [
      "../data/examples/scope_sl_gz01_record1.txt",
      "../data/examples/scope_sl_gz01_record2.txt"
    ],
    "SL-BH02": [
      "../data/examples/scope_sl_bh02_record1.txt",
      "../data/examples/scope_sl_bh02_record2.txt"
    ],
    "SL-HC03": [
      "../data/examples/scope_sl_hc03_record1.txt",
      "../data/examples/scope_sl_hc03_record2.txt"
    ],
    "EX-SL-001": ["../data/examples/example1_rainfall_slope.txt"],
    "EX-SL-002": ["../data/examples/example3_tunnel_slope.txt"]
  };
  const generatedInspectionGraphSourceMap = {
    "BR-BY01": [
      "../risk_workflow/outputs/node2/front_inspection_records_1_bridge_br_by01_record1_20260423_141533/iter0/canon_kg.txt",
      "../risk_workflow/outputs/node2/front_inspection_records_2_bridge_br_by01_record2_20260423_141852/iter0/canon_kg.txt"
    ]
  };
  const generatedMonitorGraphSourceMap = {
    "BR-BY01": [
      "../risk_workflow/outputs/node3/node3_monitor_records_1_BR-BY01_monitor_01_20260423_143811/iter0/canon_kg.txt"
    ],
    "BR-HZ07": [
      "../risk_workflow/outputs/node3/node3_monitor_records_2_BR-HZ07_monitor_01_20260423_144322/iter0/canon_kg.txt"
    ]
  };
  const monitorTextSourceMap = {
    "BR-BY01": ["../data/monitor_data/BR-BY01_monitor_01.txt"],
    "SP-LB13": ["../data/monitor_data/SP-LB13_monitor_01.txt"],
    "BR-LZ02": ["../data/monitor_data/BR-LZ02_monitor_01.txt"],
    "BR-HZ07": ["../data/monitor_data/BR-HZ07_monitor_01.txt"],
    "BR-QS09": ["../data/monitor_data/BR-QS09_monitor_01.txt"],
    "EX-BR-001": ["../data/monitor_data/EX-BR-001_monitor_01.txt"],
    "SL-GZ01": ["../data/monitor_data/SL-GZ01_monitor_01.txt"],
    "SL-BH02": ["../data/monitor_data/SL-BH02_monitor_01.txt"],
    "SL-HC03": ["../data/monitor_data/SL-HC03_monitor_01.txt"],
    "EX-SL-001": ["../data/monitor_data/EX-SL-001_monitor_01.txt"],
    "EX-SL-002": ["../data/monitor_data/EX-SL-002_monitor_01.txt"]
  };

  const pointListEl = document.getElementById("point-list");
  const modalEl = document.getElementById("detail-modal");
  const mapRootEl = document.getElementById("map-root");
  const listSummaryEl = document.getElementById("list-summary");
  const monitorCountEl = document.getElementById("stat-monitor-count");
  const typeBreakdownEl = document.getElementById("stat-type-breakdown");
  const alertBreakdownEl = document.getElementById("stat-alert-breakdown");
  const currentTimeEl = document.getElementById("current-time");
  const tabButtons = Array.from(document.querySelectorAll(".mini-tab"));
  const detailOverviewEl = document.getElementById("detail-overview");
  const detailReviewPageEl = document.getElementById("detail-review-page");
  const detailInspectionPageEl = document.getElementById("detail-inspection-page");
  const reviewPageSubtitleEl = document.getElementById("review-page-subtitle");
  const reviewBackBtn = document.getElementById("review-back-btn");
  const inspectionPageSubtitleEl = document.getElementById("inspection-page-subtitle");
  const inspectionBackBtn = document.getElementById("inspection-back-btn");
  const inspectionSummaryPanelEl = document.getElementById("inspection-summary-panel");
  const inspectionDetailPanelEl = document.getElementById("inspection-detail-panel");
  const reviewNodeGradeEl = document.getElementById("review-node-grade");
  const reviewManualGradeEl = document.getElementById("review-manual-grade");
  const reviewRemarkEl = document.getElementById("review-remark");
  const reviewResultPanelEl = document.getElementById("review-result-panel");
  const reviewSubmitBtn = document.getElementById("review-submit-btn");

  let mapInstance = null;
  let provinceLayer = null;
  let activeMarker = null;
  let currentType = "桥梁";
  let currentDetailPoint = null;
  const markerById = new Map();
  const graphCache = new Map();
  const tripleCache = new Map();
  const inspectionTextCache = new Map();
  const monitorTextCache = new Map();

  function parseLngLat(value) {
    if (!value) {
      return null;
    }

    if (typeof value === "object" && value.lng !== undefined && value.lat !== undefined) {
      const lng = Number(value.lng);
      const lat = Number(value.lat);
      if (Number.isNaN(lng) || Number.isNaN(lat)) {
        return null;
      }
      return { lng, lat };
    }

    const parts = String(value)
      .split(",")
      .map((item) => Number(item.trim()));

    if (parts.length !== 2 || parts.some((item) => Number.isNaN(item))) {
      return null;
    }

    return { lng: parts[0], lat: parts[1] };
  }

  function formatLngLat(value) {
    const parsed = parseLngLat(value);
    if (!parsed) {
      return "";
    }
    return `${parsed.lng}, ${parsed.lat}`;
  }

  function inferGraphPath(pointId, type) {
    if (pointId.startsWith("EX-BR-") || pointId.startsWith("BR-") || pointId.startsWith("SP-")) {
      return "../risk_workflow/outputs/node2/batch_examples_2_example2_bridge_joint_20260422_232822/iter0/canon_kg.txt";
    }
    if (pointId === "EX-SL-002" || pointId === "SL-BH02") {
      return "../risk_workflow/outputs/node2/batch_examples_3_example3_tunnel_slope_20260422_233255/iter0/canon_kg.txt";
    }
    if (type === "边坡") {
      return "../risk_workflow/outputs/node2/batch_examples_1_example1_rainfall_slope_20260422_232429/iter0/canon_kg.txt";
    }
    return "";
  }

  function inferGraphPaths(pointId, type) {
    const generatedPaths = generatedInspectionGraphSourceMap[pointId];
    if (generatedPaths?.length) {
      return generatedPaths;
    }

    const fallbackPath = inferGraphPath(pointId, type);
    return fallbackPath ? [fallbackPath] : [];
  }

  function inferMonitorGraphPaths(pointId) {
    return generatedMonitorGraphSourceMap[pointId] || [];
  }

  function inferMonitorTextSources(pointId) {
    if (!pointId) {
      return [];
    }
    return [`../data/monitor_data/${pointId}_monitor_01.txt`];
  }

  function normalizePoint(rawPoint) {
    const type = rawPoint.category || rawPoint.type || "桥梁";
    const riskLevel = rawPoint.risk_level || rawPoint.riskLevel || "III级";

    return {
      id: rawPoint.id,
      name: rawPoint.name,
      type,
      riskLevel,
      riskClass: rawPoint.risk_class || rawPoint.riskClass || riskClassMap[riskLevel] || "risk-iii",
      locationText: rawPoint.location || rawPoint.locationText || rawPoint.name,
      lnglat: formatLngLat(rawPoint.lnglat),
      region: rawPoint.region || "",
      latestEvent: rawPoint.latest_event || rawPoint.latestEvent || "巡检记录",
      latestTime: rawPoint.latest_time || rawPoint.latestTime || "",
      inspectionSummary:
        rawPoint.inspection_summary ||
        rawPoint.inspectionSummary ||
        "",
      monitoringPoints: rawPoint.monitoring_points || rawPoint.monitoringPoints || [],
      monitorTextSources:
        rawPoint.monitor_text_sources ||
        monitorTextSourceMap[rawPoint.id] ||
        inferMonitorTextSources(rawPoint.id),
      inspectionRecords: rawPoint.inspection_records || rawPoint.inspectionRecords || [],
      inspectionTextSources: rawPoint.inspection_text_sources || inspectionTextSourceMap[rawPoint.id] || [],
      inspectionGraph: {
        sourcePath:
          rawPoint.inspection_graph_source_path ||
          rawPoint.inspectionGraph?.sourcePath ||
          inferGraphPath(rawPoint.id, type),
        sourcePaths:
          rawPoint.inspection_graph_source_paths ||
          rawPoint.inspectionGraph?.sourcePaths ||
          inferGraphPaths(rawPoint.id, type)
      },
      monitorGraph: {
        sourcePath:
          rawPoint.monitor_graph_source_path ||
          rawPoint.monitorGraph?.sourcePath ||
          inferMonitorGraphPaths(rawPoint.id)[0] ||
          "",
        sourcePaths:
          rawPoint.monitor_graph_source_paths ||
          rawPoint.monitorGraph?.sourcePaths ||
          inferMonitorGraphPaths(rawPoint.id)
      },
      gradeResult: {
        level: rawPoint.grade_result?.level || rawPoint.gradeResult?.level || riskLevel,
        desc:
          rawPoint.grade_result?.description ||
          rawPoint.gradeResult?.desc ||
          "当前仅展示基础分级结果。"
      },
      review: {
        text:
          rawPoint.review_learning?.text ||
          rawPoint.review?.text ||
          "人工复核当前风险点并生成学习反馈。",
        note:
          rawPoint.review_learning?.note ||
          rawPoint.review?.note ||
          "进入详情页填写复核内容。"
      }
    };
  }

  async function loadJsonFile(path) {
    const response = await fetch(path);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
  }

  async function loadTextFile(path) {
    const response = await fetch(path);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.text();
  }

  async function loadInspectionTextRecords(point) {
    if (!point.inspectionTextSources.length) {
      return point.inspectionRecords;
    }

    const cacheKey = `${point.id}:${point.inspectionTextSources.join("|")}`;
    if (inspectionTextCache.has(cacheKey)) {
      return inspectionTextCache.get(cacheKey);
    }

    const records = await Promise.all(
      point.inspectionTextSources.map(async (sourcePath, index) => {
        try {
          const rawText = await loadTextFile(sourcePath);
          const summary = rawText
            .split(/\r?\n/)
            .map((line) => line.trim())
            .filter(Boolean)
            .join("\n");

          return {
            title: `${point.name} 巡检记录 ${index + 1}`,
            time: point.latestTime || "",
            summary,
            tone: point.riskClass === "risk-i" ? "danger" : point.riskClass === "risk-ii" ? "green" : "blue"
          };
        } catch (error) {
          return {
            title: `${point.name} 巡检记录 ${index + 1}`,
            time: point.latestTime || "",
            summary: "巡检文本加载失败",
            tone: "blue"
          };
        }
      })
    );

    inspectionTextCache.set(cacheKey, records);
    return records;
  }

  async function loadMonitorTextRecords(point) {
    if (!point.monitorTextSources.length) {
      return [];
    }

    const cacheKey = `${point.id}:${point.monitorTextSources.join("|")}`;
    if (monitorTextCache.has(cacheKey)) {
      return monitorTextCache.get(cacheKey);
    }

    const records = await Promise.all(
      point.monitorTextSources.map(async (sourcePath, index) => {
        try {
          const rawText = await loadTextFile(sourcePath);
          return {
            title: `${point.name} 监测记录 ${index + 1}`,
            time: point.latestTime || "",
            summary: rawText
              .split(/\r?\n/)
              .map((line) => line.trim())
              .filter(Boolean)
              .join("\n")
          };
        } catch (error) {
          return {
            title: `${point.name} 监测记录 ${index + 1}`,
            time: point.latestTime || "",
            summary: "监测记录加载失败"
          };
        }
      })
    );

    monitorTextCache.set(cacheKey, records);
    return records;
  }

  async function loadAppData() {
    try {
      const [bridgeData, scopeData] = await Promise.all([
        loadJsonFile("../data/info/bridge.json"),
        loadJsonFile("../data/info/scope.json")
      ]);

      appData.points = [...(bridgeData.points || []), ...(scopeData.points || [])].map(normalizePoint);
    } catch (error) {
      const fallback = Array.isArray(window.RISK_APP_DATA?.points) ? window.RISK_APP_DATA.points : [];
      appData.points = fallback.map(normalizePoint);
    }

    if (appData.points.length && !appData.points.some((item) => item.type === currentType)) {
      currentType = appData.points[0].type;
    }
  }

  function getPointsByType(type) {
    return appData.points.filter((item) => item.type === type);
  }

  function getRiskCounts(points) {
    return {
      "I级": points.filter((item) => item.riskLevel === "I级").length,
      "II级": points.filter((item) => item.riskLevel === "II级").length,
      "III级": points.filter((item) => item.riskLevel === "III级").length,
      "IV级": points.filter((item) => item.riskLevel === "IV级").length
    };
  }

  function initDashboard() {
    const bridgeCount = getPointsByType("桥梁").length;
    const slopeCount = getPointsByType("边坡").length;
    const riskCount = getRiskCounts(appData.points);

    currentTimeEl.textContent = appData.dashboard.currentTime;
    monitorCountEl.textContent = appData.points.length;
    typeBreakdownEl.textContent = `${bridgeCount} / ${slopeCount}`;
    alertBreakdownEl.textContent = `${riskCount["I级"]} 高 · ${riskCount["II级"]} 中 · ${riskCount["III级"] + riskCount["IV级"]} 低`;
    listSummaryEl.textContent = `桥梁：${bridgeCount} 处 | 边坡：${slopeCount} 处`;
  }

  function setActiveTabs() {
    tabButtons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.type === currentType);
    });
  }

  function setActivePoint(pointId) {
    pointListEl.querySelectorAll(".point-item").forEach((item) => {
      item.classList.toggle("is-active", item.dataset.pointId === pointId);
    });
  }

  function buildPointCard(point, isActive) {
    return `
      <button class="point-item ${isActive ? "is-active" : ""}" type="button" data-point-id="${point.id}">
        <div class="point-item-head">
          <strong>${point.name}</strong>
          <span class="type-pill">${point.type}</span>
        </div>
        <div class="point-item-meta">
          <span class="risk-pill ${point.riskClass}">${point.riskLevel}风险</span>
          <span>最新事件：${point.latestEvent}</span>
          <span>时间：${point.latestTime || "未设置"}</span>
        </div>
      </button>
    `;
  }

  function renderList() {
    const visiblePoints = getPointsByType(currentType);
    pointListEl.innerHTML = visiblePoints
      .map((point, index) => buildPointCard(point, index === 0))
      .join("");
  }

  function buildMarkerHtml(point) {
    return `
      <div class="map-marker ${point.riskClass}">
        <span class="map-marker-pulse"></span>
        <span class="map-marker-core"></span>
      </div>
    `;
  }

  function buildPopupHtml(point) {
    return `
      <div class="map-popup">
        <strong>${point.name}</strong>
        <span>${point.type} · ${point.riskLevel}</span>
        <span>${point.lnglat}</span>
      </div>
    `;
  }

  function renderMapFallback(message) {
    mapRootEl.innerHTML = `
      <div class="map-fallback">
        <strong>地图加载失败</strong>
        <p>${message || "当前无法加载广西地图数据，但仍可使用左侧列表查看详情。"}</p>
      </div>
    `;
  }

  function buildRegionLabel(feature) {
    const center = feature.properties?.center;
    if (!Array.isArray(center) || center.length !== 2) {
      return null;
    }

    return window.L.marker([center[1], center[0]], {
      interactive: false,
      icon: window.L.divIcon({
        className: "region-label-wrap",
        html: `<span class="region-label">${feature.properties.name}</span>`
      })
    });
  }

  function showMarkersByType(type) {
    const bounds = [];

    markerById.forEach((marker, pointId) => {
      const point = appData.points.find((item) => item.id === pointId);
      if (!point) {
        return;
      }

      if (point.type === type) {
        marker.addTo(mapInstance);
        const lngLat = parseLngLat(point.lnglat);
        if (lngLat) {
          bounds.push([lngLat.lat, lngLat.lng]);
        }
      } else {
        marker.remove();
      }
    });

    if (!mapInstance || !bounds.length) {
      return;
    }

    const markerBounds = window.L.latLngBounds(bounds);
    const targetBounds =
      provinceLayer && provinceLayer.getBounds().isValid()
        ? provinceLayer.getBounds().extend(markerBounds)
        : markerBounds;

    mapInstance.fitBounds(targetBounds.pad(0.04), {
      padding: [48, 48],
      maxZoom: 8
    });
  }

  function focusMarker(point) {
    if (!mapInstance) {
      return;
    }

    const marker = markerById.get(point.id);
    if (!marker) {
      return;
    }

    if (activeMarker) {
      activeMarker.getElement()?.classList.remove("is-active");
    }

    activeMarker = marker;
    marker.addTo(mapInstance);
    marker.getElement()?.classList.add("is-active");
    marker.openPopup();

    const lngLat = parseLngLat(point.lnglat);
    if (lngLat) {
      mapInstance.flyTo([lngLat.lat, lngLat.lng], Math.max(mapInstance.getZoom(), 9), {
        duration: 0.8
      });
    }
  }

  async function renderMap() {
    if (!window.L || !mapRootEl) {
      renderMapFallback("地图组件未加载。");
      return;
    }

    mapInstance = window.L.map(mapRootEl, {
      crs: window.L.CRS.EPSG4326,
      zoomControl: true,
      attributionControl: false
    });
    mapInstance.setView([22.9, 108.3], 7);

    try {
      const response = await fetch("./data/guangxi.json");
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const geoJson = await response.json();
      const provinceFeature = geoJson.features.find((feature) => feature.properties?.level === 1);
      const cityFeatures = geoJson.features.filter((feature) => feature.properties?.level === 2);

      window.L.geoJSON(cityFeatures, {
        style: function () {
          return {
            color: "#bdd1e7",
            weight: 1.2,
            fillColor: "#f8fbff",
            fillOpacity: 0.96
          };
        }
      }).addTo(mapInstance);

      cityFeatures.forEach((feature) => {
        const label = buildRegionLabel(feature);
        if (label) {
          label.addTo(mapInstance);
        }
      });

      if (provinceFeature) {
        provinceLayer = window.L.geoJSON(provinceFeature, {
          style: function () {
            return {
              color: "#7ea1c6",
              weight: 2.6,
              fillColor: "#edf5ff",
              fillOpacity: 0.1
            };
          }
        }).addTo(mapInstance);

        const provinceBounds = provinceLayer.getBounds();
        if (provinceBounds.isValid()) {
          mapInstance.fitBounds(provinceBounds.pad(0.06));
          mapInstance.setMaxBounds(provinceBounds.pad(0.18));
        }
      }
    } catch (error) {
      renderMapFallback("广西地图边界数据加载失败。");
      return;
    }

    appData.points.forEach((point) => {
      const lngLat = parseLngLat(point.lnglat);
      if (!lngLat) {
        return;
      }

      const marker = window.L.marker([lngLat.lat, lngLat.lng], {
        icon: window.L.divIcon({
          className: "map-marker-wrap",
          html: buildMarkerHtml(point),
          iconSize: [28, 28],
          iconAnchor: [14, 14],
          popupAnchor: [0, -14]
        })
      });

      marker.bindPopup(buildPopupHtml(point), {
        closeButton: false,
        offset: [0, -8]
      });

      marker.on("click", function () {
        currentType = point.type;
        setActiveTabs();
        renderList();
        setActivePoint(point.id);
        showMarkersByType(currentType);
        focusMarker(point);
        openDetail(point);
      });

      markerById.set(point.id, marker);
    });

    showMarkersByType(currentType);
  }

  function renderBasic(point) {
    return `
      <div class="card-head">
        <div>
          <h3>基础信息</h3>
        </div>
      </div>
      <div class="basic-block">
        <h4>${point.name}</h4>
        <div class="basic-tags">
          <span class="type-pill">${point.type}</span>
          <span class="risk-pill ${point.riskClass}">${point.riskLevel}风险</span>
        </div>
      </div>
      <div class="info-grid">
        <div><span>编号</span><strong>${point.id}</strong></div>
        <div><span>类型</span><strong>${point.type}</strong></div>
        <div><span>位置</span><strong>${point.locationText}</strong></div>
        <div><span>经纬度</span><strong>${point.lnglat || "未设置"}</strong></div>
      </div>
      ${point.inspectionSummary ? `<p class="summary-text">${point.inspectionSummary}</p>` : ""}
    `;
  }

  function renderMonitorList(point) {
    const monitors = point.monitorTextRecords?.length
      ? point.monitorTextRecords
          .map(
            (record) => `
              <div class="inspection-text-card">
                <strong>${record.title}</strong>
                <span>${record.time || ""}</span>
                <p>${record.summary || ""}</p>
              </div>
            `
          )
          .join("")
      : point.monitoringPoints.length
        ? point.monitoringPoints
            .map(
              (monitor) => `
                <div class="monitor-row">
                  <div>
                    <strong>${monitor.name}</strong>
                    <span>${monitor.time || ""}</span>
                  </div>
                  <div>
                    <strong>${monitor.value || "-"}</strong>
                    <span>${monitor.status || "-"}</span>
                  </div>
                </div>
              `
            )
            .join("")
        : '<div class="empty-graph">当前未接入监测点详情</div>';

    return `
      <div class="card-head">
        <div>
          <h3>巡检检测记录</h3>
          <p>${(point.monitorTextRecords?.length || point.monitoringPoints.length)} 条监测记录 / ${point.inspectionRecords.length} 条巡检记录</p>
        </div>
      </div>
      <div class="section-block">
        <p class="section-title">巡检记录</p>
        <button class="inspection-summary-card" type="button" data-open-inspection-page="true">
          <p>巡检记录</p>
        </button>
      </div>
      <div class="section-block">
        <p class="section-title">监测点信息</p>
        <div class="monitor-list">${monitors}</div>
      </div>
    `;
  }

  function renderGrade(point) {
    return `
      <div class="card-head">
        <div>
          <h3>分级结果</h3>
        </div>
        <button class="primary-outline small" type="button">查看详情</button>
      </div>
      <div class="grade-result">
        <div class="grade-badge ${point.riskClass}">${point.gradeResult.level}</div>
        <p>${point.gradeResult.desc}</p>
      </div>
    `;
  }

  function renderReview(point) {
    return `
      <div class="card-head">
        <div>
          <h3>复核学习</h3>
          <p>${point.review.text}</p>
        </div>
        <button class="primary-btn small" type="button" data-open-review-form="true">填写内容</button>
      </div>
      <div class="review-box">
        <p>${point.review.note}</p>
      </div>
    `;
  }

  function showOverviewView() {
    detailOverviewEl.classList.remove("hidden");
    detailReviewPageEl.classList.add("hidden");
    detailInspectionPageEl.classList.add("hidden");
  }

  function showReviewView(point) {
    currentDetailPoint = point;
    detailOverviewEl.classList.add("hidden");
    detailReviewPageEl.classList.remove("hidden");
    detailInspectionPageEl.classList.add("hidden");
    reviewPageSubtitleEl.textContent = point.locationText || point.name;
    reviewNodeGradeEl.value = point.gradeResult.level;
    reviewManualGradeEl.value = point.gradeResult.level;
    reviewRemarkEl.value = "";
    reviewResultPanelEl.textContent = "暂无复核结果。";
  }

  function showInspectionView(point) {
    currentDetailPoint = point;
    detailOverviewEl.classList.add("hidden");
    detailReviewPageEl.classList.add("hidden");
    detailInspectionPageEl.classList.remove("hidden");
    inspectionPageSubtitleEl.textContent = point.locationText || point.name;
    inspectionSummaryPanelEl.innerHTML = `
      <div class="inspection-summary-meta">
        <div><span>检测点</span><strong>${point.name}</strong></div>
        <div><span>巡检记录条数</span><strong>${point.inspectionRecords.length}</strong></div>
        <div><span>最新时间</span><strong>${point.latestTime || "未设置"}</strong></div>
      </div>
    `;
    inspectionDetailPanelEl.innerHTML = point.inspectionRecords.length
      ? point.inspectionRecords
          .map(
            (record) => `
              <div class="inspection-text-card">
                <strong>${record.title}</strong>
                <span>${record.time || ""}</span>
                <p>${record.summary || ""}</p>
              </div>
            `
          )
          .join("")
      : '<div class="empty-graph">当前未接入巡检记录详情</div>';
  }

  function collectCheckedValue(name) {
    const target = document.querySelector(`input[name="${name}"]:checked`);
    return target ? target.value : "";
  }

  function renderGraph(containerId, graph) {
    const container = document.getElementById(containerId);
    if (!graph.nodes.length) {
      container.innerHTML = '<div class="empty-graph">当前节点暂无图谱数据</div>';
      return;
    }

    function getNodeWidth(node) {
      return Math.max(148, Math.min(220, 84 + node.label.length * 16));
    }

    const lines = graph.links
      .map((link, index) => {
        const from = graph.nodes[link.from];
        const to = graph.nodes[link.to];
        const tx = (from.x + to.x) / 2;
        const ty = (from.y + to.y) / 2;
        const dx = to.x - from.x;
        const dy = to.y - from.y;
        const len = Math.sqrt(dx * dx + dy * dy) || 1;
        const offsetX = (dy / len) * 16;
        const offsetY = (-dx / len) * 16;
        return `
          <g class="graph-edge-group" style="animation-delay:${index * 120}ms">
            <line class="graph-edge" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}"></line>
            <rect class="graph-edge-label-bg" x="${tx - 50 + offsetX}" y="${ty - 16 + offsetY}" rx="12" ry="12" width="100" height="30"></rect>
            <text class="graph-edge-label" x="${tx + offsetX}" y="${ty + 4 + offsetY}">${link.text}</text>
          </g>
        `;
      })
      .join("");

    const nodes = graph.nodes
      .map((node, index) => {
        const width = getNodeWidth(node);
        const x = node.x - width / 2;
        const y = node.y - 42;
        return `
          <g class="graph-node-card ${node.kind}" style="animation-delay:${index * 90}ms">
            <circle class="graph-node-halo" cx="${node.x}" cy="${node.y}" r="52"></circle>
            <rect class="graph-node-box" x="${x}" y="${y}" rx="22" ry="22" width="${width}" height="84"></rect>
            <circle class="graph-node-dot" cx="${x + 22}" cy="${y + 24}" r="7"></circle>
            <text class="graph-node-title" x="${x + 38}" y="${y + 30}">${node.label}</text>
            <text class="graph-node-meta" x="${x + 18}" y="${y + 58}">${node.role}</text>
            <text class="graph-node-meta sub" x="${x + 18}" y="${y + 76}">关联度 ${node.degree}</text>
          </g>
        `;
      })
      .join("");

    container.innerHTML = `
      <div class="graph-interact-hint">滚轮缩放，拖拽平移，双击重置</div>
      <div class="graph-canvas" data-graph-canvas="true">
        <svg viewBox="0 0 1280 1040" preserveAspectRatio="xMidYMid meet">
          <defs>
            <marker id="graph-arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">
              <path d="M0,0 L12,6 L0,12 z" class="graph-arrow-head"></path>
            </marker>
          </defs>
          <g class="graph-links">${lines}</g>
          <g class="graph-nodes">${nodes}</g>
        </svg>
      </div>
    `;

    bindGraphInteractions(container);
  }

  function bindGraphInteractions(container) {
    const canvas = container.querySelector("[data-graph-canvas='true']");
    const svg = canvas?.querySelector("svg");
    if (!canvas || !svg) {
      return;
    }

    let scale = 1;
    let offsetX = 0;
    let offsetY = 0;
    let isDragging = false;
    let startX = 0;
    let startY = 0;

    function applyTransform() {
      svg.style.transform = `translate(${offsetX}px, ${offsetY}px) scale(${scale})`;
    }

    function resetTransform() {
      scale = 1;
      offsetX = 0;
      offsetY = 0;
      applyTransform();
    }

    canvas.addEventListener(
      "wheel",
      function (event) {
        event.preventDefault();
        const delta = event.deltaY < 0 ? 0.12 : -0.12;
        scale = Math.max(0.65, Math.min(2.2, scale + delta));
        applyTransform();
      },
      { passive: false }
    );

    canvas.addEventListener("mousedown", function (event) {
      isDragging = true;
      startX = event.clientX - offsetX;
      startY = event.clientY - offsetY;
      canvas.classList.add("is-dragging");
    });

    window.addEventListener("mousemove", function (event) {
      if (!isDragging) {
        return;
      }
      offsetX = event.clientX - startX;
      offsetY = event.clientY - startY;
      applyTransform();
    });

    window.addEventListener("mouseup", function () {
      isDragging = false;
      canvas.classList.remove("is-dragging");
    });

    canvas.addEventListener("dblclick", function () {
      resetTransform();
    });

    resetTransform();
  }

  function parseCanonTriples(rawText) {
    const lines = rawText
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);

    if (!lines.length) {
      return [];
    }

    try {
      return JSON.parse(lines[0].replace(/'/g, '"'));
    } catch (error) {
      return [];
    }
  }

  function serializeTriplesKey(triple) {
    return triple.map((item) => String(item)).join("||");
  }

  function dedupeTriples(triples) {
    const seen = new Set();
    return triples.filter((triple) => {
      if (!Array.isArray(triple) || triple.length < 3) {
        return false;
      }
      const key = serializeTriplesKey(triple);
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }

  function buildGraphFromTriples(triples) {
    const nodeMap = new Map();
    const links = [];
    const subjectSet = new Set();
    const objectSet = new Set();

    triples.forEach((triple) => {
      if (!Array.isArray(triple) || triple.length < 3) {
        return;
      }

      const [subject, predicate, object] = triple.map((item) => String(item));
      subjectSet.add(subject);
      objectSet.add(object);

      if (!nodeMap.has(subject)) {
        nodeMap.set(subject, { label: subject, degree: 0 });
      }
      if (!nodeMap.has(object)) {
        nodeMap.set(object, { label: object, degree: 0 });
      }

      nodeMap.get(subject).degree += 1;
      nodeMap.get(object).degree += 1;
      links.push({
        from: subject,
        to: object,
        text: predicate
      });
    });

    const nodes = Array.from(nodeMap.values()).map((node) => {
      let role = "属性值";
      let kind = "value";
      if (subjectSet.has(node.label) && objectSet.has(node.label)) {
        role = "中间实体";
        kind = "hub";
      } else if (subjectSet.has(node.label)) {
        role = "巡检实体";
        kind = "entity";
      }
      return {
        ...node,
        role,
        kind
      };
    });

    const entityNodes = nodes.filter((node) => node.kind === "entity");
    const hubNodes = nodes.filter((node) => node.kind === "hub");
    const valueNodes = nodes.filter((node) => node.kind === "value");

    function layoutColumn(items, x, minY, maxY, preferredGap) {
      if (!items.length) {
        return [];
      }

      const availableHeight = maxY - minY;
      const computedGap =
        items.length > 1 ? Math.min(preferredGap, availableHeight / (items.length - 1)) : 0;
      const totalHeight = (items.length - 1) * computedGap;
      const startY = minY + (availableHeight - totalHeight) / 2;

      return items.map((item, index) => ({
        ...item,
        x,
        y: startY + index * computedGap
      }));
    }

    const positionedNodes = [
      ...layoutColumn(entityNodes, 220, 120, 920, 126),
      ...layoutColumn(hubNodes, 560, 220, 820, 118),
      ...layoutColumn(valueNodes, 980, 90, 950, 108)
    ];

    const nodeIndex = new Map(positionedNodes.map((node, index) => [node.label, index]));
    const normalizedLinks = links
      .map((link) => ({
        from: nodeIndex.get(link.from),
        to: nodeIndex.get(link.to),
        text: link.text
      }))
      .filter((link) => Number.isInteger(link.from) && Number.isInteger(link.to));

    return {
      meta: `${positionedNodes.length} 个节点 / ${normalizedLinks.length} 条关系`,
      nodes: positionedNodes,
      links: normalizedLinks
    };
  }

  async function loadTriplesFromPath(sourcePath) {
    if (!sourcePath) {
      return [];
    }

    if (tripleCache.has(sourcePath)) {
      return tripleCache.get(sourcePath);
    }

    try {
      const response = await fetch(sourcePath);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const rawText = await response.text();
      const triples = dedupeTriples(parseCanonTriples(rawText));
      tripleCache.set(sourcePath, triples);
      return triples;
    } catch (error) {
      return [];
    }
  }

  function getGraphSourcePaths(graph) {
    const sourcePaths = Array.isArray(graph?.sourcePaths) ? graph.sourcePaths.filter(Boolean) : [];
    if (sourcePaths.length) {
      return sourcePaths;
    }
    return graph?.sourcePath ? [graph.sourcePath] : [];
  }

  async function loadTriplesFromPaths(sourcePaths) {
    if (!sourcePaths.length) {
      return [];
    }

    const tripletGroups = await Promise.all(sourcePaths.map((sourcePath) => loadTriplesFromPath(sourcePath)));
    return dedupeTriples(tripletGroups.flat());
  }

  function buildMonitoringTriples(point) {
    const triples = [];
    const monitoringRoot = `${point.name}监测记录`;

    point.monitoringPoints.forEach((monitor) => {
      triples.push([point.name, "关联监测", monitor.name]);
      triples.push([monitoringRoot, "包含记录", monitor.name]);
      triples.push([monitor.name, "状态", monitor.status]);
      triples.push([monitor.name, "数值", monitor.value]);
      triples.push([monitor.name, "时间", monitor.time]);
    });

    if (point.monitoringPoints.some((monitor) => monitor.status === "异常")) {
      triples.push([point.name, "发现异常", "监测异常"]);
    }

    return dedupeTriples(triples);
  }

  async function loadInspectionGraph(graph) {
    const sourcePaths = getGraphSourcePaths(graph);
    if (!sourcePaths.length) {
      return { meta: "0 个节点 / 0 条关系", nodes: [], links: [] };
    }

    const cacheKey = `inspection:${sourcePaths.join("|")}`;
    if (graphCache.has(cacheKey)) {
      return graphCache.get(cacheKey);
    }

    const triples = await loadTriplesFromPaths(sourcePaths);
    const parsedGraph = buildGraphFromTriples(triples);
    graphCache.set(cacheKey, parsedGraph);
    return parsedGraph;
  }

  async function loadMonitoringFusionGraph(point) {
    const inspectionSourcePaths = getGraphSourcePaths(point.inspectionGraph);
    const monitorSourcePaths = getGraphSourcePaths(point.monitorGraph);
    const cacheKey = `monitor:${point.id}:${inspectionSourcePaths.join("|")}:${monitorSourcePaths.join("|")}`;

    if (graphCache.has(cacheKey)) {
      return graphCache.get(cacheKey);
    }

    const [inspectionTriples, generatedMonitoringTriples] = await Promise.all([
      loadTriplesFromPaths(inspectionSourcePaths),
      loadTriplesFromPaths(monitorSourcePaths)
    ]);
    const fallbackMonitoringTriples = generatedMonitoringTriples.length ? [] : buildMonitoringTriples(point);
    const mergedTriples = dedupeTriples([
      ...inspectionTriples,
      ...generatedMonitoringTriples,
      ...fallbackMonitoringTriples
    ]);
    const fusionGraph = buildGraphFromTriples(mergedTriples);
    graphCache.set(cacheKey, fusionGraph);
    return fusionGraph;
  }

  async function openDetail(point) {
    const inspectionRecords = await loadInspectionTextRecords(point);
    const monitorTextRecords = await loadMonitorTextRecords(point);
    const detailPoint = {
      ...point,
      inspectionRecords,
      monitorTextRecords
    };

    currentDetailPoint = detailPoint;
    showOverviewView();

    document.getElementById("detail-title").textContent = `${detailPoint.name} 风险点详情`;
    document.getElementById("detail-basic").innerHTML = renderBasic(detailPoint);
    document.getElementById("detail-monitor-list").innerHTML = renderMonitorList(detailPoint);
    document.getElementById("detail-grade").innerHTML = renderGrade(detailPoint);
    document.getElementById("detail-review").innerHTML = renderReview(detailPoint);

    document.getElementById("inspection-graph").innerHTML =
      '<div class="empty-graph">正在加载后端巡检知识图谱...</div>';
    document.getElementById("monitor-graph").innerHTML =
      '<div class="empty-graph">正在合并巡检三元组与监测新增三元组...</div>';
    document.getElementById("inspection-graph-meta").textContent = "正在读取巡检三元组...";
    document.getElementById("monitor-graph-meta").textContent = "正在生成监测融合图谱...";

    const inspectionGraph = await loadInspectionGraph(detailPoint.inspectionGraph);
    const monitorFusionGraph = await loadMonitoringFusionGraph(detailPoint);

    document.getElementById("inspection-graph-meta").textContent = inspectionGraph.meta;
    document.getElementById("monitor-graph-meta").textContent = monitorFusionGraph.meta;
    renderGraph("inspection-graph", inspectionGraph);
    renderGraph("monitor-graph", monitorFusionGraph);

    modalEl.classList.remove("hidden");
    document.body.classList.add("modal-open");
  }

  function bindListEvents() {
    pointListEl.addEventListener("click", function (event) {
      const target = event.target.closest("[data-point-id]");
      if (!target) {
        return;
      }

      const point = appData.points.find((item) => item.id === target.dataset.pointId);
      if (!point) {
        return;
      }

      setActivePoint(point.id);
      focusMarker(point);
      openDetail(point);
    });
  }

  function bindTabs() {
    tabButtons.forEach((button) => {
      button.addEventListener("click", function () {
        currentType = button.dataset.type;
        setActiveTabs();
        renderList();
        showMarkersByType(currentType);
      });
    });
  }

  function bindModal() {
    document.addEventListener("click", function (event) {
      const reviewTrigger = event.target.closest("[data-open-review-form]");
      if (reviewTrigger && currentDetailPoint) {
        showReviewView(currentDetailPoint);
        return;
      }

      const inspectionTrigger = event.target.closest("[data-open-inspection-page]");
      if (inspectionTrigger && currentDetailPoint) {
        showInspectionView(currentDetailPoint);
        return;
      }

      const trigger = event.target.closest("[data-close-modal]");
      if (!trigger) {
        return;
      }

      modalEl.classList.add("hidden");
      document.body.classList.remove("modal-open");
      showOverviewView();
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        modalEl.classList.add("hidden");
        document.body.classList.remove("modal-open");
        showOverviewView();
      }
    });

    reviewBackBtn.addEventListener("click", function () {
      showOverviewView();
    });

    inspectionBackBtn.addEventListener("click", function () {
      showOverviewView();
    });

    reviewSubmitBtn.addEventListener("click", function () {
      const summary = [
        `节点等级：${reviewNodeGradeEl.value}`,
        `人工修正等级：${reviewManualGradeEl.value}`,
        `人工结论：${collectCheckedValue("review-conclusion")}`,
        `是否正确：${collectCheckedValue("review-correct")}`,
        `备注：${reviewRemarkEl.value || "无"}`
      ];
      reviewResultPanelEl.innerHTML = summary.map((item) => `<p>${item}</p>`).join("");
    });
  }

  async function init() {
    await loadAppData();
    initDashboard();
    setActiveTabs();
    renderList();
    bindListEvents();
    bindTabs();
    bindModal();
    await renderMap();
  }

  init();
})();
