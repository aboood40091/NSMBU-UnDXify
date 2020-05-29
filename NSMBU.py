#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# hi skawo

from items import ObjectItem, ZoneItem, LocationItem, SpriteItem, EntranceItem
import os.path
import SarcLib
import struct

from tileset import LoadTileset, SaveTileset


def bytes_to_string(data, offset=0, charWidth=1, encoding='utf-8'):
    # Thanks RoadrunnerWMC
    end = data.find(b'\0' * charWidth, offset)
    if end == -1:
        return data[offset:].decode(encoding)

    return data[offset:end].decode(encoding)


def to_bytes(inp, length=1, endianness='big'):
    if isinstance(inp, bytearray):
        return bytes(inp)

    elif isinstance(inp, int):
        return inp.to_bytes(length, endianness)

    elif isinstance(inp, str):
        return inp.encode('utf-8').ljust(length, b'\0')

def exists(arc, fn):
    try:
        arc[fn]

    except KeyError:
        return False

    return True


def checkContent(data):
    if not data.startswith(b'SARC'):
        return False

    required = (b'course/', b'course1.bin')
    for r in required:
        if r not in data:
            return False

    return True


def IsNSMBLevel(filename):
    """
    Does some basic checks to confirm a file is a NSMB level
    """
    if not os.path.isfile(filename): return False

    with open(filename, 'rb') as f:
        data = f.read()

    return checkContent(data)


