"""说明 Introduction:
A simple text editor written in Python.It supports editing text files,
binary files ,encodings and changing font size.
When you edit a binary file, the contents of the file are
displayed as escape sequences.
You can also find and replace words.
In addition, code highlighting is supported when editing Python code files,like IDLE.
What's more, dragging and dropping files into the editor window is now supported.

一款使用tkinter编写的文本编辑器, 支持编辑文本文件、二进制文件、改变字体大小。
支持ansi、gbk、utf-8等编码。编辑二进制文件时, 文件内容以转义序列形式显示。
支持查找、替换、改变字体大小; 且支持撤销、重做; 支持将文件拖放入窗口。
编辑python代码文件时, 支持代码高亮显示, 类似IDLE。

作者:qfcy (七分诚意)
版本:1.2.8.6
"""
import sys,os,time,pickle
from tkinter import *
from tkinter.scrolledtext import ScrolledText
import tkinter.ttk as ttk
import tkinter.messagebox as msgbox
import tkinter.filedialog as dialog
import tkinter.simpledialog as simpledialog

try:
    from idlelib.colorizer import ColorDelegator
    from idlelib.percolator import Percolator
except ImportError:
    ColorDelegator=Percolator=None
try:import windnd
except ImportError:windnd=None

__email__="3416445406@qq.com"
__author__="七分诚意 qq:3076711200 邮箱:%s"%__email__
__version__="1.2.8.6"

def view_hex(bytes):
    result=''
    for i in range(0,len(bytes)):
        result+= hex(bytes[i])[2:].zfill(2) + ' '
        if (i+1) % 4 == 0:result+='\n'
    return result

def to_escape_str(bytes):
    # 将字节(bytes)转换为转义字符串
    str='';length=1024
    for i in range(0,len(bytes),length):
        str+=repr( bytes[i: i+length] ) [2:-1]
        str+='\n'
    return str

def to_bytes(escape_str):
    # 将转义字符串转换为字节
    # -*****- 1.2.5版更新: 忽略二进制模式中文字的换行符
    escape_str=escape_str.replace('\n','')
    escape_str=escape_str.replace('"""','\\"\\"\\"') # 避免引号导致的SyntaxError
    escape_str=escape_str.replace("'''","\\'\\'\\'")
    try:
        return eval('b"""'+escape_str+'"""')
    except SyntaxError:
        return eval("b'''"+escape_str+"'''")

def bell_(widget=None):
    try: 
        import winsound
        winsound.PlaySound('.',winsound.SND_ASYNC)
    except (ImportError, RuntimeError):
        if widget is not None:widget.bell()

def handle(err,parent=None):
    # showinfo()中,parent参数指定消息框的父窗口
    msgbox.showinfo("错误",type(err).__name__+': '+str(err),parent=parent)

