from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph


class EnrichmentState(TypedDict):
    project_id: str
    session_id: str
    thread_id: str
    status: str


def _enrichment_complete(_: EnrichmentState) -> dict[str, str]:
    return {"status": "enrichment_complete"}


async def checkpoint_enrichment_stage(state: EnrichmentState, database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    builder = StateGraph(EnrichmentState)
    builder.add_node("enrichment", _enrichment_complete)
    builder.add_edge(START, "enrichment")
    builder.add_edge("enrichment", END)
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as saver:
        graph = builder.compile(checkpointer=saver)
        await graph.ainvoke(
            state,
            {"configurable": {"thread_id": state["thread_id"], "checkpoint_ns": "enrichment"}},
        )