class Metadata:
    """
    Class for the new level metadata system
    """

    # This new system is much more useful and flexible than the old
    # system, but is incompatible with older versions of Reggie.
    # They will fail to understand the data, and skip it like it
    # doesn't exist. The new system is written with forward-compatibility
    # in mind. Thus, when newer versions of Reggie are created
    # with new metadata values, they will be easily able to add to
    # the existing ones. In addition, the metadata system is lossless,
    # so unrecognized values will be preserved when you open and save.

    # Type values:
    # 0 = binary
    # 1 = string
    # 2+ = undefined as of now - future Reggies can use them
    # Theoretical limit to type values is 4,294,967,296

    def __init__(self, data=None):
        """
        Creates a metadata object with the data given
        """
        self.DataDict = {}
        if data is None: return

        if data[0:4] != b'MD2_':
            # This is old-style metadata - convert it
            try:
                strdata = ''
                for d in data: strdata += chr(d)
                level_info = pickle.loads(strdata)
                for k, v in level_info.iteritems():
                    self.setStrData(k, v)
            except Exception:
                pass
            if ('Website' not in self.DataDict) and ('Webpage' in self.DataDict):
                self.DataDict['Website'] = self.DataDict['Webpage']
            return

        # Iterate through the data
        idx = 4
        while idx < len(data) - 4:

            # Read the next (first) four bytes - the key length
            rawKeyLen = data[idx:idx + 4]
            idx += 4

            keyLen = (rawKeyLen[0] << 24) | (rawKeyLen[1] << 16) | (rawKeyLen[2] << 8) | rawKeyLen[3]

            # Read the next (key length) bytes - the key (as a str)
            rawKey = data[idx:idx + keyLen]
            idx += keyLen

            key = ''
            for b in rawKey: key += chr(b)

            # Read the next four bytes - the number of type entries
            rawTypeEntries = data[idx:idx + 4]
            idx += 4

            typeEntries = (rawTypeEntries[0] << 24) | (rawTypeEntries[1] << 16) | (rawTypeEntries[2] << 8) | \
                          rawTypeEntries[3]

            # Iterate through each type entry
            for entry in range(typeEntries):
                # Read the next four bytes - the type
                rawType = data[idx:idx + 4]
                idx += 4

                type = (rawType[0] << 24) | (rawType[1] << 16) | (rawType[2] << 8) | rawType[3]

                # Read the next four bytes - the data length
                rawDataLen = data[idx:idx + 4]
                idx += 4

                dataLen = (rawDataLen[0] << 24) | (rawDataLen[1] << 16) | (rawDataLen[2] << 8) | rawDataLen[3]

                # Read the next (data length) bytes - the data (as bytes)
                entryData = data[idx:idx + dataLen]
                idx += dataLen

                # Add it to typeData
                self.setOtherData(key, type, entryData)

    def binData(self, key):
        """
        Returns the binary data associated with key
        """
        return self.otherData(key, 0)

    def strData(self, key):
        """
        Returns the string data associated with key
        """
        data = self.otherData(key, 1)
        if data is None: return
        s = ''
        for d in data: s += chr(d)
        return s

    def otherData(self, key, type):
        """
        Returns unknown data, with the given type value, associated with key (as binary data)
        """
        if key not in self.DataDict: return
        if type not in self.DataDict[key]: return
        return self.DataDict[key][type]

    def setBinData(self, key, value):
        """
        Sets binary data, overwriting any existing binary data with that key
        """
        self.setOtherData(key, 0, value)

    def setStrData(self, key, value):
        """
        Sets string data, overwriting any existing string data with that key
        """
        data = []
        for char in value: data.append(ord(char))
        self.setOtherData(key, 1, data)

    def setOtherData(self, key, type, value):
        """
        Sets other (binary) data, overwriting any existing data with that key and type
        """
        if key not in self.DataDict: self.DataDict[key] = {}
        self.DataDict[key][type] = value

    def save(self):
        """
        Returns a bytes object that can later be loaded from
        """

        # Sort self.DataDict
        dataDictSorted = []
        for dataKey in self.DataDict: dataDictSorted.append((dataKey, self.DataDict[dataKey]))
        dataDictSorted.sort(key=lambda entry: entry[0])

        data = []

        # Add 'MD2_'
        data.append(ord('M'))
        data.append(ord('D'))
        data.append(ord('2'))
        data.append(ord('_'))

        # Iterate through self.DataDict
        for dataKey, types in dataDictSorted:

            # Add the key length (4 bytes)
            keyLen = len(dataKey)
            data.append(keyLen >> 24)
            data.append((keyLen >> 16) & 0xFF)
            data.append((keyLen >> 8) & 0xFF)
            data.append(keyLen & 0xFF)

            # Add the key (key length bytes)
            for char in dataKey: data.append(ord(char))

            # Sort the types
            typesSorted = []
            for type in types: typesSorted.append((type, types[type]))
            typesSorted.sort(key=lambda entry: entry[0])

            # Add the number of types (4 bytes)
            typeNum = len(typesSorted)
            data.append(typeNum >> 24)
            data.append((typeNum >> 16) & 0xFF)
            data.append((typeNum >> 8) & 0xFF)
            data.append(typeNum & 0xFF)

            # Iterate through typesSorted
            for type, typeData in typesSorted:

                # Add the type (4 bytes)
                data.append(type >> 24)
                data.append((type >> 16) & 0xFF)
                data.append((type >> 8) & 0xFF)
                data.append(type & 0xFF)

                # Add the data length (4 bytes)
                dataLen = len(typeData)
                data.append(dataLen >> 24)
                data.append((dataLen >> 16) & 0xFF)
                data.append((dataLen >> 8) & 0xFF)
                data.append(dataLen & 0xFF)

                # Add the data (data length bytes)
                for d in typeData: data.append(d)

        return data


