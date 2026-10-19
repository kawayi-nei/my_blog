import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal, engine
from app.models.post import Post
from app.models.tag import Tag

CONTENT = (
    "# 第一篇测试文章\n\n"
    "这是用于本地开发验证的 Markdown 内容。\n\n"
    "```python\nprint('hello')\n```\n"
)


async def main() -> None:
    try:
        async with SessionLocal() as db:
            tag_result = await db.execute(select(Tag).where(Tag.slug == "backend"))
            tag = tag_result.scalar_one_or_none()
            if tag is None:
                tag = Tag(name="后端", slug="backend")
                db.add(tag)
                await db.flush()

            post_result = await db.execute(
                select(Post).where(Post.slug == "first-post")
            )
            post = post_result.scalar_one_or_none()
            if post is None:
                db.add(
                    Post(
                        slug="first-post",
                        title="第一篇测试文章",
                        excerpt="用于本地开发验证的文章。",
                        content_md=CONTENT,
                        language="zh",
                        status="published",
                        published_at=datetime.now(timezone.utc),
                        tags=[tag],
                    )
                )
                print("created demo post: first-post")
            else:
                post.title = "第一篇测试文章"
                post.excerpt = "用于本地开发验证的文章。"
                post.content_md = CONTENT
                post.language = "zh"
                post.status = "published"
                post.published_at = datetime.now(timezone.utc)
                if tag not in post.tags:
                    post.tags.append(tag)
                print("updated demo post: first-post")
            await db.commit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