class SearchDialog(Toplevel):
    #查找对话框
    instances=[]
    def __init__(self,master):
        self.master=master
        self.coding=self.master.coding.get()
        cls=self.__class__
        cls.instances.append(self)
    def init_window(self,title="查找"):
        Toplevel.__init__(self,self.master)
        self.title(title)
        self.attributes("-toolwindow",True)
        self.attributes("-topmost",True)
        self.wm_protocol("WM_DELETE_WINDOW",self.onquit)
    def show(self):
        self.init_window()
        frame=Frame(self)
        ttk.Button(frame,text="查找下一个",command=self.search).pack()
        ttk.Button(frame,text="退出",command=self.onquit).pack()
        frame.pack(side=RIGHT,fill=Y)
        inputbox=Frame(self)
        Label(inputbox,text="查找内容:").pack(side=LEFT)
        self.keyword=StringVar(self.master)
        keyword=ttk.Entry(inputbox,textvariable=self.keyword)
        keyword.pack(side=LEFT,expand=True,fill=X)
        keyword.bind("<Key-Return>",self.search)
        keyword.focus_force()
        inputbox.pack(fill=X)
        options=Frame(self)
        self.create_options(options)
        options.pack(fill=X)
    def create_options(self,master):
        Label(master,text="选项: ").pack(side=LEFT)
        self.use_regexpr=IntVar(self.master)
        ttk.Checkbutton(master,text="使用正则表达式",variable=self.use_regexpr)\
        .pack(side=LEFT)
        self.match_case=IntVar(self.master)
        ttk.Checkbutton(master,text="区分大小写",variable=self.match_case)\
        .pack(side=LEFT)
        self.use_escape_char=IntVar(self.master)
        self.use_escape_char.set(self.master.isbinary)
        ttk.Checkbutton(master,text="使用转义字符",variable=self.use_escape_char)\
        .pack(side=LEFT)

    def search(self,event=None,mark=True,bell=True):
        text=self.master.contents
        key=self.keyword.get()
        if not key:return
        if self.use_escape_char.get():
            try:key=str(to_bytes(key),encoding=self.coding)
            except Exception as err:
                handle(err,parent=self);return
        text.tag_remove("sel","1.0",END)
        # 默认从当前光标位置开始查找
        pos=text.search(key,INSERT,END,
                        regexp=self.use_regexpr.get(),
                        nocase=not self.match_case.get())
        if not pos:
            pos=text.search(key,'1.0',END, # 尝试从开头循环查找
                        regexp=self.use_regexpr.get(),
                        nocase=not self.match_case.get())
        if pos:
            newpos="%s+%dc"%(pos,len(key))
            text.mark_set(INSERT,newpos)
            if mark:self.mark_text(pos,newpos)
            return pos,newpos
        elif bell: # 未找到
            bell_(widget=self)
    def findnext(self,cursor_pos='end',mark=True):
        # cursor_pos:标记文本后将光标放在找到文本开头还是末尾
        # 因为search()默认从当前光标位置开始查找
        # end 用于查找下一个操作, start 用于替换操作
        result=self.search(mark=mark)
        if not result:return
        if cursor_pos=='end':
            self.master.contents.mark_set('insert',result[1])
        elif cursor_pos=='start':
            self.master.contents.mark_set('insert',result[0])
        return result
    def mark_text(self,start_pos,end_pos):
        text=self.master.contents
        text.tag_add("sel", start_pos,end_pos)
        lines=text.get('1.0',END)[:-1].count(os.linesep) + 1
        lineno=int(start_pos.split('.')[0])
        text.yview('moveto', str((lineno-text['height'])/lines)) # -****- 1.2.5版
        text.focus_force()
        self.master.update_status()
    def onquit(self):
##        cls=self.__class__
##        if self in cls.instances:cls.instances.remove(self)
        self.withdraw()

