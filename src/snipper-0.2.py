#! /usr/bin/python
# -*- coding: utf-8 -*-
# Copyright © 2005 Thomas Coopman
#
# This file is part of Snipper.
#
# Snipper is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Snipper is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Snipper; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  
# USA

import cElementTree as ElementTree
import vim
import os
import re
import logging

class Helper(object):
  def __init__(self):
    self.readTabs()
    LOG_FILENAME = os.path.expanduser('~/.vim/snipper/log')
    logging.basicConfig(filename=LOG_FILENAME,
    level=logging.DEBUG)

  def readTabs(self):
    if vim.eval("&expandtab"):
      if vim.eval("&smarttab"):
        tabno = int(vim.eval("&shiftwidth"))
      else:
        tabno = int(vim.eval("&tabstop"))
      tab = "".join([" " for k in xrange(tabno)])
    else:
      tab = "\t"
      tabno = int(vim.eval("&tabstop"))
    self.tab = tab
    self.tabno = tabno

  def convertTabs(self, line):
    return line.replace("\t", self.tab)

  def addTabs(self, line, startpos):
    nb = startpos / self.tabno + 1
    tab = "".join([self.tab for tab in xrange(nb)])
    return tab + line

  def getFiletype(self):
    return vim.eval("&ft")

  def getBuffer(self):
    return vim.current.buffer

  def redraw(self):
    vim.command("redraw")

  def log(self, message):
    logging.debug(message)

  def insertTab(self):
    """Insert a tab"""
    tab = self.tab
    tabno = self.tabno
    row, col = vim.current.window.cursor
    line = vim.current.line
    if len(line) == col + 1:
      #if cursor is at the end of the line, don't take the last char
      vim.current.line = line[0:col+1] + tab + line[col+1:]
    else:  
      vim.current.line = line[0:col] + tab + line[col:]
    vim.current.window.cursor = (row, col +tabno)
    self.redraw()

  def detect(self):
    vim.command("filetype detect")

  def row(self):
    row, col = vim.current.window.cursor
    return row

  def col(self):
    row, col = vim.current.window.cursor
    return col


class IncorrectPlaceholderException(Exception):
  pass

class PlaceholderNotFoundException(Exception):
  pass

class NoTemplateFoundException(Exception):
  """A template is one piece of text to replace with one trigger"""
  pass

class NoSnippetFoundException(Exception):
  """A snippet is the complete file containing all the templates"""
  pass

class NoMorePlaceHoldersException(Exception):
  pass

class NoWordFoundException(Exception):
  pass

class Placeholder(object):
  """This class contains a placeholder
  @invar  Every placeholder has a placeholder that matches with the strPat
  """
  strPat = r'\${[\w| _.-]*}'
  vimPat = r'${[a-zA-Z_.-]*}'
  cursor = "${cursor}"
  pattern = re.compile(strPat)

  def __init__(self, placeholder):
    """Create a new placeholder
    @param  placeholder
    """
    if self._correctPlaceholder(placeholder):
      self.placeholder = placeholder
    else:
      raise IncorrectPlaceholderException

  def _correctPlaceholder(self,placeholder):
    """Test if the placeholder fits the strPat"""
    if re.match(Placeholder.pattern, placeholder):
      return True
    else:
      return False

  def value(self):
    """Returns the value of the placeholder"""
    return self.placeholder.strip("$").strip("{").strip("}")

  def __cmp__(self, other):
    """Compares placeholders with each other, the cursor must the last in the
    list, else the position may not change
    """
    if self.placeholder == Placeholder.cursor:
      return 1
    elif other.placeholder == Placeholder.cursor:
      return -1
    else:
      return 0

  def __len__(self):
    return len(self.placeholder)

  def __str__(self):
    return self.placeholder

  def __repr__(self):
    return str(self)

