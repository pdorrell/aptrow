
def _toString(data): 
    if type(data) in [tuple, list]:
        return "".join([_toString(item) for item in data])
    else:
        return str(data)

class Tag:
    def __init__(self, name, *children, **attributes):
        self.name = name
        self.children = children
        self.attributes = attributes
        
    def __str__(self):
        return self.startString() + _toString(self.children) + self.endString()
    
    def __repr__(self):
        return str(self)
    
    def startString(self):
        if len(self.attributes) == 0:
            attributesString = ""
        else:
            attributesString = " %s" % " ".join(["%s=\"%s\"" % (key, value) 
                                                 for key, value in self.attributes.items()])
        return "<%s%s>" % (self.name, attributesString)
    
    def endString(self):
        return "</%s>" % self.name

class H2(Tag):
    def __init__(self, *children):
        Tag.__init__(self, "h2", *children)
        
class A(Tag):
    def __init__(self, *children, **attributes):
        Tag.__init__(self, "a", *children, **attributes)

    
class P(Tag):
    def __init__(self, *children, **attributes):
        Tag.__init__(self, "p", *children, **attributes)
    
class B(Tag):
    def __init__(self, *children, **attributes):
        Tag.__init__(self, "b", *children, **attributes)
    
        