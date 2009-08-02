from aptrow import *

# Aptrow module presenting a character string (encoded in the URL) as a resource

aptrowModule = ResourceModule()

@resourceTypeNameInModule("string", aptrowModule)
class String(BaseResource):
    """A resource representing a String value. (There is no external resource, as the 
    string is provided as a parameter. This resource type is mostly useful for testing, 
    for example to test HTML quoting. But it could have other uses, for example to display
    all the properties of a string, what characters it contains, how long it is, etc.)"""
    
    resourceParams = [StringParam("value")]

    def __init__(self, value):
        BaseResource.__init__(self)
        self.value = value
        
    def urlParams(self):
        """Parameters required to construct the URL for this resource."""
        return {"value": [self.value]}

    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "String: %r" % self.value
    
    def html(self, view):
        """HTML content for string: show it in bold."""
        yield "<p>String: <b>%s</b></p>" % h(self.value)
        
