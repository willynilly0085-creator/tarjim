from dataclasses import dataclass
from pathlib import Path

from tarjim.languages import Language, language
from tarjim.rules import Rules, rules_for


@dataclass(frozen=True)
class Job:
    video: Path
    target: str = "ar"
    dialect: str = "saudi"
    burn: bool = True
    font: str = ""

    @property
    def language(self) -> Language:
        return language(self.target)

    @property
    def rules(self) -> Rules:
        return rules_for(self.language)

    @property
    def font_name(self) -> str:
        return self.font or self.language.font

    @property
    def cache(self) -> Path:
        folder = self.video.parent / ".tarjim" / self.video.stem
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def output(self, suffix: str) -> Path:
        return self.video.with_name(f"{self.video.stem}.{self.target}{suffix}")
