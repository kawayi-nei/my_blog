from io import BytesIO

from PIL import Image

from app.models.media import Media


def make_png(size: tuple[int, int] = (4, 4)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (255, 0, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


async def test_upload_png(admin_client, upload_dir):
    response = await admin_client.post(
        "/api/admin/uploads",
        files={"file": ("photo.png", make_png(), "image/png")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["url"].startswith("/uploads/")
    assert body["url"].endswith(".png")
    assert body["mime"] == "image/png"
    assert body["size"] > 0
    assert (upload_dir / body["filename"]).exists()


async def test_upload_rejects_non_image(admin_client, upload_dir):
    response = await admin_client.post(
        "/api/admin/uploads",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 422


async def test_upload_rejects_oversize(admin_client, upload_dir):
    response = await admin_client.post(
        "/api/admin/uploads",
        files={"file": ("big.png", b"x" * (5 * 1024 * 1024 + 1), "image/png")},
    )
    assert response.status_code == 413


async def test_upload_rejects_fake_image(admin_client, upload_dir):
    response = await admin_client.post(
        "/api/admin/uploads",
        files={"file": ("fake.png", b"not-an-image", "image/png")},
    )
    assert response.status_code == 422


async def test_upload_rejects_empty_file(admin_client, upload_dir):
    response = await admin_client.post(
        "/api/admin/uploads",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert response.status_code == 422


async def test_upload_rejects_huge_dimensions(admin_client, upload_dir):
    response = await admin_client.post(
        "/api/admin/uploads",
        files={"file": ("huge.png", make_png((12001, 1)), "image/png")},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "图片尺寸过大"


async def test_upload_truncates_long_original_name(admin_client, upload_dir):
    response = await admin_client.post(
        "/api/admin/uploads",
        files={"file": ("a" * 300 + ".png", make_png(), "image/png")},
    )
    assert response.status_code == 201

    listed = await admin_client.get("/api/admin/media")
    assert listed.status_code == 200
    assert len(listed.json()["items"][0]["original_name"]) == 255


async def test_list_media(admin_client, upload_dir):
    await admin_client.post(
        "/api/admin/uploads",
        files={"file": ("one.png", make_png(), "image/png")},
    )
    await admin_client.post(
        "/api/admin/uploads",
        files={"file": ("two.png", make_png(), "image/png")},
    )

    response = await admin_client.get("/api/admin/media")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["url"].startswith("/uploads/")


async def test_delete_media_removes_file(admin_client, upload_dir):
    created = await admin_client.post(
        "/api/admin/uploads",
        files={"file": ("delete-me.png", make_png(), "image/png")},
    )
    body = created.json()
    stored = upload_dir / body["filename"]
    assert stored.exists()

    listed = await admin_client.get("/api/admin/media")
    media_id = listed.json()["items"][0]["id"]

    deleted = await admin_client.delete(f"/api/admin/media/{media_id}")
    assert deleted.status_code == 204
    assert not stored.exists()
    assert (await admin_client.get("/api/admin/media")).json()["total"] == 0


async def test_delete_missing_media_returns_404(admin_client, upload_dir):
    response = await admin_client.delete("/api/admin/media/999999")
    assert response.status_code == 404


async def test_delete_rejects_path_traversal(admin_client, db_session, upload_dir):
    media = Media(
        filename="../evil.png",
        original_name="evil.png",
        mime="image/png",
        size_bytes=1,
    )
    db_session.add(media)
    await db_session.commit()
    await db_session.refresh(media)

    response = await admin_client.delete(f"/api/admin/media/{media.id}")
    assert response.status_code == 400

    listed = await admin_client.get("/api/admin/media")
    assert listed.json()["total"] == 1
