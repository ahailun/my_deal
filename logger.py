#!/usr/bin/python
# -*- coding: utf8 -*-

import time, logging
from tkinter import END

class Logger:
    def __init__(self, listbox=None, logfile=time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))+'.log', clevel = logging.DEBUG, Flevel = logging.DEBUG):
        self.logger = logging.getLogger(logfile)
        self.logger.setLevel(logging.DEBUG)
        self.listbox = listbox
        fmt = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
        #设置CMD日志
        # sh = logging.StreamHandler()
        # sh.setFormatter(fmt)
        # sh.setLevel(clevel)
        #设置文件日志
        fh = logging.FileHandler(logfile)
        fh.setFormatter(fmt)
        fh.setLevel(Flevel)
        # self.logger.addHandler(sh)
        self.logger.addHandler(fh)
        if self.listbox:
            self.listbox.delete(0, END)
            self.listbox.yview_moveto(1)
            self.listbox.update()

    def debug(self,message):
        self.logger.debug(message)
        if self.listbox:
            self.listbox.insert(END,  '[ %s ] [ Debug ] ' % time.strftime("%Y-%m-%d %X",time.localtime()) + message)
            self.listbox.yview_moveto(1)
            self.listbox.update()

    def info(self,message):
        self.logger.info(message)
        if self.listbox:
            self.listbox.insert(END, '[ %s ] [ Info ] ' % time.strftime("%Y-%m-%d %X",time.localtime()) + message)
            self.listbox.yview_moveto(1)
            self.listbox.update()

    def warn(self,message):
        self.logger.warn(message)
        if self.listbox:
            self.listbox.insert(END, '[ %s ] [ Warn ] ' % time.strftime("%Y-%m-%d %X",time.localtime()) + message)
            self.listbox.yview_moveto(1)
            self.listbox.update()

    def error(self,message):
        self.logger.error(message)
        if self.listbox:
            self.listbox.insert(END, '[ %s ] [ Error ] ' % time.strftime("%Y-%m-%d %X",time.localtime()) + message)
            self.listbox.yview_moveto(1)
            self.listbox.update()

