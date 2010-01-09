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


RANGE_AUTO = "range_auto"


def graph_sort_data(data):
    """
    Sorts the data points by the x values.
    """
    f = lambda a, b: cmp(a[0], b[0])
    data.sort(f)
    
def graph_make_ranges(data):
    """
    Calculates the xrange and the yrange from data.
    """
    if data == []:
        return None, None
    #data points are sorted by x values, so xrange is simple:
    xrange = [data[0][0], data[-1][0]]
    #iterate over all data points to find min and max y values
    yrange = [data[0][1], data[0][1]]
    for x, y in data:
        yrange[0] = min(yrange[0], y)
        yrange[1] = max(yrange[1], y)
        
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
    
def graph_draw_points(context, rect, data, xrange, yrange, ppu_x, ppu_y, point_style, point_size):
    if point_style != pygtk_chart.POINT_STYLE_NONE:
        for point in data:
            x, y = point
            if not xrange[0] <= x <= xrange[1]: continue
            posx = rect.x + ppu_x * (x - xrange[0])
            posy = rect.y + rect.height - ppu_y * (y - yrange[0])
            
            if type(point_style) != gtk.gdk.Pixbuf:
                graph_draw_point(context, posx, posy, point_size, point_style)
            else:
                graph_draw_point_pixbuf(context, posx, posy, point_style)
                
def graph_draw_lines(context, rect, data, xrange, yrange, ppu_x, ppu_y, line_style):
    if line_style != pygtk_chart.LINE_STYLE_NONE:
        set_context_line_style(context, line_style)
        first_point = True
        for point in data:
            x, y = point
            if not xrange[0] <= x <= xrange[1]: continue
            posx = rect.x + ppu_x * (x - xrange[0])
            posy = rect.y + rect.height - ppu_y * (y - yrange[0])
            
            if first_point:
                context.move_to(posx, posy)
                first_point = False
            else:
                context.line_to(posx, posy)
        context.stroke()
            
    
    

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
                                        gobject.PARAM_READWRITE)}
    
    _xrange = None
    _yrange = None
    _line_style = pygtk_chart.LINE_STYLE_SOLID
    _point_style = pygtk_chart.POINT_STYLE_CIRCLE
    _point_size = 2
    _color = COLOR_AUTO
    
    def __init__(self, name, points=[]):
        super(Graph, self).__init__()
        self._name = name
        self._data = points
        
        self._process_data()
        
    def __len__(self):
        return len(self._data)
        
    def do_get_property(self, property):
        if property.name == "xrange":
            return self._xrange
        elif property.name == "yrange":
            return self._yrange
        elif property.name == "line-style":
            return self._line_style
        elif property.name == "point-style":
            return self._point_style
        elif property.name == "point-size":
            return self._point_size
        elif property.name == "color":
            return self._color
        else:
            return super(Graph, self).do_get_property(property)
        
    def do_set_property(self, property, value):
        if property.name == "line-style":
            self._line_style = value
        elif property.name == "point-style":
            self._point_style = value
        elif property.name == "point-size":
            self._point_size = value
        elif property.name == "color":
            self._color = value
        else:
            super(Graph, self).do_set_property(property, value)
        
    def _process_data(self):
        """
        Sorts data points and calculates ranges.
        """
        graph_sort_data(self._data)
        self._xrange, self._yrange = graph_make_ranges(self._data)
        
    def _do_draw(self, context, rect, xrange, yrange, color):
        #ppu: pixel per unit
        ppu_x = float(rect.width) / abs(xrange[0] - xrange[1])
        ppu_y = float(rect.height) / abs(yrange[0] - yrange[1])
        
        context.set_source_rgb(*color_gdk_to_cairo(color))
        graph_draw_lines(context, rect, self._data, xrange, yrange, ppu_x, ppu_y, self._line_style)                
        graph_draw_points(context, rect, self._data, xrange, yrange, ppu_x, ppu_y, self._point_style, self._point_size)                
        
    def add_point(self, point):
        """
        Add a single data point [(x, y) pair] to the graph.
        """
        self._data.append(point)
        self._process_data()
        self.emit("appearance_changed")
        
    def add_points(self, points):
        """
        Add a list of data points [(x, y) pairs] to the graph.
        """
        self._data += points
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
        
    def get_point_style(self):
        """
        Returns the point style for this graph.
        
        (getter method for property 'point-style', see setter method for
        details)
        
        @return: a point style constant, or a gtk.gdk.Pixbuf
        """
        return self.get_property("line-style")
        
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
        

