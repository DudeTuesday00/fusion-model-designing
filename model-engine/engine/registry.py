"""In-memory registry of available generators.

Generators register themselves with @register when their module is imported
(see engine/generators/__init__.py, which imports every generator module so
this happens automatically on add-in startup).
"""

_generators: dict = {}


def register(generator_cls):
    """Class decorator: instantiates the generator and adds it to the registry."""
    instance = generator_cls()
    if not instance.id:
        raise ValueError(f"{generator_cls.__name__} must set an `id`")
    _generators[instance.id] = instance
    return generator_cls


def get(generator_id: str):
    return _generators[generator_id]


def list_all() -> list:
    """Returns all registered generators, sorted by category then display name."""
    return sorted(_generators.values(), key=lambda g: (g.category, g.display_name))


def clear():
    """Only used by tests/dev reload - not called during normal operation."""
    _generators.clear()
