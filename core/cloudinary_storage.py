from cloudinary_storage.storage import MediaCloudinaryStorage


class SafeMediaCloudinaryStorage(MediaCloudinaryStorage):
    """A Cloudinary storage wrapper that rewinds uploaded files before saving.

    Some Django file upload flows validate image files before the storage layer
    receives them. That validation can advance the underlying file pointer, which
    causes Cloudinary uploads to see empty content and fail with "Invalid image file".
    """

    def _save(self, name, content):
        if hasattr(content, 'seek') and callable(content.seek):
            try:
                content.seek(0)
            except Exception:
                pass
        return super()._save(name, content)
