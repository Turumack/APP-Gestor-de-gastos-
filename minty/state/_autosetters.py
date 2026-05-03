"""Auto-generate set_<field> event handlers for all annotated vars on a State.

Reflex 0.9 removed automatic setter generation. This helper restores it
and coerces incoming values to the annotated type (strings from HTML
inputs become int/float/bool as expected).
"""
from __future__ import annotations

import typing


def _coerce(value, target_type):
    if value is None or target_type is None:
        return value
    # Handle Optional[X] / Union[X, None]
    origin = typing.get_origin(target_type)
    if origin is typing.Union:
        args = [a for a in typing.get_args(target_type) if a is not type(None)]
        if not args:
            return value
        target_type = args[0]
        origin = typing.get_origin(target_type)

    if target_type in (int, float):
        if isinstance(value, str):
            s = value.strip()
            if s == "" or s == "-":
                return target_type(0)
            try:
                return target_type(float(s))
            except (ValueError, TypeError):
                return target_type(0)
        try:
            return target_type(value)
        except (ValueError, TypeError):
            return target_type(0)
    if target_type is bool:
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)
    if target_type is str:
        return "" if value is None else str(value)
    return value


def auto_setters(cls):
    """Add ``set_<field>`` event handlers for every base var on ``cls``."""
    hints = typing.get_type_hints(cls, include_extras=False)
    for name in list(cls.base_vars.keys()):
        if name.startswith("_") or name == "is_hydrated":
            continue
        setter_name = f"set_{name}"
        # Sobrescribir incluso si Reflex ya generó uno automático con tipo
        # incompatible (ej. value: float que rompe el handler de <input>).

        target_type = hints.get(name)

        def _make(_n, _tt):
            def _setter(self, value: str):
                setattr(self, _n, _coerce(value, _tt))
            _setter.__name__ = f"set_{_n}"
            _setter.__qualname__ = f"{cls.__qualname__}.set_{_n}"
            _setter.__annotations__ = {"value": str, "return": None}
            return _setter

        fn = _make(name, target_type)
        handler = cls._create_event_handler(fn)
        cls.event_handlers[setter_name] = handler
        setattr(cls, setter_name, handler)

    return cls

