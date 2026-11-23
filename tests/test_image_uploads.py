"""Uploaded tour/event images keep the whole picture: shrink if huge, never crop."""
import io
from unittest.mock import patch

from fastapi import UploadFile

from src.services.cloudinary_service import cloudinary_service


def _upload_with_defaults():
    fake = {"secure_url": "https://res.cloudinary.com/x/image/upload/a.webp", "public_id": "a"}
    with patch("cloudinary.uploader.upload", return_value=fake) as upload:
        cloudinary_service.upload_image(UploadFile(file=io.BytesIO(b"img"), filename="a.jpg"))
    return upload.call_args.kwargs["transformation"]


def test_default_upload_never_crops():
    transformation = _upload_with_defaults()
    assert transformation["crop"] == "limit"


def test_default_upload_keeps_aspect_ratio_limits_size():
    transformation = _upload_with_defaults()
    assert transformation["width"] == transformation["height"] == 2000
