from app.core.database import get_session
from app.main import app
from app.models.entities import AgentExecution, AnalysisSession


async def test_operational_logs_include_audits_and_executions(client):
    project = (await client.post("/api/v1/projects", json={"name": "Log Project"})).json()
    dependency = app.dependency_overrides[get_session]
    async for db in dependency():
        session = AnalysisSession(project_id=project["id"], thread_id="22222222-2222-2222-2222-222222222222")
        db.add(session)
        await db.flush()
        db.add(AgentExecution(
            session_id=session.id, node_name="Backlog", status="completed", model="gpt-4o",
            input_tokens=100, output_tokens=20, duration_ms=250,
        ))
        await db.commit()
        break

    response = await client.get("/api/v1/logs", params={"project_id": project["id"]})

    assert response.status_code == 200
    result = response.json()
    assert result["projects"] == [{"id": project["id"], "name": "Log Project"}]
    assert {entry["kind"] for entry in result["entries"]} == {"audit", "execution"}
    execution = next(entry for entry in result["entries"] if entry["kind"] == "execution")
    assert execution["source"] == "Backlog"
    assert execution["metadata"]["input_tokens"] == 100