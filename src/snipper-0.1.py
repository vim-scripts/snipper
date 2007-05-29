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


class Templates(object):
  def __init__(self):
    self.helper = Helper()
    self.hasTemplate = False
    self.templateMode = False
    self.template_folder = os.path.expanduser("~/.vim/templates")   
    self.cursor = "${cursor}"
    self.strPat = r'\${[\w| _.-]*}'
    self.vimPat = r'${[a-zA-Z_.-]*}'
    self.pattern = re.compile(self.strPat)
    self._highlightPattern(self.vimPat)
    self.init()
      
  def init(self):
    self.template_files = self._readFiles()
    #TODO, read filetype, get type and fill templates
    self.file = self.getFile()
    if self.file:
      self.templates = self.readTemplate(self.file)
  
  
  def _highlightPattern(self, pattern):
    com = "match Visual /" + pattern + "/"
    vim.command(com)

  def _readFiles(self):
    """read all the template files"""
    template_files = []
    for file in os.listdir(self.template_folder):
      if file.endswith(".xml"):
        template_files.append(file)
    return template_files

  def readTemplate(self, file):
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

  def _convertTabs(self, templates):
    for template in templates.values():
      template[1] = self.helper.convertTabs(template[1])

  def getFile(self):
    """This file tries to look up the filetype of the current vim file and then
    searches for the template file in template_folder
    """
    #try to redetect the filetype
    vim.command("filetype detect")
    #return the filetype
    filetype = vim.eval("&ft")
    #filetype = vim.command("&ft")
    if filetype:
      for file in self.template_files:
        if filetype.lower() in file.lower():
          self.hasTemplate = True
          return open(self.template_folder + "/" + file, 'r')
    return None

  def trigger(self):
    if self.hasTemplate:
      if self.templateMode:
        try:
          self.insert().next()
        except StopIteration:
          self.templateMode = False
          self.doTemplate()
      else:
        self.doTemplate()
    else:
      self.insertTab() 
  
  def doTemplate(self):
    (row, col) = vim.current.window.cursor
    col = col+1
    line = vim.current.line
    lline = line[0:col]
    #read untill white space
    if col == 1 or lline.strip() == "" or lline[-1].isspace() or lline[-2].isspace():
      self.insertTab()
    else:
      word = lline.split()[-1]
      pos = (col-len(word), len(word))
      self.insertTemplate(word, line, pos)

  def insertTab(self):
    """Insert a tab"""
    tab = self.helper.tab
    tabno = self.helper.tabno
    row, col = vim.current.window.cursor
    line = vim.current.line
    if len(line) == col + 1:
      #if cursor is at the end of the line, don't take the last char
      vim.current.line = line[0:col+1] + tab + line[col+1:]
    else:  
      vim.current.line = line[0:col] + tab + line[col:]
    vim.current.window.cursor = (row, col +tabno)

  def insertTemplate(self, word, line, pos):
    """tries to insert the template, if the template does not exist, insert a
    tab
    @pre  There exists a template file
    """
    try:
      template =  self.templates[word][1]
      before = line[0:pos[0]]
      after = line[pos[0]+pos[1]:]
      template = before + template + after
      template_list = template.split("\n")
      self.template_list = template_list
      #TODO replace with correct tabs
      (row, col) = vim.current.window.cursor
      self.buffer = vim.current.buffer
      new_list = []
      new_list.append(template_list[0])
      for template in template_list[1:]:
        new_list.append(self.helper.addTabs(template, col-len(word)))
      template_list = new_list 
      self.buffer[row-1:row] = template_list
      self.placeholders = self.getAllPlaceholders(template_list)
      #template inserted, now go to template mode with and cycle with tabs
      self.row = row
      self.templateMode = True
      #set autocommand for insert mode
      #vim.command('norm "\<C-\\>\<C-N>"') 
      #vim.command("startinsert")
      #vim.command("autocmd CursorMovedI * python template.trigger()")
    except KeyError:
      self.insertTab()
      
  def insert(self):
    """only do this in template mode"""
    #vim.command("autocmd! CursorMovedI *")
    try:
      placeholder = self.placeholders.pop()
      pos = self.findPlaceholder(placeholder)
    except IndexError:
      #TODO here I could do a findAllPlaceHolders on the complete file, for
      #reducing errors!
      pos = (0,0,0)
    if pos !=(0,0,0):
      line = self.buffer[pos[0]]
      new_line = line[:pos[1]] + "" + line[pos[1]+pos[2]:]
      cursor = (pos[0]+1, pos[1])
      vim.current.window.cursor = cursor
      vim.command("startinsert")
      vim.command("redraw")
      self.buffer[pos[0]] = new_line
      yield
    self.templateMode = False
    return
    
  def getAllPlaceholders(self, template_list):
    """Return all the placeholders"""
    placeholders = []
    for line in template_list:
      found = re.findall(self.pattern, line)
      placeholders.extend(found)
    placeholders.reverse()
    #place the cursor placeholder at the begin
    placeholders = self._placeCursors(placeholders)
    return placeholders

  def _placeCursors(self, placeholders):
    return [x for x in placeholders if x == self.cursor] + [x for x in placeholders if x != self.cursor] 
  
  def findPlaceholder(self, placeholder):
    """searches the position of the first placeholder found"""
    start = self.row
    for lineno in xrange(start-1, len(self.buffer)):
      x = self.buffer[lineno].find(placeholder)
      if x != -1:
        return (lineno, x, len(placeholder))
    #not found after, search to start backwords!
    for lineno in xrange(start-1, 0, -1):
      x = self.buffer[lineno].find(placeholder)
      if x != -1:
        return (lineno, x, len(placeholder))
    return (0,0,0)

class Worker(object):
  def __init__(self):
  	self.template = Templates()

  def reInit(self):
	  self.template.init()
	
  def trigger(self):
    self.template.trigger()

class Helper(object):
  def __init__(self):
    self.readTabs()

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

template = Worker()
