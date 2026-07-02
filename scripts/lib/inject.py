from .cache import Cache
from .install_vm import InstallVM

import os

from pathlib import Path

class Inject:
    def __init__(self):
        self._cache = None
    
    def cache(self) -> Cache:
        cache_dir = os.path.join(os.environ["HOME"], ".local", "share", "kubelab", "cache")
        if self._cache is None:
            self._cache = Cache(Path(cache_dir))
        return self._cache
    
    def InstallVM(self) -> InstallVM:
        image_dir = os.path.join(os.environ["HOME"], ".local", "share", "kubelab", "images")
        return InstallVM(self.cache(), Path(image_dir))