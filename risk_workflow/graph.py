"""Graph construction utilities for the risk workflow."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .nodes import (
    build_initial_kg,
    fetch_and_analyze_monitoring,
    generate_risk_grade_and_basis,
    human_review,
    parse_inspection_rules,
    reconstruct_kg_with_anomaly,
    update_inspection_rules,
    validate_with_history,
)
from .routes import route_after_human_review, route_after_monitoring
from .state import RiskWorkflowState


def build_graph(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Build and compile the workflow graph.

    Nodes:
    1) parse_inspection_rules
    2) build_initial_kg
    3) fetch_and_analyze_monitoring
    4) reconstruct_kg_with_anomaly
    5) generate_risk_grade_and_basis
    6) validate_with_history
    7) human_review
    8) update_inspection_rules
    """
    builder = StateGraph(RiskWorkflowState)

    # Register all nodes
    builder.add_node("parse_inspection_rules", parse_inspection_rules)
    builder.add_node("build_initial_kg", build_initial_kg)
    builder.add_node("fetch_and_analyze_monitoring", fetch_and_analyze_monitoring)
    builder.add_node("reconstruct_kg_with_anomaly", reconstruct_kg_with_anomaly)
    builder.add_node("generate_risk_grade_and_basis", generate_risk_grade_and_basis)
    builder.add_node("validate_with_history", validate_with_history)
    builder.add_node("human_review", human_review)
    builder.add_node("update_inspection_rules", update_inspection_rules)

    # Register normal edges in the requested order
    builder.add_edge(START, "parse_inspection_rules")
    builder.add_edge("parse_inspection_rules", "build_initial_kg")
    builder.add_edge("build_initial_kg", "fetch_and_analyze_monitoring")
    builder.add_edge("reconstruct_kg_with_anomaly", "generate_risk_grade_and_basis")
    builder.add_edge("generate_risk_grade_and_basis", "validate_with_history")
    builder.add_edge("validate_with_history", "human_review")
    builder.add_edge("update_inspection_rules", "build_initial_kg")

    # Register conditional edges
    builder.add_conditional_edges("fetch_and_analyze_monitoring", route_after_monitoring)
    builder.add_conditional_edges("human_review", route_after_human_review)

    return builder.compile(checkpointer=checkpointer)


def get_graph(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Alias for build_graph() to simplify imports and reuse."""
    return build_graph(checkpointer=checkpointer)


@contextmanager
def sqlite_checkpointer(db_path: str | Path) -> Iterator[SqliteSaver]:
    """Create a SQLite checkpointer context for persistent graph checkpoints."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with SqliteSaver.from_conn_string(str(path)) as checkpointer:
        checkpointer.setup()
        yield checkpointer
