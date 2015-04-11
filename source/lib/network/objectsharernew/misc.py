class RemoteException(Exception):
    pass

class TimeoutError(RuntimeError):
    pass

def ellipsize(s):
    if len(s) > 64:
        return s[:64] + '...'
    else:
        return s

class UID(object):
    '''
    Lower overhead UID object than uuid.UUID.
    - Construction is over 30 times faster.
    - Hashing is faster because it uses the binary representation
    - Pickle is slightly larger due to objectsharer in name
    '''

    def __init__(self, bytes=None):
        self.b = bytes

    def __str__(self):
        s = ''.join(['%02x'%ord(b) for b in self.b])
        return '-'.join((s[:8], s[8:12], s[12:16], s[16:20], s[20:]))

    def __eq__(self, other):
        if isinstance(other, UID):
            return self.b == other.b
        else:
            return self.b == other

    def __hash__(self):
        return hash(self.b)
