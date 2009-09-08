
def toString(data):
    """Return string form of object,  _unless_ it is a tuple or list, in which
    case concatenate string forms of items in the tuple/list."""
    if type(data) in [tuple, list]:
        return "".join([toString(item) for item in data])
    else:
        return str(data)

class Tag:
    """Class representing an HTML tag element. Has name, child elements, and attributes."""
    def __init__(self, name, *children, **attributes):
        self.name = name
        self.children = children
        self.attributes = attributes
        
    def __str__(self):
        """How this tag is output as HTML text."""
        if len(self.children) == 0:
            return self.start(closed = True)
        else:
            return self.start() + toString(self.children) + self.end()
        
    def __repr__(self):
        return str(self)
    
    def start(self, closed = False):
        """Output HTML string for opening tag for this element"""
        if len(self.attributes) == 0:
            attributesString = ""
        else:
            attributesString = " %s" % " ".join(["%s=\"%s\"" % (key, value) 
                                                 for key, value in self.attributes.items()])
        closeSlash = "/" if closed else ""
        return "<%s%s%s>" % (self.name, attributesString, closeSlash)
    
    def end(self):
        """Output HTML string for closing tag for this element"""
        return "</%s>" % self.name
    
def tagFunction(name):
    """Return a function for creating a Tag object with specified name"""
    def func(*children, **attributes): 
        return Tag(name, *children, **attributes)
    return func

"""List of HTML tags (incomplete at the moment)"""
htmlTagNames = ["h1", "h2", "h3", "h4", "h5", "h6", "a", "p", "b", "ul", "li", "small", "br", 
                "table", "thead", "tbody", "tr", "tr", "td"]

"""Define tag functions for names in htmlTagNames (function names 
are capitalized, e.g. UL for <ul> tag)."""
for tagName in htmlTagNames:
    globals()[tagName.upper()] = tagFunction(tagName)
