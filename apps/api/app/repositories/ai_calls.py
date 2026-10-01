"""The AI call log (FND-013). Calls can belong to no workspace (the demo), so this is a plain
function rather than a workspace repository. Only `app/ai/` writes it."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AICall


async def add(session: AsyncSession, call: AICall) -> None:
    session.add(call)
    await session.commit()
