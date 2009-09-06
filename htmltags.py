
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
    
def tagFunction(name):
    def func(*children, **attributes): 
        return Tag(name, *children, **attributes)
    return func
    
H2 = tagFunction("h2")
A = tagFunction("a")
P = tagFunction("p")
B = tagFunction("b")
UL = tagFunction("ul")
LI = tagFunction("li")
SMALL = tagFunction("small")
