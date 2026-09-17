from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph


class DependencyState(TypedDict):
    project_id: str
    session_id: str
    thread_id: str
    dependency_ids: list[str]
    status: str


def _dependencies_complete(_: DependencyState) -> dict[str, str]:
    return {"status": "dependencies_complete"}


async def checkpoint_dependency_stage(state: DependencyState, database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    builder = StateGraph(DependencyState)
    builder.add_node("dependencies", _dependencies_complete)
    builder.add_edge(START, "dependencies")
    builder.add_edge("dependencies", END)
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as saver:
        graph = builder.compile(checkpointer=saver)
        await graph.ainvoke(
            state,
            {"configurable": {"thread_id": state["thread_id"], "checkpoint_ns": "dependencies"}},
        )