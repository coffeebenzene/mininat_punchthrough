from Tkinter import *

window = Tk()

messages = Text(window)
messages.pack()

input_user = StringVar()
input_field = Entry(window, text = input_user)
input_field.pack(side = BOTTOM, fill = X)

def enter_pressed(event):
    input_get = input_field.get()
    print(input_get)
    messages.insert(INSERT, 'Me: %s\n' % input_get)
    input_user.set('')
    return "break"

def message_recd(event, msg, sender):
    messages.insert(INSERT, '%s: %s\n' % (sender, msg))
    return "break"

frame = Frame(window)
input_field.bind("<Return>", enter_pressed)
frame.pack()

window.mainloop()