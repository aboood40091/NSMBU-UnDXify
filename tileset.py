#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import struct

import bntx as BNTX
import gtx
import SarcLib

from yaz0 import determineCompressionMethod
_, DecompYaz0 = determineCompressionMethod()


TilesetPath = ''


class Tileset:
    def __init__(self):
        self.defs = None
        self.colldata = b''

        self.img = None
        self.nml = None
        self.hatena_anime = None
        self.block_anime = None
        self.hatena_anime_L = None
        self.block_anime_L = None
        self.tuka_coin_anime = None
        self.belt_conveyor_anime = None


class ObjectDef:
    """
    Class for the object definitions
    """

    def __init__(self):
        """
        Constructor
        """
        self.width = 0
        self.height = 0
        self.folderIndex = -1
        self.objAllIndex = -1
        self.randByte = 0
        self.reversed = False
        self.mainPartAt = -1
        self.subPartAt = -1
        self.rows = []
        self.data = 0

    def load(self, source, offset):
        """
        Load an object definition
        """
        source = source[offset:]

        if source[0] & 0x80 and source[0] & 2:
            self.reversed = True

        i = 0
        row = []
        cbyte = source[i]

        while i < len(source):
            cbyte = source[i]

            if cbyte == 0xFF:
                break

            elif cbyte == 0xFE:
                self.rows.append(row)
                i += 1
                row = []

            elif (cbyte & 0x80) != 0:
                if self.mainPartAt == -1:
                    self.mainPartAt = 0

                else:
                    self.subPartAt = len(self.rows)

                row.append((cbyte,))
                i += 1

            else:
                if i + 3 > len(source):
                    source += b'\0' * (i + 3 - len(source)) + b'\xfe\xff'

                extra = source[i + 2]
                tile = [cbyte, source[i + 1] | ((extra & 3) << 8), extra >> 2]
                row.append(tile)
                i += 3


def loadBNTXFromBFRES(inb):
    assert inb[:8] == b'FRES    '
    bom = ">" if inb[0xC:0xE] == b'\xFE\xFF' else "<"
    startoff = struct.unpack(bom + "q", inb[0x98:0xA0])[0]
    count = struct.unpack(bom + "q", inb[0xC8:0xD0])[0]

    if not count:
        raise RuntimeError("Tileset not found")

    else:
        # Not sure if this is correct, I hope it is.
        # If you face any problems, try replacing "0x20" with "0x10 * count".
        namesoff = struct.unpack(bom + "q", inb[0xA0:0xA8])[0] + 0x20

        for i in range(count):
            fileoff = struct.unpack(bom + "q", inb[startoff + i * 16:startoff + 8 + i * 16])[0]
            dataSize = struct.unpack(bom + "q", inb[startoff + 8 + i * 16:startoff + 16 + i * 16])[0]

            data = inb[fileoff:fileoff + dataSize]
            nameoff = struct.unpack(bom + "q", inb[namesoff + i * 16:namesoff + 8 + i * 16])[0]
            nameSize = struct.unpack(bom + 'H', inb[nameoff:nameoff + 2])[0]
            name = inb[nameoff + 2:nameoff + 2 + nameSize].decode('utf-8')

            if name == "textures.bntx":
                bntx = BNTX.File(); bntx.load(data, 0)
                break

        else:
            raise RuntimeError("Tileset not found")

    return bntx


def loadTexFromBNTX(bntx, name):
    for texture in bntx.textures:
        if name == texture.name:
            break

    else:
        raise RuntimeError("Tileset not found")

    # Assume RGBA8
    # I won't bother adding other formats cuz
    # RGBA8 is what OG NSMBUDX uses
    if texture.format_ in [0xb01, 0xb06] and texture.dim == 2:
        result, _, _ = bntx.rawData(texture)
        return [result[0], texture.width, texture.height, texture.compSel]

    raise RuntimeError("%s could not be loaded" % name)


