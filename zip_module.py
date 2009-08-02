from aptrow import *
import zipfile

aptrowModule = ResourceModule()
    
class ZipItemsTree:
    """Representation of items in a zip file as a recursively defined tree structure"""
    def __init__(self):
        self.files = []
        self.subdirs = {}
        
    def addPath(self, path, zipItem):
        slashPos = path.find("/")
        if slashPos == -1:
            self.files.append((path, zipItem))
        else:
            subdir = path[:slashPos]
            restOfPath = path[slashPos+1:]
            subdirTree = self.subdirs.get(subdir)
            if subdirTree == None:
                subdirTree = ZipItemsTree()
                self.subdirs[subdir] = subdirTree
            if len(restOfPath) > 0:
                subdirTree.addPath(restOfPath, zipItem)
    
    def asHtml(self):
        buffer = io.StringIO()
        subdirKeys = self.subdirs.keys()
        if len(subdirKeys) + len(self.files) > 0:
            buffer.write("<ul>")
            for file,zipItem in self.files:
                buffer.write("<li><a href=\"%s\">%s</a> <small>(<a href=\"%s\">contents</a>)</small></li>" 
                             % (zipItem.url(), h(file), zipItem.contents().url()))
            for subdir in subdirKeys:
                 buffer.write("<li>%s\n" % h(subdir))
                 buffer.write("%s\n" % self.subdirs[subdir].asHtml())
                 buffer.write("</li>\n")
            buffer.write("</ul>")
        return buffer.getvalue()
        
@resourceTypeNameInModule("zip", aptrowModule)
class ZipFile(BaseResource):
    """A resource representing a Zip file, which gives access to the items within the Zip file
    as nested resources. The ZipFile resource needs to be created from a 'file' resource, where
    the 'file' can be anything with a suitable 'openBinaryFile()' method."""
    
    resourceParams = [ResourceParam("file")]

    def __init__(self, fileResource):
        BaseResource.__init__(self)
        self.fileResource = fileResource
        
    def urlParams(self):
        """Parameters required to construct the URL for this resource."""
        return {"file": [self.fileResource.url()]}
        
    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "Zip file[%s]" % self.fileResource.heading()
    
    def checkExists(self):
        self.fileResource.checkExists()

    def openZipFile(self):
        """Return on open (read-only) zipfile.ZipFile object."""
        return zipfile.ZipFile(self.fileResource.openBinaryFile(), "r")
    
    @staticmethod
    @interpretationOf(fileLikeResource)
    def interpretationLink(fileResource):
        return "<a href =\"%s\">zipFile</a>" % ZipFile(fileResource).url()
    
    def getZipInfos(self):
        """Get the list of ZipInfo objects representing information about the
        items in the zip file."""
        zipFile = self.openZipFile()
        try:
            return zipFile.infolist()
        finally:
            zipFile.close()
            
    viewsAndDescriptions = [(View(type), type) for type in ["list", "tree"]]
            
    def defaultView(self):
        return View("list")

    def html(self, view):
        """HTML content for this resource. Link back to base file resource, and list
        items within the file."""
        yield "<p>Resource <b>%s</b> interpreted as a Zip file</p>" % self.fileResource.htmlLink()
        yield "<p>Views: %s</p>" % self.viewLinksHtml(ZipFile.viewsAndDescriptions, view)
        for text in self.showZipItems[view.type](self): yield text
            
    @byViewMethod
    def showZipItems(self):
        pass

    @byView("list", showZipItems)
    def showZipItemsAsList(self):
        """Show list of links to zip items within the zip file."""
        zipInfos = self.getZipInfos()
        yield "<h3>Items</h3>"
        yield "<ul>"
        for zipInfo in zipInfos:
            itemName = zipInfo.filename
            yield "<li><a href=\"%s\">%s</a></li>" % (ZipItem(self, itemName).url(), h(itemName))
        yield "</ul>"
        
    @byView("tree", showZipItems)
    def showZipItemsAsTree(self):
        """Show list of links to zip items as a tree."""
        zipInfos = self.getZipInfos()
        yield "<h3>Items Tree</h3>"
        zipItemsTree = ZipItemsTree()
        for zipInfo in zipInfos:
            itemName = zipInfo.filename
            zipItemsTree.addPath(itemName, ZipItem(self, itemName))
        yield zipItemsTree.asHtml()
        
    @attribute(StringParam("name"))
    def item(self, name):
        """Return a named item from this zip file as a ZipItem resource"""
        return ZipItem(self, name)
    
    @attribute(StringParam("path"))
    def dir(self, path):
        """Return a named item from this zip file as a ZipFileDir resource"""
        return ZipFileDir(self, path)
    
