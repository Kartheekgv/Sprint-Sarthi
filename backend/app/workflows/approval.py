from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class ApprovalState(TypedDict):
    project_id: str
    session_id: str
    thread_id: str
    status: str
    decision: str | None


def _human_approval(state: ApprovalState) -> dict[str, str]:
    decision = interrupt({
        "type": "human_approval",
        "project_id": state["project_id"],
        "session_id": state["session_id"],
        "allowed_decisions": ["approve", "reject", "changes_requested"],
    })
    return {"status": str(decision.get("decision", "changes_requested")), "decision": str(decision.get("decision"))}


def _build_graph(checkpointer: AsyncSqliteSaver):
    builder = StateGraph(ApprovalState)
    builder.add_node("human_approval", _human_approval)
    builder.add_edge(START, "human_approval")
    builder.add_edge("human_approval", END)
    return builder.compile(checkpointer=checkpointer)


async def start_approval_graph(state: ApprovalState, database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as saver:
        graph = _build_graph(saver)
        await graph.ainvoke(state, {"configurable": {"thread_id": state["thread_id"], "checkpoint_ns": "human_approval"}})


async def resume_approval_graph(
    thread_id: str,
    decision: str,
    database_path: Path,
) -> str:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as saver:
        graph = _build_graph(saver)
        result = await graph.ainvoke(
            Command(resume={"decision": decision}),
            {"configurable": {"thread_id": thread_id, "checkpoint_ns": "human_approval"}},
        )
        return str(result.get("decision", ""))