class Snipper(object):
  """This class is the main class,
  when buffers are switched it makes sure the correct Buffer is called
  """
  template_folder = os.path.expanduser("~/.vim/snipper/templates")   

  def __init__(self):
    self.helper = Helper()
    self.template_files = self._readFiles()
    self.buffers = {} 

  def registerBuffer(self):
    """Registers a new buffer depending on the filetype
    """
    self.helper.detect()
    self.helper.log("register Buffer")
    filetype = self.helper.getFiletype() 
    if filetype:
      try:
        buffer = self._getBuffer(filetype)
        self.buffers[filetype] = buffer
        self.helper.log("buffer got registered for "+ filetype)
      except NoTemplateFoundException:
        self.helper.log("No template found for " + filetype)
        self.buffers[filetype] = None 

  def trigger(self):
    try:
      self.helper.log("main trigger activated")
      buffer = self._getCurrentBuffer()
      buffer.trigger()
    except NoTemplateFoundException:
      self.helper.log("main trigger insert tab")
      self.helper.insertTab()

  def _getCurrentBuffer(self):
    try:
      buffer = self.buffers[self.helper.getFiletype()]
      if buffer == None:
        raise NoTemplateFoundException()
      else:
        return buffer
    except KeyError:
      # There is no buffer at hand for the current filetype, try redetecting the type 
      self.registerBuffer()
      try:
        self.buffers[self.helper.getFiletype()]
        if buffer == None:
          raise NoTemplateFoundException()
      except:
        raise NoTemplateFoundException()

  def expand(self):
    """Just tries to expand the current template, if this fails, nothing is
    done. 
    """
    try:
      buffer = self._getCurrentBuffer()
      buffer.expand()
    except:
      pass

  def jump(self):
    """Just tries to jump to the next placeholder,  if this fails, nothing is
    done. 
    """
    try:
      buffer = self._getCurrentBuffer()
      buffer.jump()
    except:
      pass
  
    
  def _getBuffer(self, filetype):
    """This file tries to search if there is a template file associated to
    filetype, if so, create a new buffer and return that buffer, else,
    raise an exception
    @raises NoTemplateFoundException
    """
    for file in self.template_files:
      if filetype.lower() in file.lower():
        bfile =  open(self.template_folder + "/" + file, 'r')
        return Buffer(bfile) 

    raise NoTemplateFoundException

  def _readFiles(self):
    """reads all the template files"""
    template_files = []
    for file in os.listdir(Snipper.template_folder):
      if file.endswith(".xml"):
        template_files.append(file)
    return template_files

class Buffer(object):
  """This class contains the templates of a buffer"""
  def __init__(self, file):
    """Creates a new Buffer
    @param file: the file where all the snippets are
    """
    self.helper = Helper()
    self.file = file
    self.templates = self._readTemplate(file)
    self.helper = Helper()
    self.active = None
    self.previousPos = 0
    self.previousPos = ""

  def _readTemplate(self, file):
    """This reads the template in and returns a dict with the trigger as key and
    the template as value"""
    templates = {}
    doc = ElementTree.parse(file)
    entries = doc.findall("entry")
    for entry in entries:
      templates[entry.find("trigger").text] = [entry.find("description").text,
      entry.find("template").text]
    self._convertTabs(templates)
    return templates

  def _highlightPattern(self, pattern):
    com = "match Visual /" + pattern + "/"
    vim.command(com)

  def _convertTabs(self, templates):
    for template in templates.values():
      template[1] = template[1].replace("\t", self.helper.tab)

  def trigger(self):
    #TODO ugly!
    #here small bug
    #if you move and try to insert a new template, the previous must close and
    #the new one must get expanded
    #this is wrong with the if self.active.pos == ...
    try:
      (word, line, pos, linenb) = self._readTemplateTrigger()
    except NoWordFoundException:
      if self.hasActive():
        self.active.jump()
    else:
      try:
        if self.hasActive():
          #if there is a template word out of the range of the active
          #close the current active and open a new active
          if self._isTrigger(word):
            if not self.active.inRange(linenb):
              self._expand(word,line,pos)
            else:
              self.active.jump()
          else:
            self.active.jump()
        else:
          self._expand(word, line, pos)
      except NoTemplateFoundException:
        self.helper.insertTab()
      except NoMorePlaceHoldersException:
        self.helper.insertTab()
        self._closeActive()

  def hasActive(self):
    if self.active == None:
      return False
    else:
      if self.active.isActive():
        return True
      else:
        return False

  def expand(self):
    """Tries to expand a new template, if this succeeds, the active template,
    if any, is closed
    This method is needed for if you want a standalone expand button
    """
    (word, line, pos, linenb) = self._readTemplateTrigger()
    self._expand(word, line, pos)

  def jump(self):
    """Tries to jump,
    this method is needed if you want a standalone expand button
    """
    self.active.jump()

  def _expand(self, word, line, pos):
    self.helper.log("start expanding")
    self._closeActive()
    self.active = self._expandTemplate(word, line, pos)
    self.helper.log("stop expanding")
      
  def _readTemplateTrigger(self):
    (row, col) = vim.current.window.cursor
    col = col+1
    line = vim.current.line
    lline = line[0:col]
    #read untill white space
    if col == 1 or lline.strip() == "" or lline[-1].isspace() or lline[-2].isspace():
      self.helper.log("_readTemplateTrigger found empty line")
      raise NoWordFoundException()
    else:
      word = lline.split()[-1]
      pos = (col-len(word), len(word))
      return (word, line, pos, row)

    
  def _isTrigger(self, word):
    try:
      self.templates[word]
      return True
    except KeyError:
      return False

  def _expandTemplate(self, word, line, pos):
    """tries to insert the template, if the template does not exist, insert a
    tab
    @pre  There exists a template file
    """
    try:
      template =  self.templates[word][1]
      return Template(template, word, line, pos)
    except KeyError:
      raise NoTemplateFoundException()

  def _closeActive(self):
    """Closes the active template"""
    try:
      self.active.close()
      self.active = None
    except:
      # If there is no active then nothing needs to be closed
      pass

    
