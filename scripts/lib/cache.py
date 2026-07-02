import hashlib
import shutil

from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

class Cache():
    def __init__(self, cache_dir: Path):
        self._cache_dir = cache_dir

    def _cache_key(self, uri: str) -> str:
        """
        Create a stable filename from the URI.
        """
        return hashlib.sha256(uri.encode("utf-8")).hexdigest()
    
    def _get_cached_path(self, uri: str) -> Path:
        parsed = urlparse(uri)
    
        # Preserve original extension if possible
        ext = Path(parsed.path).suffix
    
        return self._cache_dir / f"{self._cache_key(uri)}{ext}"
    
    
    def _fetch_url(self, uri: str, dest: Path):
        with urlopen(uri) as response:
            with open(dest, "wb") as f:
                shutil.copyfileobj(response, f)
    
    
    def _copy_file_uri(uri: str, dest: Path):
        parsed = urlparse(uri)
    
        path = parsed.path
    
        if not path:
            raise ValueError(f"Invalid file URI: {uri}")
    
        src = Path(path)
    
        if not src.exists():
            raise FileNotFoundError(src)
    
        shutil.copy2(src, dest)
    
    
    def fetch(self, uri: str, dest: Path):
        dest.parent.mkdir(parents=True, exist_ok=True)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
    
        cached_file = self._get_cached_path(uri)
    
        if cached_file.exists():
            print(f"Using cached file: {cached_file}")
            shutil.copy2(cached_file, dest)
            return
    
        print(f"Downloading: {uri}")
    
        parsed = urlparse(uri)
    
        if parsed.scheme in ("http", "https"):
            self._fetch_url(uri, cached_file)
        elif parsed.scheme == "file":
            shutil.copy2(Path(parsed.path), cached_file)
            return
        else:
            raise ValueError(f"Unsupported URI scheme: {parsed.scheme}")
    
        print(f"Copying to: {dest}")
        shutil.copy2(cached_file, dest)