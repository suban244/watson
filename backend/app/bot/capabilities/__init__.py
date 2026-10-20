from pydantic_ai.capabilities import Capability

from .charts import charts
from .database import database
from .fizzy import fizzy
from .ledger import ledger
from .people import people
from .reminders import reminders
from .tags import tags
from .transactions import transactions


def make_capability_eager[DepsT](capability: Capability[DepsT]) -> Capability[DepsT]:
    """A copy of the capability that is loaded from the start, for an agent with
    a fixed job.

    pydantic-ai has no switch to preload a deferred capability, so this builds a
    non-deferred twin from its public getters; the original stays deferred for
    the chat agent. The toolset is shared, so tools registered later still show
    up, but instructions are copied: register them before calling this.
    """
    toolset = capability.get_toolset()
    return Capability(
        id=capability.id,
        description=capability.get_description(),
        instructions=capability.get_instructions(),
        toolsets=[toolset] if toolset is not None else None,
    )


__all__ = [
    "charts",
    "database",
    "fizzy",
    "ledger",
    "make_capability_eager",
    "people",
    "reminders",
    "tags",
    "transactions",
]
