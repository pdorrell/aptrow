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

@resourceTypeNameInModule("database", aptrowModule)
class SqliteDatabase(Resource):

    """A resource representing a sqlite database"""
    
    resourceParams = [ResourceParam("file")]

    def init(self, fileResource):
        self.fileResource = fileResource

    def heading(self):
        """Default heading to describe this resource (plain text, no HTML)"""
        return "Sqlite database [%s]" % self.fileResource.heading()
    
    def checkExists(self):
        self.fileResource.checkExists()
    
    def connect(self):
        return sqlite3.connect(getFileResourcePath(self.fileResource))
    
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
        yield tag.P("Resource ", tag.B(self.fileResource.htmlLink()), " interpreted as a Sqlite database")
        yield tag.H2("Master Tables")
        yield tag.UL().start()
        for tableName in ['sqlite_master']:
            table = self.table(tableName)
            yield tag.LI(tag.A(h(table.name), href = table.url()))
        yield tag.UL().end()
        yield tag.H2("Tables")
        yield tag.UL().start()
        for tableName in self.listTables():
            table = self.table(tableName)
            yield tag.LI(tag.A(h(table.name), href = table.url()))
        yield tag.UL().end()
        
    @attribute(StringParam("name"))
    def table(self, name):
        return SqliteTable(self, name)

@resourceTypeNameInModule("table", aptrowModule)
class SqliteTable(Resource):
    
    """A resource representing a sqlite table"""
    
    resourceParams = [ResourceParam("database", defaultClass = SqliteDatabase), StringParam("name")]
    
    def init(self, database, name):
        self.database = database
        self.name = name
        
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
        
    def listQueryResults(self, query, args = [], maxCount = None):
        with self.database.connect() as connection:
            cursor = connection.cursor()
            cursor.execute (query, *args)
            yield (True, [desc[0] for desc in cursor.description])
            count = 0
            for row in cursor:
                if maxCount == None or count < maxCount:
                    yield (False, row)
                    count += 1
                else:
                    break
                
    def listQueryResultsInHtmlTable(self, query, args = [], maxCount = None):
        yield tag.TABLE(border = 1).start()
        for isHeader, row in self.listQueryResults(query, maxCount = maxCount):
            yield tag.TR([tag.TD(ht(str(item))) for item in row])
        yield tag.TABLE().end()
    
    def html(self, view):
        """HTML content for this resource. Link back to base file resource, and list
        items within the file."""
        yield tag.P(tag.A("Database", href = self.database.url()))
        yield tag.H2("Table Info")
        for element in self.listQueryResultsInHtmlTable("pragma table_info(\"%s\")" % self.name): yield element
        yield tag.H2("Rows (up to a maximum of 100)")
        for element in self.listQueryResultsInHtmlTable("SELECT * FROM \"%s\"" % self.name, 
                                                        maxCount = 100): yield element
