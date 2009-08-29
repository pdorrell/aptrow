""" Copyright 2009 Philip Dorrell http://www.1729.com/ (email: http://www.1729.com/email.html)
    
  This file is part of Aptrow ("Advance Programming Technology Read-Only Webification": http://www.1729.com/aptrow/)

  Aptrow is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License 
  as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

  Aptrow is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty 
  of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along with Aptrow (as license-gplv3.txt).
  If not, see <http://www.gnu.org/licenses/>."""

# Platform: Python 3.1 (currently being developed on MS Windows)

# Base module to be imported by all modules presenting specific resource types, and also by aptrow_server.py

import urllib
import os
import traceback
import cgi
import io

def h(value):
    """ HTML escape a string value """
    return cgi.escape(value)

def hr(value):
    """ HTML escape %r version of object description """
    return h(value.__repr__())

def spacedList(list):
    newList = [" "] * (len(list)*2-1)
    for i, item in enumerate (list):
        newList[i*2] = item
    return newList

resourceModules = {}

def addResourceModule(prefix, resourceModule):
    resourceModule.urlPrefix = prefix
    resourceModules[prefix] = resourceModule
    
def addModule(prefix, moduleName, moduleAttribute = "aptrowModule"):
    module =__import__(moduleName, locals(), globals(), [], -1)
    addResourceModule(prefix, getattr(module, moduleAttribute))

class ResourceModule:
    def __init__(self):
        self.classes = {}
        
    def getResourceClass(self, name):
        resourceClass = self.classes.get(name)
        print("In ResourceModule found class %s for name %s" % (resourceClass, name))
        if resourceClass == None:
            raise ResourceTypeNotFoundForPathException("%s%s" % (self.urlPrefix, name))
        return resourceClass
        
def resourceTypeNameInModule(name, module):
    """ Class decorator to define the resource type (i.e. 1st part of URL) 
    for a base resource class, i.e. a class derived from BaseResource, relative to a ResourceModule """
    def registerResourceClass(resourceClass):
        print("Registering resource class %s" % (resourceClass.__name__))
        module.classes[name] = resourceClass
        resourceClass.resourcePath = name
        resourceClass.module = module
        return resourceClass
    return registerResourceClass

class MessageException(Exception):
    """An exception class whose default string representation is the 'message' attribute."""
    def __str__(self):
        return self.message

class ResourceTypeNotFoundForPathException(MessageException):
    """Thrown when looking up a resource type not registered in resourceClasses."""
    def __init__(self, path):
        self.path = path
        self.message = "No resource type defined for path \"%s\"" % path

def getResource(url):
    """Given a URL, find or create the corresponding resource that the URL represents.
    (The intention is to support remote resources from other Aptrow servers, but currently
    only URL's relative to the local server are supported.)
    
    Even though WSGI functions parse URL's and query parameters for you, this method is needed
    to process URL's included as parameter values in other URL's. """
    
    if url.startswith("/"):
        localUrl = url[1:]
        queryStart = localUrl.find("?")
        if queryStart == -1:
            path = localUrl
            query = None
        else:
            path = localUrl[:queryStart]
            query = localUrl[queryStart+1:]
        resource, view = getResourceAndViewFromPathAndQuery(path, query)
        return resource
    else:
        raise Error("Non-local resource URL's not yet implemented (doesn't start with '/'): %s" % localUrl)
    
class UnknownAttributeException(MessageException):
    """Thrown when an attribute name is not valid."""
    def __init__(self, attribute, resource):
        self.attribute = attribute
        self.resource = resource
        self.message = "No attribute \"%s\" defined for resource [%s]" % (attribute, resource.heading())
    
