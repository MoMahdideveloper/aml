"""Registration safety tests for SQLAlchemy model listeners."""

from event_handlers import EventHandlers


def test_event_handler_registration_is_global_across_instances(app):
    """Separate handler objects must not install a second listener set."""
    assert EventHandlers._handlers_registered_globally is True

    first = EventHandlers()
    second = EventHandlers()

    first.register_handlers()
    second.register_handlers()

    assert EventHandlers._handlers_registered_globally is True
    assert first._registered is True
    assert second._registered is True
