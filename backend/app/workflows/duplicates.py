from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph


class DuplicateState(TypedDict):
    project_id: str
    session_id: str
    thread_id: str
    candidate_ids: list[str]
    status: str


def _duplicates_complete(_: DuplicateState) -> dict[str, str]:
    return {"status": "duplicates_complete"}


async def checkpoint_duplicate_stage(state: DuplicateState, database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    builder = StateGraph(DuplicateState)
    builder.add_node("duplicates", _duplicates_complete)
    builder.add_edge(START, "duplicates")
    builder.add_edge("duplicates", END)
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as saver:
        graph = builder.compile(checkpointer=saver)
        await graph.ainvoke(state, {"configurable": {"thread_id": state["thread_id"], "checkpoint_ns": "duplicates"}})