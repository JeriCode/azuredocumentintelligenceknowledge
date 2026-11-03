from __future__ import annotations

from typing import Any

from azure.ai.projects.models import (
    AISearchIndexResource,
    AzureAISearchQueryType,
    AzureAISearchTool,
    AzureAISearchToolResource,
    FixedRatioVersionSelectionRule,
    PromptAgentDefinition,
    VersionSelector,
)


class FoundryConfigurationError(RuntimeError):
    """Raised when an existing Foundry agent cannot use the Search index."""


class MicrosoftFoundryKnowledgeSource:
    def __init__(
        self,
        project_client: Any,
        agent_name: str,
        search_index_name: str,
        search_connection_name: str | None = None,
    ) -> None:
        self._project_client = project_client
        self._agent_name = agent_name
        self._search_index_name = search_index_name
        self._search_connection_name = search_connection_name

    def validate_agent(self) -> None:
        agent = self._project_client.agents.get(agent_name=self._agent_name)
        if not getattr(agent, "agent_endpoint", None):
            raise FoundryConfigurationError(
                f"Agent '{self._agent_name}' has no configured endpoint or active version"
            )

    def ensure_search_tool(self) -> str:
        agent = self._project_client.agents.get(agent_name=self._agent_name)
        version = _active_version(agent)
        details = self._project_client.agents.get_version(
            agent_name=self._agent_name,
            agent_version=version,
        )
        definition = details.definition
        if not isinstance(definition, PromptAgentDefinition):
            raise FoundryConfigurationError(
                f"Agent '{self._agent_name}' is not a prompt agent; attach the Search tool manually"
            )

        if _has_search_index(definition, self._search_index_name):
            return version

        connection_id = self._resolve_search_connection_id()
        tool = AzureAISearchTool(
            azure_ai_search=AzureAISearchToolResource(
                indexes=[
                    AISearchIndexResource(
                        project_connection_id=connection_id,
                        index_name=self._search_index_name,
                        query_type=AzureAISearchQueryType.SIMPLE,
                    )
                ]
            )
        )
        definition.tools = [*(definition.tools or []), tool]
        created = self._project_client.agents.create_version(
            agent_name=self._agent_name,
            definition=definition,
            description=f"Attach Azure AI Search index {self._search_index_name}",
        )
        endpoint = agent.agent_endpoint
        endpoint.version_selector = VersionSelector(
            version_selection_rules=[
                FixedRatioVersionSelectionRule(
                    agent_version=created.version,
                    traffic_percentage=100,
                )
            ]
        )
        self._project_client.agents.update_details(
            agent_name=self._agent_name,
            agent_endpoint=endpoint,
        )
        return str(created.version)

    def _resolve_search_connection_id(self) -> str:
        connections = list(self._project_client.connections.list())
        if self._search_connection_name:
            matches = [
                connection
                for connection in connections
                if getattr(connection, "name", None) == self._search_connection_name
            ]
        else:
            matches = [
                connection
                for connection in connections
                if "search" in str(getattr(connection, "type", "")).casefold()
            ]
        if len(matches) != 1:
            qualifier = self._search_connection_name or "an Azure AI Search connection"
            raise FoundryConfigurationError(
                f"Expected exactly one connection matching {qualifier!r}; found {len(matches)}"
            )
        connection_id = getattr(matches[0], "id", None)
        if not connection_id:
            raise FoundryConfigurationError("The selected Search connection has no resource ID")
        return str(connection_id)


def _active_version(agent: Any) -> str:
    endpoint = getattr(agent, "agent_endpoint", None)
    selector = getattr(endpoint, "version_selector", None)
    rules = getattr(selector, "version_selection_rules", None) or []
    active_rules = [rule for rule in rules if getattr(rule, "traffic_percentage", 0) > 0]
    if len(active_rules) != 1:
        raise FoundryConfigurationError(
            "The existing agent must have exactly one active version before automatic attachment"
        )
    return str(active_rules[0].agent_version)


def _has_search_index(definition: PromptAgentDefinition, index_name: str) -> bool:
    for tool in definition.tools or []:
        resource = getattr(tool, "azure_ai_search", None)
        for index in getattr(resource, "indexes", None) or []:
            if getattr(index, "index_name", None) == index_name:
                return True
    return False