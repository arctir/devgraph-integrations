from typing import List, Union

from pydantic import BaseModel

from devgraph_integrations.types.entities import Entity, EntityRelation, FieldSelectedEntityRelation


class GraphMutations(BaseModel):
    create_entities: List[Entity] = []
    delete_entities: List[Entity] = []
    create_relations: List[Union[EntityRelation, FieldSelectedEntityRelation]] = []
    delete_relations: List[Union[EntityRelation, FieldSelectedEntityRelation]] = []
