import os
import uuid

_ALLOWED_IMAGE_EXTS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"})


class UploadToUnique:
    """
    upload_to paramétrable, sérialisable en migrations.
    Nom de fichier = UUID + extension (chemins courts, pas de collision).
    """

    def __init__(self, subdir: str):
        self.subdir = subdir.strip("/")

    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in _ALLOWED_IMAGE_EXTS:
            ext = ".bin"
        return f"{self.subdir}/{uuid.uuid4().hex}{ext}"

    def __eq__(self, other):
        return isinstance(other, UploadToUnique) and self.subdir == other.subdir

    def deconstruct(self):
        return (
            f"{self.__class__.__module__}.{self.__class__.__qualname__}",
            [self.subdir],
            {},
        )