class Game:
    class Level:
        """
        Class for a level from New Super Mario Bros. U
        """

        def __init__(self, name):
            """
            Initializes the level with default settings
            """
            self.name = name
            self.areas = []

        class Area:
            """
            Class for a parsed NSMBU level area
            """

            def __init__(self):
                """
                Creates a completely new NSMBW area
                """
                # Default area number
                self.areanum = 1

                # Default tileset names for NSMBU
                self.tileset0 = 'Pa0_jyotyu'
                self.tileset1 = ''
                self.tileset2 = ''
                self.tileset3 = ''

                self.blocks = [b''] * 15
                self.blocks[4] = (to_bytes(0, 8) + to_bytes(0x426C61636B, 5)
                                  + to_bytes(0, 15))

                # Settings
                self.eventBits32 = 0
                self.eventBits64 = 0
                self.wrapFlag = False
                self.unkFlag1 = False
                self.timelimit = 400
                self.unkFlag2 = True
                self.unkFlag3 = True
                self.unkFlag4 = True
                self.startEntrance = 0
                self.startEntranceCoinBoost = 0
                self.timelimit2 = 300
                self.timelimit3 = 0

                # Lists of things
                self.entrances = []
                self.sprites = []
                self.bounding = []
                self.zones = []
                self.locations = []
                self.pathdata = []
                self.layers = [[], [], []]

                # Metadata
                self.LoadMiyamotoInfo(None)

                # BG data
                self.bgs = {}
                bg = struct.unpack('<HHHH16sxBxx', self.blocks[4])
                self.bgs[bg[0]] = bg

            def load(self, course, L0, L1, L2, progress=None):
                """
                Loads an area from the archive files
                """

                # Load in the course file and blocks
                self.LoadBlocks(course)

                # Load stuff from individual blocks
                self.LoadTilesetNames()  # block 1
                self.LoadOptions()  # block 2
                self.LoadEntrances()  # block 7
                self.LoadSprites()  # block 8
                self.LoadZones()  # blocks 10, 3, and 5
                self.LoadLocations()  # block 11
                self.LoadPaths()  # block 14 and 15

                # Load the editor metadata
                if self.block1pos[0] != 0x78:
                    rddata = course[0x78:self.block1pos[0]]
                    self.LoadMiyamotoInfo(rddata)

                else:
                    self.LoadMiyamotoInfo(None)

                del self.block1pos

                # Load the object layers
                self.layers = [[], [], []]

                if L0 is not None:
                    self.LoadLayer(0, L0)
                if L1 is not None:
                    self.LoadLayer(1, L1)
                if L2 is not None:
                    self.LoadLayer(2, L2)

                return True

            def LoadBlocks(self, course):
                """
                Loads self.blocks from the course file
                """
                self.blocks = [None] * 15
                getblock = struct.Struct('<II')
                for i in range(15):
                    data = getblock.unpack_from(course, i * 8)
                    if data[1] == 0:
                        self.blocks[i] = b''
                    else:
                        self.blocks[i] = course[data[0]:data[0] + data[1]]

                self.block1pos = getblock.unpack_from(course, 0)

            def LoadTilesetNames(self):
                """
                Loads block 1, the tileset names
                """
                data = struct.unpack_from('32s32s32s32s', self.blocks[0])
                self.tileset0 = bytes_to_string(data[0])
                self.tileset1 = bytes_to_string(data[1])
                self.tileset2 = bytes_to_string(data[2])
                self.tileset3 = bytes_to_string(data[3])

                self.tileset0Obj = LoadTileset(0, self.tileset0)
                self.tileset1Obj = LoadTileset(1, self.tileset1)
                self.tileset2Obj = LoadTileset(2, self.tileset2)
                self.tileset3Obj = LoadTileset(3, self.tileset3)

            def LoadBackgrounds(self):
                """
                Loads block 5, the background data
                """
                bgData = self.blocks[4]
                bgCount = len(bgData) // 28

                bgStruct = struct.Struct('<HHHH16sxBxx')
                offset = 0

                bgs = {}
                for i in range(bgCount):
                    bg = bgStruct.unpack_from(bgData, offset)
                    bgs[bg[0]] = bg

                    offset += 28

                return bgs

            def LoadSprites(self):
                """
                Loads block 8, the sprites
                """
                spritedata = self.blocks[7]
                sprcount = len(spritedata) // 24
                sprstruct = struct.Struct('<HHHHIIBB2sBxxx')
                offset = 0
                sprites = []

                unpack = sprstruct.unpack_from
                append = sprites.append
                obj = SpriteItem
                for i in range(sprcount):
                    data = unpack(spritedata, offset)
                    append(obj(data[0], data[1], data[2], to_bytes(data[3], 2) + to_bytes(data[4], 4) + to_bytes(data[5], 4) + data[8], data[6], data[7], data[9]))
                    offset += 24
                self.sprites = sprites

            def save(self):
                """
                Save the area back to a file
                """
                # We don't parse blocks 4, 6, 12, 13
                # Save the other blocks
                self.SaveTilesetNames()  # block 1
                self.SaveOptions()  # block 2
                self.SaveEntrances()  # block 7
                self.SaveSprites()  # block 8
                self.SaveLoadedSprites()  # block 9
                self.SaveZones()  # blocks 10, 3, and 5
                self.SaveLocations()  # block 11
                self.SavePaths()  # blocks 14 and 15

                # Save the metadata
                rdata = bytearray(self.Metadata.save())
                if len(rdata) % 4 != 0:
                    for i in range(4 - (len(rdata) % 4)):
                        rdata.append(0)
                rdata = bytes(rdata)
                if rdata == b'MD2_':
                    rdata = b''

                # Save the main course file
                # We'll be passing over the blocks array two times.
                # Using bytearray here because it offers mutable bytes
                # and works directly with struct.pack_into(), so it's a
                # win-win situation
                FileLength = (15 * 8) + len(rdata)
                for block in self.blocks:
                    FileLength += len(block)

                course = bytearray()
                for i in range(FileLength): course.append(0)
                saveblock = struct.Struct('>II')

                HeaderOffset = 0
                FileOffset = (15 * 8) + len(rdata)
                struct.pack_into('{0}s'.format(len(rdata)), course, 0x78, rdata)
                for block in self.blocks:
                    blocksize = len(block)
                    saveblock.pack_into(course, HeaderOffset, FileOffset, blocksize)
                    if blocksize > 0:
                        course[FileOffset:FileOffset + blocksize] = block
                    HeaderOffset += 8
                    FileOffset += blocksize

                # Return stuff
                return (
                    bytes(course),
                    self.SaveLayer(0),
                    self.SaveLayer(1),
                    self.SaveLayer(2),
                )

            def LoadMiyamotoInfo(self, data):
                if (data is None) or (len(data) == 0):
                    self.Metadata = Metadata()
                    return

                try:
                    self.Metadata = Metadata(data)
                except Exception:
                    self.Metadata = Metadata()  # fallback

            def LoadOptions(self):
                """
                Loads block 2, the general options
                """
                optdata = self.blocks[1]
                optstruct = struct.Struct('<IIHHxBBBBxxBHH')
                offset = 0
                data = optstruct.unpack_from(optdata, offset)
                self.eventBits32, self.eventBits64, wrapByte, self.timelimit, unk1, unk2, unk3, self.startEntrance, self.startEntranceCoinBoost, self.timelimit2, self.timelimit3 = data
                self.wrapFlag = bool(wrapByte & 1)
                self.unkFlag1 = bool(wrapByte >> 3)
                self.unkFlag2 = bool(unk1 == 100)
                self.unkFlag3 = bool(unk2 == 100)
                self.unkFlag4 = bool(unk3 == 100)

            def LoadEntrances(self):
                """
                Loads block 7, the entrances
                """
                entdata = self.blocks[6]
                entcount = len(entdata) // 24
                entstruct = struct.Struct('<HHhhBBBBBBxBHBBBBBx')
                offset = 0
                entrances = []
                for i in range(entcount):
                    data = entstruct.unpack_from(entdata, offset)
                    entrances.append(EntranceItem(*data))
                    offset += 24
                self.entrances = entrances

            def LoadZones(self):
                """
                Loads blocks 3, 5 and 10 - the bounding, background and zone data
                """

                # Block 3 - bounding data
                bdngdata = self.blocks[2]
                count = len(bdngdata) // 28
                bdngstruct = struct.Struct('<llllHHxxxxxxxx')
                offset = 0
                bounding = []
                for i in range(count):
                    datab = bdngstruct.unpack_from(bdngdata, offset)
                    bounding.append([datab[0], datab[1], datab[2], datab[3], datab[4], datab[5]])
                    offset += 28
                self.bounding = bounding

                # Block 5 - Bg data
                self.bgs = self.LoadBackgrounds()

                # Block 10 - zone data
                zonedata = self.blocks[9]
                zonestruct = struct.Struct('<HHHHHHBBBBxBBxBxBBxBxx')
                count = len(zonedata) // 28
                offset = 0
                zones = []
                for i in range(count):
                    dataz = zonestruct.unpack_from(zonedata, offset)

                    # Find the proper bounding
                    boundObj = None
                    zoneBoundId = dataz[7]
                    for checkb in self.bounding:
                        if checkb[4] == zoneBoundId: boundObj = checkb

                    # Find the proper bg
                    try:
                        bgObj = self.bgs[dataz[11]]

                    except KeyError:
                        print("Warning!!! Zone %d has an invalid BG block!" % dataz[6])
                        bgObj = None

                    zones.append(ZoneItem(
                        dataz[0], dataz[1], dataz[2], dataz[3],
                        dataz[4], dataz[5], dataz[6], dataz[7],
                        dataz[8], dataz[9], dataz[10], dataz[11],
                        dataz[12], dataz[13], dataz[14], dataz[15],
                        boundObj, bgObj, i))
                    offset += 28
                self.zones = zones

            def LoadLocations(self):
                """
                Loads block 11, the locations
                """
                locdata = self.blocks[10]
                locstruct = struct.Struct('<HHHHBxxx')
                count = len(locdata) // 12
                offset = 0
                locations = []
                for i in range(count):
                    data = locstruct.unpack_from(locdata, offset)
                    locations.append(LocationItem(data[0], data[1], data[2], data[3], data[4]))
                    offset += 12
                self.locations = locations

            def LoadLayer(self, idx, layerdata):
                """
                Loads a specific object layer from a bytes object
                """
                objcount = len(layerdata) // 16
                objstruct = struct.Struct('<HhhHHB')
                offset = 0
                z = (2 - idx) * 8192

                layer = self.layers[idx]
                append = layer.append
                unpack = objstruct.unpack_from
                for i in range(objcount):
                    data = unpack(layerdata, offset)
                    # Just for clarity, assigning these things to variables explaining what they are
                    tileset = (data[0] >> 12) & 3
                    type = data[0] & 255
                    layer = idx
                    x = data[1]
                    y = data[2]
                    width = data[3]
                    height = data[4]
                    z = z
                    objdata = data[5]
                    append(ObjectItem(tileset, type, layer, x, y, width, height, z, objdata))
                    z += 1
                    offset += 16

            def LoadPaths(self):
                """
                Loads blocks 14 and 15, the paths
                """
                pathdata = self.blocks[13]
                pathcount = len(pathdata) // 12
                pathstruct = struct.Struct('<BbHHHxxxx')  # updated struct -- MrRean
                offset = 0
                unpack = pathstruct.unpack_from
                pathinfo = []
                for i in range(pathcount):
                    data = unpack(pathdata, offset)

                    nodes = self.LoadPathNodes(data[2], data[3])
                    add2p = {'id': int(data[0]),
                             'unk1': int(data[1]),  # no idea what this is
                             'nodes': [node for node in nodes],
                             'loops': data[4] == 2,
                             }
                    pathinfo.append(add2p)

                    offset += 12

                self.pathdata = pathinfo

            def LoadPathNodes(self, startindex, count):
                """
                Loads block 15, the path nodes
                """
                ret = []
                nodedata = self.blocks[14]
                nodestruct = struct.Struct('<HHffhHBBBx')
                offset = startindex * 20
                unpack = nodestruct.unpack_from
                for i in range(count):
                    data = unpack(nodedata, offset)
                    ret.append({'x': int(data[0]),
                                'y': int(data[1]),
                                'speed': float(data[2]),
                                'accel': float(data[3]),
                                'delay': int(data[4]),
                                'unk1': int(data[5]),
                                'unk2': int(data[6]),
                                'unk3': int(data[7]),
                                'unk4': int(data[8]),
                                })
                    offset += 20
                return ret

            def SaveTilesetNames(self):
                """
                Saves the tileset names back to block 1
                """
                self.blocks[0] = ''.join(
                    [self.tileset0.ljust(32, '\0'), self.tileset1.ljust(32, '\0'), self.tileset2.ljust(32, '\0'),
                     self.tileset3.ljust(32, '\0')]).encode('utf-8')

            def SaveOptions(self):
                """
                Saves block 2, the general options
                """
                wrapByte = 1 if self.wrapFlag else 0
                if self.unkFlag1: wrapByte |= 8
                unk1 = 100 if self.unkFlag2 else 0
                unk2 = 100 if self.unkFlag3 else 0
                unk3 = 100 if self.unkFlag4 else 0

                optstruct = struct.Struct('>IIHHxBBBBxxBHH')
                buffer = bytearray(0x18)
                optstruct.pack_into(buffer, 0, self.eventBits32, self.eventBits64, wrapByte, self.timelimit,
                                    unk1, unk2, unk3, self.startEntrance, self.startEntranceCoinBoost, self.timelimit2, self.timelimit3)
                self.blocks[1] = bytes(buffer)

            def SaveLayer(self, idx):
                """
                Saves an object layer to a bytes object
                """
                layer = self.layers[idx]
                if not layer: return None

                offset = 0
                objstruct = struct.Struct('>HhhHHB')
                buffer = bytearray((len(layer) * 16) + 2)
                f_int = int
                for obj in layer:
                    objstruct.pack_into(buffer,
                                        offset,
                                        f_int((obj.tileset << 12) | obj.type),
                                        f_int(obj.objx),
                                        f_int(obj.objy),
                                        f_int(obj.width),
                                        f_int(obj.height),
                                        f_int(obj.data))
                    offset += 16
                buffer[offset] = 0xFF
                buffer[offset + 1] = 0xFF
                return bytes(buffer)

            def SaveEntrances(self):
                """
                Saves the entrances back to block 7
                """
                offset = 0
                entstruct = struct.Struct('>HHhhBBBBBBxBHBBBBBx')
                buffer = bytearray(len(self.entrances) * 24)
                zonelist = self.zones
                for entrance in self.entrances:
                    entstruct.pack_into(buffer, offset, int(entrance.objx), int(entrance.objy), int(entrance.camerax),
                                        int(entrance.cameray), int(entrance.entid), int(entrance.destarea), int(entrance.destentrance),
                                        int(entrance.enttype), int(entrance.players), int(entrance.entzone), int(entrance.playerDistance),
                                        int(entrance.entsettings), int(entrance.otherID), int(entrance.coinOrder),
                                        int(entrance.pathID), int(entrance.pathnodeindex), int(entrance.transition))
                    offset += 24
                self.blocks[6] = bytes(buffer)

            def SavePaths(self):
                """
                Saves the paths back to block 14 and 15
                """
                pathstruct = struct.Struct('>BbHHHxxxx')
                nodecount = 0
                for path in self.pathdata:
                    nodecount += len(path['nodes'])
                nodebuffer = bytearray(nodecount * 20)
                nodeoffset = 0
                nodeindex = 0
                offset = 0
                pathcount = len(self.pathdata)
                buffer = bytearray(pathcount * 12)

                for path in self.pathdata:
                    if len(path['nodes']) < 1: continue

                    self.WritePathNodes(nodebuffer, nodeoffset, path['nodes'])

                    pathstruct.pack_into(buffer, offset, int(path['id']), 0, int(nodeindex), int(len(path['nodes'])),
                                         2 if path['loops'] else 0)
                    offset += 12
                    nodeoffset += len(path['nodes']) * 20
                    nodeindex += len(path['nodes'])

                self.blocks[13] = bytes(buffer)
                self.blocks[14] = bytes(nodebuffer)

            def WritePathNodes(self, buffer, offst, nodes):
                """
                Writes the path node data to the block 15 bytearray
                """
                offset = int(offst)

                nodestruct = struct.Struct('>HHffhHBBBx')
                for node in nodes:
                    nodestruct.pack_into(buffer, offset, int(node['x']), int(node['y']), float(node['speed']),
                                         float(node['accel']), int(node['delay']), int(node['unk1']), int(node['unk2']),
                                         int(node['unk3']), int(node['unk4']))
                    offset += 20

            def SaveSprites(self):
                """
                Saves the sprites back to block 8
                """
                offset = 0
                sprstruct = struct.Struct('>HHHHIIBB2sBxxx')
                buffer = bytearray((len(self.sprites) * 24) + 4)
                f_int = int
                for sprite in self.sprites:
                    sprstruct.pack_into(buffer, offset, f_int(sprite.type), f_int(sprite.objx), f_int(sprite.objy),
                                        struct.unpack(">H", sprite.spritedata[:2])[0], struct.unpack(">I", sprite.spritedata[2:6])[0], struct.unpack(">I", sprite.spritedata[6:10])[0],
                                        sprite.zoneID,
                                        sprite.layer, sprite.spritedata[10:], sprite.initialState)
                    offset += 24
                buffer[offset] = 0xFF
                buffer[offset + 1] = 0xFF
                buffer[offset + 2] = 0xFF
                buffer[offset + 3] = 0xFF
                self.blocks[7] = bytes(buffer)

            def SaveLoadedSprites(self):
                """
                Saves the list of loaded sprites back to block 9
                """
                ls = []
                for sprite in self.sprites:
                    if sprite.type not in ls: ls.append(sprite.type)
                ls.sort()

                offset = 0
                sprstruct = struct.Struct('>Hxx')
                buffer = bytearray(len(ls) * 4)
                for s in ls:
                    sprstruct.pack_into(buffer, offset, int(s))
                    offset += 4
                self.blocks[8] = bytes(buffer)

            def SaveZones(self):
                """
                Saves blocks 10, 3, and 5; the zone data, boundings, and background data respectively
                """
                bdngstruct = struct.Struct('>llllHHxxxxxxxx')
                bgStruct = struct.Struct('>HHHH16sxBxx')
                zonestruct = struct.Struct('>HHHHHHBBBBxBBxBxBBxBxx')
                offset = 0
                bdngs, bdngcount = self.GetOptimizedBoundings()
                bgs, bgcount = self.GetOptimizedBGs()
                zcount = len(self.zones)
                buffer2 = bytearray(28 * bdngcount)
                buffer4 = bytearray(28 * bgcount)
                buffer9 = bytearray(28 * zcount)
                for z in self.zones:
                    if z.objx < 0: z.objx = 0
                    if z.objy < 0: z.objy = 0
                    bounding = bdngs[z.id]
                    bdngstruct.pack_into(buffer2, bounding[4] * 28, bounding[0], bounding[1], bounding[2], bounding[3], bounding[4],
                                         bounding[5])
                    background = bgs[z.id]
                    bgStruct.pack_into(buffer4, background[0] * 28, background[0], background[1], background[2], background[3],
                                       background[4], background[5])
                    zonestruct.pack_into(buffer9, offset,
                                         z.objx, z.objy, z.width, z.height,
                                         0, 0, z.id, bounding[4],
                                         z.cammode, z.camzoom, z.visibility, background[0],
                                         z.camtrack, z.music, z.sfxmod, z.type)
                    offset += 28

                self.blocks[2] = bytes(buffer2)
                self.blocks[4] = bytes(buffer4)
                self.blocks[9] = bytes(buffer9)

            def GetOptimizedBoundings(self):
                bdngs = {}
                bdngstruct = struct.Struct('>llllHHxxxxxxxx')
                for z in self.zones:
                    bdng = bdngstruct.pack(z.yupperbound, z.ylowerbound, z.yupperbound2, z.ylowerbound2, 0, z.unknownbnf)
                    if bdng not in bdngs:
                        bdngs[bdng] = []
                    bdngs[bdng].append(z.id)
                bdngs = sorted(bdngs.items(), key=lambda kv: min(kv[1]))
                oBdngs = {}
                for i, bdng in enumerate(bdngs):
                    for z in self.zones:
                        if z.id in bdng[1]:
                            oBdngs[z.id] = *bdngstruct.unpack(bdng[0])[:4], i, bdngstruct.unpack(bdng[0])[5]

                return oBdngs, len(bdngs)

            def GetOptimizedBGs(self):
                bgs = {}
                bgStruct = struct.Struct('>HHHH16sxBxx')
                for z in self.zones:
                    bg = bgStruct.pack(0, z.background[1], z.background[2], z.background[3], z.background[4], z.background[5])
                    if bg not in bgs:
                        bgs[bg] = []
                    bgs[bg].append(z.id)
                bgs = sorted(bgs.items(), key=lambda kv: min(kv[1]))
                oBgs = {}
                for i, bg in enumerate(bgs):
                    for z in self.zones:
                        if z.id in bg[1]:
                            oBgs[z.id] = i, *bgStruct.unpack(bg[0])[1:]

                return oBgs, len(bgs)

            def SaveLocations(self):
                """
                Saves block 11, the location data
                """
                locstruct = struct.Struct('>HHHHBxxx')
                offset = 0
                zcount = len(self.locations)
                buffer = bytearray(12 * zcount)

                for z in self.locations:
                    locstruct.pack_into(buffer, offset, int(z.objx), int(z.objy), int(z.width), int(z.height), int(z.id))
                    offset += 12

                self.blocks[10] = bytes(buffer)

        def load(self, data):
            """
            Loads a NSMBU level from bytes data.
            """
            arc = SarcLib.SARC_Archive()
            arc.load(data)

            try:
                courseFolder = arc['course']
            except:
                return False

            # Sort the area data
            areaData = {}
            for file in courseFolder.contents:
                name, val = file.name, file.data

                if val is None: continue

                if not name.startswith('course'): continue
                if not name.endswith('.bin'): continue
                if '_bgdatL' in name:
                    # It's a layer file
                    if len(name) != 19: continue
                    try:
                        thisArea = int(name[6])
                        laynum = int(name[14])
                    except ValueError:
                        continue
                    if not (0 < thisArea < 5): continue

                    if thisArea not in areaData: areaData[thisArea] = [None] * 4
                    areaData[thisArea][laynum + 1] = val
                else:
                    # It's the course file
                    if len(name) != 11: continue
                    try:
                        thisArea = int(name[6])
                    except ValueError:
                        continue
                    if not (0 < thisArea < 5): continue

                    if thisArea not in areaData: areaData[thisArea] = [None] * 4
                    areaData[thisArea][0] = val

            # Create area objects
            self.areas = []
            thisArea = 1
            while thisArea in areaData:
                course = areaData[thisArea][0]
                L0 = areaData[thisArea][1]
                L1 = areaData[thisArea][2]
                L2 = areaData[thisArea][3]

                print("Processing Area %d..." % thisArea)

                newarea = self.Area()
                newarea.areanum = thisArea
                newarea.load(course, L0, L1, L2)

                self.areas.append(newarea)

                thisArea += 1

            return True

        def save(self):
            """
            Save the level back to a file
            """

            # Make a new archive
            newArchive = SarcLib.SARC_Archive()

            # Create a folder within the archive
            courseFolder = SarcLib.Folder('course')
            newArchive.addFolder(courseFolder)

            outerArchive = SarcLib.SARC_Archive()

            # Go through the areas, save them and add them back to the archive
            for areanum, area in enumerate(self.areas):
                course, L0, L1, L2 = area.save()

                if course is not None:
                    courseFolder.addFile(SarcLib.File('course%d.bin' % (areanum + 1), course))
                if L0 is not None:
                    courseFolder.addFile(SarcLib.File('course%d_bgdatL0.bin' % (areanum + 1), L0))
                if L1 is not None:
                    courseFolder.addFile(SarcLib.File('course%d_bgdatL1.bin' % (areanum + 1), L1))
                if L2 is not None:
                    courseFolder.addFile(SarcLib.File('course%d_bgdatL2.bin' % (areanum + 1), L2))

                # I need to kick in tileset saving here
                if area.tileset0 and area.tileset0Obj and not exists(outerArchive, area.tileset0):
                    outerArchive.addFile(SarcLib.File(area.tileset0, SaveTileset(area.tileset0, area.tileset0Obj)))

                if area.tileset1 and area.tileset1Obj and not exists(outerArchive, area.tileset1):
                    outerArchive.addFile(SarcLib.File(area.tileset1, SaveTileset(area.tileset1, area.tileset1Obj)))

                if area.tileset2 and area.tileset2Obj and not exists(outerArchive, area.tileset2):
                    outerArchive.addFile(SarcLib.File(area.tileset2, SaveTileset(area.tileset2, area.tileset2Obj)))

                if area.tileset3 and area.tileset3Obj and not exists(outerArchive, area.tileset3):
                    outerArchive.addFile(SarcLib.File(area.tileset3, SaveTileset(area.tileset3, area.tileset3Obj)))

            outerArchive.addFile(SarcLib.File(self.name, newArchive.save()[0]))

            return outerArchive.save()[0]

    def LoadLevel(self, name):
        if not os.path.isfile(name):
            return False

        if not IsNSMBLevel(name):
            return False

        # Open the file
        with open(name, 'rb') as fileobj:
            levelData = fileobj.read()

        if not levelData.startswith(b'SARC'):
            return False  # keep it from crashing by loading things it shouldn't

        levelName = os.path.basename(os.path.splitext(name)[0])

        # Load the actual level
        # Create the new level object
        self.level = self.Level(levelName)

        # Load it
        if not self.level.load(levelData):
            raise Exception

        # If we got this far, everything worked! Return True.
        return True
