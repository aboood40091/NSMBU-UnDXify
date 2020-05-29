#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# hi splo


class QRectF:
    """
    Why would we import PyQt5 just to use a few functions from QRectF?
    Let's make our own custom implementation!
    """
    def __init__(self, *args):
        self.x, self.y, self.w, self.h = args

    def left(self):
        return self.x

    def right(self):
        return self.x + self.w

    def top(self):
        return self.y

    def bottom(self):
        return self.y + self.h

    def contains(self, x, y):
        return x in range(self.x, self.x + self.w) and y in range(self.y, self.y + self.h)


class ObjectItem:
    def __init__(self, tileset, type, layer, x, y, width, height, z, data=0):
        """
        Creates an object with specific data
        """
        # Specify the data value for each Item-containing block
        items = {16: 1, 17: 2, 18: 3, 19: 4, 20: 5, 21: 6, 22: 7, 23: 8,
                 24: 9, 25: 10, 26: 11, 27: 12, 28: data, 29: 14, 30: 15,
                 31: 16, 32: 17, 33: 18, 34: 19, 35: 20, 36: 21, 37: 22, 38: 23, 39: 24}

        self.tileset = tileset
        self.type = type
        self.original_type = type
        self.objx = x
        self.objy = y
        self.layer = layer
        self.width = width
        self.height = height

        if self.tileset == 0 and self.type in items:
            # Set the data value for
            # each Item-containing block.
            self.data = items[self.type]

            # Transform Item-containing blocks into
            # ? blocks with specific data values.

            # Technically, we don't even need to do this
            # but this is how Nintendo did it, so... ¯\_(ツ)_/¯
            self.type = 28

            # Nintendo didn't use value 0 for ?
            # blocks even though it's fully functional.
            # Let's use value 13, like them.
            if self.data == 0: self.data = 13

        else:
            # In NSMBU, you can transform *any* object
            # from *any* tileset into a brick/?/stone/etc.
            # block by changing its data value.
            # (from 0 to something else)

            # This was discovered by flzmx
            # and AboodXD by an accident.

            # The tiles' properties can also effect
            # what the object will turn into
            # when its data value is not 0.

            # Let's hardcode the object's data value to 0
            # to prevent funny stuff from happening ingame.
            if data > 0: SetDirty()
            self.data = 0


class ZoneItem:
    def __init__(self, a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, bounding=None, bg=None, id=None):
        """
        Creates a zone with specific data
        """
        self.objx = a
        self.objy = b
        self.width = c
        self.height = d
        self.modeldark = e
        self.terraindark = f
        self.id = g
        self.block3id = h
        self.cammode = i
        self.camzoom = j
        self.visibility = k
        self.block5id = l
        self.camtrack = m
        self.music = n
        self.sfxmod = o
        self.type = p

        if id is not None:
            self.id = id

        if bounding:
            self.yupperbound = bounding[0]
            self.ylowerbound = bounding[1]
            self.yupperbound2 = bounding[2]
            self.ylowerbound2 = bounding[3]
            self.entryid = bounding[4]
            self.unknownbnf = bounding[5]

        else:
            self.yupperbound = 0
            self.ylowerbound = 0
            self.yupperbound2 = 0
            self.ylowerbound2 = 0
            self.entryid = 0
            self.unknownbnf = 0

        if bg is not None:
            self.background = bg

        else:
            self.background = (0, 0, 0, 0, to_bytes('Black', 16), 0)

        self.ZoneRect = QRectF(self.objx, self.objy, self.width, self.height)


class LocationItem:
    def __init__(self, x, y, width, height, id):
        """
        Creates a location with specific data
        """
        self.objx = x
        self.objy = y
        self.width = width
        self.height = height
        self.id = id

    def __lt__(self, other):
        return self.id < other.id


class SpriteItem:
    def __init__(self, type, x, y, data, zoneID=0, layer=0, initialState=0):
        """
        Creates a sprite with specific data
        """
        self.type = type
        self.objx = x
        self.objy = y
        self.spritedata = data
        self.zoneID = zoneID
        self.layer = layer
        self.initialState = initialState

    def __lt__(self, other):
        # Sort by objx, then objy, then sprite type
        score = lambda sprite: (sprite.objx * 100000 + sprite.objy) * 1000 + sprite.type

        return score(self) < score(other)


class EntranceItem:
    def __init__(self, x, y, cameraX, cameraY, id, destarea, destentrance, type, players, zone, playerDistance, settings, otherID, coinOrder,
                 pathID, pathnodeindex, transition):
        """
        Creates an entrance with specific data
        """
        self.objx = x
        self.objy = y
        self.camerax = cameraX
        self.cameray = cameraY
        self.entid = id
        self.destarea = destarea
        self.destentrance = destentrance
        self.enttype = type
        self.players = players
        self.entzone = zone
        self.playerDistance = playerDistance
        self.entsettings = settings
        self.otherID = otherID
        self.coinOrder = coinOrder
        self.pathID = pathID
        self.pathnodeindex = pathnodeindex
        self.transition = transition

    def __lt__(self, other):
        return self.entid < other.entid