class ReplaceDialog(SearchDialog):
    #替换对话框
    instances=[]
    def show(self):
        self.init_window(title="替换")
        frame=Frame(self)
        ttk.Button(frame,text="查找下一个",command=
                   lambda:self.findnext('start')).pack()
        ttk.Button(frame,text="替换",command=self.replace).pack()
        ttk.Button(frame,text="全部替换",command=self.replace_all).pack()
        ttk.Button(frame,text="退出",command=self.onquit).pack()
        frame.pack(side=RIGHT,fill=Y)

        inputbox=Frame(self)
        Label(inputbox,text="查找内容:").pack(side=LEFT)
        self.keyword=StringVar(self.master)
        keyword=ttk.Entry(inputbox,textvariable=self.keyword)
        keyword.pack(side=LEFT,expand=True,fill=X)
        keyword.focus_force()
        inputbox.pack(fill=X)

        replace=Frame(self)
        Label(replace,text="替换为:  ").pack(side=LEFT)
        self.text_to_replace=StringVar(self.master)
        replace_text=ttk.Entry(replace,textvariable=self.text_to_replace)
        replace_text.pack(side=LEFT,expand=True,fill=X)
        replace_text.bind("<Key-Return>",self.replace)
        replace.pack(fill=X)

        options=Frame(self)
        self.create_options(options)
        options.pack(fill=X)
        
    def replace(self,bell=True,mark=True):
        text=self.master.contents
        result=self.search(mark=False,bell=bell)
        if not result:return -1 #-1标志已无文本可替换
        self.master.text_change()
        pos,newpos=result
        newtext=self.text_to_replace.get()
        if self.use_escape_char.get():
            newtext=to_bytes(newtext).decode(self.master.coding.get())
        if self.use_regexpr.get():
            old=text.get(pos,newpos)
            newtext=re.sub(self.keyword.get(),newtext,old)
        text.delete(pos,newpos)
        text.insert(pos,newtext)
        end_pos="%s+%dc"%(pos,len(newtext))
        if mark:self.mark_text(pos,end_pos)
        return pos,end_pos
    def replace_all(self):
        self.master.contents.mark_set("insert","1.0")
        flag=False # 标志是否已有文字被替换

        # 以下代码会导致无限替换, 使程序卡死, 新的代码修复了该bug
        #while self.replace(bell=False)!=-1:
        #    flag=True
        last = (0,0)
        while True:
            result=self.replace(bell=False,mark=False)
            if result==-1:break
            flag = True
            ln,col = self.findnext('start',mark=False)[0].split('.')
            ln,col = int(ln),int(col)
            # 判断新的偏移量是增加还是减小
            if ln < last[0]:
                self.mark_text(*result) # 已完成一轮替换
                break
            elif ln==last[0] and col<last[1]:
                self.mark_text(*result)
                break
            last=ln,col
        if not flag:bell_()
     