def getResourceAndViewFromPathAndQuery(path, query):
    """Look up resource object from URL path and query. This includes processing of parameters passed to the
    base resource type, and optionally the processing of attribute parameters, for when one resource is
    defined as an attribute of another. (For example, a FileContents resource is the "contents" attribute
    of a File resource, with additional optional parameter "contentType".) A numbering scheme allows attribute
    lookups to be chained (see AptrowQueryParams for details). 
    """
    secondSlashPos = path.find("/")
    if secondSlashPos != -1:
        urlPrefix = path[:secondSlashPos]
        print("urlPrefix = %r" % urlPrefix)
        resourceModule = resourceModules.get(urlPrefix)
    else:
        resourceModule = None
    if resourceModule == None:
        raise ResourceTypeNotFoundForPathException(path)
    else:
        print ("Found resourceModule with prefix %s" % resourceModule.urlPrefix)
        resourceClass = resourceModule.getResourceClass(path[secondSlashPos+1:])
    if resourceClass == None:
        raise ResourceTypeNotFoundForPathException(path)
    queryParams = urllib.parse.parse_qs(query)
    aptrowQueryParams = AptrowQueryParams(queryParams)
    resourceParamValues = getResourceParams(aptrowQueryParams, resourceClass.resourceParams)
    object = resourceClass(*resourceParamValues)
    object.resourceParamValues = resourceParamValues # record parameters passed in
    for attribute,params in aptrowQueryParams.attributesAndParams():
        attributeValue = object.resolveAttribute(attribute, params)
        if attributeValue == None:
            raise UnknownAttributeException(attribute, object)
        object = attributeValue
    view = aptrowQueryParams.getView()
    if view == None and object != None:
        view = object.defaultView()
    return object, view
                    
class AptrowApp:
    """The main WSGI Aptrow web application. It accepts the URL representing a resource, finds
    the resource, and then asks the resource to display itself."""
    
    def __init__(self, environ, start_response):
        """WSGI initialiser: save environment and response object"""
        self.environ = environ
        self.start = start_response
        #print ("environ = %r" % environ)
        
    def not_found(self, message):
        """General handler for something not found: currently a message in a plain-text page."""
        self.start('404 Not Found', [('Content-type', 'text/plain')])
        return message
    
    def __iter__(self):
        """Main WSGI method to yield content of requested web page. Looks up resource from URL, 
        and then calls resouce "page" method to render the web page."""
        pathInfo = self.environ['PATH_INFO']
        # print ("pathInfo = %r" % pathInfo)
        if pathInfo.startswith("/"):
            pathInfo = pathInfo[1:]
        queryString = self.environ['QUERY_STRING']
        print ("queryString = %r" % queryString)
        try:
            object, view = getResourceAndViewFromPathAndQuery(pathInfo, queryString)
            object.checkExists()
            #msg = "<p>AppClass sez, you requested <strong>%s</strong> with query string <b>%s</b></p>"
            #self.message = msg % (h(pathInfo), hr(queryString))
            self.message = ""
            for text in object.page(self, view): yield text
        except MissingParameterException as exc:
            yield self.not_found("For resource type \"%s\" %s" % (pathInfo, exc.message))
        except UnknownAttributeException as exc:
            yield self.not_found(exc.message)
        except ResourceTypeNotFoundForPathException as exc:
            yield self.not_found("No resource type defined for path \"%s\"" % pathInfo)
        except (NoSuchObjectException, ParameterException) as exception:
            yield self.not_found(exception.message)

def runAptrowServer(host, port):
    from wsgiref.simple_server import make_server

    httpd = make_server(host, port, AptrowApp)
    print("Serving HTTP on http://%s:%s/ ..." % (host, port))

    # Respond to requests until process is killed
    httpd.serve_forever()

class ParameterException(MessageException):
    """Thrown when a URL parameter is invalid or missing"""
    def __init__(self, message):
        self.message = message
        
class MissingParameterException(MessageException):
    """Thrown when a required URL parameter is missing"""
    def __init__(self, name = None):
        self.message = "Missing parameter %s" % name
        
