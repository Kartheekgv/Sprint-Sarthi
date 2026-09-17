from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph


class DecompositionState(TypedDict):
    project_id: str
    session_id: str
    thread_id: str
    decomposition_ids: list[str]
    status: str


def _decomposition_complete(_: DecompositionState) -> dict[str, str]:
    return {"status": "decomposition_complete"}


async def checkpoint_decomposition_stage(state: DecompositionState, database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    builder = StateGraph(DecompositionState)
    builder.add_node("decomposition", _decomposition_complete)
    builder.add_edge(START, "decomposition")
    builder.add_edge("decomposition", END)
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as saver:
        graph = builder.compile(checkpointer=saver)
        await graph.ainvoke(
            state,
            {"configurable": {"thread_id": state["thread_id"], "checkpoint_ns": "decomposition"}},
        )