class Editor(Tk):
    TITLE="PyNotepad"
    encodings="ansi","utf-8","utf-16","utf-32","gbk","big5"
    ICON="notepad.ico"
    NORMAL_CODING="utf-8"
    FONTSIZES=8, 9, 10, 11, 12, 14, 18, 20, 22, 24, 30
    NORMAL_FONT='宋体'
    NORMAL_FONTSIZE=11
    FILETYPES=[("所有文件","*.*")]
    CONFIGFILE=os.getenv("userprofile")+"\.pynotepad.pkl"

    windows=[]
    def __init__(self,filename=""):
        super().__init__()
        self.withdraw() # 暂时隐藏窗口,避免调用create_widgets()时窗口闪烁
        self.title(self.TITLE)
        self.bind("<Key>",self.window_onkey)
        self.bind("<FocusIn>",self.focus)
        self.bind("<FocusOut>",self.focus)
        self.protocol("WM_DELETE_WINDOW",self.ask_for_save)

        self.isbinary=self.file_changed=False
        self.colorobj=self._codefilter=None
        Editor.windows.append(self)

        self.load_icon()
        self.loadconfig()
        self.create_widgets()
        self.wm_deiconify();self.update() # wm_deiconfy恢复被隐藏的窗口
        if windnd:windnd.hook_dropfiles(self,func=self.onfiledrag);self.drag_files=[]
        self.filename=''
        if filename:
            self.load(filename)
    def load_icon(self):
        for path in sys.path + [os.path.split(sys.executable)[0]]: # 用于Py2exe
            try:
                self.iconbitmap("{}\{}".format(path,self.ICON))
            except TclError:pass
            else:break
    def create_widgets(self):
        # 创建控件
        self.statusbar=Frame(self)
        self.statusbar.pack(side=BOTTOM,fill=X)
        self.status=Label(self.statusbar,justify=RIGHT)
        self.status.pack(side=RIGHT)
        self.bin_data=ScrolledText(self.statusbar,width=6,height=6)
        self.charmap=ScrolledText(self.statusbar,width=14,height=5)

        frame=Frame(self)
        frame.pack(side=TOP,fill=X)

        ttk.Button(frame,text='新建', command=self.new,width=7).pack(side=LEFT)
        ttk.Button(frame,text='打开', command=self.open,width=7).pack(side=LEFT)
        ttk.Button(frame,text='打开二进制文件',
                   command=self.open_as_binary,width=13).pack(side=LEFT)
        ttk.Button(frame,text='保存', command=self.save,width=7).pack(side=LEFT)

        Label(frame,text="编码:").pack(side=LEFT)
        self.coding=StringVar(self)
        self.coding.set(self.NORMAL_CODING)
        coding=ttk.Combobox(frame,textvariable=self.coding)
        def tip(event):
            self.msg['text']='重新打开或保存即可生效'
            self.msg.after(2500,clear)
        def clear():self.msg['text']=''
        coding.bind('<<ComboboxSelected>>',tip)
        coding["value"]=self.encodings
        coding.pack(side=LEFT)
        self.msg=Label(frame)
        self.msg.pack(side=LEFT)

        self.contents=ScrolledText(self,undo=True,width=75,height=24,
                        font=(self.NORMAL_FONT,self.NORMAL_FONTSIZE,"normal"))
        self.contents.pack(expand=True,fill=BOTH)
        self.contents.bind("<Key>",self.text_change)
        self.contents.bind("<B1-ButtonRelease>",self.update_status)
        order = self.contents.bindtags() # 修复无法获取选定的文本的bug
        self.contents.bindtags((order[1], order[0])+order[2:])
        self.update_offset()

        self.create_menu()
    def create_binarytools(self):
        if self.isbinary:
            self.bin_data.pack(side=LEFT,expand=True,fill=BOTH)
            self.charmap.pack(fill=Y)
            self.status.pack_forget()
            self.status.pack(fill=X)
        else: # 隐藏工具
            if self.bin_data:
                self.bin_data.pack_forget()
            if self.charmap:
                self.charmap.pack_forget()
            self.status.pack(side=RIGHT)
    def create_menu(self):
        menu=Menu(self)
        filemenu=Menu(self,tearoff=False)
        filemenu.add_command(label="新建",
                             command=self.new,accelerator="Ctrl+N")
        filemenu.add_command(label="新建二进制文件",command=self.new_binary)
        filemenu.add_command(label="打开",
                             command=self.open,accelerator="Ctrl+O")
        filemenu.add_command(label="打开二进制文件",command=self.open_as_binary)
        filemenu.add_command(label="保存",
                             command=self.save,accelerator="Ctrl+S")
        filemenu.add_command(label="另存为",command=self.save_as)
        filemenu.add_separator()
        filemenu.add_command(label="退出",command=self.ask_for_save)

        self.editmenu=Menu(self.contents,tearoff=False)
        master = self.contents
        self.editmenu.add_command(label="剪切  ",
                         command=lambda:self.text_change()\
                                ==master.event_generate("<<Cut>>"))
        self.editmenu.add_command(label="复制  ",
                         command=lambda:master.event_generate("<<Copy>>"))
        self.editmenu.add_command(label="粘贴  ",
                         command=lambda:self.text_change()\
                                ==master.event_generate("<<Paste>>"))
        self.editmenu.add_separator()
        self.editmenu.add_command(label="查找",accelerator="Ctrl+F",
                                  command=lambda:self.show_dialog(SearchDialog))
        self.editmenu.add_command(label="查找下一个",accelerator="F3",
                                  command=self.findnext)
        self.editmenu.add_command(label="替换",accelerator="Ctrl+H",
                                  command=lambda:self.show_dialog(ReplaceDialog))

        view=Menu(self.contents,tearoff=False)
        self.is_autowrap=IntVar(self.contents) # 是否自动换行
        self.is_autowrap.set(1)
        view.add_checkbutton(label="自动换行", command=self.set_wrap,
                             variable=self.is_autowrap)
        fontsize=Menu(self.contents,tearoff=False)
        fontsize.add_command(label="选择字体",
                             command=self.choose_font)
        fontsize.add_separator()
        fontsize.add_command(label="增大字体   ",accelerator='Ctrl+ "+"',
                             command=self.increase_font)
        fontsize.add_command(label="减小字体   ",accelerator='Ctrl+ "-"',
                             command=self.decrease_font)
        fontsize.add_separator()

        for i in range(len(self.FONTSIZES)):
            def resize(index=i):
                self.set_fontsize(index)
            fontsize.add_command(label=self.FONTSIZES[i],command=resize)

        self.contents.bind("<Button-3>",
                    lambda event:self.editmenu.post(event.x_root,event.y_root))
        view.add_cascade(label="字体",menu=fontsize)

        helpmenu=Menu(self,tearoff=False)
        helpmenu.add_command(label="关于",command=self.about)

        menu.add_cascade(label="文件",menu=filemenu)
        menu.add_cascade(label="编辑",menu=self.editmenu)
        menu.add_cascade(label="查看",menu=view)
        menu.add_cascade(label="帮助",menu=helpmenu)

        popup1=Menu(self.bin_data,tearoff=False)
        popup1.add_command(
            label="复制",command=lambda:self.bin_data.event_generate("<<Copy>>"))
        popup2=Menu(self.charmap,tearoff=False)
        popup2.add_command(
            label="复制",command=lambda:self.charmap.event_generate("<<Copy>>"))
        self.bin_data.bind("<Button-3>",
                    lambda event:popup1.post(event.x_root,event.y_root))
        self.charmap.bind("<Button-3>",
                    lambda event:popup2.post(event.x_root,event.y_root))
        # 显示菜单
        self.config(menu=menu)


    def show_dialog(self,dialog_type):
        # dialog_type是对话框的类型
        for dialog in dialog_type.instances:
            if dialog.master is self:
                dialog.state('normal') # 恢复隐藏的窗口
                dialog.focus_force()
                return # 不再显示新的对话框
        dialog_type(self).show()
    def findnext(self):
        for dialog in SearchDialog.instances:
            if dialog.master is self:
                dialog.findnext()
                return
        for dialog in ReplaceDialog.instances:
            if dialog.master is self:
                dialog.findnext()
                return
    def set_fontsize(self,index):
        newsize=self.FONTSIZES[index]
        fontname=self.contents["font"].split(' ')[0]
        self.contents["font"]=(fontname,newsize,"normal")
    def choose_font(self):
        oldfont=self.contents["font"].split(' ')[0]
        font=simpledialog.askstring(
                '', '输入字体名称: (例如: 楷体)', initialvalue = oldfont)
        if font is not None:
            self.contents["font"]=[font] + self.contents["font"].split(' ')[1:]
    def increase_font(self):
        # 增大字体
        fontsize=int(self.contents["font"].split(' ')[1])
        index=self.FONTSIZES.index(fontsize)+1
        if 0<=index<len(self.FONTSIZES): self.set_fontsize(index)
    def decrease_font(self):
        # 减小字体
        fontsize=int(self.contents["font"].split(' ')[1])
        index=self.FONTSIZES.index(fontsize)-1
        if 0<=index<len(self.FONTSIZES): self.set_fontsize(index)
    def set_wrap(self):
        if self.is_autowrap.get():
            self.contents['wrap'] = CHAR
        else:
            self.contents['wrap'] = NONE
          # 注意:不需要此行代码
