import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.models.assistant import AIMessage, AISuggestionRun, AIThread
from backend.app.models.base import Base


def test_threads_messages_and_suggestions_remain_isolated(tmp_path):
    async def exercise() -> None:
        engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'assistant.sqlite3').as_posix()}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            first = AIThread(draft_id="draft-a")
            second = AIThread(draft_id="draft-b")
            session.add_all([first, second])
            await session.flush()
            first_message = AIMessage(thread_id=first.id, role="user", content="黄铜书签")
            second_message = AIMessage(thread_id=second.id, role="user", content="陶艺体验")
            session.add_all([first_message, second_message])
            await session.flush()
            session.add(
                AISuggestionRun(
                    thread_id=first.id,
                    assistant_message_id=first_message.id,
                    patch_json=[{"path": "priceMin", "value": 39}],
                    confidence=0.9,
                    source_refs_json=[{"label": "用户描述"}],
                )
            )
            await session.commit()

            first_messages = (
                await session.execute(select(AIMessage).where(AIMessage.thread_id == first.id))
            ).scalars().all()
            second_messages = (
                await session.execute(select(AIMessage).where(AIMessage.thread_id == second.id))
            ).scalars().all()
            first_runs = (
                await session.execute(select(AISuggestionRun).where(AISuggestionRun.thread_id == first.id))
            ).scalars().all()

            assert first.id != second.id
            assert [message.content for message in first_messages] == ["黄铜书签"]
            assert [message.content for message in second_messages] == ["陶艺体验"]
            assert first_runs[0].patch_json == [{"path": "priceMin", "value": 39}]
            assert first_runs[0].applied_fields == []
            assert first_runs[0].ignored_fields == []

        await engine.dispose()

    asyncio.run(exercise())
