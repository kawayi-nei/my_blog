from io import BytesIO

from PIL import Image


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
