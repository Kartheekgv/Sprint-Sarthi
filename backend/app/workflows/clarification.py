from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class ClarificationState(TypedDict):
    project_id: str
    session_id: str
    thread_id: str
    question_ids: list[str]
    status: str


def _clarify(state: ClarificationState) -> dict[str, str]:
    for question_id in state["question_ids"]:
        interrupt({"clarification_id": question_id})
    return {"status": "clarifications_complete"}


def _build_graph(checkpointer: AsyncSqliteSaver):
    builder = StateGraph(ClarificationState)
    builder.add_node("clarification", _clarify)
    builder.add_edge(START, "clarification")
    builder.add_edge("clarification", END)
    return builder.compile(checkpointer=checkpointer)


async def start_clarification_graph(state: ClarificationState, database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as saver:
        graph = _build_graph(saver)
        await graph.ainvoke(state, {"configurable": {"thread_id": state["thread_id"]}})


async def resume_clarification_graph(thread_id: str, answer: dict[str, str | None], database_path: Path) -> bool:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as saver:
        graph = _build_graph(saver)
        result = await graph.ainvoke(Command(resume=answer), {"configurable": {"thread_id": thread_id}})
        return result.get("status") == "clarifications_complete"