def chart_calculate_ranges(xrange, yrange, graphs):
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
            
    return calc_xrange, calc_yrange
    
    
def chart_calculate_tics_for_range(crange):
    """
    This function calculates the tics that should be drawn for a given
    range.
    """
    tics = []
    delta = abs(crange[0] - crange[1])
    exp = int(math.log10(delta))
    
    ten_exp = math.pow(10, exp) #store this value for performance reasons
    
    m = int(crange[0] / ten_exp) - 1
    n = int(crange[1] / ten_exp) + 1
    for i in range(m, n + 1):
        tics.append(i * ten_exp)
        tics.append((i + 0.5) * ten_exp)
    tics = filter(lambda x: crange[0] <= x <= crange[1], tics) #filter out tics not in range (there can be one or two)
    return tics


class LineChart(chart.Chart):
    
    _xrange = RANGE_AUTO
    _yrange = RANGE_AUTO
    
    def __init__(self):
        super(LineChart, self).__init__()
        #public attributes
        self.xaxis = XAxis()
        self.yaxis = YAxis()
        self.grid = Grid()
        #private attributes
        self._graphs = []
        
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
        
        calculated_xrange, calculated_yrange = chart_calculate_ranges(self._xrange, self._yrange, self._graphs)
        xtics = chart_calculate_tics_for_range(calculated_xrange)
        ytics = chart_calculate_tics_for_range(calculated_yrange)
        rect, xtics_drawn_at, ytics_drawn_at = self._draw_axes(context, rect, calculated_xrange, calculated_yrange, xtics, ytics)
        self._draw_grid(context, rect, xtics_drawn_at, ytics_drawn_at)
        
        self._draw_graphs(context, rect, calculated_xrange, calculated_yrange)
        
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
        for i, graph in enumerate(self._graphs):
            gc = graph.get_property("color")
            if gc == COLOR_AUTO:
                gc = COLORS[i % len(COLORS)]
            graph.draw(context, rect, calculated_xrange, calculated_yrange, gc)
        
    def add_graph(self, graph):
        self._graphs.append(graph)
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
                                        gobject.PARAM_READWRITE)}
                                    
    _label = ""
    _show_label = True
    _label_spacing = 3
    _show_tics = True
    _show_tic_labels = True
    _tic_label_format = str
    _tics_size = 3
    _min_tic_spacing = 20 
    _offset_by_tic_label = 0
    
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
                    last_pos = x
                    tics_drawn_at.append((tic, x))
        return tics_drawn_at
        
    def _draw_label(self, context, rect):
        if self._label and self._show_label:
            pos = rect.x + rect.width / 2, rect.y + rect.height + self._offset_by_tic_label + self._label_spacing
            label_object = label.Label(pos, self._label, anchor=label.ANCHOR_TOP_CENTER)
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
                    last_pos = y
                    tics_drawn_at.append((tic, y))
        return tics_drawn_at
        
    def _draw_label(self, context, rect):
        if self._label and self._show_label:
            pos = rect.x - self._offset_by_tic_label - self._label_spacing, rect.y + rect.height / 2
            label_object = label.Label(pos, self._label, anchor=label.ANCHOR_RIGHT_CENTER)
            label_object.set_rotation(270)
            label_object.set_wrap(False)
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
            label_object = label.Label(pos, self._label, anchor=label.ANCHOR_RIGHT_CENTER)
            label_object.set_rotation(270)
            label_object.set_wrap(False)
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
                context.move_to(xpos, rect.y)
                context.rel_line_to(0, rect.height - xaxis.get_tic_size())
                context.stroke()
        #draw horizontal lines
        if self._show_horizontal_lines:
            set_context_line_style(context, self._line_style_horizontal)
            for y, ypos in ytics:
                context.move_to(rect.x + yaxis.get_tic_size(), ypos)
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
