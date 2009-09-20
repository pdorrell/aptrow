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
import re

import htmltags as tag

def h(value):
    """ HTML escape a string value """
    return cgi.escape(value)

def hr(value):
    """ HTML escape %r version of object description """
    return h(value.__repr__())

def spacedList(theList):
    """Take a list and return a list with spaces inserted between the strings"""
    newList = [" "] * (len(theList)*2-1)
    for i, item in enumerate (theList):
        newList[i*2] = item
    return newList

"""A mapping from URL prefix to ResourceModule"""
resourceModules = {}

def addResourceModule(prefix, resourceModule):
    """Add a ResourceModule to resourceModules, also record the ResourceModule's urlPrefix value
    (so we can go from URL to Resource and back again)"""
    resourceModule.urlPrefix = prefix
    resourceModules[prefix] = resourceModule
    
def addModule(prefix, moduleName, moduleAttribute = "aptrowModule"):
    """Import the named module and add it's enclosed ResourceModule 
    (by default defined as <module>.aptrowModule)"""
    module =__import__(moduleName, locals(), globals(), [], -1)
    addResourceModule(prefix, getattr(module, moduleAttribute))

class ResourceModule:
    """A ResourceModule represents information about Resource classes defined within one
    Python module.
    Lookup of resources occurs in several steps:
    1. Lookup ResourceModule in resourceModules by first portion of path in URL
    2. Lookup Resource class from ResourceModule by second portion of path in URL
    3. Intepret query parameters to create base Resource from Resource class
    4. (Optional, one or more times) interpret 'attribute' query parameters to determine attribute of base resource
    """
    def __init__(self):
        self.classes = {}
        
    def getResourceClass(self, name):
        """Lookup named Resource class"""
        resourceClass = self.classes.get(name)
        if resourceClass == None:
            raise ResourceTypeNotFoundForPathException("%s%s" % (self.urlPrefix, name))
        return resourceClass
        
aptrowModule = ResourceModule()

def resourceTypeNameInModule(name, module):
    """ Class decorator to define the resource type (i.e. 2nd part of URL) 
    for a resource class, i.e. a class derived from Resource, relative to a ResourceModule """
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
    
    Even though WSGI functions parse URL's and query parameters for you, this method (which
    duplicates some of that parsing) is needed
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
        raise ParameterException("Non-local resource URL's not yet implemented (doesn't start with '/'): %s" % localUrl)
    
class UnknownAttributeException(MessageException):
    """Thrown when an attribute name is not valid."""
    def __init__(self, attribute, resource):
        self.attribute = attribute
        self.resource = resource
        self.message = "No attribute \"%s\" defined for resource [%s]" % (attribute, resource.heading())
    
def getResourceAndViewFromPathAndQuery(path, query):
    """Look up resource object from URL path and query. This includes processing of parameters passed to the
    base resource type, and optionally the processing of attribute parameters, for when one resource is
    defined as an attribute of another. (For example, a FileContents resource can be specified as the 
    "contents" attribute of a File resource, with additional optional parameter "contentType".) 
    A numbering scheme allows attribute lookups to be chained (see AptrowQueryParams for details). 
    """
    dotPos = path.find(".")
    if dotPos != -1:
        urlPrefix = path[:dotPos]
        resourceModule = resourceModules.get(urlPrefix)
    else:
        resourceModule = None
    if resourceModule == None:
        raise ResourceTypeNotFoundForPathException(path)
    else:
        resourceClass = resourceModule.getResourceClass(path[dotPos+1:])
    if resourceClass == None:
        raise ResourceTypeNotFoundForPathException(path)
    queryParams = urllib.parse.parse_qs(query)
    aptrowQueryParams = AptrowQueryParams(queryParams)
    resourceParamValues = getResourceParams(aptrowQueryParams.paramTree, resourceClass.resourceParams)
    object = resourceClass(*resourceParamValues)
    object.resourceParamValues = resourceParamValues # record parameters passed in
    for paramTree in aptrowQueryParams.attributeParams:
        attributeValue = object.resolveAttribute(paramTree.value, paramTree)
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
        return tag.A(h(self.description), href = self.resource.url())
        
