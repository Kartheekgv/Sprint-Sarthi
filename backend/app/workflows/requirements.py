from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph


class RequirementState(TypedDict):
    project_id: str
    session_id: str
    thread_id: str
    requirement_ids: list[str]
    status: str


def _requirement_complete(_: RequirementState) -> dict[str, str]:
    return {"status": "requirements_complete"}


async def checkpoint_requirement_stage(state: RequirementState, database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    builder = StateGraph(RequirementState)
    builder.add_node("requirement", _requirement_complete)
    builder.add_edge(START, "requirement")
    builder.add_edge("requirement", END)
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as saver:
        graph = builder.compile(checkpointer=saver)
        await graph.ainvoke(
            state,
            {"configurable": {"thread_id": state["thread_id"], "checkpoint_ns": "requirement"}},
        )