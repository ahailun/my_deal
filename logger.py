#!/usr/bin/python
# -*- coding: utf8 -*-

import os, time, logging, datetime
from tkinter import END

#TODO 按照日志文件大小分割https://www.jianshu.com/p/c373cd6c628f
class Logger:
    def __init__(self, listbox=None, logfile=time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))+'.log', clevel = logging.DEBUG, Flevel = logging.DEBUG):
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        self.listbox = listbox
        fmt = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
        #设置CMD日志
        # sh = logging.StreamHandler()
        # sh.setFormatter(fmt)
        # sh.setLevel(clevel)
        #设置文件日志
        log_path = os.getcwd() + '/Logs/'
        if not os.path.exists(log_path):
            os.mkdir(log_path)
        fh = logging.FileHandler(log_path+logfile)
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
            self.listbox.insert(END,  '[ %s ] [ Debug ] ' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f') + message)
            self.listbox.yview_moveto(1)
            self.listbox.update()

    def info(self,message):
        self.logger.info(message)
        if self.listbox:
            self.listbox.insert(END, '[ %s ] [ Info ] ' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f') + message)
            self.listbox.yview_moveto(1)
            self.listbox.update()

    def warn(self,message):
        self.logger.warn(message)
        if self.listbox:
            self.listbox.insert(END, '[ %s ] [ Warn ] ' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f') + message)
            self.listbox.yview_moveto(1)
            self.listbox.update()

    def error(self,message):
        self.logger.error(message)
        if self.listbox:
            self.listbox.insert(END, '[ %s ] [ Error ] ' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f') + message)
            self.listbox.yview_moveto(1)
            self.listbox.update()

