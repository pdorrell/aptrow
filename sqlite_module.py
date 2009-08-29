""" Copyright 2009 Philip Dorrell http://www.1729.com/ (email: http://www.1729.com/email.html)
    
  This file is part of Aptrow ("Advance Programming Technology Read-Only Webification": http://www.1729.com/aptrow/)

  Aptrow is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License 
  as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

  Aptrow is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty 
  of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along with Aptrow (as license-gplv3.txt).
  If not, see <http://www.gnu.org/licenses/>."""

from aptrow import *

import sqlite3

aptrowModule = ResourceModule()

@resourceTypeNameInModule("sqlite", aptrowModule)
class SqliteDatabase(BaseResource):

    """A resource representing a sqlite database"""
    
    resourceParams = [ResourceParam("file")]

    def __init__(self, fileResource):
        BaseResource.__init__(self)
        self.fileResource = fileResource

    def urlParams(self):
        """Parameters required to construct the URL for this resource."""
        return {"file": [self.fileResource.url()]}

    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "Sqlite database [%s]" % self.fileResource.heading()
    
    def checkExists(self):
        self.fileResource.checkExists()
    
    def connect(self):
        return sqlite3.connect(self.fileResource.path)
    
    def listTables(self):
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute ("SELECT name FROM sqlite_master WHERE type = \"table\"")
            for row in cursor:
                yield row[0]
                
    @staticmethod
    @interpretationOf(fileLikeResource)
    def interpretation(fileResource):
        return Interpretation(SqliteDatabase(fileResource), "sqlite", 
                              likely = fileResource.extension() == "sqlite")
    
    def html(self, view):
        """HTML content for this resource. Link back to base file resource, and list
        items within the file."""
        yield "<p>Resource <b>%s</b> interpreted as a Sqlite database</p>" % self.fileResource.htmlLink()
        yield "<h2>Master Tables</h2><ul>"
        for tableName in ['sqlite_master']:
            table = self.table(tableName)
            yield "<li><a href=\"%s\">%s</a></li>" % (table.url(), h(table.name))
        yield "</ul>"
        yield "<h2>Tables</h2><ul>"
        for tableName in self.listTables():
            table = self.table(tableName)
            yield "<li><a href=\"%s\">%s</a></li>" % (table.url(), h(table.name))
        yield "</ul>"
        
    @attribute(StringParam("name"))
    def table(self, name):
        return SqliteTable(self, name)

class SqliteTable(AttributeResource):
    def __init__(self, database, name):
        self.database = database
        self.name = name

    def baseObjectAndParams(self):
        return (self.database, "table", {"name": self.name})
    
    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "Table %s in %s" % (self.name, self.database.heading())
    
    def checkExists(self):
        self.database.checkExists()
        tableExists = False
        if self.name == "sqlite_master":
            return
        with self.database.connect() as connection:
            cursor = connection.cursor()
            cursor.execute ("SELECT name FROM sqlite_master WHERE type = \"table\" and name = ?", (self.name, ))
            for row in cursor:
                tableExists = True
        if not tableExists:
            raise NoSuchObjectException("No table %s in %s" %(self.name, self.database.heading()))
        
    def listQueryResults(self, query, args = []):
        with self.database.connect() as connection:
            cursor = connection.cursor()
            cursor.execute (query, *args)
            yield (True, [desc[0] for desc in cursor.description])
            for row in cursor:
                yield (False, row)
                
    def listQueryResultsInHtmlTable(self, query, args = []):
        yield "<table border=1>"
        for isHeader, row in self.listQueryResults(query):
            yield "<tr>%s</tr>" % "".join(["<td>%s</td>" % h(str(item)) for item in row])
        yield "</table>"
    
    def html(self, view):
        """HTML content for this resource. Link back to base file resource, and list
        items within the file."""
        yield "<p><a href=\"%s\">Database</a></p>" % self.database.url()
        yield "<h2>Table Info</h2>"
        for text in self.listQueryResultsInHtmlTable("pragma table_info(\"%s\")" % self.name): yield text
        yield "<h2>Rows</h2>"
        for text in self.listQueryResultsInHtmlTable("SELECT * FROM \"%s\"" % self.name): yield text
