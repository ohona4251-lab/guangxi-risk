# AGENTS.md

## 目标

请在当前仓库中生成一个**可运行但业务逻辑留空**的 LangGraph Graph API 项目骨架，用于实现如下风险评估工作流。当前阶段**只要求完整图结构、状态定义、节点定义、条件边、人工复核中断与回环逻辑**，**不要实现具体业务算法**（例如规则解析、知识图谱构建、异常检测、风险推理等）。并且我想持久化到磁盘/数据库，要换成持久化 checkpointer。SQLite

项目最终应做到：

1. 能清晰表达完整的 LangGraph 执行图。
2. 所有节点、条件边、回环边都已定义完成。
3. 代码结构清晰，后续容易逐步填充业务逻辑。
4. 支持人工复核节点的中断/恢复设计。
5. 支持复核不通过后，进入“更新巡检规则”节点，并重新从图谱构建开始执行，直到人工复核通过才结束。

---

## 业务流程（最终编号）

请严格按下面 8 个业务步骤生成图：

1. **解析巡检规则**
2. **构建初始知识图谱**
3. **获取并分析监测异常**
4. **异常补图谱与重构**
5. **风险分级和依据生成**
6. **历史结果校验**
7. **人工复核**
8. **更新巡检规则**

### 主流程

```text
1 -> 2 -> 3 -> (若异常则 4，否则跳过 4) -> 5 -> 6 -> 7
```

### 复核回环逻辑

- 如果第 7 步“人工复核”**通过**，流程结束。
- 如果第 7 步“人工复核”**不通过**，进入第 8 步“更新巡检规则”。
- 第 8 步完成后，重新从第 2 步“构建初始知识图谱”开始继续执行。
- 之后再次依次执行到第 7 步。
- **只有第 7 步人工复核通过时，整个图才能结束。**

### 等价流程图语义

```text
START
  -> 1 解析巡检规则
  -> 2 构建初始知识图谱
  -> 3 获取并分析监测异常
  -> [条件分支]
       - 有异常  -> 4 异常补图谱与重构 -> 5 风险分级和依据生成
       - 无异常  -> 5 风险分级和依据生成
  -> 6 历史结果校验
  -> 7 人工复核
  -> [条件分支]
       - 通过    -> END
       - 不通过  -> 8 更新巡检规则 -> 2 构建初始知识图谱 -> ... -> 7 人工复核
```

---

## 节点命名要求

请使用英文函数名和节点名，建议严格采用如下命名：

1. `parse_inspection_rules`
2. `build_initial_kg`
3. `fetch_and_analyze_monitoring`
4. `reconstruct_kg_with_anomaly`
5. `generate_risk_grade_and_basis`
6. `validate_with_history`
7. `human_review`
8. `update_inspection_rules`

路由函数建议使用：

- `route_after_monitoring`
- `route_after_human_review`

---

## 状态设计要求

请定义一个统一的 Graph State，例如：

```python
class RiskWorkflowState(TypedDict, total=False):
    case_id: str
    object_id: str

    # 输入
    raw_rule_docs: list[str]
    inspection_text: str
    object_meta: dict
    monitoring_data: dict
    history_records: list[dict]

    # 规则相关
    parsed_rules: dict
    updated_rules: dict
    required_info: list[str]
    rule_update_log: list[dict]

    # 图谱相关
    initial_kg: dict
    reconstructed_kg: dict
    kg_updated: bool

    # 监测异常相关
    anomaly_detected: bool
    anomaly_list: list[dict]
    anomaly_summary: str

    # 风险分级相关
    candidate_risk_level: str
    grading_basis: dict
    explanation: str

    # 历史校验相关
    history_validation_report: dict
    validated_result: dict

    # 人工复核相关
    review_payload: dict
    review_decision: str
    review_comment: str
```
```

### 状态设计原则

1. 每个节点都应只返回**自己负责更新的 state 字段**。
2. 不要在节点内部直接修改原 state；请返回 partial update。
3. 字段命名清晰，便于后续逐步填充业务逻辑。
4. 要给关键字段写清晰注释。

---

## 各节点职责要求

### 1. `parse_inspection_rules`
职责：
- 接收原始巡检规则文档。
- 输出解析后的规则结构。
- 这里只做骨架，不做真实解析。

建议返回：
- `parsed_rules`
- `required_info`

### 2. `build_initial_kg`
职责：
- 根据规则、现场描述、对象元信息构建初始知识图谱。
- 当前阶段只生成占位图谱结构。

建议返回：
- `initial_kg`

### 3. `fetch_and_analyze_monitoring`
职责：
- 读取监测数据。
- 判断短期监测数据是否异常。
- 这里不要实现真实算法，但要保留明确输出结构。

建议返回：
- `anomaly_detected`
- `anomaly_list`
- `anomaly_summary`

### 4. `reconstruct_kg_with_anomaly`
职责：
- 当存在异常且需要补图谱时，将异常补入图谱并重构。
- 当前阶段只做占位重构。

建议返回：
- `reconstructed_kg`
- `kg_updated`

### 5. `generate_risk_grade_and_basis`
职责：
- 基于规则、图谱、异常信息，输出候选风险等级和依据。
- 当前阶段返回结构化占位结果。

建议返回：
- `candidate_risk_level`
- `grading_basis`
- `explanation`

### 6. `validate_with_history`
职责：
- 使用历史记录对当前候选结果进行校验。
- 当前阶段只生成占位校验结果。

建议返回：
- `history_validation_report`
- `validated_result`
- `review_payload`

### 7. `human_review`
职责：
- 作为人工复核节点。
- 需要具备等待人工输入的语义。
- 当前阶段允许使用占位实现，但代码结构上要预留成可替换为 `interrupt(...)` 的形式。

建议返回：
- `review_decision`
- `review_comment`

### 8. `update_inspection_rules`
职责：
- 当人工复核不通过时，根据复核意见修正规则。
- 当前阶段只生成修正规则的占位结果。

建议返回：
- `updated_rules`
- `parsed_rules`
- `rule_update_log`

---

## 条件边要求

### 条件边 1：监测异常分支
在 `fetch_and_analyze_monitoring` 节点之后添加条件边：

- 若 `anomaly_detected == True`，进入 `reconstruct_kg_with_anomaly`
- 若 `anomaly_detected == False`，直接进入 `generate_risk_grade_and_basis`

请实现一个路由函数：

```python
def route_after_monitoring(state: RiskWorkflowState) -> str:
    ...
