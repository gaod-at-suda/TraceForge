"""EventBus 和事件存储测试。"""

from traceforge.events import EventBus, InMemoryEventStore


def test_event_bus_delivers_events():
    bus = EventBus()
    store = InMemoryEventStore()
    bus.subscribe(store.on_event)

    event = bus.emit("tool_started", "run1", step=2, data={"tool": "read_file"})
    items = store.after(0)

    assert event.seq == 1
    assert items[0]["event_type"] == "tool_started"
    assert items[0]["data"]["tool"] == "read_file"
