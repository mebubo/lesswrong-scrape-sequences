class Sequence(object):
    def __init__(self, title):
        self._title = title
        self._entries = []
    
    def title(self):
        return self._title
    
    def append(self, p):
        self._entries.append(p)
    
    def before(self, p):
        ix = self._entries.index(p)
        if ix == 0:
            return None
        return self._entries[ix -1]
    
    def after(self, p):
        ix = self._entries.index(p)
        if ix+1 == len(self._entries):
            return None
        return self._entries[ix +1]
        
