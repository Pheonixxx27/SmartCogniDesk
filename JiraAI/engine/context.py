from datetime import datetime


class ExecutionContext:
    def __init__(self, **kwargs):
        # All state lives in this dict
        self.data = kwargs

        # Execution artifacts
        self.logs = []
        self.events = []

        # Stop flag
        self._stop = False

    # -------------------------
    # Logging
    # -------------------------
    def log(self, message, level="INFO", step=None):
        entry = {
            "timestamp": datetime.utcnow(),
            "level": level,
            "step": step,
            "message": message,
            "ticket": self.data.get("issue_key"),
        }
        self.logs.append(entry)
        print(message)

    # -------------------------
    # Events
    # -------------------------
    def emit_event(self, event_type, payload):
        self.events.append({
            "timestamp": datetime.utcnow(),
            "type": event_type,
            "ticket": self.data.get("issue_key"),
            "payload": payload,
        })

    # -------------------------
    # Stop control
    # -------------------------
    def stop(self):
        self._stop = True
        self.emit_event(
            "SOP_STOPPED",
            {
                "step": self.get("__step_index__"),
                "reason": self.get("intent_reason"),
            },
        )

    def should_stop(self):
        return self._stop

    # -------------------------
    # Dict-style access
    # -------------------------
    def get(self, key, default=None):
        return self.data.get(key, default)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    # -------------------------
    # Child context (THREAD SAFE)
    # -------------------------
    def spawn_child(self):
        # ✅ create empty child
        child = ExecutionContext()

        # ✅ copy ALL context data safely
        child.data = dict(self.data)

        # ✅ isolate execution state
        child.logs = []
        child.events = []
        child._stop = False

        return child
