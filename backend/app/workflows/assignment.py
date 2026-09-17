from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph


class AssignmentState(TypedDict):
    project_id: str
    session_id: str
    thread_id: str
    assignment_ids: list[str]
    status: str


def _assignment_complete(_: AssignmentState) -> dict[str, str]:
    return {"status": "assignment_complete"}


async def checkpoint_assignment_stage(state: AssignmentState, database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    builder = StateGraph(AssignmentState)
    builder.add_node("assignment", _assignment_complete)
    builder.add_edge(START, "assignment")
    builder.add_edge("assignment", END)
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as saver:
        graph = builder.compile(checkpointer=saver)
        await graph.ainvoke(
            state,
            {"configurable": {"thread_id": state["thread_id"], "checkpoint_ns": "assignment"}},
        )