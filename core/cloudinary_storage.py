from cloudinary_storage.storage import RawMediaCloudinaryStorage


class SafeMediaCloudinaryStorage(RawMediaCloudinaryStorage):
    """
    Cloudinary storage that:
    1. Supports ALL file types (raw)
    2. Fixes file pointer issues (seek(0))
    """

    def _save(self, name, content):
        # rewind file pointer (your fix - keep it)
        if hasattr(content, 'seek') and callable(content.seek):
            try:
                content.seek(0)
            except Exception:
                pass

        return super()._save(name, content)