class ResourceInterface:
    """A holder for methods that can 'interpret' a give type of resource, e.g. a 'file-like' resource.
    Useage: add resource interfaces to the 'resourceInterfaces' class variable of the target resource classes, and
    define @interpretationOf-decorated (static) methods in the resource classes providing the interpretations.
    """
    def __init__(self):
        self.interpretationMethods = []
        
    def addInterpretation(self, method):
        self.interpretationMethods.append(method)
        
    def getInterpretationsOf(self, resource):
        return [method(resource) for method in self.interpretationMethods]
    
"""all resources are "aptrow" resources (do not include this in 'resourceInterfaces' because
it is always implicitly included.)"""
aptrowResource = ResourceInterface()
    
""" resource interface for resources which are "like" a File
So if your resource class is 'file-like', then add this resource interface to
the class variable 'resourceInterfaces' of your class.
Current requirements for 'file-like' are:
* openBinaryFile(self) method which returns an opened binary file
(todo: some other way to return binary data from an object which can not be accessed this way) """
fileLikeResource = ResourceInterface()

def interpretationOf(resourceInterface):
    """Use this decorator to decorate a function (or static method) which returns an Interpretation
    of a supplied source. The resourceInterface argument describes what 'kind' of resource it applies to."""
    def decorator(interpretationMethod):
        resourceInterface.addInterpretation(interpretationMethod)
        return interpretationMethod
    return decorator
        
class View:
    """A 'View' is information about how a resource is to be presented, and
    is defined by URL parameters prefixed with 'view'.
    To present a Resource in different ways (at least as HTML), add necessary
    parameters to the associated View object.
    A integer 'depth' parameter is included as standard.
    """
    def __init__(self, type, params = {}):
        self.type = type
        self.params = params
        self.depth = self.params.get("depth")
        if self.depth != None:
            self.depth = int(self.depth)
            
    def depthLessOne(self):
        """One less than defined depth (if depth is defined)"""
        if self.depth == None:
            return None
        else:
            return self.depth-1
        
    def __eq__(self, other):
        """Is this view the same as another view. 
        (Used to implement the 'make-the-link-to-yourself-inactive' functionality.)"""
        return other != None and self.type == other.type and self.params == other.params
    
    def __repr__(self):
        return "View[%s, %r]" % (self.type, self.params)
    
    def htmlParamsDict(self):
        """Return HTML parameter dictionary (used to recreate view params in URL)"""
        dict = {}
        if self.type != None:
            dict["view"] = self.type
        for key, value in self.params.items():
            dict["view.%s" % key] = value
        return dict
    
class MethodsByViewType:
    """A dictionary of methods retrieved by view type. 
    Throws UnknownViewTypeException if view type is unknown.
    Effectively wraps a dict so that it throws an UnknownViewTypeException
    if the view type is not defined.
    """
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
    """Use this decorator to replace a method with a lookup table
    which looks up a method by view type."""
    return MethodsByViewType()

def byView(viewType, methodsByViewType):
    """Use this decorator to mark the methods that will be found
    when a method defined by the 'byViewMethod' has a lookup done on it."""
    def decorator(func):
        methodsByViewType[viewType] = func
        return func
    return decorator

class ParamTree:
    def __init__(self, value = None):
        self.value = value
        self.branches = {}
        
    def addValue(self, key, value):
        dotPos = key.find(".")
        if dotPos == -1:
            self.branches[key] = ParamTree(value)
        else:
            keyStart = key[:dotPos]
            restOfKey = key[dotPos+1:]
            branch = self.branches.get(keyStart)
            if branch == None:
                branch = ParamTree()
                self.branches[keyStart] = branch
            branch.addValue(restOfKey, value)
            
    def simpleKeyValues(self):
        for key, branchValue in self.branches.items():
            if branchValue.value != None:
                yield key, branchValue.value
                
    def getBranch(self, name):
        return self.branches.get(name)
  
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
        self.processParams()
        
    identifierPattern = r"([a-zA-Z][a-zA-Z0-9_]*)"
    viewParamRegexp = re.compile(r"view\." + identifierPattern + "$")
    attributeKeyRegexp = re.compile(r"_([0-9]*)$")
    attributeParamRegexp = re.compile(r"_([0-9]*)\." + identifierPattern + "$")
    
    def processParams(self):
        print("htmlParams = %r" % self.htmlParams)
        self.paramTree = ParamTree()
        for key, values in self.htmlParams.items():
            self.paramTree.addValue(key, values)
        self.processViewParams()
        self.processAttributeParams()
        
    def processViewParams(self):
        self.viewType = None
        self.viewParams = {}
        viewParamTree = self.paramTree.getBranch("view")
        if viewParamTree != None:
            self.viewType = viewParamTree.value[0]
            for key, value in viewParamTree.simpleKeyValues():
                self.viewParams[key] = value[0]
                
    def processAttributeParams(self):
        count = 1
        finished = False
        self.attributeParams = []
        while not finished:
            attributeKey = "_%s" % count
            attributeParamTree = self.paramTree.branches.get(attributeKey)
            if attributeParamTree != None and attributeParamTree.value != None:
                self.attributeParams.push(attributeParamTree)
                count += 1
            else:
                finished = True
                
    def getParamTree(self, name):
        return self.paramTree.getBranch(name)
    
    def getRequiredParamTree(self, name):
        value = self.paramTree(name)
        if value == None:
            raise ParameterException("Missing parameter %r" % name)
        return value
        
    def getView(self, defaultType = None):
        """Get the View object defined by the 'view' and 'view.<param>' URL parameters."""
        if self.viewType == None:
            return None
        else:
            return View(self.viewType, self.viewParams)
    
