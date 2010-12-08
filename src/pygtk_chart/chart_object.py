#!/usr/bin/env python
#
#       chart_object.py
#       
#       Copyright 2009 Sven Festersen <sven@sven-festersen.de>
#       
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
"""
This module contains the ChartObject class.

Author: Sven Festersen (sven@sven-festersen.de)
"""
import cairo
import gobject
import gtk

class ChartObject(gobject.GObject):
    """
    This is the base class for all things that can be drawn on a chart
    widget.
    It emits the signal 'appearance-changed' when it needs to be
    redrawn.
    
    Properties
    ==========
    ChartObject inherits properties from gobject.GObject.
    Additional properties:
     - visible (sets whether the object should be visible,
       type: boolean)
     - antialias (sets whether the object should be antialiased,
       type: boolean).
       
    Signals
    =======
    ChartObject inherits signals from gobject.GObject,
    Additional signals:
     - appearance-changed (emitted if the object needs to be redrawn).
    """
    
    __gsignals__ = {"appearance-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])}

    
    __gproperties__ = {"visible": (gobject.TYPE_BOOLEAN,
                                    "visibilty of the object",
                                    "Set whether to draw the object or not.",
                                    True, gobject.PARAM_READWRITE),
                        "antialias": (gobject.TYPE_BOOLEAN,
                                    "use antialiasing",
                                    "Set whether to use antialiasing when drawing the object.",
                                    True, gobject.PARAM_READWRITE)}
                                    
    _surface = None
    _changed = True
    
    def __init__(self):
        gobject.GObject.__init__(self)
        self._show = True
        self._antialias = True
        
    def do_get_property(self, property):
        if property.name == "visible":
            return self._show
        elif property.name == "antialias":
            return self._antialias
        else:
            raise AttributeError, "Property %s does not exist." % property.name

    def do_set_property(self, property, value):
        if property.name == "visible":
            self._show = value
        elif property.name == "antialias":
            self._antialias = value
        else:
            raise AttributeError, "Property %s does not exist." % property.name
        
    def _do_draw(self, context, rect):
        """
        A derived class should override this method. The drawing stuff
        should happen here.
        
        @type context: cairo.Context
        @param context: The context to draw on.
        @type rect: gtk.gdk.Rectangle
        @param rect: A rectangle representing the charts area.
        """
        pass
        
    def draw(self, context, rect, *args):
        """
        This method is called by the parent Chart instance. It
        calls _do_draw.
        
        @type context: cairo.Context
        @param context: The context to draw on.
        @type rect: gtk.gdk.Rectangle
        @param rect: A rectangle representing the charts area.
        """
        res = None
        if self._show:
            if self._surface != None:
                print rect.width, self._surface.get_width()
                print rect.height, self._surface.get_height()
                if rect.width != self._surface.get_width() - 2:
                    self._changed = True
                if rect.height != self._surface.get_height() - 2:
                    self._changed = True
            
            if self._surface == None or self._changed:
                print type(self)
                self._surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                                    rect.width + 2,
                                                    rect.height + 2)
                ctx = cairo.Context(self._surface)
                
                if not self._antialias:
                    ctx.set_antialias(cairo.ANTIALIAS_NONE)
                #res = self._do_draw(ctx, rect, *args)
                nrect = gtk.gdk.Rectangle(0, 0, rect.width, rect.height)
                res = self._do_draw(ctx, nrect, *args)
                ctx.set_antialias(cairo.ANTIALIAS_DEFAULT)
                
                self._changed = False
                
            context.move_to(rect.x, rect.y)
            context.set_source_surface(self._surface, rect.x, rect.y)
            context.rectangle(rect.x - 1, rect.y - 1, rect.width + 2,
                                rect.height + 2)
            context.fill()
        return res
        
    def set_antialias(self, antialias):
        """
        This method sets the antialiasing mode of the ChartObject. Antialiasing
        is enabled by default.
        
        @type antialias: boolean
        @param antialias: If False, antialiasing is disabled for this 
        ChartObject.
        """
        self.set_property("antialias", antialias)
        self.emit("appearance_changed")
        
    def get_antialias(self):
        """
        Returns True if antialiasing is enabled for the object.
        
        @return: boolean.
        """
        return self.get_property("antialias")
        
    def set_visible(self, visible):
        """
        Use this method to set whether the ChartObject should be visible or
        not.
        
        @type visible: boolean
        @param visible: If False, the PlotObject won't be drawn.
        """
        self.set_property("visible", visible)
        self.emit("appearance_changed")
        
    def get_visible(self):
        """
        Returns True if the object is visble.
        
        @return: boolean.
        """
        return self.get_property("visible")
        
    def emit(self, event_name, *args):
        if event_name in ["appearance_changed", "appearance-changed"]:
            self._changed = True
        super(ChartObject, self).emit(event_name, *args)
        

gobject.type_register(ChartObject)
