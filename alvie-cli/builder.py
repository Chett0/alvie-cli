from instructions import Entity
from entities import build_enclave, build_attacker

def build_entity(entity: Entity):
    if entity == Entity.ENCLAVE:
        build_enclave()
    elif entity == Entity.ATTACKER:
        build_attacker()
    else:
        raise RuntimeError(f"Unknown entity type: {entity.value}")