#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       untitled.py
#       
#       Copyright 2010 Sven Festersen <sven@sven-laptop>
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
import gobject
import gtk


class ColorSet(gobject.GObject):
    
    _name = ""
    _colors = []
    _index = 0
    
    def __init__(self):
        super(ColorSet, self).__init__()
        
    def __str__(self):
        return self._name
        
    def get_color(self):
        c = self._colors[self._index % len(self._colors)]
        self._index += 1
        return gtk.gdk.color_parse(c)
        
    def reset(self):
        self._index = 0
        
        
class TangoColors(ColorSet):
    
    _name = "Tango Colors"
    _colors = ["#cc0000",
                "#3465a4",
                "#73d216",
                "#f57900",
                "#75507b",
                "#c17d11",
                "#edd400"]
        
        
class SimpleColors(ColorSet):
    
    _name = "Simple Colors"
    _colors = ["#FF0000",
                "#00FF00",
                "#0000FF",
                "#FFFF00",
                "#FF00FF",
                "#00FFFF"]
                
                
                
class GrayScaleColors(ColorSet):
    
    _name = "Gray Scale Colors"
    _colors = ["#000000",
                "#6D6D6D",
                "#969696",
                "#C6C6C6"]
                
                
                
