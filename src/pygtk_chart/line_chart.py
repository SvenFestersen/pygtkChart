#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       unbenannt.py
#       
#       Copyright 2009 Sven Festersen <sven@sven-laptop>
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
Contains the LineChart widget.

Author: Sven Festersen (sven@sven-festersen.de)
"""
__docformat__ = "epytext"
import cairo
import gtk
import gobject
import os
import math

import pygtk_chart
from pygtk_chart.basics import *
from pygtk_chart.chart_object import ChartObject
from pygtk_chart import chart
from pygtk_chart import label

from pygtk_chart import COLORS, COLOR_AUTO

try:
    import numpy
except:
    pass


RANGE_AUTO = "range_auto"
KEY_POSITION_TOP_RIGHT = 0
KEY_POSITION_TOP_LEFT = 1
KEY_POSITION_BOTTOM_LEFT = 2
KEY_POSITION_BOTTOM_RIGHT = 3

def safe_concatenation(a, b):
    """
    Concatenates lists or numpy arrays.
    """
    if type(a) == list and type(b) == list:
        return a + b
    elif type(a) == list and type(b) == numpy.ndarray:
        return numpy.concatenate((numpy.array(a), b))
    elif type(a) == numpy.ndarray and type(b) == list:
        return numpy.concatenate((a, numpy.array(b)))
    elif type(a) == numpy.ndarray and type(b) == numpy.ndarray:
        return numpy.concatenate((a, b))
    
def graph_make_ranges(data):
    """
    Calculates the xrange and the yrange from data.
    """
    xdata, ydata = data
    if data == []:
        return None, None
    xrange = [min(xdata), max(xdata)]
    yrange = [min(ydata), max(ydata)]
        
    if xrange[0] == xrange[1]:
        #if there is only one point, extend the xrange
        xrange[0] = xrange[0] - 0.1
        xrange[1] = xrange[1] + 0.1
        
    if yrange[0] == yrange[1]:
        #if there is only one point, extend the yrange
        yrange[0] = yrange[0] - 0.1
        yrange[1] = yrange[1] + 0.1
        
    return tuple(xrange), tuple(yrange)

def graph_draw_point(context, x, y, radius, style):
    a = radius / 1.414 #1.414=sqrt(2)
    if style == pygtk_chart.POINT_STYLE_CIRCLE:
        context.arc(x, y, radius, 0, 2 * math.pi)
        context.fill()
    elif style == pygtk_chart.POINT_STYLE_SQUARE:
        context.rectangle(x - a, y- a, 2 * a, 2 * a)
        context.fill()
    elif style == pygtk_chart.POINT_STYLE_CROSS:
        context.move_to(x, y - a)
        context.rel_line_to(0, 2 * a)
        context.stroke()
        context.move_to(x - a, y)
        context.rel_line_to(2 * a, 0)
        context.stroke()
    elif style == pygtk_chart.POINT_STYLE_TRIANGLE_UP:
        a = 1.732 * radius #1.732=sqrt(3)
        b = a / (2 * 1.732)
        context.move_to(x - a / 2, y + b)
        context.rel_line_to(a, 0)
        context.rel_line_to(-a / 2, -(radius + b))
        context.rel_line_to(-a / 2, radius + b)
        context.close_path()
        context.fill()
    elif style == pygtk_chart.POINT_STYLE_TRIANGLE_DOWN:
        a = 1.732 * radius #1.732=sqrt(3)
        b = a / (2 * 1.732)
        context.move_to(x - a / 2, y - b)
        context.rel_line_to(a, 0)
        context.rel_line_to(-a / 2, radius + b)
        context.rel_line_to(-a / 2, -(radius + b))
        context.close_path()
        context.fill()
    elif style == pygtk_chart.POINT_STYLE_DIAMOND:
        context.move_to(x, y - a)
        context.rel_line_to(a, a)
        context.rel_line_to(-a, a)
        context.rel_line_to(-a, -a)
        context.rel_line_to(a, -a)
        context.fill()
        
def graph_draw_point_pixbuf(context, x, y, pixbuf):
    w = pixbuf.get_width()
    h = pixbuf.get_height()
    ax = x - w / 2
    ay = y - h / 2
    context.set_source_pixbuf(pixbuf, ax, ay)
    context.rectangle(ax, ay, w, h)
    context.fill()
    
def graph_draw_points(graph, context, rect, data, xrange, yrange, ppu_x, ppu_y, point_style, color, point_size, highlighted):
    context.set_source_rgb(*color_gdk_to_cairo(color))
    if point_style != pygtk_chart.POINT_STYLE_NONE:
        xdata, ydata = data
        for i in range(0, len(xdata)):
            x, y = xdata[i], ydata[i]
            if not xrange[0] <= x <= xrange[1]: continue
            posx = rect.x + ppu_x * (x - xrange[0])
            posy = rect.y + rect.height - ppu_y * (y - yrange[0])
            
            if type(point_style) != gtk.gdk.Pixbuf:
                chart.add_sensitive_area(chart.AREA_CIRCLE, (posx, posy, point_size), (graph, (x, y)))
                graph_draw_point(context, posx, posy, point_size, point_style)
                if (x, y) in highlighted:
                    context.set_source_rgba(1, 1, 1, 0.3)
                    graph_draw_point(context, posx, posy, point_size, point_style)
                    context.set_source_rgb(*color_gdk_to_cairo(color))
            else:
                graph_draw_point_pixbuf(context, posx, posy, point_style)
                
def graph_draw_lines(context, rect, data, xrange, yrange, ppu_x, ppu_y, line_style, line_width, color, logscale):
    context.set_source_rgb(*color_gdk_to_cairo(color))
    context.set_line_width(line_width)
    if line_style != pygtk_chart.LINE_STYLE_NONE:
        set_context_line_style(context, line_style)
        xdata, ydata = data
        first_point = True
        for i in range(0, len(xdata)):
            x = xdata[i]
            y = ydata[i]
            if logscale[0]: x = math.log10(x)
            if logscale[1]: y = math.log10(y)
            if not xrange[0] <= x <= xrange[1]: continue
            posx = rect.x + ppu_x * (x - xrange[0])
            posy = rect.y + rect.height - ppu_y * (y - yrange[0])
            
            if first_point:
                context.move_to(posx, posy)
                first_point = False
            else:
                context.line_to(posx, posy)
        context.stroke()
    context.set_line_width(1)
        
def graph_new_constant(xmin, xmax, value):
    g = Graph("", [xmin, xmax], [value, value])
    return g
        
def graph_draw_fill_to(context, rect, data, xrange, yrange, ppu_x, ppu_y, fill_to, color, opacity):
    fill_graph = None
    xmin, xmax = xrange
    if type(fill_to) == Graph:
        fill_graph = fill_to
        xmin = max(xrange[0], min(data[0]))
        xmax = min(xrange[1], max(data[0]))
    elif type(fill_to) in [int, float]:
        xmin = max(xrange[0], min(data[0]))
        xmax = min(xrange[1], max(data[0]))
        fill_graph = graph_new_constant(xmin, xmax, fill_to)
        
    if fill_graph != None:
        c = color_gdk_to_cairo(color)
        context.set_source_rgba(c[0], c[1], c[2], opacity)
        other_data = fill_graph.get_points()[:]
        xmin = max(xmin, min(other_data[0]))
        xmax = min(xmax, max(other_data[0]))
        other_data[0].reverse()
        other_data[1].reverse()
        first_point = True
        
        xdata, ydata = data
        for i in range(0, len(xdata)):
            x, y = xdata[i], ydata[i]
            if not xmin <= x <= xmax: continue
            posx = rect.x + ppu_x * (x - xrange[0])
            posy = rect.y + rect.height - ppu_y * (y - yrange[0])
            
            if first_point:
                context.move_to(posx, posy)
                first_point = False
            else:
                context.line_to(posx, posy)
        for i in range(0, len(other_data[0])):
            x, y = other_data[0][i], other_data[1][i]
            if not xmin <= x <= xmax: continue
            posx = rect.x + ppu_x * (x - xrange[0])
            posy = rect.y + rect.height - ppu_y * (y - yrange[0])
            context.line_to(posx, posy)
        context.fill()
            
    
    

class Graph(ChartObject):
    
    __gproperties__ = {"xrange": (gobject.TYPE_PYOBJECT,
                                    "the xrange",
                                    "The xrange of the graph.",
                                    gobject.PARAM_READABLE),
                        "yrange": (gobject.TYPE_PYOBJECT,
                                    "the yrange",
                                    "The yrange of the graph.",
                                    gobject.PARAM_READABLE),
                        "line-style": (gobject.TYPE_INT,
                                        "line style",
                                        "The line style for the graph.",
                                        -1, 3, 0, gobject.PARAM_READWRITE),
                        "line-width": (gobject.TYPE_INT,
                                        "line width",
                                        "The line width for the graph.",
                                        1, 15, 1, gobject.PARAM_READWRITE),
                        "point-style": (gobject.TYPE_PYOBJECT,
                                        "point style",
                                        "The point style for the graph.",
                                        gobject.PARAM_READWRITE),
                        "point-size": (gobject.TYPE_INT,
                                        "point size",
                                        "The point size for the graph.",
                                        1, 50, 2, gobject.PARAM_READWRITE),
                        "color": (gobject.TYPE_PYOBJECT,
                                        "color",
                                        "Graph color.",
                                        gobject.PARAM_READWRITE),
                        "fill-to": (gobject.TYPE_PYOBJECT,
                                    "fill the sapce under the graph",
                                    "Fill the space under the graph or between two graphs.",
                                    gobject.PARAM_READWRITE),
                        "fill-opacity": (gobject.TYPE_FLOAT,
                                        "opacity of the filled area",
                                        "The opacity of filled areas.",
                                        0.0, 1.0, 0.3,
                                        gobject.PARAM_READWRITE),
                        "highlighted": (gobject.TYPE_PYOBJECT,
                                        "list of points to highlight",
                                        "List of points to highlight.",
                                        gobject.PARAM_READWRITE)}
    
    _xrange = None
    _yrange = None
    _line_style = pygtk_chart.LINE_STYLE_SOLID
    _line_width = 1
    _point_style = pygtk_chart.POINT_STYLE_CIRCLE
    _point_size = 2
    _color = COLOR_AUTO
    _fill_to = None
    _fill_opacity = 0.3
    _highlighted = []
    
    def __init__(self, name, xdata, ydata):
        super(Graph, self).__init__()
        self._name = name
        self._data = (xdata, ydata)
        
        self._process_data()
        
    def __len__(self):
        return len(self._data)
        
    def __getitem__(self, item):
        xdata, ydata = self._data
        if isinstance(item, slice):
            nxdata = xdata[item.start:item.stop:item.step]
            nydata = ydata[item.start:item.stop:item.step]
            name = "%s-%s:%s:%s" % (self._name, item.start, item.stop,
                                    item.step)
            g = Graph(name, nxdata, nydata)
            return g
        else:
            return xdata[item], ydata[item]
            
    def __add__(self, other):
        """
        Concatenate the data of two graph objects.
        """
        xdata, ydata = self._data
        oxdata, oydata = other.get_points()
        xdata = safe_concatenation(xdata, oxdata)
        ydata = safe_concatenation(ydata, oydata)
        return Graph("%s+%s" % (self._name, other.get_name()), xdata, ydata)
            
    def __radd__(self, other):
        """
        Concatenate the data of two graph objects.
        Swapped operands.
        """
        xdata, ydata = self._data
        oxdata, oydata = other.get_points()
        xdata = safe_concatenation(oxdata, xdata)
        ydata = safe_concatenation(oydata, ydata)
        return Graph("%s+%s" % (other.get_name(), self._name), xdata, ydata)
            
    def __iadd__(self, other):
        """
        Replace the graphs data with a concatenation of its data and the data
        of other.
        """
        xdata, ydata = self._data
        oxdata, oydata = other.get_points()
        xdata = safe_concatenation(xdata, oxdata)
        ydata = safe_concatenation(ydata, oydata)
        self._data = xdata, ydata
        return self
        
    def __mul__(self, n):
        """
        Repetition of the graphs data. Creates a periodic extension of the
        graph in positive x direction.
        """
        nxdata = []
        nydata = []
        xdata, ydata = self._data
        delta = abs(xdata[1] - xdata[0])
        for i in range(0, n):
            nxdata = safe_concatenation(nxdata,
                                        map(lambda x: x + i * delta, xdata))
            nydata = safe_concatenation(nydata, ydata)
        return Graph("%s*%s" % (n, self._name), nxdata, nydata)
        
    def do_get_property(self, property):
        if property.name == "xrange":
            return self._xrange
        elif property.name == "yrange":
            return self._yrange
        elif property.name == "line-style":
            return self._line_style
        elif property.name == "line-width":
            return self._line_width
        elif property.name == "point-style":
            return self._point_style
        elif property.name == "point-size":
            return self._point_size
        elif property.name == "color":
            return self._color
        elif property.name == "fill-to":
            return self._fill_to
        elif property.name == "fill-opacity":
            return self._fill_opacity
        elif property.name == "highlighted":
            return self._highlighted
        else:
            return super(Graph, self).do_get_property(property)
        
    def do_set_property(self, property, value):
        if property.name == "line-style":
            self._line_style = value
        elif property.name == "line-width":
            self._line_width = value
        elif property.name == "point-style":
            self._point_style = value
        elif property.name == "point-size":
            self._point_size = value
        elif property.name == "color":
            self._color = value
        elif property.name == "fill-to":
            if type(value) in [float, int, Graph]:
                self._fill_to = value
        elif property.name == "fill-opacity":
            self._fill_opacity = value
        elif property.name == "highlighted":
            self._highlighted = value
        else:
            super(Graph, self).do_set_property(property, value)
        
    def _process_data(self):
        """
        Sorts data points and calculates ranges.
        """
        self._xrange, self._yrange = graph_make_ranges(self._data)
        
    def _do_draw(self, context, rect, xrange, yrange, color, logscale):
        #ppu: pixel per unit
        ppu_x = float(rect.width) / abs(xrange[0] - xrange[1])
        ppu_y = float(rect.height) / abs(yrange[0] - yrange[1])
        
        graph_draw_fill_to(context, rect, self._data, xrange, yrange, ppu_x, ppu_y, self._fill_to, color, self._fill_opacity)
        graph_draw_lines(context, rect, self._data, xrange, yrange, ppu_x, ppu_y, self._line_style, self._line_width, color, logscale)                
        graph_draw_points(self, context, rect, self._data, xrange, yrange, ppu_x, ppu_y, self._point_style, color, self._point_size, self._highlighted)    
        
    def get_points(self):
        return self._data
        
    def get_name(self):
        return self._name
        
    def add_point(self, point):
        """
        Add a single data point [(x, y) pair] to the graph.
        """
        x, y = point
        self._data[0].append(x)
        self._data[1].append(y)
        self._process_data()
        self.emit("appearance_changed")
        
    def add_points(self, points):
        """
        Add a list of data points [(x, y) pairs] to the graph.
        """
        self._data[0] += points[0]
        self._data[1] += points[1]
        self._process_data()
        self.emit("appearance_changed")
        
    def set_points(self, points):
        """
        Replace the data points of the graph with a new list of points
        [(x, y) pairs].
        """
        self._data = points
        self._process_data()
        self.emit("appearance_changed")
        
    def get_ranges(self):
        """
        Returns the xrange and the yrange of the graph.
        """
        return self.get_xrange(), self.get_yrange()
        
    def get_xrange(self):
        """
        Returns the xrange of this graph. The xrange is a pair
        holding the minimum and the maximum x values (xmin, xmax).
        
        @return: pair of float
        """
        return self.get_property("xrange")
        
    def get_yrange(self):
        """
        Returns the yrange of this graph. The yrange is a pair
        holding the minimum and the maximum y values (ymin, ymax).
        
        @return: pair of float
        """
        return self.get_property("yrange")
        
    def get_line_style(self):
        """
        Returns the line style for this graph.
        
        (getter method for property 'line-style', see setter method for
        details)
        
        @return: a line style constant
        """
        return self.get_property("line-style")
        
    def set_line_style(self, style):
        """
        Set the line style of the graph. style has to be one of these
        line style constants:
         - pygtk_chart.LINE_STYLE_NONE = -1
         - pygtk_chart.LINE_STYLE_SOLID = 0
         - pygtk_chart.LINE_STYLE_DOTTED = 1
         - pygtk_chart.LINE_STYLE_DASHED = 2
         - pygtk_chart.LINE_STYLE_DASHED_ASYMMETRIC = 3
         
        This is the setter method for the property 'line-style'.
        Property type: gobject.TYPE_INT
        Property minimum value: -1
        Property maximum value: 3
        Property default value: 0 (pygtk_chart.LINE_STYLE_SOLID)
        
        @type style: a line style constant (see above)
        """
        self.set_property("line-style", style)
        self.emit("appearance_changed")
    
    def get_line_width(self):
        """
        Returns the line width for this graph.
        
        @return: int
        """
        return self.get_property("line-width")
        
    def set_line_width(self, width):
        """
        Set the line width for this graph.
        
        @param width: new line width
        @type width: int
        """
        self.set_property("line-width", width)
        self.emit("appearance_changed")
        
    def get_point_style(self):
        """
        Returns the point style for this graph.
        
        (getter method for property 'point-style', see setter method for
        details)
        
        @return: a point style constant, or a gtk.gdk.Pixbuf
        """
        return self.get_property("point-style")
        
    def set_point_style(self, style):
        """
        Set the point style of the graph. style either has to be one of
        these point style constants:
         - pygtk_chart.POINT_STYLE_NONE = -1
         - pygtk_chart.POINT_STYLE_CIRCLE = 0
         - pygtk_chart.POINT_STYLE_SQUARE = 1
         - pygtk_chart.POINT_STYLE_CROSS = 2
         - pygtk_chart.POINT_STYLE_TRIANGLE_UP = 3
         - pygtk_chart.POINT_STYLE_TRIANGLE_DOWN = 4
         - pygtk_chart.POINT_STYLE_DIAMOND = 5
        or a gtk.gdk.Pixbuf. If style is a pixbuf, the pixbuf will be
        drawn instead of points.
         
        This is the setter method for the property 'point-style'.
        Property type: gobject.TYPE_PYOBJECT
        Property default value: 0 (pygtk_chart.POINT_STYLE_CIRCLE)
        
        @type style: a point style constant or gtk.gdk.Pixbuf
        """
        self.set_property("point-style", style)
        
    def get_point_size(self):
        """
        Returns the point size in pixels.
        
        (getter method for property 'point-size', see setter method for
        details)
        
        @return: int
        """
        return self.get_property("point-size")
        
    def set_point_size(self, size):
        """
        Sets the radius of the datapoints in pixels. If the point style
        is a gtk.gdk.Pixbuf, the point size does not have any effect.
        
        This is the setter method for the property 'point-size'.
        Property type: gobject.TYPE_INT
        Property minimum value: 1
        Property maximum value: 50
        Property default value: 2
        
        @param size: point size in px
        @type size: int
        """
        self.set_property("point-size", size)
        
    def get_color(self):
        """
        Returns the manually set color of the graph or
        pygtk_chart.COLOR_AUTO.
        
        (getter method for property 'color', see setter method for
        details)
        
        @return: gtk.gdk.COLOR or pygtk_chart.COLOR_AUTO
        """
        return self.get_property("color")
        
    def set_color(self, color):
        """
        Set the color of the graph. color has to be a gtk.gdk.Color
        or pygtk_chart.COLOR_AUTO.
        
        This is the setter method for the property 'color'.
        Property type: gobject.TYPE_PYOBJECT
        Property default value: pygtk_chart.COLOR_AUTO
        
        @param color: the color of the graph
        @type color: gtk.gdk.Color or pygtk_chart.COLOR_AUTO
        """
        self.set_property("color", color)
        
    def get_fill_to(self):
        """
        If the area under the graph or bewteen is filled, this returns
        the value or the graph to which the area is filled.
        Otherwise None is returned.
        
        (getter method for property 'fill-to', see setter method for
        details)
        
        @return: int, float, line_chart.Graph or None
        """
        return self.get_property("fill-to")
        
    def set_fill_to(self, fill):
        """
        Sets whether and how the area under the graph should be filled.
        If fill is int or float, the area between this value and the
        graph is filled. If fill is a line_chart.Graph, the area
        between the two graphs if filled.
        The area will be filled with the color of the graph and the
        opacity set by 'fill-opacity'.
        Set fill to None if you do not want anything filled.
        
        This is the setter method for the property 'fill-to'.
        Property type: gobject.TYPE_PYOBJECT
        Property default value: None
        
        @type fill: int, float, line_chart.Graph or None
        """
        self.set_property("fill-to", fill)
        
    def get_fill_opacity(self):
        """
        Returns the opacity of filled areas under the graph.
        
        (getter method for property 'fill-opacity', see setter method
        for details)
        
        @return: float
        """
        return self.get_property("fill-opacity")
        
    def set_fill_opacity(self, opacity):
        """
        Set the opacity of filled areas under the graph.
        
        This is the setter method for the property 'fill-opacity'.
        Property type: gobject.TYPE_FLOAT
        Property minimum value: 0.0
        Property maximum value: 1.0
        Property default value: 0.3
        
        @type opacity: float
        """
        self.set_property("fill-opacity", opacity)
        
    def get_highlighted(self):
        """
        Returns a list of highlighted datapoints.
        
        (getter method for property 'highlighted', see setter method
        for details)
        
        @return: list of datapoints
        """
        return self.get_property("highlighted")
        
    def set_highlighted(self, points):
        """
        Set the list points to be highlighted.
        
        This is the setter method for the property 'highlighted'.
        Property type: gobject.TYPE_PYOBJECT
        Property default value: []
        
        @type points: a list of points
        """
        self.set_property("highlighted", points)
        
    def add_highlighted(self, point):
        """
        Add a point to the highlighted list.
        """
        self._highlighted.append(point)
        
        

def chart_calculate_ranges(xrange, yrange, graphs, extend_x=(0, 0), extend_y=(0, 0), logscale=(False, False)):
    if xrange != RANGE_AUTO:
        #the xrange was set manually => no calculation neccessary
        calc_xrange = xrange
    else:
        #calculate the xrange from graphs. (0, 1) if there is no graph
        calc_xrange = None
        for graph in graphs:
            if not graph.get_visible() or len(graph) == 0: continue
            g_xrange, g_yrange = graph.get_ranges()
            if calc_xrange == None:
                calc_xrange = g_xrange
            else:
                calc_xrange = min(calc_xrange[0], g_xrange[0]), max(calc_xrange[1], g_xrange[1])
        if calc_xrange == None:
            calc_xrange = (0, 1)
        else:
            delta = abs(calc_xrange[1] - calc_xrange[0])
            calc_xrange = (calc_xrange[0] - delta * extend_x[0],
                            calc_xrange[1] + delta * extend_x[1])
            
    if yrange != RANGE_AUTO:
        #the yrange was set manually => no calculation neccessary
        calc_yrange = yrange
    else:
        #calculate the yrange from graphs. (0, 1) if there is no graph
        calc_yrange = None
        for graph in graphs:
            if not graph.get_visible() or len(graph) == 0: continue
            g_xrange, g_yrange = graph.get_ranges()
            if calc_yrange == None:
                calc_yrange = g_yrange
            else:
                calc_yrange = min(calc_yrange[0], g_yrange[0]), max(calc_yrange[1], g_yrange[1])
                
        if calc_yrange == None:
            calc_yrange = (0, 1)
        else:
            delta = abs(calc_yrange[1] - calc_yrange[0])
            calc_yrange = (calc_yrange[0] - delta * extend_y[0],
                            calc_yrange[1] + delta * extend_y[1])
                            
    if logscale[0]:
        if calc_xrange[0] <= 0: calc_xrange = (0.001, calc_xrange[1])
        calc_xrange = map(math.log10, calc_xrange)
    if logscale[1]:
        if calc_yrange[0] <= 0: calc_yrange = (0.001, calc_yrange[1])
        calc_yrange = map(math.log10, calc_yrange)
        
    return calc_xrange, calc_yrange
    
    
def chart_calculate_tics_for_range(crange, logscale):
    """
    This function calculates the tics that should be drawn for a given
    range.
    """
    tics = []
    if not logscale:
        delta = abs(crange[0] - crange[1])
        exp = int(math.log10(delta))
        
        ten_exp = math.pow(10, exp) #store this value for performance reasons
        
        if delta / ten_exp < 1:
            ten_exp = ten_exp / 10
        
        m = int(crange[0] / ten_exp) - 1
        n = int(crange[1] / ten_exp) + 1
        for i in range(m, n + 1):
            for j in range(0, 10):
                tics.append((i + j / 10.0) * ten_exp)
        tics = filter(lambda x: crange[0] <= x <= crange[1], tics) #filter out tics not in range (there can be one or two)
    else:
        tics = chart_calculate_tics_for_range(crange, False)
    return tics


class LineChart(chart.Chart):
    
    __gsignals__ = {"point-clicked": (gobject.SIGNAL_RUN_LAST,
                                        gobject.TYPE_NONE,
                                        (gobject.TYPE_PYOBJECT,
                                        gobject.TYPE_PYOBJECT)),
                    "point-hovered": (gobject.SIGNAL_RUN_LAST,
                                        gobject.TYPE_NONE,
                                        (gobject.TYPE_PYOBJECT,
                                        gobject.TYPE_PYOBJECT))}
                                        
    __gproperties__ = {"mouse-over-effect": (gobject.TYPE_BOOLEAN,
                                            "set whether to show datapoint mouse over effect",
                                            "Set whether to show datapoint mouse over effect.",
                                            True, gobject.PARAM_READWRITE),
                        "extend-xrange": (gobject.TYPE_PYOBJECT,
                                            "set how to extend the xrange",
                                            "Set how to extend the xrange.",
                                            gobject.PARAM_READWRITE),
                        "extend-yrange": (gobject.TYPE_PYOBJECT,
                                            "set how to extend the yrange",
                                            "Set how to extend the yrange.",
                                            gobject.PARAM_READWRITE)}
    
    _xrange = RANGE_AUTO
    _yrange = RANGE_AUTO
    _mouse_over_effect = True
    _extend_xrange = (0, 0)
    _extend_yrange = (0, 0)
    _peak_marker = None
    
    def __init__(self):
        super(LineChart, self).__init__()
        #public attributes
        self.xaxis = XAxis()
        self.yaxis = YAxis()
        self.grid = Grid()
        self.key = LineChartKey()
        #private attributes
        self._graphs = []
        
        #connect to "appearance-changed" signals
        self.xaxis.connect("appearance-changed", self._cb_appearance_changed)
        self.yaxis.connect("appearance-changed", self._cb_appearance_changed)
        self.grid.connect("appearance-changed", self._cb_appearance_changed)
        self.key.connect("appearance-changed", self._cb_appearance_changed)
        
    def do_get_property(self, property):
        if property.name == "mouse-over-effect":
            return self._mouse_over_effect
        elif property.name == "extend-xrange":
            return self._extend_xrange
        elif property.name == "extend-yrange":
            return self._extend_yrange
        else:
            return super(LineChart, self).do_get_property(property)
            
    def do_set_property(self, property, value):
        if property.name == "mouse-over-effect":
            self._mouse_over_effect = value
        elif property.name == "extend-xrange":
            self._extend_xrange = value
        elif property.name == "extend-yrange":
            self._extend_yrange = value
        else:
            super(LineChart, self).do_set_property(property, value)
        
    def _cb_button_pressed(self, widget, event):
        data = chart.get_sensitive_areas(event.x, event.y)
        for graph, point in data:
            self.emit("point-clicked", graph, point)
    
    def _cb_motion_notify(self, widget, event):
        if not self._mouse_over_effect: return
        data = chart.get_sensitive_areas(event.x, event.y)
        change = False
        for graph in self._graphs:
            if graph.get_highlighted() != []:
                change = True
            graph.set_highlighted([])
        for graph, point in data:
            graph.add_highlighted(point)
            self.emit("point-hovered", graph, point)
        if data != [] or change:
            self.queue_draw()
        
    def draw(self, context):
        """
        Draw the widget. This method is called automatically. Don't call it
        yourself. If you want to force a redrawing of the widget, call
        the queue_draw() method.
        
        @type context: cairo.Context
        @param context: The context to draw on.
        """
        label.begin_drawing()
        
        rect = self.get_allocation()
        rect = gtk.gdk.Rectangle(0, 0, rect.width, rect.height) #transform rect to context coordinates
        context.set_line_width(1)
                                    
        rect = self._draw_basics(context, rect)
        
        extend_x = self._extend_xrange
        extend_y = self._extend_yrange
        
        if self._peak_marker != None:
            #extend the y range 10% at the top to show peak marker
            extend_y = extend_y[0], extend_y[1] + 0.1
        
        logscale = (self.xaxis.get_property("logscale"),
                    self.yaxis.get_property("logscale"))
        
        calculated_xrange, calculated_yrange = chart_calculate_ranges(self._xrange, self._yrange, self._graphs, extend_x, extend_y, logscale)
        xtics = chart_calculate_tics_for_range(calculated_xrange, logscale[0])
        ytics = chart_calculate_tics_for_range(calculated_yrange, logscale[1])
        rect, xtics_drawn_at, ytics_drawn_at = self._draw_axes(context, rect, calculated_xrange, calculated_yrange, xtics, ytics)
        
        #restrict drawing area
        context.save()
        context.rectangle(rect.x + 1, rect.y + 1, rect.width - 1, rect.height - 1)
        context.clip()
        
        self._draw_grid(context, rect, xtics_drawn_at, ytics_drawn_at)
        
        self._draw_graphs(context, rect, calculated_xrange, calculated_yrange)
        
        self._draw_peak_marker(context, rect, calculated_xrange, calculated_yrange)
        
        #draw key
        context.restore()
        self.key.draw(context, rect, self._graphs)
        
        label.finish_drawing()
        
    def _draw_basics(self, context, rect):
        """
        Draw basic things that every plot has (background, title, ...).
        
        @type context: cairo.Context
        @param context: The context to draw on.
        @type rect: gtk.gdk.Rectangle
        @param rect: A rectangle representing the charts area.
        """
        self.background.draw(context, rect)
        self.title.draw(context, rect, self._padding)
        
        #calculate the rectangle that's available for drawing the chart
        title_height = self.title.get_real_dimensions()[1]
        rect_height = int(rect.height - 3 * self._padding - title_height)
        rect_width = int(rect.width - 2 * self._padding)
        rect_x = int(rect.x + self._padding)
        rect_y = int(rect.y + title_height + 2 * self._padding)
        return gtk.gdk.Rectangle(rect_x, rect_y, rect_width, rect_height)
        
    def _draw_axes(self, context, rect, calculated_xrange, calculated_yrange, xtics, ytics):
        rect = self.xaxis.make_rect_label_offset(context, rect, xtics)
        rect = self.yaxis.make_rect_label_offset(context, rect, ytics)
        xtics_drawn_at = self.xaxis.draw(context, rect, calculated_xrange, xtics)
        ytics_drawn_at = self.yaxis.draw(context, rect, calculated_yrange, ytics)
        
        return rect, xtics_drawn_at, ytics_drawn_at
        
    def _draw_grid(self, context, rect, xtics, ytics):
        self.grid.draw(context, rect, xtics, ytics, self.xaxis, self.yaxis)
        
    def _draw_graphs(self, context, rect, calculated_xrange, calculated_yrange):
        logscale = (self.xaxis.get_property("logscale"),
                    self.yaxis.get_property("logscale"))
        chart.init_sensitive_areas()
        for i, graph in enumerate(self._graphs):
            gc = graph.get_property("color")
            if gc == COLOR_AUTO:
                gc = COLORS[i % len(COLORS)]
            graph.draw(context, rect, calculated_xrange, calculated_yrange, gc, logscale)
            
    def _draw_peak_marker(self, context, rect, xrange, yrange):
        if self._peak_marker != None:
            ppu_x = float(rect.width) / abs(xrange[0] - xrange[1])
            ppu_y = float(rect.height) / abs(yrange[0] - yrange[1])
            
            x, y = self._peak_marker
            
            posx = rect.x + ppu_x * (x - xrange[0])
            posy = rect.y + rect.height - ppu_y * (y - yrange[0])
            
            context.set_source_rgb(0, 0, 0)
            context.move_to(posx, posy)
            context.rel_line_to(5, -5)
            context.rel_line_to(-10, 0)
            context.close_path()
            context.fill()
        
    def add_graph(self, graph):
        self._graphs.append(graph)
        self.queue_draw()
        
    def clear(self):
        self._graphs = []
        self.queue_draw()
        
    def get_mouse_over_effect(self):
        """
        Returns True if a mouse over effect is shown at datapoints.
        
        (getter method for property 'mouse-over-effect', see setter
        method for details)
        
        @return: boolean
        """
        return self.get_property("mouse-over-effect")
        
    def set_mouse_over_effect(self, mouseover):
        """
        Set whether to show mouse over effect at datapoints.
        
        This is the setter method for the property 'mouse-over-effect'.
        Property type: gobject.TYPE_BOOLEAN
        Property default value: True
        
        @type mouseover: boolean
        """
        self.set_property("mouse-over-effect", mouseover)
        
    def set_peak_marker(self, pos):
        """
        Add a peak marker (small black triangle at pos=(x,y)). A chart can
        only have one peak marker.
        Set pos=None to remove the marker.
        
        @param pos: the marker position
        @type pos: pair of float
        """
        self._peak_marker = pos
        self.queue_draw()
        
    def get_extend_xrange(self):
        """
        Returns a pair of floating point numbers that describe the extension
        of the xrange (see setter function for details).
        
        @return: pair of float
        """
        return self.get_property("extend-xrange")
        
    def set_extend_xrange(self, extend):
        """
        Set how to extend the xrange. extend has to be a pair of float values
        (a, b). If the original xrange is [xmin, xmax] it will be set to
        [xmin * (1 + a), xmax * (1 + b)] on drawing.
        
        @param extend: extend parameters
        @type extend: pair of float
        """
        self.set_property("extend-xrange", extend)
        self.queue_draw()
        
    def get_extend_yrange(self):
        """
        Returns a pair of floating point numbers that describe the extension
        of the yrange (see setter function for details).
        
        @return: pair of float
        """
        return self.get_property("extend-yrange")
        
    def set_extend_yrange(self, extend):
        """
        Set how to extend the yrange. extend has to be a pair of float values
        (a, b). If the original yrange is [ymin, ymax] it will be set to
        [ymin * (1 + a), ymax * (1 + b)] on drawing.
        
        @param extend: extend parameters
        @type extend: pair of float
        """
        self.set_property("extend-yrange", extend)
        self.queue_draw()


class Axis(ChartObject):
    
    __gproperties__ = {"label": (gobject.TYPE_STRING,
                                    "axis label",
                                    "The label for the axis.",
                                    "", gobject.PARAM_READWRITE),
                        "show-label": (gobject.TYPE_BOOLEAN,
                                        "set whether to show the axis label",
                                        "Set whether to show the axis label.",
                                        True, gobject.PARAM_READWRITE),
                        "show-tics": (gobject.TYPE_BOOLEAN,
                                        "set whether to show tics at the axis",
                                        "Set whether to show tics at the axis.",
                                        True, gobject.PARAM_READWRITE),
                        "show-tic-labels": (gobject.TYPE_BOOLEAN,
                                        "set whether to show labels at the tics",
                                        "Set whether to show labels at the tics.",
                                        True, gobject.PARAM_READWRITE),
                        "tic-size": (gobject.TYPE_INT, "the tic size",
                                        "Size of the axis' tics in px.",
                                        1, 100, 3,
                                        gobject.PARAM_READWRITE),
                        "tic-format": (gobject.TYPE_PYOBJECT,
                                        "funtion to format the tic label",
                                        "The funtion to use to format the tic label.",
                                        gobject.PARAM_READWRITE),
                        "show-other-side": (gobject.TYPE_BOOLEAN,
                                            "also draw axis on the opposite side",
                                            "Set whether to also draw axis on theopposite side.",
                                            True, gobject.PARAM_READWRITE),
                        "logscale": (gobject.TYPE_BOOLEAN, "set logscale",
                                        "Set whether to use a logarithmic scale on this axis.",
                                        False, gobject.PARAM_READWRITE)}
                                    
    _label = ""
    _show_label = True
    _label_spacing = 3
    _show_tics = True
    _show_tic_labels = True
    _tic_label_format = lambda self, x: "%.2g" % x
    _tics_size = 3
    _min_tic_spacing = 35 
    _offset_by_tic_label = 0
    _show_other_side = True
    _logscale = False
    
    def __init__(self):
        super(Axis, self).__init__()
        self.set_property("antialias", False)
        
    def do_get_property(self, property):
        if property.name == "label":
            return self._label
        elif property.name == "show-label":
            return self._show_label
        elif property.name == "show-tics":
            return self._show_tics
        elif property.name == "show-tic-labels":
            return self._show_tic_labels
        elif property.name == "tic-size":
            return self._tics_size
        elif property.name == "tic-format":
            return self._tic_label_format
        elif property.name == "show-other-side":
            return self._show_other_side
        elif property.name == "logscale":
            return self._logscale
        else:
            return super(Axis, self).do_get_property(property)
        
    def do_set_property(self, property, value):
        if property.name == "label":
            self._label = value
        elif property.name == "show-label":
            self._show_label = value
        elif property.name == "show-tics":
            self._show_tics = value
        elif property.name == "show-tic-labels":
            self._show_tic_labels = value
        elif property.name == "tic-size":
            self._tics_size = value
        elif property.name == "tic-format":
            self._tic_label_format = value
        elif property.name == "show-other-side":
            self._show_other_side = value
        elif property.name == "logscale":
            self._logscale = value
            if value:
                self._tic_label_format = lambda x: "%.2g" % math.pow(10, x)
        else:
            super(Axis, self).do_set_property(property, value)
            
    def get_label(self):
        """
        Returns the current label of the axis.
        
        (getter method for property 'label', see setter method for
        details)
        
        @return: string
        """
        return self.get_property("label")
            
    def set_label(self, label):
        """
        Set the label of the axis.
        
        This is the setter method for the property 'label'.
        Property type: gobject.TYPE_STRING
        Property default value: ""
        
        @param label: new label
        @type label: string
        """
        self.set_property("label", label)
        
    def get_show_label(self):
        """
        Return True if the axis' label is shown.
        
        (getter method for property 'show-label', see setter method for
        details)
        
        @return: boolean
        """
        return self.get_property("show-label")
        
    def set_show_label(self, show):
        """
        Set whether to show the axis' label.
        
        This is the setter method for the property 'show-label'.
        Property type: gobject.TYPE_BOOLEAN
        Property default value: True
        
        @type show: boolean
        """
        self.set_property("show-label", show)
        
    def get_show_tics(self):
        """
        Return True tics are shown.
        
        (getter method for property 'show-tics', see setter method for
        details)
        
        @return: boolean
        """
        return self.get_property("show-tics")
        
    def set_show_tics(self, show):
        """
        Set whether to show tics at the axis.
        
        This is the setter method for the property 'show-tics'.
        Property type: gobject.TYPE_BOOLEAN
        Property default value: True
        
        @type show: boolean
        """
        self.set_property("show-tics", show)
        
    def get_show_tic_labels(self):
        """
        Return True if labels are shown at the axis' tics.
        
        (getter method for property 'show-tic-labels', see setter method
        for details)
        
        @return: boolean
        """
        return self.get_property("show-tic-labels")
        
    def set_show_tic_labels(self, show):
        """
        Set whether to show labels at the axis' tics. If the property
        'show-tics' is False, labels are not shown regardless of what
        value 'show-tic-labels' has.
        
        This is the setter method for the property 'show-tic-labels'.
        Property type: gobject.TYPE_BOOLEAN
        Property default value: True
        
        @type show: boolean
        """
        self.set_property("show-tic-labels", show)
        
    def get_tic_size(self):
        """
        Returns the size of the axis' tics in pixels.
        
        (getter method for property 'tic-size', see setter method for
        details)
        
        @return: int
        """
        return self.get_property("tic-size")
        
    def set_tic_size(self, size):
        """
        Set the size of the axis' tics in pixels.
        
        This is the setter method for the property 'tic-size'.
        Property type: gobject.TYPE_INT
        Property minimum value: 1
        Property maximum value: 100
        Property default value: 3
        
        @param size: new size for the tics
        @type size: interger
        """
        self.set_property("tic-size", size)
        
    def get_tic_format(self):
        """
        Returns the function that is used to format the tic labels.
        
        (getter method for property 'tic-format', see setter method for
        details)
        
        @return: function
        """
        return self.get_property("tic-format")
        
    def set_tic_format(self, func):
        """
        Set the function to format the tic labels. The function
        'func' has to take a float as the only argument and should
        return a string.
        
        This is the setter method for the property 'tic-format'.
        Property type: gobject.TYPE_PYOBJECT
        Property default value: str
        
        @param func: new label formating function
        @type func: function
        """
        self.set_property("tic-format", func)
        
    def get_show_other_side(self):
        """
        Returns True if axis is also drawn at the opposite side.
        
        (getter method for property 'show-other-side', see setter method
        for details)
        
        @return: boolean
        """
        return self.get_property("show-other-side")
        
    def set_show_other_side(self, show):
        """
        Set whether the axis should also be drawn at the opposite side.
        
        This is the setter method for the property 'show-other-side'.
        Property type: gobject.TYPE_BOOLEAN
        Property default value: True
        
        @type show: boolean
        """
        self.set_property("show-other-side", show)


class XAxis(Axis):
    
    def __init__(self):
        super(XAxis, self).__init__()
        self._label = "x"
    
    def _do_draw(self, context, rect, calculated_xrange, tics):
        self._draw_label(context, rect)
        context.set_line_width(1)
        context.set_source_rgb(0, 0, 0)
        context.move_to(rect.x, rect.y + rect.height + 0.5)
        context.rel_line_to(rect.width, 0)
        context.stroke()
        
        if self._show_other_side:
            context.move_to(rect.x, rect.y + 0.5)
            context.rel_line_to(rect.width, 0)
            context.stroke()
        
        tics_drawn_at = self._draw_tics(context, rect, calculated_xrange, tics)
        self._draw_tic_labels(context, rect, tics_drawn_at)
        return tics_drawn_at
        
    def _draw_tics(self, context, rect, xrange, tics):
        tics_drawn_at = []
        if self._show_tics:
            ppu = float(rect.width) / abs(xrange[0] - xrange[1])
            y = rect.y + rect.height
            last_pos = -100
            for tic in tics:
                x = rect.x + ppu * (tic - xrange[0])
                if abs(x - last_pos) >= self._min_tic_spacing:
                    context.move_to(x, y)
                    context.rel_line_to(0, -self._tics_size)
                    context.stroke()
                    
                    if self._show_other_side:
                        context.move_to(x, rect.y)
                        context.rel_line_to(0, self._tics_size)
                        context.stroke()
                    
                    last_pos = x
                    tics_drawn_at.append((tic, x))
        return tics_drawn_at
        
    def _draw_label(self, context, rect):
        if self._label and self._show_label:
            pos = rect.x + rect.width / 2, rect.y + rect.height + self._offset_by_tic_label + self._label_spacing
            label_object = label.Label(pos, self._label, anchor=label.ANCHOR_TOP_CENTER)
            label_object.set_use_markup(True)
            label_object.draw(context, rect)
            
    def _draw_tic_labels(self, context, rect, tics_drawn_at):
        if self._show_tics and self._show_tic_labels:
            posy = rect.y + rect.height + self._label_spacing
            for x, posx in tics_drawn_at:
                pos = (posx, posy)
                label_object = label.Label(pos, self._tic_label_format(x), anchor=label.ANCHOR_TOP_CENTER)
                label_object.set_fixed(True)
                label_object.draw(context, rect)
                
    def make_rect_label_offset(self, context, rect, tics):
        offset = 0
        if self._label and self._show_label:
            pos = rect.x + rect.width / 2, rect.y + rect.height
            label_object = label.Label(pos, self._label, anchor=label.ANCHOR_TOP_CENTER)
            label_object.set_max_width(rect.width)
            label_object.set_use_markup(True)
            w, h = label_object.get_calculated_dimensions(context, rect)
            offset = int(h)
        if self._show_tics and self._show_tic_labels:
            label_object = label.Label((0, 0), self._tic_label_format(tics[0]), anchor=label.ANCHOR_TOP_LEFT)
            w, h = label_object.get_calculated_dimensions(context, rect)
            offset += int(h)
            self._offset_by_tic_label = int(h) + self._label_spacing
        rect = gtk.gdk.Rectangle(rect.x, rect.y, rect.width, rect.height - offset)
        return rect
    
    
    
class YAxis(Axis):
    
    def __init__(self):
        super(YAxis, self).__init__()
        self._label = "y"
    
    def _do_draw(self, context, rect, calculated_yrange, tics):
        self._draw_label(context, rect)
        context.set_line_width(1)
        context.set_source_rgb(0, 0, 0)
        context.move_to(rect.x + 0.5, rect.y)
        context.rel_line_to(0, rect.height)
        context.stroke()
        
        if self._show_other_side:
            context.move_to(rect.x + rect.width + 0.5, rect.y)
            context.rel_line_to(0, rect.height)
            context.stroke()
        
        tics_drawn_at = self._draw_tics(context, rect, calculated_yrange, tics)
        self._draw_tic_labels(context, rect, tics_drawn_at)
        return tics_drawn_at
        
    def _draw_tics(self, context, rect, yrange, tics):
        tics_drawn_at = []
        if self._show_tics:
            ppu = float(rect.height) / abs(yrange[0] - yrange[1])
            x = rect.x
            last_pos = -100
            for tic in tics:
                y = rect.y + rect.height - ppu * (tic - yrange[0])
                if abs(y - last_pos) >= self._min_tic_spacing:
                    context.move_to(x, y)
                    context.rel_line_to(self._tics_size, 0)
                    context.stroke()
                    
                    if self._show_other_side:
                        context.move_to(x + rect.width, y)
                        context.rel_line_to(-self._tics_size, 0)
                        context.stroke()
                    
                    last_pos = y
                    tics_drawn_at.append((tic, y))
        return tics_drawn_at
        
    def _draw_label(self, context, rect):
        if self._label and self._show_label:
            pos = rect.x - self._offset_by_tic_label - self._label_spacing, rect.y + rect.height / 2
            label_object = label.Label(pos, self._label, anchor=label.ANCHOR_BOTTOM_CENTER)
            label_object.set_rotation(90)
            label_object.set_wrap(False)
            label_object.set_use_markup(True)
            label_object.set_max_width(rect.height)
            label_object.draw(context, rect)
            
    def _draw_tic_labels(self, context, rect, tics_drawn_at):
        if self._show_tics and self._show_tic_labels:
            posx = rect.x - self._label_spacing
            for y, posy in tics_drawn_at:
                pos = (posx, posy)
                label_object = label.Label(pos, self._tic_label_format(y), anchor=label.ANCHOR_RIGHT_CENTER)
                label_object.set_fixed(True)
                label_object.draw(context, rect)
        
    def make_rect_label_offset(self, context, rect, tics):
        offset = 0
        if self._label and self._show_label:
            pos = rect.x, rect.y + rect.height / 2
            label_object = label.Label(pos, self._label, anchor=label.ANCHOR_TOP_CENTER)
            label_object.set_rotation(90)
            label_object.set_wrap(False)
            label_object.set_use_markup(True)
            label_object.set_max_width(rect.height)
            w, h = label_object.get_calculated_dimensions(context, rect)
            offset = int(w)
        if self._show_tics and self._show_tic_labels:
            m = ""
            w = 0
            for y in tics:
                if len(self._tic_label_format(y)) > len(m):
                    m = self._tic_label_format(y)
                label_object = label.Label((0, 0), m, anchor=label.ANCHOR_TOP_LEFT)
                w, h = label_object.get_calculated_dimensions(context, rect)
            self._offset_by_tic_label = int(w) + self._label_spacing
            offset += int(w)
        rect = gtk.gdk.Rectangle(rect.x + offset, rect.y, rect.width - offset, rect.height)
        return rect

class Grid(ChartObject):
    
    __gproperties__ = {"show-horizontal-lines": (gobject.TYPE_BOOLEAN,
                                                "show horizontal lines",
                                                "Sets whether to show horizontal grid lines.",
                                                True, gobject.PARAM_READWRITE),
                        "show-vertical-lines": (gobject.TYPE_BOOLEAN,
                                                "show vertical lines",
                                                "Sets whether to show vertical grid lines.",
                                                True, gobject.PARAM_READWRITE),
                        "line-style-horizontal": (gobject.TYPE_INT,
                                                    "horizontal line style",
                                                    "Style of the horizontal lines.",
                                                    -1, 3, 0,
                                                    gobject.PARAM_READWRITE),
                        "line-style-vertical": (gobject.TYPE_INT,
                                                    "vertical line style",
                                                    "Style of the vertical lines.",
                                                    -1, 3, 0,
                                                    gobject.PARAM_READWRITE),
                        "color": (gobject.TYPE_PYOBJECT, "line color",
                                    "Color of the grid lines.",
                                    gobject.PARAM_READWRITE)}
                                                        
    _show_horizontal_lines = True
    _show_vertical_lines = True
    _line_style_horizontal = pygtk_chart.LINE_STYLE_DOTTED
    _line_style_vertical = pygtk_chart.LINE_STYLE_DOTTED
    _color = gtk.gdk.color_parse("#cccccc")
    
    def __init__(self):
        super(Grid, self).__init__()
        
    def do_get_property(self, property):
        if property.name == "show-horizontal-lines":
            return self._show_horizontal_lines
        elif property.name == "show-vertical-lines":
            return self._show_vertical_lines
        elif property.name == "line-style-horizontal":
            return self._line_style_horizontal
        elif property.name == "line-style-vertical":
            return self._line_style_vertical
        elif property.name == "color":
            return self._color
        else:
            return super(Grid, self).do_get_property(property)
            
    def do_set_property(self, property, value):
        if property.name == "show-horizontal-lines":
            self._show_horizontal_lines = value
        elif property.name == "show-vertical-lines":
            self._show_vertical_lines = value
        elif property.name == "line-style-horizontal":
            self._line_style_horizontal = value
        elif property.name == "line-style-vertical":
            self._line_style_vertical = value
        elif property.name == "color":
            self._color = value
        else:
            super(Grid, self).do_set_property(property, value)
        
    def _do_draw(self, context, rect, xtics, ytics, xaxis, yaxis):
        context.set_source_rgb(*color_gdk_to_cairo(self._color))
        #draw vertical lines
        if self._show_vertical_lines:
            set_context_line_style(context, self._line_style_vertical)
            for x, xpos in xtics:
                if xaxis.get_show_other_side():
                    context.move_to(xpos, rect.y + xaxis.get_tic_size())
                    context.rel_line_to(0, rect.height - 2 * xaxis.get_tic_size())
                else:
                    context.move_to(xpos, rect.y)
                    context.rel_line_to(0, rect.height - xaxis.get_tic_size())
                context.stroke()
        #draw horizontal lines
        if self._show_horizontal_lines:
            set_context_line_style(context, self._line_style_horizontal)
            for y, ypos in ytics:
                context.move_to(rect.x + yaxis.get_tic_size(), ypos)
                if yaxis.get_show_other_side():
                    context.rel_line_to(rect.width - 2 * yaxis.get_tic_size(), 0)
                else:
                    context.rel_line_to(rect.width - yaxis.get_tic_size(), 0)
                context.stroke()
                
    def get_show_horizontal_lines(self):
        """
        Returns True if horizontal grid lines are shown.
        
        (getter method for property 'show-horizontal-lines', see setter
        method for details)
        
        @return: boolean
        """
        return self.get_property("show-horizontal-lines")
        
    def set_show_horizontal_lines(self, show):
        """
        Set whether to show horizontal grid lines.
        
        This is the setter method for the property
        'show-horizontal-lines'.
        Property type: gobject.TYPE_BOOLEAN
        Property default value: True
        
        @type show: boolean
        """
        self.set_property("show-horizontal-lines", show)
                
    def get_show_vertical_lines(self):
        """
        Returns True if vertical grid lines are shown.
        
        (getter method for property 'show-vertical-lines', see setter
        method for details)
        
        @return: boolean
        """
        return self.get_property("show-vertical-lines")
        
    def set_show_vertical_lines(self, show):
        """
        Set whether to show vertical grid lines.
        
        This is the setter method for the property
        'show-vertical-lines'.
        Property type: gobject.TYPE_BOOLEAN
        Property default value: True
        
        @type show: boolean
        """
        self.set_property("show-vertical-lines", show)
        
    def get_line_style_horizontal(self):
        """
        Returns the line style for the horizontal grid lines.
        
        (getter method for property 'line-style-horizontal', see setter
        method for details)
        
        @return: line style constant
        """
        return self.get_property("line-style-horizontal")
        
    def set_line_style_horizontal(self, style):
        """
        Sets the line style for the horizontal grid lines.
        style has to be one of the following line style constants:
         - pygtk_chart.LINE_STYLE_NONE = -1
         - pygtk_chart.LINE_STYLE_SOLID = 0
         - pygtk_chart.LINE_STYLE_DOTTED = 1
         - pygtk_chart.LINE_STYLE_DASHED = 2
         - pygtk_chart.LINE_STYLE_DASHED_ASYMMETRIC = 3
         
        This is the setter method for the property
        'line-style-horizontal'.
        Property type: gobject.TYPE_INT
        Property minimum value: -1
        Property maximum value: 3
        Property default value: 0 (pygtk_chart.LINE_STYLE_SOLID)
        
        @type style: a line style constant
        """
        self.set_property("line-style-horizontal", style)
        
    def get_line_style_vertical(self):
        """
        Returns the line style for the vertical grid lines.
        
        (getter method for property 'line-style-vertical', see setter
        method for details)
        
        @return: line style constant
        """
        return self.get_property("line-style-vertical")
        
    def set_line_style_vertical(self, style):
        """
        Sets the line style for the vertical grid lines.
        style has to be one of the following line style constants:
         - pygtk_chart.LINE_STYLE_NONE = -1
         - pygtk_chart.LINE_STYLE_SOLID = 0
         - pygtk_chart.LINE_STYLE_DOTTED = 1
         - pygtk_chart.LINE_STYLE_DASHED = 2
         - pygtk_chart.LINE_STYLE_DASHED_ASYMMETRIC = 3
         
        This is the setter method for the property
        'line-style-vertical'.
        Property type: gobject.TYPE_INT
        Property minimum value: -1
        Property maximum value: 3
        Property default value: 0 (pygtk_chart.LINE_STYLE_SOLID)
        
        @type style: a line style constant
        """
        self.set_property("line-style-vertical", style)
        
    def get_color(self):
        """
        Returns the grid color.
        
        (getter method for property 'color', see setter method for
        details)
        
        @return: gtk.gdk.COlOR.
        """
        return self.get_property("color")
        
    def set_color(self, color):
        """
        Set the color of the grid.
        
        This is the setter method for the property 'color'.
        Property type: gobject.TYPE_PYOBJECT
        Property default value: gtk.gdk.color_parse('#cccccc')
        
        @param color: new grid color
        @type color: gtk.gdk.Color
        """
        self.set_property("color", color)


class LineChartKey(ChartObject):
    """
    This class is used to display a simple key on a LineChart widget. You
    don't need to create it yourself, every LineChart has an instance of
    this class stored in LineChart.key.
    """
    
    __gproperties__ = {"width": (gobject.TYPE_FLOAT, "relative width of key",
                                    "The relative width of the key.",
                                    0.1, 0.9, 0.4, gobject.PARAM_READWRITE),
                        "position": (gobject.TYPE_INT, "key position",
                                        "Position of the key.", 0, 3, 0,
                                        gobject.PARAM_READWRITE),
                        "line-length": (gobject.TYPE_INT, "sample line length",
                                        "Length of the sample line.", 5, 25,
                                        10, gobject.PARAM_READWRITE),
                        "padding": (gobject.TYPE_INT, "key padding",
                                    "key padding", 1, 25, 10,
                                    gobject.PARAM_READWRITE),
                        "opacity": (gobject.TYPE_FLOAT, "key opacity",
                                    "Opacity of the key.", 0.0, 1.0, 0.75,
                                    gobject.PARAM_READWRITE)}
        
    _width = 0.4
    _position = KEY_POSITION_TOP_RIGHT
    _line_length = 10
    _padding = 10
    _bg_opacity = 0.75
    
    def __init__(self):
        super(LineChartKey, self).__init__()
        self.set_visible(False)
        
    def _do_draw(self, context, rect, graph_list):
        set_context_line_style(context, pygtk_chart.LINE_STYLE_SOLID)
        
        width = self._width * rect.width
        height = 0
        
        context.push_group()
        
        cx = self._padding
        cy = self._padding
        context.move_to(0, 0)
        context.set_source_rgb(0, 0, 0)
        
        i = 0
        item_width = 0
        for graph in graph_list:
            if not graph.get_visible(): continue
            
            #draw line
            context.move_to(cx, cy)
            gc = graph.get_property("color")
            if gc == COLOR_AUTO:
                gc = COLORS[i % len(COLORS)]
                
            context.set_source_rgb(*color_gdk_to_cairo(gc))
            if graph.get_line_style() != pygtk_chart.LINE_STYLE_NONE:
                set_context_line_style(context, graph.get_line_style())
                context.rel_line_to(self._line_length, 0)
                context.stroke()
            
            #draw point
            graph_draw_point(context, cx + self._line_length, cy, graph.get_point_size(), graph.get_point_style())
            
            #draw title
            l = label.Label((cx + self._line_length + self._padding, cy - 8), graph.get_name())
            l.set_anchor(label.ANCHOR_TOP_LEFT)
            l.set_max_width(width - 3 * self._padding - self._line_length)
            l.set_wrap(True)
            l.draw(context, rect)
            
            item_width = max(item_width, 3 * self._padding + self._line_length + l.get_real_dimensions()[0])
            
            if l.get_real_dimensions()[1] <= 10:
                cy += 20
            else:
                cy += l.get_real_dimensions()[1]
                cy += 10

            i += 1
        
        width = min(width, item_width)
        height = cy - 10
        
        group = context.pop_group()
        
        #place key
        if self._position == KEY_POSITION_TOP_RIGHT:
            x = rect.x + rect.width - width
            y = rect.y
        elif self._position == KEY_POSITION_TOP_LEFT:
            x = rect.x
            y = rect.y
        elif self._position == KEY_POSITION_BOTTOM_LEFT:
            x = rect.x
            y = rect.y + rect.height - height
        elif self._position == KEY_POSITION_BOTTOM_RIGHT:
            x = rect.x + rect.width - width
            y = rect.y + rect.height - height
            
        context.translate(x, y)
        
        context.set_source_rgba(1, 1, 1, self._bg_opacity)
        context.rectangle(1, 1, width - 1, height - 1)
        context.fill()
        context.set_source(group)
        context.rectangle(0, 0, width, height)
        context.fill()
        
        context.translate(-x, -y)
        
    def do_get_property(self, property):
        if property.name == "width":
            return self._width
        elif property.name == "position":
            return self._position
        elif property.name == "line-length":
            return self._line_length
        elif property.name == "padding":
            return self._padding
        elif property.name == "opacity":
            return self._bg_opacity
        else:
            return super(LineChartKey, self).do_get_property(property)
            
    def do_set_property(self, property, value):
        if property.name == "width":
            self._width = value
            self.emit("appearance-changed")
        elif property.name == "position":
            self._position = value
            self.emit("appearance-changed")
        elif property.name == "line-length":
            self._line_length = value
            self.emit("appearance-changed")
        elif property.name == "padding":
            self._padding = value
            self.emit("appearance-changed")
        elif property.name == "opacity":
            self._bg_opacity = value
            self.emit("appearance-changed")
        else:
            super(LineChartKey, self).do_set_property(property, value)
            
    def get_line_length(self):
        """
        Returns the length of sample lines.
        
        @return: int
        """
        return self.get_property("line-length")
        
    def set_line_length(self, length):
        """
        Set the length of sample lines drawn for graphs.
        
        @param length: new length
        @type length: int in range [5, 25]
        """
        self.set_property("line-length", length)
        
    def get_opacity(self):
        """
        Returns the opacity of the key's background.
        
        @return: float
        """
        return self.get_property("opacity")
        
    def set_opacity(self, opacity):
        """
        Set the opacity of the key's background.
        
        @param opacity: the new opacity
        @type opacity: float in range [0.0, 1.0]
        """
        self.set_property("opacity", opacity)
        
    def get_padding(self):
        """
        Returns the contents padding.
        
        @return: int
        """
        return self.get_property("padding")
        
    def set_padding(self, padding):
        """
        Set the amount of content padding.
        
        @param padding: new padding
        @type padding: int in range [1, 25]
        """
        self.set_property("padding", padding)
            
    def get_position(self):
        """
        Returns a key position constant determining the key's position.
        
        @return: position constant
        """
        return self.get_property("position")
        
        
    def set_position(self, position):
        """
        Set the key's position. position has to be one of the following
        constants:
        
         - line_chart.KEY_POSITION_TOP_RIGHT
         - line_chart.KEY_POSITION_TOP_LEFT
         - line_chart.KEY_POSITION_BOTTOM_LEFT
         - line_chart.KEY_POSITION_BOTTOM_RIGHT
        
        @param positon: new position
        @type position: one of the constants above.
        """
        self.set_property("position", position)        
            
    def get_width(self):
        """
        Returns the relative width of the key.
        
        @return: float
        """
        return self.get_property("width")
        
    def set_width(self, width):
        """
        Set the relative width of the key.
        
        @param width: new relative width
        @type width: float in range [0.0, 1.0]
        """
        self.set_property("width", width)