class UnknownViewTypeException(MessageException):
    """Thrown when a view type is invalid"""
    def __init__(self, type):
        self.message = "Unknown view type \"%s\"" % type
        
class Interpretation:
    """A possible interpretation of this resource as another resource."""
    def __init__(self, resource, description, likely):
        self.resource = resource
        self.description = description
        self.likely = likely
        
    def link(self):
        return "<a href=\"%s\">%s</a>" % (self.resource.url(), h(self.description))
        
class ResourceInterface:
    """A holder for methods that can 'interpret' a give type of resource, e.g. a 'file-like' resource.
    Add resource interfaces to the 'resourceInterfaces' class variable of the target resource classes, and
    define @interpretationOf-decorated (static) methods in the resource classes providing the interpretations.
    """
    def __init__(self):
        self.interpretationMethods = []
        
    def addInterpretation(self, method):
        self.interpretationMethods.append(method)
        
    def getInterpretationsOf(self, resource):
        return [method(resource) for method in self.interpretationMethods]
    
# all resources are "aptrow" resources
aptrowResource = ResourceInterface()
    
# resource interface for resources which are "like" a File
fileLikeResource = ResourceInterface()

def interpretationOf(resourceInterface):
    def decorator(interpretationMethod):
        resourceInterface.addInterpretation(interpretationMethod)
        return interpretationMethod
    return decorator
        
class View:
    def __init__(self, type, params = {}):
        self.type = type
        self.params = params
        self.depth = self.params.get("depth")
        if self.depth != None:
            self.depth = int(self.depth)
            
    def depthLessOne(self):
        if self.depth == None:
            return None
        else:
            return self.depth-1
        
    def __eq__(self, other):
        return other != None and self.type == other.type and self.params == other.params
    
    def __repr__(self):
        return "View[%s, %r]" % (self.type, self.params)
    
    def htmlParamsDict(self):
        dict = {}
        if self.type != None:
            dict["view"] = self.type
        for key, value in self.params.items():
            dict["view.%s" % key] = value
        return dict
    
class MethodsByViewType:
    """A dictionary of methods retrieved by view type. 
    Throws UnknownViewTypeException if view type is unknown."""
    def __init__(self):
        self.methods = {}
        
    def __setitem__(self, key, value):
        self.methods[key] = value
    
    def __getitem__(self, key):
        value = self.methods.get(key)
        if value == None:
            raise UnknownViewTypeException(key)
        else:
            return value
        
def byViewMethod(func):
    return MethodsByViewType()

def byView(viewType, methodsByViewType):
    """Decorator for methods to be looked up by view type"""
    def decorator(func):
        methodsByViewType[viewType] = func
        return func
    return decorator
  
class AptrowQueryParams:
    """An object wrapping URL parameters, and presenting them as follows:
    
    Parameters consist of:
    
    * Base parameters passed directly to the resource type in order to retrieve (or create) the base resource.
    * Attribute parameters.
    
    Attribute parameters (and any other special parameters, but there aren't any so far) start with '_'. 
    All base parameters should start with an alphabetic character.
    
    Attribute parameters represent a possible chain of 1 more attribute lookups, each with an attribute
    name and a set of named parameters for each lookup. The lookups are applied first to the base resource, 
    and then in turn to the result of each previous lookup.
    
    The chain of N attribute names is represented by parameters with the key '_<n>' for n = 1 to N. 
    Individual attribute parameters are numbered from 1 up, with the format '_<n>.<name>', where <n> is the 
    number, and <name> is the parameter name (which should also start with an alphabetic character).
    
    The attribute calls are in effect method calls, because they can take parameters. However they are called
    'attributes' to emphasise their read-only nature. """
    
    def __init__(self, htmlParams):
        self.htmlParams = htmlParams
        
    def getString(self, name):
        """Retrieve an optional base resource parameter by name."""
        valuesArray = self.htmlParams.get(name)
        return None if valuesArray == None else valuesArray[0]
    
    def getRequiredString(self, name):
        """Retrieve a required base resource parameter by name."""
        value = self.getString(name)
        if value == None:
            raise ParameterException("Missing parameter %r" % name)
        return value
    
    def attributesAndParams(self):
        """Extract attribute parameters as a list of pairs of names and parameter dicts."""
        count = 1
        finished = False
        while not finished:
            attributeKey = "_%s" % count
            attribute = self.getString(attributeKey)
            if attribute == None:
                finished = True
            else:
                yield (attribute, self.attributeParams(count))
                count += 1
                
    def attributeParams(self, count):
        """For a given attribute lookup (identified by number from 1 up), retrieve parameters
        for that lookup into a dict."""
        params = {}
        for key, value in self.htmlParams.items():
            prefix = "_%s." % count
            if key.startswith(prefix):
                params[key[len(prefix):]] = value[0]
        return params
    
    def getView(self, defaultType = None):
        type = self.getString("view")
        if type == None:
            return None
        else:
            params = {}
            for key, value in self.htmlParams.items():
                if key.startswith("view."):
                    params[key[len("view."):]] = value[0]
            return View(type, params)
    
