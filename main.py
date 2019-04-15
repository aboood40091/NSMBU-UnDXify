#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# NSMBUDX to NSMBU Level Converter
# Copyright © 2018 AboodXD
# Licensed under GNU GPLv3

from NSMBU import Game

name = input('Enter level path, e.g. "e.g. "C:\\NSMBUDX\\romfs\\Course\\1-1.sarc": ')

game = Game()
game.LoadLevel(name)

with open(game.level.name + "_out.sarc", "wb") as out:
    out.write(game.level.save())