class ZipFileDir(AttributeResource):
    """A resource representing a directory within a zip file. Considered to exist if the path
    name ends in '/', and, either (1) a corresponding Zip item exists, or (2) other Zip items exist 
    with the path as a prefix. The root directory is represented by '/', even though for matching
    purposes, it is really ''."""
    
    def __init__(self, zipFile, path):
        self.zipFile = zipFile
        self.path = path
        self.matchPath = "" if path == "/" else path
        
    def isRoot(self):
        return self.path == "/"
    
    def baseObjectAndParams(self):
        """This resource is defined as a named 'dir' attribute of the enclosing ZipFile resource."""
        return (self.zipFile, "dir", {"path": self.path})
        
    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "Directory %s in %s" % (self.path, self.zipFile.heading())
    
    def checkExists(self):
        self.zipFile.checkExists()
        if not (self.isRoot() or self.path.endswith("/")):
            raise NoSuchObjectException("Invalid Zip dir %s does not end with '/'" % self.path)
        zipFile = self.zipFile.openZipFile()
        try:
            zipInfo = zipFile.getinfo(self.path)
        except KeyError:
            childItems = self.getChildItems()
            if len(childItems) == 0:
                raise NoSuchObjectException("No item or child items for zip dir %s in %s" 
                                            % (self.path, self.zipFile.heading()))
        
    def defaultView(self):
        return View("list")

    @attribute()
    def parent(self):
        """Parent directory"""
        if self.isRoot():
            return None
        else:
            previousSlashPos = self.path[:-1].rfind("/")
            if previousSlashPos == -1:
                return ZipFileDir(self.zipFile, "/")
            else:
                return ZipFileDir(self.zipFile, self.path[0:previousSlashPos+1])
            
    def getZipInfos(self):
        return [zipInfo for zipInfo in self.zipFile.getZipInfos() if zipInfo.filename.startswith(self.matchPath)]
        
    def getChildItems(self):
        return [ZipItem(self.zipFile, zipInfo.filename) for zipInfo in self.getZipInfos()]
    
    @attribute(StringParam("name"))
    def item(self, name):
        """Return a named item from this ZipFileDir as a ZipItem resource"""
        return ZipItem(self.zipFile, self.path + name)
    
    viewsAndDescriptions = [(View(type), type) for type in ["list", "tree"]]
    
    @byViewMethod
    def showZipItems(self):
        pass

    @byView("list", showZipItems)
    def showZipItemsAsList(self, view = None):
        """Show list of links to zip items within the zip file."""
        yield "<h3>Items</h3>"
        yield "<ul>"
        for childItem in self.getChildItems():
            yield "<li><a href=\"%s\">%s</a></li>" % (childItem.url(), h(childItem.name))
        yield "</ul>"
        
    @byView("tree", showZipItems)
    def showZipItemsAsTree(self, view = None):
        yield "<h3>Items (Tree)</h3>"
        yield "<ul>"
        zipItemsTree = ZipItemsTree()
        pathLength = len(self.path)
        for zipInfo in self.getZipInfos():
            itemName = zipInfo.filename[pathLength:]
            if itemName != "":
                zipItemsTree.addPath(itemName, ZipItem(self, itemName))
        yield zipItemsTree.asHtml()
        yield "</ul>"
        
        
    def html(self, view):
        """HTML content for this resource."""
        yield "<p>Views: %s</p>" % self.viewLinksHtml(ZipFileDir.viewsAndDescriptions, 
                                                      view)
        yield "<p>Zip file: <a href=\"%s\">%s</a></p>" % (self.zipFile.url(), self.zipFile.heading())
        parentDir = self.parent()
        if parentDir:
            parentPath = parentDir.path
            yield "<p>Parent: <a href=\"%s\">%s</a></p>" % (parentDir.url(), parentPath)
        for text in self.showZipItems[view.type](self): yield text
        
