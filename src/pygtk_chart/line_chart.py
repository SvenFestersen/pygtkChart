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
        elif property.name == "visible":
            return self._show
        elif property.name == "antialias":
            return self._antialias
        elif property.name == "color":
            return self._color
        
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
        return self._xrange, self._yrange
        

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
        rect = self._draw_axes(context, rect, calculated_xrange, calculated_yrange, xtics, ytics)
        
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
        self.xaxis.draw(context, rect, calculated_xrange, xtics)
        self.yaxis.draw(context, rect, calculated_yrange, ytics)
        
        return rect
        
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
                                        "set whether to show the axis label or not",
                                        "Set whether to show the axis label or not.",
                                        True, gobject.PARAM_READWRITE)}
                                    
    _label = ""
    _show_label = True
    _label_spacing = 3
    _show_tics = True #make gobject property
    _show_tic_labels = True #make gobject property
    _tic_label_format = str #make gobject property
    _tics_size = 3 #make gobject property
    _min_tic_spacing = 10 
    _offset_by_tic_label = 0
    
    def __init__(self):
        super(Axis, self).__init__()
        self.set_property("antialias", False)
        
    def do_get_property(self, property):
        if property.name == "label":
            return self._label
        elif property.name == "show-label":
            return self._show_label
        super(Axis, self).do_get_property(property)
        
    def do_set_property(self, property, value):
        if property.name == "label":
            self._label = value
        elif property.name == "show-label":
            self._show_label = value
        else:
            super(Axis, self).do_set_property(property, value)


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
