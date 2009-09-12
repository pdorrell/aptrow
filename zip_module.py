""" Copyright 2009 Philip Dorrell http://www.1729.com/ (email: http://www.1729.com/email.html)
    
  This file is part of Aptrow ("Advance Programming Technology Read-Only Webification": http://www.1729.com/aptrow/)

  Aptrow is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License 
  as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

  Aptrow is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty 
  of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along with Aptrow (as license-gplv3.txt).
  If not, see <http://www.gnu.org/licenses/>."""

from aptrow import *
import zipfile
import htmltags as tag

# Aptrow module enabling a "file-like" resource to be intrepreted as a zip file
# (and presenting items within a zip file as "file-like" resources).

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
        subdirKeys = self.subdirs.keys()
        if len(subdirKeys) + len(self.files) > 0:
            return tag.UL([tag.LI(tag.A(h(file), href = zipItem.url()), " ", 
                                  tag.SMALL("(", tag.A("contents", 
                                                       href = zipItem.contents().url()), ")"))
                           for file, zipItem in self.files], 
                          [tag.LI(h(subdir), " ", 
                                  self.subdirs[subdir].asHtml())
                           for subdir in subdirKeys])
        
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
    def interpretation(fileResource, likely = True):
        return Interpretation(ZipFile(fileResource), "zipFile", 
                              likely = fileResource.extension() in ["zip", "jar", "war"])
    
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
        yield tag.P("Resource ", tag.B(self.fileResource.htmlLink()), 
                    " interpreted as a Zip file")
        yield tag.P("Views: ", self.viewLinksHtml(ZipFile.viewsAndDescriptions, view))
        for text in self.showZipItems[view.type](self): yield text
            
    @byViewMethod
    def showZipItems(self):
        pass

    @byView("list", showZipItems)
    def showZipItemsAsList(self):
        """Show list of links to zip items within the zip file."""
        zipInfos = self.getZipInfos()
        yield tag.H3("Items")
        yield tag.UL().start()
        for zipInfo in zipInfos:
            itemName = zipInfo.filename
            yield tag.LI(tag.A(h(itemName), href = ZipItem(self, itemName).url()))
        yield tag.UL().end()
        
    @byView("tree", showZipItems)
    def showZipItemsAsTree(self):
        """Show list of links to zip items as a tree."""
        zipInfos = self.getZipInfos()
        yield tag.H3("Items Tree")
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
    
@resourceTypeNameInModule("dir", aptrowModule)
class ZipFileDir(BaseResource):
    """A resource representing a directory within a zip file. Considered to exist if the path
    name ends in '/', and, either (1) a corresponding Zip item exists, or (2) other Zip items exist 
    with the path as a prefix. The root directory is represented by '/', even though for matching
    purposes, it is really ''."""
    
    resourceParams = [ResourceParam("zipfile"), StringParam("path")]
    
    def __init__(self, zipFile, path):
        BaseResource.__init__(self)
        self.zipFile = zipFile
        self.path = path
        self.matchPath = "" if path == "/" else path
        
    def urlParams(self):
        """Parameters required to construct the URL for this resource."""
        return {"zipfile": [self.zipFile.url()], "path": [self.path]}
    
    def isRoot(self):
        return self.path == "/"
    
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
        yield tag.H3("Items")
        yield tag.UL().start()
        for childItem in self.getChildItems():
            yield tag.LI(tag.A(h(childItem.name), href = childItem.url()))
        yield tag.UL().end()
        
    @byView("tree", showZipItems)
    def showZipItemsAsTree(self, view = None):
        yield tag.H3("Items (Tree)")
        yield tag.UL().start()
        zipItemsTree = ZipItemsTree()
        pathLength = len(self.path)
        for childItem in self.getChildItems():
            itemName = childItem.name[pathLength:]
            if itemName != "":
                zipItemsTree.addPath(itemName, childItem)
        yield zipItemsTree.asHtml()
        yield tag.UL().end()
        
    def html(self, view):
        """HTML content for this resource."""
        yield tag.P("Views: ", self.viewLinksHtml(ZipFileDir.viewsAndDescriptions, view))
        yield tag.P("Zip file: ", tag.A(self.zipFile.heading(), href = self.zipFile.url()))
        parentDir = self.parent()
        if parentDir:
            parentPath = parentDir.path
            yield tag.P("Parent: ", tag.A(h(parentPath), href = parentDir.url()))
        for text in self.showZipItems[view.type](self): yield text

import tempfile
        
@resourceTypeNameInModule("item", aptrowModule)
class ZipItem(BaseResource):
    """A resource representing a named item within a zip file. (Note: current implementation
    specifies name only, so if there are multiple items with the same name -- something generally
    to be avoided when creating zip files, but it can happen -- there is currently no way to access 
    them. Some additional information would have to be included in this resource class to handle multiple items.)"""

    resourceParams = [ResourceParam("zipfile"), StringParam("name")]

    resourceInterfaces = [fileLikeResource]

    def __init__(self, zipFile, name):
        BaseResource.__init__(self)
        self.zipFile = zipFile
        self.name = name
        
    def urlParams(self):
        """Parameters required to construct the URL for this resource."""
        return {"zipfile": [self.zipFile.url()], "name": [self.name]}
    
    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "Item %s in %s" % (self.name, self.zipFile.heading())
    
    def getZipInfo(self):
        return self.zipFile.openZipFile().getinfo(self.name)
    
    def extension(self):
        lastDotPos = self.name.rfind(".")
        if lastDotPos == -1:
            return ""
        else:
            return self.name[lastDotPos+1:]
        
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
        zipFile = self.zipFile.openZipFile()
        memoryFile = io.BytesIO()
        zipItem = zipFile.open(self.name, "r")
        zipItemBytes = zipItem.read()
        memoryFile.write(zipItemBytes)
        memoryFile.seek(0)
        zipItem.close()
        zipFile.close()
        return memoryFile
    
    def getFileName(self):
        nameDir, nameFilePart = os.path.split(self.name)
        return nameFilePart
    
    zipInfoAttributes = "filename date_time compress_type comment extra create_system create_version extract_version reserved flag_bits volume internal_attr external_attr header_offset CRC compress_size file_size".split()
    
    def zipInfoHtml(self):
        zipInfo = self.getZipInfo()
        return [tag.H3("Zip Info attributes"), 
                tag.TABLE([tag.TR(tag.TD(attr, ":"), tag.TD(tag.B(hr(getattr(zipInfo, attr)))))
                           for attr in ZipItem.zipInfoAttributes])]
    
    def asZipFileDir(self):
        return ZipFileDir(self.zipFile, self.name)
    
    def html(self, view):
        """HTML content for zip item. Somewhat similar to what is displayed for File resource."""
        yield tag.P(tag.A("Content", href = FileContents(self, "text/plain").url()), 
                    " (", tag.A("html", href = FileContents(self, "text/html").url()), ")")
        if self.name.endswith("/"):
            zipFileDir = self.asZipFileDir()
            yield tag.P(tag.A("(as Zip directory)", href = zipFileDir.url()))
        yield self.zipInfoHtml()

    @attribute(StringParam("contentType", optional = True))
    def contents(self, contentType = None):
        """Return contents of zip item with optional content type"""
        return FileContents(self, contentType)
    