##        self.is_autowrap.set(int(not self.is_autowrap.get()))

    def window_onkey(self,event):
        # 如果按下Ctrl键
        if event.state in (4,6,12,14,36,38,44,46): # 适应多种按键情况(Num,Caps,Scroll)
            key=event.keysym.lower()
            if key=='o':#按下Ctrl+O键
                self.open()
            elif key=='s':#Ctrl+S键
                self.save()
            elif key=='f':
                self.show_dialog(SearchDialog)
            elif key=='h':
                self.show_dialog(ReplaceDialog)
            elif key=='equal':#Ctrl+ "+" 增大字体
                self.increase_font()
            elif key=='minus':#Ctrl+ "-" 减小字体
                self.decrease_font()
        elif event.keysym.lower()=='f3':
            self.findnext()
    def focus(self,event):
        # 当窗口获得或失去焦点时,调用此函数, 用于使对话框置于主窗体前
        for dialog in SearchDialog.instances + ReplaceDialog.instances:
            if dialog.master is self and not dialog.wm_state()=='withdrawn':
                if event.type==EventType.FocusIn:
                    dialog.attributes("-topmost",True)
                    if not dialog.wm_state()=="normal":
                        dialog.deiconify()
                    self.contents.focus_force()
                else:
                    dialog.attributes("-topmost",False)
                    if self.wm_state()=="iconic":
                        dialog.withdraw()
                        #window.iconify()
                break

    def text_change(self,event=None):
        self.file_changed=True
        self.update_status();self.change_title()
    def update_status(self,event=None):
        if self.isbinary:
            try:
                selected=self.contents.get(SEL_FIRST,SEL_LAST)
                data=to_bytes(selected)
                try:text=str(data,encoding=self.coding.get(),
                             errors="backslashreplace")
                except TypeError:
                    # 忽略Python 3.4的bug: don't know how to handle
                    # UnicodeDecodeError in error callback
                    text=str(data,encoding=self.coding.get(),
                             errors="replace")
                self.bin_data.delete("1.0",END)
                self.bin_data.insert(INSERT,text)
                self.charmap.delete("1.0",END)
                self.charmap.insert(INSERT,view_hex(data))
                self.status["text"]="选区长度: %d (Bytes)"%len(data)
            except (TclError,SyntaxError): #忽略未选取内容, 或格式不正确
                self.bin_data.delete("1.0",END)
                self.charmap.delete("1.0",END)
                self.update_offset()
        else:self.update_offset()
    def update_offset(self,event=None):
        if self.isbinary:
            prev=self.contents.get("1.0",INSERT)
            try:
                data=to_bytes(prev)
            except SyntaxError:
                sep='\\'
                # self.update()
                prev=sep.join(prev.split(sep)[0:-1])
                data=to_bytes(prev)
            self.status["text"]="偏移量: {} ({})".format(len(data),hex(len(data)))
        else:
            offset=self.contents.index(CURRENT).split('.')
            self.status["text"]="Ln: {}  Col: {}".format(*offset)

    @classmethod
    def new(cls):
        window=cls()
        window.focus_force()
    @classmethod
    def new_binary(cls):
        window=cls()
        window.isbinary=True
        window.create_binarytools()
        window.change_title()
        window.change_mode()
        window.contents.edit_reset()
        window.focus_force()
    def open(self,filename=None):
        #加载一个文件
        if self.ask_for_save(quit=False)==0:return
        if not filename:
            filename=dialog.askopenfilename(master=self,title='打开',
                                initialdir=os.path.split(self.filename)[0],
                                filetypes=self.FILETYPES)
        self.load(filename)
    def open_as_binary(self):
        if self.ask_for_save(quit=False)==0:return
        filename=dialog.askopenfilename(master=self,title='打开二进制文件',
                                initialdir=os.path.split(self.filename)[0],
                                filetypes=self.FILETYPES)
        self.load(filename,binary=True)
    def load(self,filename,binary=False):
        # 加载文件
        if not filename.strip():
            return
        self.isbinary=binary
        try:
            data=self._load_data(filename)
            if data==0:return
            self.filename=filename
            self.contents.delete('1.0', END)
            if self.isbinary:
                self.contents.insert(INSERT,data)
            else:
                for char in data:
                    try:
                        self.contents.insert(INSERT,char)
                    except TclError:self.contents.insert(INSERT,' ')
            self.contents.mark_set(INSERT,"1.0")
            self.create_binarytools()
            self.file_changed=False
            self.change_title()
            self.change_mode()
            self.contents.edit_reset() # -*****- 1.2.5版更新 !!!!!!!
            self.contents.focus_force()
        except Exception as err:handle(err,parent=self)
    def _load_data(self,filename):
        # 从文件加载数据
        f=open(filename,"rb")
        if self.isbinary:
            data=to_escape_str(f.read())
            return data
        else:
            try:
                #读取文件,并对文件内容进行编码
                data=str(f.read(),encoding=self.coding.get())
            except UnicodeDecodeError:
                f.seek(0)
                result=msgbox.askyesnocancel("PyNotepad","""%s编码无法解码此文件,
是否使用二进制模式打开?"""%self.coding.get(),parent=self)
                if result:
                    self.isbinary=True
                    data=to_escape_str(f.read())
                elif result is not None:
                    self.isbinary=False
                    data=str(f.read(),encoding=self.coding.get(),errors="replace")
                else:
                    return 0 # 表示取消
            # return data.replace('\r','')
            return data
    def change_title(self):
        file = os.path.split(self.filename)[1] or "未命名"
        newtitle="PyNotepad - "+ file +\
                  (" (二进制模式)" if self.isbinary else '')
        if self.file_changed:
            newtitle="*%s*"%newtitle
        self.title(newtitle)
    def change_mode(self):
        if ColorDelegator:
            if self.filename.lower().endswith((".py",".pyw"))\
                   and (not self.isbinary):
                self._codefilter=ColorDelegator()
                if not self.colorobj:
                    self.colorobj=Percolator(self.contents)
                self.colorobj.insertfilter(self._codefilter)
            elif self.colorobj and self._codefilter.delegate:
                self.colorobj.removefilter(self._codefilter)
    def ask_for_save(self,quit=True):
        my_ret=None
        if self.file_changed: ## and self.filenamebox.get():
            retval=msgbox.askyesnocancel("文件尚未保存",
                              "是否保存{}的更改?".format(
                            os.path.split(self.filename)[1] or "当前文件"),
                                parent=self)
            if not retval is None:
                if retval==True:
                    # 是
                    ret=self.save()
                    # 在保存对话框中取消
                    if ret==0:
                        my_ret=0;quit=False
                # 否
            else:
                # 取消
                my_ret=0;quit=False  # 0表示cancel
        if quit:
            Editor.windows.remove(self)
            self.saveconfig()
            self.destroy()
        return my_ret
    def save(self):
        #保存文件
        if not self.filename:
            self.filename=dialog.asksaveasfilename(master=self,
                    initialdir=os.path.split(self.filename)[0],
                    filetypes=self.FILETYPES)
        filename=self.filename
        if filename.strip():
            try:
                text=self.contents.get('1.0', END)[:-1] # [:-1]: 去除换行符
                if self.isbinary:
                    data=to_bytes(text)
                else:
                    data=bytes(text,encoding=self.coding.get(),errors='replace')
                with open(filename, 'wb') as f:
                    f.write(data)
                self.filename=filename
                self.file_changed=False
            except Exception as err:handle(err,parent=self)
            self.change_title()
            self.change_mode()
        else:
            return 0 # 0表示cancel
    def save_as(self):
        filename=dialog.asksaveasfilename(master=self,
                    initialdir=os.path.split(self.filename)[0],
                    filetypes=self.FILETYPES)
        if filename:
            self.filename=filename
            self.save()

    def about(self):
        msgbox.showinfo("关于",__doc__+"\n作者: "+__author__,parent=self)
    def loadconfig(self):
        try:
            with open(self.CONFIGFILE,'rb') as f:
                cfg=pickle.load(f)
                for key in cfg:
                    setattr(Editor,key,cfg[key])
        except OSError:
            pass
    def saveconfig(self):
        font=self.contents['font'].split(' ')
        cfg={'NORMAL_CODING':self.coding.get(),
             'NORMAL_FONT': font[0],
             'NORMAL_FONTSIZE': int(font[1])}
        with open(self.CONFIGFILE,'wb') as f:
            pickle.dump(cfg,f)
    def onfiledrag(self,files):
        self.drag_files=files
        self.after(50,self.onfiledrag2)
    def onfiledrag2(self):
        if not self.contents.get('1.0',END).strip() and not self.file_changed:
            self.open(self.drag_files[0].decode('gbk'))
            del self.drag_files[0]
        for item in self.drag_files:
            Editor(item.decode('gbk'))

def main():
    if len(sys.argv)>1:
        for arg in sys.argv[1:]:
            try:
                Editor(arg)
            except OSError:pass
    else: Editor()
    mainloop()

if __name__=="__main__":main()
