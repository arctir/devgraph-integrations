from devgraph_integrations.types.entities import EntityRelation


class GithubRepositoryHostedByRelation(EntityRelation):
    relation: str = "HOSTED_BY"
