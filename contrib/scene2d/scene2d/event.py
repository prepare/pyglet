#!/usr/bin/env python

'''
Event filters for scene2d Views
===============================

This module provides decorators which limit the cells and sprites for which
events are generated by scene2d Views. Some examples of usage::


    # attach the following event handler to the map
    @event(view)
    # only highlight cells that are buildable
    @for_cells([m], is_buildable=True)
    def on_mouse_enter(cells, x, y):
        """ The mouse is hovering at map pixel position (x,y) over the
            indicated cells."""
           
    @event(view)
    @for_cells([m], is_buildable=True)
    def on_mouse_leave(cells):
        ' The mouse has stopped hovering over the indicated cells.'
               
    @event(view)
    # just for the car sprite
    @for_sprites([car])
    def on_mouse_press(sprite, x, y, button, modifiers):
        ' Click on car to make it flash '

Some other calls::

    @for_cells()             # for any map cell
     
    @for_cells([map, map])   # may have multiple maps
    # event could be generated for every cell in the map(s)
     
    @for_cells([map], name=value, name=value)
    # looks up property by name on Cell, then Tile, then TileSet
     
    @for_cells([map], id='exit_door')
    # could be defined on Cell or Tile -- "id" special-cased as an attribute
     
    @for_cells([map], red_base=True)
     
    @for_cells([map], type='grass')
    # would be defined on Tiles by convention - but there's nothing
    # stopping an exceptional Cell having a "type" property
     
    @for_cells([map], group='grass')
    # would be defined on TileSets by convention
     
    @for_sprites()          # all sprites are active
     
    @for_sprites([list of sprites])      # limited list of sprites active

The filters may be chained::

    @event(view)
    @for_cells([map1], ...)
    @for_cells([map2], ...)
    def on_mouse_press(cell, ...):
        ...

You could have for_sprites in there too, but then the first arg to
on_mouse_press could be either a sprite or a cell. Better to have a
separate handler for sprites to keep things cleaner.
'''

__docformat__ = 'restructuredtext'
__version__ = '$Id$'


class MapFilter:
    def __init__(self, maps, properties):
        self.maps = maps
        self.properties = properties

    def __call__(self, cells):
        ''' Filter by the properties, if any.

        Look in the Cell first, falling back to the Tile if there is one.
        '''
        if not self.properties:
            return cells
        r = []
        for cell in cells:
            for k, v in self.properties.items():
                if k == 'id':
                    if cell.id == v: continue
                    else: break
                if cell.properties[k] == v:
                    continue
                if not hasattr(cell, 'tile') and cell.tile.properties[k] == v:
                    continue
                break
            else:
                r.append(cell)
        return r


class SpriteFilter:
    def __init__(self, sprites, properties):
        self.sprites = sprites
        self.properties = properties

    def __call__(self, sprites):
        ''' Filter by the properties, if any.
        '''
        if not self.properties:
            return sprites
        r = []
        for sprite in sprites:
            for k, v in self.properties.items():
                if k == 'id':
                    if sprite.id == v: continue
                    else: break
                if sprite.properties[k] != v: break
            else:
                r.append(sprite)
        return r


def for_cells(*maps, **criteria):
    def decorate(func):
        if maps: m = maps[0]
        else: m = None
        if m or criteria:
            m = MapFilter(m, criteria)
            if hasattr(func, 'map_filters'):
                if func.map_filters is None:
                    raise ValueError, 'Already seen a @for_sprites()'
                func.map_filters.append(m)
            else:
                func.map_filters = [m]
        else:
            func.map_filters = None

        if not hasattr(func, 'sprite_filters'):
            # search no sprites
            func.sprite_filters = []
        return func
    return decorate

class FitlerPass:
    pass

def for_sprites(*sprites, **criteria):
    def decorate(func):
        if sprites: s = sprites[0]
        else: s = None
        if s or criteria:
            s = SpriteFilter(s, criteria)
            if hasattr(func, 'sprite_filters'):
                if func.sprite_filters is None:
                    raise ValueError, 'Already seen a @for_sprites()'
                func.sprite_filters.append(s)
            else:
                func.sprite_filters = [s]
        else:
            func.sprite_filters = None

        if not hasattr(func, 'map_filters'):
            # search no maps
            func.map_filters = []
        return func
    return decorate

