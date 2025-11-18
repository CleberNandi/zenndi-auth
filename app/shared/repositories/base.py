from typing import Type, TypeVar, Generic, Sequence, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from sqlalchemy.orm import DeclarativeMeta

# Define o tipo genérico para o modelo ORM
ModelType = TypeVar("ModelType", bound=DeclarativeMeta)


class BaseRepository(Generic[ModelType]):
    """
    Repositório genérico base, responsável por operações CRUD assíncronas.
    Pode ser herdado por qualquer repositório específico (UserRepository, etc).
    """

    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self.session = session
        self.model = model

    # 🔍 READ -------------------------------------------------
    async def get_by_id(self, id: int) -> Optional[ModelType]:
        result = await self.session.execute(
            select(self.model).filter_by(id=id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> Sequence[ModelType]:
        result = await self.session.execute(select(self.model))
        return result.scalars().all()

    # ➕ CREATE -----------------------------------------------
    async def create(self, obj_in: ModelType) -> ModelType:
        self.session.add(obj_in)
        await self.session.commit()
        await self.session.refresh(obj_in)
        return obj_in

    # ✏️ UPDATE ----------------------------------------------
    async def update(self, id: int, obj_in: dict) -> Optional[ModelType]:
        await self.session.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**obj_in)
        )
        await self.session.commit()
        return await self.get_by_id(id)

    # ❌ DELETE ----------------------------------------------
    async def delete(self, id: int) -> bool:
        await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.session.commit()
        return True