class NoSuchObjectException(MessageException):
    """Thrown when a Resource has been created and is then later found not to represent a valid resource. 
    Generally thrown by the 'checkExists()' method."""
    def __init__(self, message):
        self.message = message
        
class Param:
    """Parameter definition for an expected base resource parameter.
    (This is a base class: the 'getStringValue' method must be defined
    by an actual concrete Parameter definition class.)
    """
    def __init__(self, name, optional = False):
        self.name = name
        self.optional = optional
        
    def getValue(self, paramTree):
        """Get value of parameter from a ParamTree
        (Depends on definition of getStringValue method, if a value is supplied.)"""
        if paramTree == None:
            if self.optional:
                return None
            else:
                raise MissingParameterException(self.name)
        else:
            return self.getValueFromParamTree(paramTree)
        
    def addDottedParams(self, paramsMap, prefix, value):
        paramsMap["%s%s" % (prefix, self.name)] = self.getStringFromValue(value)
    
    def description(self):
        return "%s[%s%s]" % (self.label(), self.name, " (optional)" if self.optional else "")

class StringParam(Param):
    """Parameter definition for an expected base resource parameter, expecting it to be a string value."""
        
    def getValueFromParamTree(self, paramTree):
        """Value for a string parameter is just the string"""
        return paramTree.value[0]
    
    def getStringFromValue(self, value):
        """Get the string which represents the value (i.e. inverse of getValueFromString)"""
        return value
    
    def label(self):
        return "String"
    
    def reflectionHtml(self, value):
        return "%s = \"%s\"" % (h(self.name), h(value))
    
class ResourceParam(Param):
    """Parameter definition for an expected base resource parameter, expecting it to be a URL representing
    another resource (to be used as input when creating the resource being created)."""
        
    def getValueFromParamTree(self, paramTree):
        """Convert to a value by looking up resource from URL"""
        if paramTree.value != None:
            return getResource(paramTree.value[0])
        else:
            return self.getResourceFromDottedParams(paramTree)
        
    def getResourceClassFromResourceType(self, resourceType):
        dotPos = resourceType.find(".")
        if dotPos == -1:
            raise ParameterException("No '.' in resource type %s" % resourceType)
        moduleKey = resourceType[:dotPos]
        resourceModule = resourceModules.get(moduleKey)
        if resourceModule == None:
            raise ParameterException("No resource module found for key %s" % moduleKey)
        classKey = resourceType[dotPos+1:]
        resourceClass = resourceModule.getResourceClass(classKey)
        if resourceClass == None:
            raise ParameterException("No resource class found for resourceType %s" % resourceType)
        return resourceClass
        
    def getResourceFromDottedParams(self, paramTree):
        resourceTypeBranch = paramTree.branches.get("_type")
        if resourceTypeBranch == None or resourceTypeBranch.value == None:
            raise ParameterException("Missing _type parameter for resource (and no resource URL supplied)")
        resourceType = resourceTypeBranch.value[0]
        # todo: refactor duplication in getResourceAndViewFromPathAndQuery
        resourceClass = self.getResourceClassFromResourceType(resourceType)
        resourceParamValues = getResourceParams(paramTree, resourceClass.resourceParams)
        object = resourceClass(*resourceParamValues)
        object.resourceParamValues = resourceParamValues # record parameters passed in
        return object
    
    def getStringFromValue(self, value):
        """Get the string which represents the value (i.e. inverse of getValueFromString)"""
        return value.url()

    def label(self):
        return "Resource"
    
    def reflectionHtml(self, value):
        return [h(self.name), " =", tag.BR(), value.reflectionHtml()]
    
    def addDottedParams(self, paramsMap, prefix, value):
        valueType = "%s.%s" % (value.modulePrefix(), value.__class__.resourcePath)
        paramsPrefix = "%s%s." % (prefix, self.name)
        paramsMap["%s_type" % paramsPrefix] = valueType
        value.addDottedParams(paramsMap, paramsPrefix)
    
