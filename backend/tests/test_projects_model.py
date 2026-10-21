from sqlalchemy import select

from app.models.project import Project


async def test_project_defaults_and_query(db_session):
    project = Project(
        slug="demo-project",
        title_zh="示例项目",
        title_en="Demo project",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    assert project.id is not None
    assert project.summary_zh == ""
    assert project.summary_en == ""
    assert project.content_md_zh == ""
    assert project.content_md_en == ""
    assert project.tech_stack == []
    assert project.featured is False
    assert project.sort_order == 0
    assert project.status == "draft"
    assert project.created_at is not None
    assert project.updated_at is not None

    loaded = await db_session.scalar(
        select(Project).where(Project.slug == "demo-project")
    )
    assert loaded is not None
    assert loaded.title_en == "Demo project"
