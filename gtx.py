#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# gtx.py
# A small script for creating RGBA8 GTX files.


################################################################
################################################################

import struct

import addrlib
from bntx import round_up as roundUp
from texRegisters import makeRegsBytearray


class GFDHeader(struct.Struct):
    def __init__(self):
        super().__init__('>4s7I')

    def data(self, data, pos):
        (self.magic,
         self.size_,
         self.majorVersion,
         self.minorVersion,
         self.gpuVersion,
         self.alignMode,
         self.reserved1,
         self.reserved2) = self.unpack_from(data, pos)


class GFDBlockHeader(struct.Struct):
    def __init__(self):
        super().__init__('>4s7I')

    def data(self, data, pos):
        (self.magic,
         self.size_,
         self.majorVersion,
         self.minorVersion,
         self.type_,
         self.dataSize,
         self.id,
         self.typeIdx) = self.unpack_from(data, pos)


class GX2Surface(struct.Struct):
    def __init__(self):
        super().__init__('>16I')

    def data(self, data, pos):
        (self.dim,
         self.width,
         self.height,
         self.depth,
         self.numMips,
         self.format_,
         self.aa,
         self.use,
         self.imageSize,
         self.imagePtr,
         self.mipSize,
         self.mipPtr,
         self.tileMode,
         self.swizzle,
         self.alignment,
         self.pitch) = self.unpack_from(data, pos)


def getAlignBlockSize(dataOffset, alignment):
    alignSize = roundUp(dataOffset, alignment) - dataOffset - 32

    z = 1
    while alignSize < 0:
        alignSize = roundUp(dataOffset + (alignment * z), alignment) - dataOffset - 32
        z += 1

    return alignSize


def writeGFD(data, width, height, compSel):
    imageData = bytes(data)

    surfOut = addrlib.getSurfaceInfo(0x1a, width, height, 1, 1, 4, 0, 0)
    alignment = surfOut.baseAlign
    imageSize = surfOut.surfSize
    pitch = surfOut.pitch

    imageData += b'\0' * (surfOut.surfSize - len(data))
    result = addrlib.swizzle(
        width, height, 1, 0x1a, 0, 1, surfOut.tileMode,
        0, surfOut.pitch, surfOut.bpp, 0, 0, imageData,
    )

    s = 13 << 16

    block_head_struct = GFDBlockHeader()
    gx2surf_blk_head = block_head_struct.pack(b"BLK{", 32, 1, 0, 0xb, 0x9c, 0, 0)

    gx2surf_struct = GX2Surface()
    gx2surf = gx2surf_struct.pack(1, width, height, 1, 1, 0x1a, 0, 1, imageSize, 0, 0, 0, 4, s, alignment, pitch)

    image_blk_head = block_head_struct.pack(b"BLK{", 32, 1, 0, 0xc, imageSize, 0, 0)
    output = gx2surf_blk_head + gx2surf
    output += b'\0' * 56

    output += 1 .to_bytes(4, 'big')
    output += b'\0' * 4
    output += 1 .to_bytes(4, 'big')

    for value in compSel:
        output += value.to_bytes(1, 'big')

    output += makeRegsBytearray(width, height, 1, 0x1a, 4, pitch, compSel)

    alignSize = getAlignBlockSize(len(output) + 64, alignment)
    align_blk_head = block_head_struct.pack(b"BLK{", 32, 1, 0, 2, alignSize, 0, 0)

    output += align_blk_head
    output += b'\0' * alignSize
    output += image_blk_head
    output += result

    return output


def fromData(data, width, height, compSel):
    head_struct = GFDHeader()
    head = head_struct.pack(b"Gfx2", 32, 7, 1, 2, 1, 0, 0)

    outData = b''.join([head, writeGFD(data, width, height, compSel)])

    block_head_struct = GFDBlockHeader()
    eof_blk_head = block_head_struct.pack(b"BLK{", 32, 1, 0, 1, 0, 0, 0)

    outData += eof_blk_head

    return outData
