from Tkinter import *

window = Tk()

messages = Text(window)
messages.grid(row=0, sticky=("N","S","E","W"))
messages.configure(state=DISABLED)
print "1"
input_user = StringVar()
input_field = Entry(window, text = input_user, padding=(10,0,0,0))
input_field.grid(row=1, sticky=(E,W,S))
print "2"
window.rowconfigure(0, weight=1)
window.columnconfigure(0, weight=1)
print "3"
def enter_pressed(event):
    input_get = input_field.get()
    print(input_get)
    messages.configure(state=NORMAL)
    messages.insert(END, 'Me: %s\n' % input_get)
    messages.configure(state=DISABLED)
    input_user.set('')
    return "break"

def message_recd(event, msg, sender):
    messages.insert(END, '%s: %s\n' % (sender, msg))
    return "break"
print "4"
#frame = Frame(window)
input_field.bind("<Return>", enter_pressed)
#frame.pack()
print "5"
window.mainloop()