class ZipItem(AttributeResource):
    """A resource representing a named item within a zip file. (Note: current implementation
    specifies name only, so if there are multiple items with the same name -- something generally
    to be avoided when creating zip files, but it can happen -- there is currently no way to access 
    them. Some additional information would have to be included in this resource class to handle multiple items.)"""

    resourceInterfaces = [fileLikeResource]

    def __init__(self, zipFile, name):
        self.zipFile = zipFile
        self.name = name
        
    def baseObjectAndParams(self):
        """This resource is defined as a named 'item' attribute of the enclosing ZipFile resource."""
        return (self.zipFile, "item", {"name": self.name})
    
    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "Item %s in %s" % (self.name, self.zipFile.heading())
    
    def getZipInfo(self):
        return self.zipFile.openZipFile().getinfo(self.name)
    
    def checkExists(self):
        self.zipFile.checkExists()
        zipFile = self.zipFile.openZipFile()
        try:
            zipInfo = zipFile.getinfo(self.name)
        except KeyError:
            raise NoSuchObjectException("Zip item %r not found in %s" % (self.name, self.zipFile.heading()))

    def openBinaryFile(self):
        """Return an open file giving direct access to the contents of the zip item.
        io.BytesIO is currently used as an intermediary, because the 'file-like' features
        of the object returned by ZipFile.open are somewhat limited.
        """
        print("ZipItem.openBinaryFile for name %s ..." % self.name)
        zipFile = self.zipFile.openZipFile()
        memoryFile = io.BytesIO()
        zipItem = zipFile.open(self.name, "r")
        zipItemBytes = zipItem.read()
        print (" read %s bytes" % len(zipItemBytes))
        memoryFile.write(zipItemBytes)
        memoryFile.seek(0)
        zipItem.close()
        zipFile.close()
        return memoryFile
    
    zipInfoAttributes = "filename date_time compress_type comment extra create_system create_version extract_version reserved flag_bits volume internal_attr external_attr header_offset CRC compress_size file_size".split()
    
    def zipInfoHtml(self):
        zipInfo = self.getZipInfo()
        buffer = io.StringIO()
        buffer.write("<h3>Zip Info attributes</h3>")
        buffer.write("<table>\n")
        for attr in ZipItem.zipInfoAttributes:
            buffer.write("<tr><td>%s:</td><td><b>%r</b></td>\n" % (attr, getattr(zipInfo, attr)))
        buffer.write("</table>\n")
        return buffer.getvalue()
    
    def asZipFileDir(self):
        return ZipFileDir(self.zipFile, self.name)
    
    def html(self, view):
        """HTML content for zip item. Somewhat similar to what is displayed for File resource."""
        yield "<p><a href=\"%s\">Content</a>" % FileContents(self, "text/plain").url()
        yield " (<a href =\"%s\">html</a>)" % FileContents(self, "text/html").url()
        yield "</p>"
        if self.name.endswith("/"):
            zipFileDir = self.asZipFileDir()
            yield "<p><a href =\"%s\">(as Zip directory)</a> " % zipFileDir.url()
        yield self.zipInfoHtml()

    @attribute(StringParam("contentType", optional = True))
    def contents(self, contentType = None):
        """Return contents of zip item with optional content type"""
        return FileContents(self, contentType)
    
