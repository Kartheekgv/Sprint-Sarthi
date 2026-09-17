from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph


class BacklogState(TypedDict):
    project_id: str
    session_id: str
    thread_id: str
    epic_ids: list[str]
    story_ids: list[str]
    task_ids: list[str]
    status: str


def _backlog_complete(_: BacklogState) -> dict[str, str]:
    return {"status": "backlog_complete"}


async def checkpoint_backlog_stage(state: BacklogState, database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    builder = StateGraph(BacklogState)
    builder.add_node("backlog", _backlog_complete)
    builder.add_edge(START, "backlog")
    builder.add_edge("backlog", END)
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as saver:
        graph = builder.compile(checkpointer=saver)
        await graph.ainvoke(
            state,
            {"configurable": {"thread_id": state["thread_id"], "checkpoint_ns": "backlog"}},
        )