class _Group:
    pass

class _Var:
    def __init__(self, label, x):
        self._label = label
        self.set(x)

    def set(self, x):
        self._val = x
        #print('SHM set: ' + self._label + ' = ' + str(x))

    def get(self):
        return self._val

hydrophones_pinger_status = _Group()
hydrophones_pinger_status.packet_number = _Var(
    'hydrophones_pinger_status.packet_number', 0)

hydrophones_pinger_results = _Group()
hydrophones_pinger_results.heading = _Var(
    'hydrophones_pinger_results.heading', 0)
hydrophones_pinger_results.elevation = _Var(
    'hydrophones_pinger_results.elevation', 0)

gx4 = _Group()
gx4.heading = _Var('gx4.heading', 0)
gx4.pitch = _Var('gx4.pitch', 0)