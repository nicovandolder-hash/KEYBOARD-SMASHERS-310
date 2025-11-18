class ReviewSubject:
    def __init__(self):
        self._observer = None

    def attach(self, observer):
        self._observer = observer

    def detach(self):
        self._observer = None

    def notify(self, event_type, event_data):
        if self._observer:
            self._observer.update(self, event_type, event_data)
