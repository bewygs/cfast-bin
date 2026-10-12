from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        build_data["pure_python"] = False
        tag = Path(self.root, ".wheel-tag").read_text().strip()
        build_data["tag"] = f"py3-none-{tag}"
