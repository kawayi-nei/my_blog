from sqlalchemy import select

from app.models.media import Media


async def test_media_defaults_and_query(db_session):
    media = Media(
        filename="2026/10/example.png",
        original_name="example.png",
        mime="image/png",
        size_bytes=123,
    )
    db_session.add(media)
    await db_session.commit()
    await db_session.refresh(media)

    assert media.id is not None
    assert media.created_at is not None
    loaded = await db_session.scalar(select(Media).where(Media.id == media.id))
    assert loaded is not None
    assert loaded.filename == "2026/10/example.png"
