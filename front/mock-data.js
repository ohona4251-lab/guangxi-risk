window.RISK_APP_DATA = {
  dashboard: {
    currentTime: "2026-04-23 09:36:09",
    gradingProgress: { done: 18, total: 20 }
  },
  points: [
    {
      id: "BR-BY01",
      name: "白云中桥",
      type: "桥梁",
      riskLevel: "II级",
      riskClass: "risk-ii",
      locationText: "白云中桥",
      lnglat: "110.295, 25.2742",
      region: "桂林市",
      latestEvent: "风险分级",
      latestTime: "2026-04-22 20:24",
      inspectionSummary: "桥面伸缩缝存在异常位移，巡检规则与监测结果存在一致性风险。",
      monitoringPoints: [
        { name: "位移计 M-01", status: "异常", value: "16mm", time: "2026-04-22 15:30" },
        { name: "裂缝计 M-02", status: "关注", value: "2.8mm", time: "2026-04-22 15:30" },
        { name: "倾角计 M-03", status: "正常", value: "0.3°", time: "2026-04-22 15:30" }
      ],
      inspectionRecords: [
        { title: "白云中桥", time: "2026-04-21 11:10:00", summary: "观测项 1 / 图谱 8 节点", tone: "blue" },
        { title: "白云中桥", time: "2026-04-22 15:30:00", summary: "异常 1 / 新增 0", tone: "green" }
      ],
      inspectionGraph: {
        sourcePath:
          "../risk_workflow/outputs/node2/batch_examples_2_example2_bridge_joint_20260422_232822/iter0/canon_kg.txt",
        meta: "8 个节点 / 9 条关系",
        nodes: [
          { label: "白云中桥", x: 50, y: 82, size: "lg" },
          { label: "变形", x: 52, y: 42, size: "md" },
          { label: "2号墩左幅", x: 25, y: 26, size: "md" },
          { label: "2号墩支座", x: 28, y: 68, size: "md" },
          { label: "加固处治", x: 77, y: 18, size: "md" },
          { label: "BR-LOCAL-002", x: 79, y: 64, size: "lg" },
          { label: "现场复核", x: 70, y: 80, size: "md" },
          { label: "监测记录", x: 48, y: 8, size: "sm" }
        ],
        links: [
          { from: 0, to: 1, text: "检测出" },
          { from: 1, to: 2, text: "定位对象" },
          { from: 1, to: 3, text: "发生部位" },
          { from: 1, to: 4, text: "处治参考" },
          { from: 5, to: 1, text: "发现异常" },
          { from: 5, to: 6, text: "转交核验" },
          { from: 6, to: 0, text: "回流结果" },
          { from: 3, to: 0, text: "从属关系" },
          { from: 1, to: 7, text: "关联监测" }
        ]
      },
      monitorGraph: {
        meta: "11 个节点 / 12 条关系",
        nodes: [
          { label: "白云中桥", x: 38, y: 60, size: "md" },
          { label: "2号墩支座", x: 26, y: 20, size: "md" },
          { label: "位移", x: 60, y: 32, size: "md" },
          { label: "场景复核", x: 82, y: 65, size: "md" },
          { label: "BR-LOCAL-002", x: 58, y: 84, size: "lg" },
          { label: "16mm", x: 6, y: 72, size: "sm", kind: "metric" },
          { label: "2.8mm", x: 92, y: 18, size: "sm", kind: "metric" }
        ],
        links: [
          { from: 1, to: 0, text: "监测对象" },
          { from: 0, to: 2, text: "发生部位" },
          { from: 2, to: 3, text: "处置要求" },
          { from: 4, to: 0, text: "补充标识" },
          { from: 4, to: 2, text: "状态同步" },
          { from: 5, to: 4, text: "测量数值" },
          { from: 6, to: 2, text: "阈值参考" }
        ]
      },
      gradeResult: {
        level: "II级",
        desc: "主体分类为桥梁，使用巡检规则链进行匹配，监测值触发二级告警阈值。"
      },
      review: {
        text: "人工复核当前风险点并生成学习反馈。",
        note: "进入详情页填写复核内容。"
      }
    },
    {
      id: "SP-LB13",
      name: "城北1号桥",
      type: "桥梁",
      riskLevel: "III级",
      riskClass: "risk-iii",
      locationText: "柳州市柳北区",
      lnglat: "109.403, 24.339",
      region: "柳州市",
      latestEvent: "风险分级",
      latestTime: "2026-04-22 20:24",
      inspectionSummary: "常规巡检发现伸缩装置轻微劣化，未形成结构性风险。",
      monitoringPoints: [
        { name: "位移计 M-11", status: "正常", value: "6mm", time: "2026-04-22 15:30" },
        { name: "应变计 M-12", status: "正常", value: "83με", time: "2026-04-22 15:30" }
      ],
      inspectionRecords: [
        { title: "城北1号桥", time: "2026-04-20 09:20:00", summary: "观测项 2 / 图谱 6 节点", tone: "blue" }
      ],
      inspectionGraph: { meta: "6 个节点 / 6 条关系", nodes: [], links: [] },
      monitorGraph: { meta: "5 个节点 / 4 条关系", nodes: [], links: [] },
      gradeResult: {
        level: "III级",
        desc: "监测数据平稳，主要由巡检记录轻度异常触发关注。"
      },
      review: {
        text: "建议保持常规巡检频次。",
        note: "暂无额外复核意见。"
      }
    },
    {
      id: "BR-LZ02",
      name: "柳江二桥",
      type: "桥梁",
      riskLevel: "III级",
      riskClass: "risk-iii",
      locationText: "柳江二桥",
      lnglat: "109.376, 24.312",
      region: "柳州市",
      latestEvent: "风险分级",
      latestTime: "2026-04-22 20:24",
      inspectionSummary: "桥面铺装局部病害，对当前风险等级影响有限。",
      monitoringPoints: [
        { name: "裂缝计 M-21", status: "关注", value: "1.7mm", time: "2026-04-22 10:12" }
      ],
      inspectionRecords: [
        { title: "柳江二桥", time: "2026-04-22 10:12:00", summary: "观测项 1 / 轻微异常", tone: "blue" }
      ],
      inspectionGraph: {
        sourcePath:
          "../risk_workflow/outputs/node2/batch_examples_2_example2_bridge_joint_20260422_232822/iter0/canon_kg.txt",
        meta: "5 个节点 / 4 条关系",
        nodes: [],
        links: []
      },
      monitorGraph: { meta: "4 个节点 / 3 条关系", nodes: [], links: [] },
      gradeResult: {
        level: "III级",
        desc: "病害程度较轻，未达到升级阈值。"
      },
      review: {
        text: "建议安排下一周期复检。",
        note: "暂无人工复核变更。"
      }
    },
    {
      id: "BR-HZ07",
      name: "红光大桥",
      type: "桥梁",
      riskLevel: "I级",
      riskClass: "risk-i",
      locationText: "红光大桥",
      lnglat: "108.361, 22.816",
      region: "南宁市",
      latestEvent: "风险分级",
      latestTime: "2026-04-22 20:24",
      inspectionSummary: "主桥关键构件异常位移超阈值，需要立即处置。",
      monitoringPoints: [
        { name: "位移计 M-31", status: "异常", value: "29mm", time: "2026-04-22 18:20" },
        { name: "裂缝计 M-32", status: "异常", value: "5.2mm", time: "2026-04-22 18:20" }
      ],
      inspectionRecords: [
        { title: "红光大桥", time: "2026-04-22 18:20:00", summary: "异常 2 / 需立即复核", tone: "danger" }
      ],
      inspectionGraph: {
        sourcePath:
          "../risk_workflow/outputs/node2/batch_examples_2_example2_bridge_joint_20260422_232822/iter0/canon_kg.txt",
        meta: "7 个节点 / 8 条关系",
        nodes: [],
        links: []
      },
      monitorGraph: { meta: "8 个节点 / 7 条关系", nodes: [], links: [] },
      gradeResult: {
        level: "I级",
        desc: "桥梁关键监测点同时触发多个高危阈值，判定为一级风险。"
      },
      review: {
        text: "应立即组织人工复核与现场处治。",
        note: "该风险点需要强制复核。"
      }
    },
    {
      id: "BR-QS09",
      name: "青秀互通通道桥",
      type: "桥梁",
      riskLevel: "IV级",
      riskClass: "risk-iv",
      locationText: "青秀互通",
      lnglat: "108.398, 22.799",
      region: "南宁市",
      latestEvent: "风险分级",
      latestTime: "2026-04-22 20:24",
      inspectionSummary: "当前结构状态稳定，仅保留常规巡检记录。",
      monitoringPoints: [
        { name: "沉降计 M-41", status: "正常", value: "1mm", time: "2026-04-22 11:40" }
      ],
      inspectionRecords: [
        { title: "青秀互通通道桥", time: "2026-04-22 11:40:00", summary: "状态稳定 / 常规记录", tone: "green" }
      ],
      inspectionGraph: {
        sourcePath:
          "../risk_workflow/outputs/node2/batch_examples_2_example2_bridge_joint_20260422_232822/iter0/canon_kg.txt",
        meta: "4 个节点 / 3 条关系",
        nodes: [],
        links: []
      },
      monitorGraph: { meta: "3 个节点 / 2 条关系", nodes: [], links: [] },
      gradeResult: {
        level: "IV级",
        desc: "未出现异常迹象，维持低风险状态。"
      },
      review: {
        text: "保持例行检查即可。",
        note: "无需人工干预。"
      }
    },
    {
      id: "SL-GZ01",
      name: "贵港东侧高边坡",
      type: "边坡",
      riskLevel: "II级",
      riskClass: "risk-ii",
      locationText: "贵港市港北区",
      lnglat: "109.5989, 23.1115",
      region: "贵港市",
      latestEvent: "风险分级",
      latestTime: "2026-04-22 18:10",
      inspectionSummary: "连续降雨后坡体浅表裂缝扩展，排水沟局部堵塞，需重点关注。",
      monitoringPoints: [
        { name: "雨量计 S-01", status: "关注", value: "68mm", time: "2026-04-22 18:00" },
        { name: "裂缝计 S-02", status: "异常", value: "4.1mm", time: "2026-04-22 18:00" }
      ],
      inspectionRecords: [
        { title: "贵港东侧高边坡", time: "2026-04-22 18:10:00", summary: "裂缝扩展 / 排水受阻", tone: "danger" }
      ],
      inspectionGraph: {
        sourcePath:
          "../risk_workflow/outputs/node2/batch_examples_1_example1_rainfall_slope_20260422_232429/iter0/canon_kg.txt",
        meta: "6 个节点 / 7 条关系",
        nodes: [],
        links: []
      },
      monitorGraph: { meta: "5 个节点 / 5 条关系", nodes: [], links: [] },
      gradeResult: {
        level: "II级",
        desc: "边坡巡检记录与降雨监测共同指向中等级别风险。"
      },
      review: {
        text: "建议安排边坡排水清理与现场复测。",
        note: "需结合下一轮降雨持续跟踪。"
      }
    },
    {
      id: "SL-BH02",
      name: "北海沿线边坡",
      type: "边坡",
      riskLevel: "III级",
      riskClass: "risk-iii",
      locationText: "北海市合浦县",
      lnglat: "109.2005, 21.6616",
      region: "北海市",
      latestEvent: "风险分级",
      latestTime: "2026-04-22 16:40",
      inspectionSummary: "坡面局部冲刷明显，但支护结构整体稳定。",
      monitoringPoints: [
        { name: "位移计 S-11", status: "正常", value: "3mm", time: "2026-04-22 16:30" }
      ],
      inspectionRecords: [
        { title: "北海沿线边坡", time: "2026-04-22 16:40:00", summary: "冲刷 1 处 / 支护稳定", tone: "blue" }
      ],
      inspectionGraph: {
        sourcePath:
          "../risk_workflow/outputs/node2/batch_examples_3_example3_tunnel_slope_20260422_233255/iter0/canon_kg.txt",
        meta: "4 个节点 / 4 条关系",
        nodes: [],
        links: []
      },
      monitorGraph: { meta: "3 个节点 / 2 条关系", nodes: [], links: [] },
      gradeResult: {
        level: "III级",
        desc: "边坡存在轻度病害，暂未触发更高等级告警。"
      },
      review: {
        text: "维持常规巡检，关注强降雨工况。",
        note: "暂无人工复核调整。"
      }
    },
    {
      id: "SL-HC03",
      name: "河池西段边坡",
      type: "边坡",
      riskLevel: "I级",
      riskClass: "risk-i",
      locationText: "河池市金城江区",
      lnglat: "108.0858, 24.6929",
      region: "河池市",
      latestEvent: "风险分级",
      latestTime: "2026-04-22 19:05",
      inspectionSummary: "坡脚渗水增强且局部滑塌，已达到一级风险处置条件。",
      monitoringPoints: [
        { name: "渗压计 S-21", status: "异常", value: "82kPa", time: "2026-04-22 19:00" },
        { name: "位移计 S-22", status: "异常", value: "33mm", time: "2026-04-22 19:00" }
      ],
      inspectionRecords: [
        { title: "河池西段边坡", time: "2026-04-22 19:05:00", summary: "滑塌征兆明显 / 已上报", tone: "danger" }
      ],
      inspectionGraph: {
        sourcePath:
          "../risk_workflow/outputs/node2/batch_examples_1_example1_rainfall_slope_20260422_232429/iter0/canon_kg.txt",
        meta: "7 个节点 / 8 条关系",
        nodes: [],
        links: []
      },
      monitorGraph: { meta: "6 个节点 / 6 条关系", nodes: [], links: [] },
      gradeResult: {
        level: "I级",
        desc: "边坡位移和渗压同步异常，判定为一级风险。"
      },
      review: {
        text: "建议立即封闭现场并组织专家复核。",
        note: "该边坡需优先处置。"
      }
    }
  ]
};
