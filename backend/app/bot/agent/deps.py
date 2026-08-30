from dataclasses import dataclass, field


@dataclass
class Attachment:
    """A file a tool produced, to be sent with the agent's reply."""

    filename: str
    content: bytes


@dataclass
class HandleAttachments:
    """A mixin for a tool that produces attachments."""

    attachments: list[Attachment] = field(default_factory=list)

    def attach(self, filename: str, content: bytes) -> None:
        self.attachments.append(Attachment(filename=filename, content=content))


@dataclass
class WatsonDeps(HandleAttachments):
    """State one agent run shares with its caller."""