def LoadTileset(idx, name):
    """
    Load in a tileset into a specific slot
    """

    if not name:
        return None

    global TilesetPath
    if not TilesetPath:
        TilesetPath = input('Enter the path to the "Unit" folder, e.g. "C:\\NSMBUDX\\romfs\\Unit": ')

    path = TilesetPath
    found = False

    if path:
        sarcname = os.path.join(os.path.dirname(path), 'Unit', name + '.szs')
        if os.path.isfile(sarcname):
            found = True

    if not found:
        raise RuntimeError("Tileset %s not found!" % name)

    # get the data
    with open(sarcname, 'rb') as fileobj:
        sarcdata = fileobj.read()

    if sarcdata[:4] != b'Yaz0':
        raise RuntimeError("Tileset is not Yaz0 compressed!")

    sarcdata = DecompYaz0(sarcdata)

    sarc = SarcLib.SARC_Archive()
    sarc.load(sarcdata)

    def exists(fn):
        nonlocal sarc

        try:
            sarc[fn]

        except KeyError:
            return False

        return True

    # Decompress the textures
    try:
        bfresdata = sarc['output.bfres'].data
        colldata = sarc['BG_chk/d_bgchk_%s.bin' % name].data

    except KeyError:
        raise RuntimeError("Looks like tileset is corrupted...")

    tileset = Tileset()

    # load in the textures
    bntx = loadBNTXFromBFRES(bfresdata)
    tileset.img = loadTexFromBNTX(bntx, name)
    tileset.nml = loadTexFromBNTX(bntx, name + "_nml")
    
    # Load the tileset animations, if there are any
    if idx == 0:
        tileoffset = idx * 256

        try:
            tileset.hatena_anime = loadTexFromBNTX(bntx, "hatena_anime")

        except:
            pass

        try:
            tileset.block_anime = loadTexFromBNTX(bntx, "block_anime")

        except:
            pass

        try:
            tileset.hatena_anime_L = loadTexFromBNTX(bntx, "hatena_anime_L")

        except:
            pass

        try:
            tileset.block_anime_L = loadTexFromBNTX(bntx, "block_anime_L")

        except:
            pass

        try:
            tileset.tuka_coin_anime = loadTexFromBNTX(bntx, "tuka_coin_anime")

        except:
            pass

        try:
            tileset.belt_conveyor_anime = loadTexFromBNTX(bntx, "belt_conveyor_anime")

        except:
            pass

    # Load the object definitions
    defs = [None] * 256

    indexfile = sarc['BG_unt/%s_hd.bin' % name].data
    deffile = sarc['BG_unt/%s.bin' % name].data
    objcount = len(indexfile) // 6
    indexstruct = struct.Struct('<HBBH')

    for i in range(objcount):
        data = indexstruct.unpack_from(indexfile, i * 6)
        obj = ObjectDef()
        obj.width = data[1]
        obj.height = data[2]
        obj.randByte = data[3]
        obj.load(deffile, data[0])
        defs[i] = obj

    tileset.defs = defs
    tileset.colldata = sarc['BG_chk/d_bgchk_%s.bin' % name].data

    return tileset


def writeGTX(data, width, height, compSel):
    """
    Generates a GTX file
    """
    toGX2CompSel = [4, 5, 0, 1, 2, 3]
    GX2CompSel = [toGX2CompSel[comp] for comp in compSel]

    gtxdata = gtx.fromData(data, width, height, GX2CompSel)
    return gtxdata


def SaveTileset(name, tilesetObj):
    """
    Saves a tileset from a specific slot
    """
    defs = tilesetObj.defs
    if defs is None:
        return False

    colldata = tilesetObj.colldata
    deffile = b''
    indexfile = b''

    for obj in defs:
        if obj is None:
            break

        indexfile += struct.pack('>HBBxB', len(deffile), obj.width, obj.height, obj.randByte)

        for row in obj.rows:
            for tile in row:
                if len(tile) == 3:
                    byte2 = tile[2] << 2
                    byte2 |= (tile[1] >> 8) & 3  # Slot

                    deffile += bytes([tile[0], tile[1] & 0xFF, byte2])

                else:
                    deffile += bytes(tile)

            deffile += b'\xFE'

        deffile += b'\xFF'

    arc = SarcLib.SARC_Archive()

    tex = SarcLib.Folder('BG_tex')
    arc.addFolder(tex)
    tex.addFile(SarcLib.File('%s.gtx' % name, writeGTX(*tilesetObj.img)))
    tex.addFile(SarcLib.File('%s_nml.gtx' % name, writeGTX(*tilesetObj.nml)))

    if tilesetObj.hatena_anime:
        tex.addFile(SarcLib.File('hatena_anime.gtx', writeGTX(*tilesetObj.hatena_anime)))

    if tilesetObj.block_anime:
        tex.addFile(SarcLib.File('block_anime.gtx', writeGTX(*tilesetObj.block_anime)))

    if tilesetObj.hatena_anime_L:
        tex.addFile(SarcLib.File('hatena_anime_L.gtx', writeGTX(*tilesetObj.hatena_anime_L)))

    if tilesetObj.block_anime_L:
        tex.addFile(SarcLib.File('block_anime_L.gtx', writeGTX(*tilesetObj.block_anime_L)))

    if tilesetObj.tuka_coin_anime:
        tex.addFile(SarcLib.File('tuka_coin_anime.gtx', writeGTX(*tilesetObj.tuka_coin_anime)))

    if tilesetObj.belt_conveyor_anime:
        tex.addFile(SarcLib.File('belt_conveyor_anime.gtx', writeGTX(*tilesetObj.belt_conveyor_anime)))

    chk = SarcLib.Folder('BG_chk')
    arc.addFolder(chk)
    chk.addFile(SarcLib.File('d_bgchk_%s.bin' % name, colldata))

    unt = SarcLib.Folder('BG_unt')
    arc.addFolder(unt)
    unt.addFile(SarcLib.File('%s.bin' % name, deffile))
    unt.addFile(SarcLib.File('%s_hd.bin' % name, indexfile))

    return arc.save()[0]
