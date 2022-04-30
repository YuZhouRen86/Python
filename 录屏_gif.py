import tkinter as tk
import tkinter.filedialog as dialog
import time
from PIL import Image,ImageGrab
import imageio

def select_area():
    area=[0,0,0,0]
    rectangle_id=None
    def _press(event):
        area[0],area[1]=event.x,event.y
    def _move_label(event,text=None):
        nonlocal tip_id,rectangle_id
        text=text or "拖曳选择录制区域(%d, %d)"%(event.x,event.y)
        cv.delete(tip_id)
        tip_id=cv.create_text((event.x+8,event.y),
                              text=text, anchor = tk.W,justify = tk.LEFT)
    def _drag(event):
        nonlocal rectangle_id
        if rectangle_id is not None:cv.delete(rectangle_id)
        rectangle_id=cv.create_rectangle(area[0],area[1],
                                         event.x,event.y)
        _move_label(event)
    def _release(event):
        area[2],area[3]=event.x,event.y
        _move_label(event,"按Enter键接受, 拖曳可重新选择")
        window.bind_all('<Key-Return>',_accept)
    def _accept(event):
        window.destroy()

    window=tk.Tk()
    window.title("选择录制区域")
    window.protocol("WM_DELETE_WINDOW",lambda:None)# 防止窗口被异常关闭
    cv=tk.Canvas(window,bg='white',cursor="target")
    cv.pack(expand=True,fill=tk.BOTH)
    tip_id=cv.create_text((cv.winfo_screenwidth()//2,
                           cv.winfo_screenheight()//2),
                          text="拖曳选择录制区域",
                            anchor = tk.W,justify = tk.LEFT)
    window.attributes("-alpha",0.6)
    window.attributes("-topmost",True)
    window.attributes("-fullscreen",True)
    window.bind('<Button-1>',_press)
    window.bind('<Motion>',_move_label)
    window.bind('<B1-Motion>',_drag,)
    window.bind('<B1-ButtonRelease>',_release)

    while 1:
        try:
            window.update()
            time.sleep(0.01)
        except tk.TclError:break # 窗口已关闭
    return area

def main():
    def _stop():
        nonlocal flag
        flag=False
        btn_stop['state']=tk.DISABLED
        root.title('录制已结束')
    def _start():
        nonlocal flag
        flag=True
        btn_stop['text']='停止'
        btn_stop['command']=_stop

    root=tk.Tk()
    root.title('录屏工具')
    btn_stop=tk.Button(root,text='开始',command=_start)
    btn_stop.pack()
    lbl_fps=tk.Label(root,text='fps:0')
    lbl_fps.pack(fill=tk.X)
    filename=dialog.asksaveasfilename(master=root,
                filetypes=[("gif动画","*.gif"),("所有文件","*.*")],
                defaultextension='.gif')
    if not filename.strip():return

    area=select_area()

    root.title('录制中')
    fps=60;flag=False
    while not flag: # 等待用户点击开始
        root.update()
    start=last=time.perf_counter()
    lst_image=[]
    while flag:
        image=ImageGrab.grab(area)
        lst_image.append(image)
        end=time.perf_counter()
        time.sleep(max(len(lst_image)/fps-(end-start),0))
        try:
            lbl_fps['text']='fps:'+str(1/(end-last))
            last=end
            root.update()
        except tk.TclError:flag=True
    imageio.mimsave(filename,lst_image,'GIF',
                    duration=(end-start)/len(lst_image))

if __name__=="__main__":main()
