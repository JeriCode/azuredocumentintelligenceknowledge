from types import SimpleNamespace

from azure.ai.projects.models import (
    AISearchIndexResource,
    AzureAISearchQueryType,
    AzureAISearchTool,
    AzureAISearchToolResource,
    PromptAgentDefinition,
)

from manual_ingestion.adapters.foundry_knowledge_source import MicrosoftFoundryKnowledgeSource


def test_existing_search_tool_does_not_create_agent_version() -> None:
    tool = AzureAISearchTool(
        azure_ai_search=AzureAISearchToolResource(
            indexes=[
                AISearchIndexResource(
                    project_connection_id="connection-id",
                    index_name="manuals",
                    query_type=AzureAISearchQueryType.SIMPLE,
                )
            ]
        )
    )
    definition = PromptAgentDefinition(model="model", instructions="Help", tools=[tool])
    agents = SimpleNamespace(
        get=lambda **_: SimpleNamespace(
            agent_endpoint=SimpleNamespace(
                version_selector=SimpleNamespace(
                    version_selection_rules=[
                        SimpleNamespace(agent_version="7", traffic_percentage=100)
                    ]
                )
            )
        ),
        get_version=lambda **_: SimpleNamespace(definition=definition),
        create_version=lambda **_: (_ for _ in ()).throw(AssertionError("must not create")),
    )
    project_client = SimpleNamespace(agents=agents, connections=SimpleNamespace(list=lambda: []))
    adapter = MicrosoftFoundryKnowledgeSource(project_client, "agent", "manuals")

    assert adapter.ensure_search_tool() == "7"
