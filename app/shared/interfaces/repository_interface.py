from typing import Protocol, TypeVar, Generic, Optional

RPInterface = TypeVar("RepositoryInterface")

class RPInterface(Protocol, Generic[RPInterface]):
    async def get_by_id(self, id: int) -> Optional[RPInterface]: ...
    async def create(self, obj_in: RPInterface) -> RPInterface: ...
