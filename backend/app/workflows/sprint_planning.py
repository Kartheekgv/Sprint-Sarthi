from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph


class SprintPlanningState(TypedDict):
    project_id: str
    session_id: str
    thread_id: str
    decision_ids: list[str]
    status: str


def _planning_complete(_: SprintPlanningState) -> dict[str, str]:
    return {"status": "sprint_planning_complete"}


async def checkpoint_sprint_planning_stage(state: SprintPlanningState, database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    builder = StateGraph(SprintPlanningState)
    builder.add_node("sprint_planning", _planning_complete)
    builder.add_edge(START, "sprint_planning")
    builder.add_edge("sprint_planning", END)
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as saver:
        graph = builder.compile(checkpointer=saver)
        await graph.ainvoke(state, {"configurable": {"thread_id": state["thread_id"], "checkpoint_ns": "sprint_planning"}})