class Template(object):
  """This is the class that contains one template"""
  def __init__(self, template, word, line, pos):
    self.helper = Helper()
    self.line = line
    self.row = self.helper.row()
    self.buffer = self.helper.getBuffer()
    self.pos = pos
    self.template = template
    self.word = word
    self.template_list = self._formatTemplate(line, pos, word)
    self.placeholders = self._getAllPlaceholders(self.template_list)
    self._expand(self.template_list)

  def isActive(self):
    if len(self.placeholders) > 0:
      return True
    else:
      return False

  def equals(self, word, line, pos):
    self.helper.log("check if equals to")
    posLog = "pos self " + str(self.pos) + " == " + str(pos)
    lineLog = "line self " + self.line + " == " + str(line)
    wordLog = "word self " + self.word + " == " + str(word)
    self.helper.log(posLog)
    self.helper.log(lineLog)
    self.helper.log(wordLog)

    if self.isActive() and self.pos == pos and self.word == word:
      self.helper.log("active is equal")
      return True
    else:
      self.helper.log("active is not equal")
      return False

  def jump(self):
    """Jumps to the next placeholder"""
    while self.isActive():
      try:
        placeholder = self.placeholders.pop()
        pos = self._findPlaceholder(placeholder) 
      except PlaceholderNotFoundException:
        continue
      else:
        line = self.buffer[pos[0]]
        new_line = self._insertText(line, pos, "") 
        cursor = (pos[0]+1, pos[1])
        vim.current.window.cursor = cursor
        vim.command("startinsert")
        self.helper.redraw()
        self.buffer[pos[0]] = new_line
        return
    else:
      raise NoMorePlaceHoldersException()

  def _insertText(self, line, pos, text):
    nl = line[:pos[1]] + text + line[pos[1]+pos[2]:]
    return nl  

  def _placeCursors(self, placeholders):
    return [x for x in placeholders if x == self.cursor] + [x for x in placeholders if x != self.cursor] 
  
  def _findPlaceholder(self, placeholder):
    """searches the position of the first placeholder found"""
    start = self.row
    for lineno in xrange(start-1, len(self.buffer)):
      x = self.buffer[lineno].find(str(placeholder))
      if x != -1:
        return (lineno, x, len(placeholder))
    #not found after, search to start backwords!
    for lineno in xrange(start-1, 0, -1):
      x = self.buffer[lineno].find(str(placeholder))
      if x != -1:
        return (lineno, x, len(placeholder))
    raise PlaceholderNotFoundException()


  def _expand(self, template_list):
    #TODO the row shouldn't be here?
    (row, col) = vim.current.window.cursor
    buffer = self.helper.getBuffer()
    buffer[row-1:row] = template_list

  def inRange(self,linenb):
    """Checks if pos is in the range of this template
    """
    myRange = self._getRange()
    if myRange == (-1, -1):
      return False
    if linenb > myRange[0] and linenb <= myRange[1]:
      return True
    else:
      return False

  def _getRange(self):
    """Gets the range of the current placeholders, if this is to slow,
    don't use it"""
    minPos = -1
    maxPos = -1
    for placeholder in self.placeholders:
      try:
        pos = self._findPlaceholder(placeholder)
        if pos[0] > maxPos:
          maxPos = pos[0]
        if minPos == -1 or pos[0] < minPos:
          minPos = pos[0]
      except PlaceholderNotFoundException:
        continue
    return (minPos, maxPos)


    
  def _formatTemplate(self, line, pos, word):
    (row, col) = vim.current.window.cursor
    template = self.template
    before = line[0:pos[0]]
    after = line[pos[0]+pos[1]:]
    template = before + template + after
    template_list = template.split("\n")
    new_list = []
    new_list.append(template_list[0])
    for template in template_list[1:]:
      new_list.append(self.helper.addTabs(template, col-len(word)))
    return new_list 
    #template inserted, now go to template mode with and cycle with tabs
    #set autocommand for insert mode
    #vim.command('norm "\<C-\\>\<C-N>"') 
    #vim.command("startinsert")
    #vim.command("autocmd CursorMovedI * python template.trigger()")

  def _getAllPlaceholders(self, template_list):
    """Return all the placeholders"""
    tmp = []
    placeholders = []
    for line in template_list:
      found = re.findall(Placeholder.pattern, line)
      tmp.extend(found)
    for placeholder in tmp:
      placeholders.append(Placeholder(placeholder))
    placeholders.sort()
    placeholders.reverse()
    return placeholders

  def close(self):
    """Closes the current template
    @post  self.isActive() == False
    """
    for placeholder in self.placeholders:
      try:
        pos = self._findPlaceholder(placeholder)
        line = self.buffer[pos[0]]
        new_line = self._insertText(line, pos, placeholder.value()) 
        self.buffer[pos[0]] = new_line
      except PlaceholderNotFoundException:
        continue
    self.helper.redraw()

snipper = Snipper()