```

返回值建议严格使用：

- `"reconstruct_kg_with_anomaly"`
- `"generate_risk_grade_and_basis"`

### 条件边 2：人工复核分支
在 `human_review` 节点之后添加条件边：

- 若 `review_decision == "approved"`，进入 `END`
- 若 `review_decision == "rejected"`，进入 `update_inspection_rules`

请实现一个路由函数：

```python
def route_after_human_review(state: RiskWorkflowState) -> str:
    ...
```

返回值建议严格使用：

- `"__end__"`
- `"update_inspection_rules"`

---

## 边定义要求

请按下面顺序搭图：

### 普通边

- `START -> parse_inspection_rules`
- `parse_inspection_rules -> build_initial_kg`
- `build_initial_kg -> fetch_and_analyze_monitoring`
- `reconstruct_kg_with_anomaly -> generate_risk_grade_and_basis`
- `generate_risk_grade_and_basis -> validate_with_history`
- `validate_with_history -> human_review`
- `update_inspection_rules -> build_initial_kg`

### 条件边

- `fetch_and_analyze_monitoring -> (route_after_monitoring)`
- `human_review -> (route_after_human_review)`



---

## 代码实现要求

### 1. 节点函数要求

每个节点函数：

- 都必须有完整 docstring
- 明确写出输入依赖和输出字段
- 当前阶段只做占位实现
- 不要写伪随机逻辑
- 不要偷偷实现复杂业务推理

建议形式：

```python
def some_node(state: RiskWorkflowState) -> dict:
    """简要说明该节点职责。"""
    return {
        "some_field": ...
    }
```

### 2. 人工复核节点要求

请将 `human_review` 设计为**后续可平滑替换为 interrupt 的接口**。

例如当前版本可以先读取：

- `state.get("review_decision")`
- 若没有，就返回一个占位 `pending` 或默认 `rejected`

但代码注释中要明确说明：

- 正式版应替换为 LangGraph 的 human-in-the-loop / interrupt 方式。
- 需要 checkpointer 支持暂停与恢复。

### 3. 图构建要求

请在 `graph.py` 中：

- 定义 builder
- 注册全部节点
- 注册普通边
- 注册条件边
- 编译 graph
- 导出 `build_graph()` 和 `get_graph()` 等便于复用的方法

### 4. 入口要求

请在 `main.py` 中提供一个最小示例：

- 构造示例 state
- 调用 graph
- 打印执行结果

注意：
- 示例 state 不必真实
- 只要能跑通骨架即可

---

## 质量要求

生成代码时请严格遵守：

1. **先保证图结构正确，再考虑占位实现是否优雅。**
2. **不要实现业务算法。**
3. **不要引入与当前阶段无关的框架。**
4. **不要把所有内容塞到一个文件里。**
5. **不要省略 docstring、类型注解和注释。**
6. **不要使用过度复杂的抽象。**
7. **代码应能作为后续逐步实现的正式骨架。**

---