class NoSuchObjectException(MessageException):
    """Thrown when a Resource has been created and is then later found not to represent a valid resource. 
    Generally thrown by the 'checkExists()' method."""
    def __init__(self, message):
        self.message = message
        
class Param:
    """Parameter definition for an expected base resource parameter."""
    def __init__(self, name, optional = False):
        self.name = name
        self.optional = optional
        
    def getValue(self, stringValue):
        """Get value of parameter from a string value. 
        (Depends on definition of getStringValue method, is a value is supplied.)"""
        if stringValue == None:
            if self.optional:
                return None
            else:
                raise MissingParameterException(self.name)
        else:
            return self.getValueFromString(stringValue)
        
    def description(self):
        return "%s[%s%s]" % (self.label(), self.name, " (optional)" if self.optional else "")

class StringParam(Param):
    """Parameter definition for an expected base resource parameter, expecting it to be a string value."""
        
    def getValueFromString(self, stringValue):
        """Value for a string parameter is just the string"""
        return stringValue
    
    def label(self):
        return "String"
    
    def reflectionHtml(self, value):
        return "%s = \"%s\"" % (h(self.name), h(value))
    
class ResourceParam(Param):
    """Parameter definition for an expected base resource parameter, expecting it to be a URL representing
    another resource (to be used as input when creating the resource being created)."""
        
    def getValueFromString(self, stringValue):
        """Convert to a value by looking up resource from URL"""
        return getResource(stringValue)
    
    def label(self):
        return "Resource"
    
    def reflectionHtml(self, value):
        return "%s =<br/>%s" % (h(self.name), value.reflectionHtml())
    
def getResourceParams(queryParams, paramDefinitions):
    """Get parameters for creating a resource from an AptrowQueryParams and an array of parameter definitions"""
    return [paramDefinition.getValue(queryParams.getString(paramDefinition.name)) 
            for paramDefinition in paramDefinitions]
  
def attribute(*params):
    """Decorator for attribute methods"""
    def decorator(func):
        func.aptrowAttributeParams = params
        return func
    return decorator

class AttributeMethod:
    """An object that replaces a method decorated by @attribute. Wraps the method and parameter definitions."""
    def __init__(self, method, params):
        self.method = method
        self.params = params
        
    def call(self, resource, paramsDict):
        """How to call this method given a resource and a dict of named parameter values."""
        return self.method(resource, *[param.getValue(paramsDict.get(param.name)) for param in self.params])
    
