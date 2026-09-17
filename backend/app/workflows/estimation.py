from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph


class EstimationState(TypedDict):
    project_id: str
    session_id: str
    thread_id: str
    status: str


def _estimation_complete(_: EstimationState) -> dict[str, str]:
    return {"status": "estimation_complete"}


async def checkpoint_estimation_stage(state: EstimationState, database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    builder = StateGraph(EstimationState)
    builder.add_node("estimation", _estimation_complete)
    builder.add_edge(START, "estimation")
    builder.add_edge("estimation", END)
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as saver:
        graph = builder.compile(checkpointer=saver)
        await graph.ainvoke(
            state,
            {"configurable": {"thread_id": state["thread_id"], "checkpoint_ns": "estimation"}},
        )