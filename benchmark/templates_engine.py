"""Prompt template rendering utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


@dataclass(frozen=True)
class PromptTemplate:
    """Prompt template descriptor.

    Attributes:
        dimension: Dimension name.
        prompt_name: Prompt identifier.
        template_name: Jinja2 template filename.
        context: Context variables passed to Jinja2.
    """

    dimension: str
    prompt_name: str
    template_name: str
    context: dict[str, str]


class PromptTemplateEngine:
    """Render benchmark prompts from Jinja2 templates.

    Args:
        templates_dir: Root templates directory.
    """

    def __init__(self, templates_dir: Path) -> None:
        prompt_dir = templates_dir / "prompts"
        self._env = Environment(
            loader=FileSystemLoader(str(prompt_dir)),
            undefined=StrictUndefined,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, item: PromptTemplate) -> str:
        """Render a single prompt template.

        Args:
            item: Template descriptor.

        Returns:
            Rendered prompt text.
        """
        template = self._env.get_template(item.template_name)
        return template.render(**item.context).strip()
