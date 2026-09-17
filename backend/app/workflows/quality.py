from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph


class ValidationState(TypedDict):
    project_id: str
    session_id: str
    thread_id: str
    status: str


async def checkpoint_validation_stage(state: ValidationState, database_path: Path, node_name: str) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    builder = StateGraph(ValidationState)
    builder.add_node(node_name, lambda _: {"status": state["status"]})
    builder.add_edge(START, node_name)
    builder.add_edge(node_name, END)
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as saver:
        graph = builder.compile(checkpointer=saver)
        await graph.ainvoke(state, {"configurable": {"thread_id": state["thread_id"], "checkpoint_ns": node_name}})