def getResourceParams(paramTree, paramDefinitions):
    """Get parameters for creating a resource from an AptrowQueryParams and an array of parameter definitions"""
    return [paramDefinition.getValue(paramTree.getBranch(paramDefinition.name)) 
            for paramDefinition in paramDefinitions]
  
def attribute(*params):
    """Decorator for attribute methods"""
    def decorator(func):
        func.aptrowAttributeParams = params
        return func
    return decorator

class Resource:
    """Base class for all resources handled and retrieved by the application."""
    
    def __init__(self, *args):
        self.module = None
        self.args = args
        self.init(*args) # have to define init method for each Resource Class
        
    def urlParams(self):
        return self.dottedUrlParams()
    
    def resourceBasedUrlParams(self):
        """Parameters required to construct the URL for this resource.
        Each resource is represented by its URL.
        Reconstructed from the args used to construct this resource object."""
        paramsMap = {}
        for resourceParam, arg in zip(self.__class__.resourceParams, self.args):
            if arg != None:
                paramsMap[resourceParam.name] = [resourceParam.getStringFromValue(arg)]
        return paramsMap
    
    def addDottedParams(self, paramsMap, prefix = ""):
        for resourceParam, arg in zip(self.__class__.resourceParams, self.args):
            if arg != None:
                resourceParam.addDottedParams(paramsMap, prefix, arg)
        return paramsMap
    
    def dottedUrlParams(self):
        """Parameters required to construct the URL for this resource.
        Using dotted parameter names for parameters which are resources.
        Reconstructed from the args used to construct this resource object."""
        paramsMap = {}
        self.addDottedParams(paramsMap, prefix = "")
        return paramsMap
    
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
            return tag.P(tag.B("Interpret as:"), " ", spacedList(likelyLinks+unlikelyLinks))
    
    def defaultView(self):
        return None
    
    def htmlLink(self):
        """Default HTML link for a resource. No styling or any other extras, 
        and uses 'heading()' for display value."""
        return tag.A(h(self.heading()), href=self.url())
    
    def attributeUrlParams(self, attribute, count, params):
        """Return URL parameters for a single (numbered) attribute lookup as a map."""
        attributeParams = {"_%s" % count: attribute}
        for key, value in params.items():
            attributeParams["_%s.%s" % (count, key)] = value
        return attributeParams
    
    def page(self, app, view):
        for element in self.htmlPage(app, view): yield tag.toString(element)
    
    def htmlPage(self, app, view):
        """Return the web page for the resource. Default is to return an HTML page
        by calling the resource's 'html()' method. (Override this method entirely
        if something else is required. Note that currently this application does
        not take any notice of requested content types.)"""
        heading = self.heading()
        response_headers = [('Content-Type','text/html')]
        app.start('200 OK', response_headers)
        yield "<html><head><title>%s</title></head><body>" % h(heading)
        yield app.message
        yield tag.H2(h(heading))
        yield self.interpretationLinksHtml()
        try:
            for text in self.html(view): yield text
        except BaseException as error:
            traceback.print_exc()
            yield "<div class =\"aptrowError\">Error: %s</div>" % (h(str(error)),)
        yield "</body></html>"
        
    def resolveAttribute(self, attribute, paramTree):
        """Resolve an attribute, by looking for a method with same name decorated by @attribute decorator."""
        attributeMethod = self.__class__.__dict__.get(attribute)
        if hasattr(attributeMethod, "aptrowAttributeParams"):
            attributeParams = attributeMethod.aptrowAttributeParams
            return attributeMethod(self, *[param.getValue(paramTree.getBranch(param.name)) for param in attributeParams])
        else:
            return None
        
    def viewLink(self, view, description, currentView):
        """HTML for the link to another view (inactive if the 'other' view is same as this view) """
        if view == currentView:
            return h(description)
        else:
            return tag.A(h(description), href = self.url(view = view))
            
    def viewLinksHtml(self, viewsAndDescriptions, currentView):
        return spacedList([self.viewLink(view, description, currentView) 
                           for view, description in viewsAndDescriptions])
            
    def listAndTreeViewLinks(self, view):
        """Common list of view types: list or tree with optional depths"""
        maxDepths = 4
        if view.type == "tree" and view.depth != None:
            maxDepths = view.depth+2
        return [self.viewLink(View("list"), "list", view), 
                " ", 
                self.viewLink(View("tree"), "tree", view), 
                "(depth: ", 
                spacedList([self.viewLink(View("tree", {"depth": str(depth)}), str(depth), view)
                            for depth in range(1, maxDepths+1)]),
                ")"]

    def modulePrefix(self):
        return self.__class__.module.urlPrefix

    def url(self, attributesAndParams = [], view = None):
        """ Construct URL for this resource, from registered resource type and parameter
        values from urlParams(). Any supplied attribute lookups are added to the end of the URL."""
        urlString = "/%s.%s?%s" % (self.modulePrefix(), self.__class__.resourcePath, 
                                   urllib.parse.urlencode(self.urlParams(), True))
        count = 1
        for attribute,params in attributesAndParams:
            urlString += "&%s" % urllib.parse.urlencode(self.attributeUrlParams(attribute, count, params))
            count += 1
        if view != None:
            urlString += "&%s" % urllib.parse.urlencode(view.htmlParamsDict())
        return urlString
    
    def formActionParamsAndCount(self, attributesAndParams = []):
        """Return form action, params (for hidden inputs) and count (for additional attribute params)"""
        action = "/%s.%s" % (self.modulePrefix(), self.__class__.resourcePath)
        params = []
        for key, values in self.urlParams().items():
            for value in values:
                params.append((key, value))
        count = 0
        for attribute,params in attributesAndParams:
            count += 1
            for key, value in self.attributeUrlParams(attribute, count, params).items():
                params.append((key, value))
        return action, params, count
    
    def getAttributeHtml(self, attribute, params):
        paramHtmls = ["%s = \"%s\"" % (h(param), h(value)) for param,value in params.items()]
        return [tag.B("->"), " ", tag.B(h(attribute)), "(",  ", ".join(paramHtmls), ")"]
    
    def reflectionHtml(self, attributesAndParams = []):
        """Output HTML showing the parameters that define this resource"""
        resourceParamsAndValues = zip(self.__class__.resourceParams, self.resourceParamValues)
        paramValuesHtmls = [param.reflectionHtml(value) for (param, value) in resourceParamsAndValues]
        paramValuesListItems = [tag.LI(html) for html in paramValuesHtmls]
        attributesAndParamsHtmls = [self.getAttributeHtml(attribute, params) 
                                   for attribute, params in attributesAndParams]
        attributeAndParamItems = [ [tag.BR(), html] for html in attributesAndParamsHtmls]
        return [tag.B(h(self.__class__.__name__), ":"), tag.UL(*paramValuesListItems), 
                attributeAndParamItems]
    
@resourceTypeNameInModule("contents", aptrowModule)
class FileContents(Resource):
    """A resource representing the contents of a file, to be returned directly
    to the web browser (with an optionally specified content type). The 'file'
    can be any resource which has a suitable 'openBinaryFile()' method."""

    resourceParams = [ResourceParam("file"), StringParam("contentType", optional = True)]
    
    def init(self, file, contentType = None):
        self.file = file
        self.contentType = contentType
        
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
            
import tempfile
            
def getFileResourcePath(fileResource):
    """Get path of file from 'file-like' resource, either 
    from .path attribute, or from getFileName() & openBinaryFile()"""
    if hasattr(fileResource, "path"):
        return fileResource.path
    else:
        tempDir = tempfile.mkdtemp(prefix = "aptrow_")
        tempFileName = os.path.join(tempDir, fileResource.getFileName())
        with fileResource.openBinaryFile() as inFile:
            fileContents = inFile.read()
            with open(tempFileName, "wb") as outFile:
                outFile.write(fileContents)
        return tempFileName