class Resource:
    """Base class for all resources handled and retrieved by the application."""
    
    def checkExists(self):
        """Default existence check: always passes.
        Resource objects are always created from URL definitions. Often they represent information
        from an external source (such as a file with a specified name), but their initial creation 
        does not depend on such information actually existing or being available (i.e. the file might not exist).
        Override the 'checkExists' method to throw NoSuchObjectException's if a resource is found
        to not represent a valid external resource.
        """
        pass
    
    def getInterpretations(self):
        interpretations = aptrowResource.getInterpretationsOf(self)
        if hasattr(self.__class__, "resourceInterfaces"):
            for interface in self.__class__.resourceInterfaces:
                interpretations += interface.getInterpretationsOf(self)
        return interpretations
    
    def interpretationLinksHtml(self):
        interpretations = self.getInterpretations()
        likelyLinks = [interpretation.link() for interpretation in interpretations if interpretation.likely]
        unlikelyLinks = [interpretation.link() for interpretation in interpretations if not interpretation.likely]
        if len(likelyLinks) + len(unlikelyLinks) == 0:
            return ""
        else:
            if len(unlikelyLinks) > 0:
                unlikelyLinks = ["("] + unlikelyLinks + [")"]
            return "<p><b>Interpret as:</b> %s" % (" ".join(likelyLinks + unlikelyLinks))
    
    def defaultView(self):
        return None
    
    def htmlLink(self):
        """Default HTML link for a resource. No styling or any other extras, 
        and uses 'heading()' for display value."""
        return "<a href=\"%s\">%s</a>" % (h(self.url()), h(self.heading()))
    
    
    def attributeUrlParams(self, attribute, count, params):
        """Return URL parameters for a single (numbered) attribute lookup as a map."""
        attributeParams = {"_%s" % count: attribute}
        for key, value in params.items():
            attributeParams["_%s.%s" % (count, key)] = value
        return attributeParams
    
    def page(self, app, view):
        """Return the web page for the resource. Default is to return an HTML page
        by calling the resource's 'html()' method. (Override this method entirely
        if something else is required. Note that currently this application does
        not take any notice of requested content types.)"""
        heading = self.heading()
        response_headers = [('Content-Type','text/html')]
        app.start('200 OK', response_headers)
        yield "<html><head><title>%s</title></head><body>" % h(heading)
        yield app.message
        yield "<h2>%s</h2>" % h(heading)
        yield self.interpretationLinksHtml()
        try:
            for text in self.html(view): yield text
        except BaseException as error:
            traceback.print_exc()
            yield "<div class =\"aptrowError\">Error: %s</div>" % (h(str(error)),)
        yield "</body></html>"
        
    def resolveAttribute(self, attribute, params):
        """Resolve an attribute, by looking for a method with same name decorated by @attribute decorator."""
        attributeMethod = self.__class__.__dict__.get(attribute)
        if hasattr(attributeMethod, "aptrowAttributeParams"):
            attributeParams = attributeMethod.aptrowAttributeParams
            return attributeMethod(self, *[param.getValue(params.get(param.name)) for param in attributeParams])
        else:
            return None
        
    def viewLink(self, view, description, currentView):
        if view == currentView:
            return h(description)
        else:
            return "<a href=\"%s\">%s</a>" % (self.url(view = view), h(description))
            
    def viewLinksHtml(self, viewsAndDescriptions, currentView):
        return " ".join([self.viewLink(view, description, currentView) 
                         for view, description in viewsAndDescriptions])
            
    def listAndTreeViewLinks(self, view):
        """Common list of view types: list or tree with optional depths"""
        maxDepths = 4
        if view.type == "tree" and view.depth != None:
            maxDepths = view.depth+2
        return "".join([self.viewLink(View("list"), "list", view), 
                        " ", 
                        self.viewLink(View("tree"), "tree", view), 
                        "(depth: "] +
                       spacedList([self.viewLink(View("tree", {"depth": str(depth)}), str(depth), view)
                                   for depth in range(1, maxDepths+1)]) +
                       [")"])

class BaseResource(Resource):
    """Base class for Resource classes representing resources constructed directly 
    from registered resource types."""
    
    def __init__(self):
        self.module = None
        
    def modulePrefix(self):
        if hasattr(self.__class__, "module"):
            return "/" + self.__class__.module.urlPrefix
        else:
            return ""

    def url(self, attributesAndParams = [], view = None):
        """ Construct URL for this resource, from registered resource type and parameter
        values from urlParams(). Any supplied attribute lookups are added to the end of the URL."""
        urlString = "%s/%s?%s" % (self.modulePrefix(), self.__class__.resourcePath, 
                                urllib.parse.urlencode(self.urlParams(), True))
        count = 1
        for attribute,params in attributesAndParams:
            urlString += "&%s" % urllib.parse.urlencode(self.attributeUrlParams(attribute, count, params))
            count += 1
        if view != None:
            urlString += "&%s" % urllib.parse.urlencode(view.htmlParamsDict())
        return urlString
    
    def getAttributeHtml(self, attribute, params):
        print ("attribute = %r, params = %r" % (attribute, params))
        paramHtmls = ["%s = \"%s\"" % (h(param), h(value)) for param,value in params.items()]
        return "<b>%s</b> <b>%s</b>(%s)" % ("->", h(attribute), ", ".join(paramHtmls))
    
    def reflectionHtml(self, attributesAndParams = []):
        """Output HTML showing the parameters that define this resource"""
        resourceParamsAndValues = zip(self.__class__.resourceParams, self.resourceParamValues)
        paramValuesHtmls = [param.reflectionHtml(value) for (param, value) in resourceParamsAndValues]
        paramValuesListItems = ["<li>%s</li>" % html for html in paramValuesHtmls]
        attributesAndParamsHtmls = [self.getAttributeHtml(attribute, params) 
                                   for attribute, params in attributesAndParams]
        attributeAndParamItems = ["<br/>%s" % html for html in attributesAndParamsHtmls]
        return "<b>%s:</b><ul>%s</ul>%s" % (h(self.__class__.__name__), 
                                            "".join(paramValuesListItems), 
                                            "".join(attributeAndParamItems))
    
class AttributeResource(Resource):
    """Base class for Resource classes representing resources which are constructed as attributes
    of other resources. """
    
    def getBaseObjectAttributesAndParams(self, attributesAndParams = []):
        baseObject, attribute, params = self.baseObjectAndParams()
        return baseObject, [(attribute, params)] + attributesAndParams
    
    def url(self, attributesAndParams = [], view = None):
        """Construct a URL for this resource, by determining the details for the base object and
        the attribute parameters used to look up this object, then append any additional supplied
        attribute lookups before creating the full URL."""
        baseObject, baseObjectAttributesAndParams = self.getBaseObjectAttributesAndParams(attributesAndParams)
        return baseObject.url(baseObjectAttributesAndParams, view = view)
                                      
    def reflectionHtml(self, attributesAndParams = []):
        baseObject, baseObjectAttributesAndParams = self.getBaseObjectAttributesAndParams(attributesAndParams)
        return baseObject.reflectionHtml(baseObjectAttributesAndParams)
                                     
class FileContents(AttributeResource):
    """A resource representing the contents of a file, to be returned directly
    to the web browser (with an optionally specified content type). The 'file'
    can be any resource which has a suitable 'openBinaryFile()' method."""
    
    def __init__(self, file, contentType = None):
        self.file = file
        self.contentType = contentType
        
    def baseObjectAndParams(self):
        """This resource is assumed to be the 'contents' attribute of the corresponding 'file' resource."""
        return (self.file, "contents", {"contentType": self.contentType})
    
    def checkExists(self):
        """This resource exists if the file resource exists."""
        self.file.checkExists()
    
    def page(self, app, view):
        """Override default page() method to send contents directly with content type (if specified)."""
        response_headers = []
        if self.contentType != None:
            response_headers.append(('Content-Type', self.contentType))
        app.start('200 OK', response_headers)
        with self.file.openBinaryFile() as f:
            yield f.read()
            
