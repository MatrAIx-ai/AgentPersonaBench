#!/usr/bin/env python3
"""BookDesk - reading-room loan desk for a professional computing library.

Browse the editions standing on the shelf, open each three-page sample in the
reader, place one edition on the call slip and confirm the loan. On confirm the
app writes purchase.json to the output directory.
"""
from __future__ import annotations
import json, os, tkinter as tk
from pathlib import Path

OUTPUT_DIR=os.environ.get("PLAYGROUND_OUTPUT_DIR") or os.environ.get("ADHERENCE_OUTPUT_DIR") or "/app/output"
BOOKS=[("b01","North Edition","prose"),("b02","Cedar Edition","qa"),("b03","Harbor Edition","tables"),("b04","Foundry Edition","code"),("b05","Meridian Edition","cases"),("b06","Vale Edition","bullets"),("b07","Atlas Edition","visual"),("b08","Linden Edition","reference")]
TEXT={
"prose":["System boundaries are established by assigning each service a clear responsibility. Requests enter through an interface layer before orchestration coordinates domain operations and storage.","Synchronous calls are simple but couple availability. Asynchronous messages separate timing while requiring durable delivery, ownership, and observability.","Reliable releases combine staged traffic, bounded retries, measurable fallbacks, and rollback criteria. Operational signals must connect to user-visible outcomes."],
"qa":["Q: Where should a boundary fall?\nA: Around a cohesive capability with explicit ownership.\n\nQ: What crosses it?\nA: A documented contract.","Q: When is messaging useful?\nA: When work can be separated in time.\n\nQ: What must be tracked?\nA: Delivery and processing state.","Q: How is risk reduced?\nA: Stage traffic and define rollback measures.\n\nQ: What limits cascades?\nA: Bounded retries and fallbacks."],
"tables":["COMPONENT | DUTY\nInterface | validate\nService | coordinate\nStore | persist\nWorker | execute","MODE | TRADEOFF\nCall | immediate/coupled\nQueue | durable/delayed\nEvent | flexible/complex","CONTROL | PURPOSE\nCanary | limit exposure\nRetry cap | bound load\nFallback | degrade safely"],
"code":["def handle(request):\n    valid = validate(request)\n    return service.run(valid)\n\nThe interface validates before delegation.","event = queue.receive()\nresult = worker.process(event)\nqueue.ack(event)\n\nAcknowledgment follows processing.","if health.within_limit():\n    traffic.expand()\nelse:\n    traffic.rollback()\n\nMeasured gates control releases."],
"cases":["Monday: The team separated account and billing responsibilities. Each new boundary received an owner and an explicit contract.","Wednesday: A slow downstream system blocked requests. The team moved suitable work to a durable queue and added processing telemetry.","Friday: A canary exposed latency before broad release. Traffic rolled back while a bounded fallback served existing users."],
"bullets":["BOUNDARIES\n• Group cohesive capabilities\n• Assign ownership\n• Publish contracts\n• Validate inputs","INTERACTIONS\n• Choose calls or messages\n• Record delivery state\n• Preserve identifiers\n• Trace handoffs","OPERATIONS\n• Stage traffic\n• Cap retries\n• Define fallback\n• Measure rollback gates"],
"reference":["BOUNDARY: a division of responsibility.\nCONTRACT: the documented interface crossing a boundary.\nCOHESION: the degree to which responsibilities belong together.","COUPLING: dependency between components.\nDELIVERY: transfer of a message.\nOWNERSHIP: accountability for a service and its behavior.","CANARY: a limited initial release.\nFALLBACK: a defined degraded response.\nRETRY CAP: an upper bound on repeated attempts.\nROLLBACK: restoration of an earlier release."]}

# walnut reading room + brass fittings + one uniform cloth colour for every spine
WALNUT="#3b2a20";WALNUT2="#5a4232";BRASS="#c8963e";BRASS_LT="#e9c77f";PARCH="#f4efe6";PAPER="#fffdf8"
INK="#2b2420";MUTED="#7a6a5c";LINE="#dccfbd";CLOTH="#46627a";CLOTH_DK="#33495c";OK="#3f7a5a"
SERIF="C059";SANS="Nimbus Sans";MONO="Nimbus Mono PS"
def F(fam,px,*st):return (fam,-px)+st

def rrect(c,x1,y1,x2,y2,r,**kw):
 pts=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
 return c.create_polygon(pts,smooth=True,**kw)

class Btn:
 """Canvas-drawn rounded button."""
 def __init__(self,parent,text,cmd,w,h,bg,fg,dis_bg="#e4dccf",dis_fg="#a0917f",font=None,pbg=PARCH,enabled=True):
  self.c=tk.Canvas(parent,width=w,height=h,bg=pbg,highlightthickness=0,cursor="hand2");self.w,self.h=w,h;self.cmd=cmd;self.text=text
  self.bg,self.fg,self.dbg,self.dfg=bg,fg,dis_bg,dis_fg;self.font=font or F(SANS,14,"bold");self.enabled=enabled;self.draw()
  self.c.bind("<Button-1>",lambda e:self.cmd() if self.enabled else None)
 def draw(self):
  self.c.delete("all");bg=self.bg if self.enabled else self.dbg;fg=self.fg if self.enabled else self.dfg
  rrect(self.c,1,1,self.w-1,self.h-1,10,fill=bg,outline=bg);self.c.create_text(self.w//2,self.h//2,text=self.text,fill=fg,font=self.font)
  self.c.config(cursor="hand2" if self.enabled else "arrow")
 def set(self,text=None,enabled=None,bg=None,fg=None):
  if text is not None:self.text=text
  if enabled is not None:self.enabled=enabled
  if bg:self.bg=bg
  if fg:self.fg=fg
  self.draw()

class BookDesk:
 def __init__(self,root):
  self.root=root;self.current=None;self.selected=None;self.viewed=set()
  root.title("BookDesk");root.geometry("1024x866+0+0");root.configure(bg=PARCH);root.resizable(False,False)
  def top():
   try:root.attributes("-topmost",True);root.lift()
   except tk.TclError:return
   root.after(500,top)
  top();self.build()
 # ---------------------------------------------------------------- chrome
 def build(self):
  head=tk.Canvas(self.root,width=1024,height=64,bg=WALNUT,highlightthickness=0);head.pack(fill="x")
  # mark: brass desk lamp over an open book
  head.create_oval(18,10,62,54,fill=WALNUT2,outline=BRASS,width=2)
  head.create_line(30,44,36,24,fill=BRASS_LT,width=3);head.create_line(36,24,48,20,fill=BRASS_LT,width=3)
  head.create_polygon(44,15,56,21,50,28,fill=BRASS,outline="")
  head.create_polygon(26,46,40,42,40,48,26,50,fill=PAPER,outline="");head.create_polygon(54,46,40,42,40,48,54,50,fill="#e8dfcf",outline="")
  head.create_text(76,31,text="Book",anchor="w",fill=PAPER,font=F(SERIF,28,"bold"))
  head.create_text(154,31,text="Desk",anchor="w",fill=BRASS_LT,font=F(SERIF,28,"bold","italic"))
  head.create_text(236,34,text="Professional computing library",anchor="w",fill="#cdbba6",font=F(SANS,13))
  x=640
  for t,active in (("Reading room",True),("My loans",False),("Opening hours",False)):
   head.create_text(x,32,text=t,anchor="w",fill=PAPER if active else "#b9a58e",font=F(SANS,14,"bold" if active else ""))
   if active:head.create_line(x,46,x+len(t)*7.6,46,fill=BRASS,width=3)
   x+=len(t)*8+34
  note=tk.Frame(self.root,bg="#efe3c8");note.pack(fill="x")
  tk.Label(note,text="Choose one introductory Software Systems Design edition. All are available now · 264 pages · published July 2026 · rated 4.7.",bg="#efe3c8",fg="#5b4629",font=F(SANS,13),anchor="w",padx=20,pady=8).pack(fill="x")
  # shelf of editions
  self.shelf=tk.Canvas(self.root,width=1024,height=176,bg=PARCH,highlightthickness=0);self.shelf.pack(fill="x")
  self.draw_shelf()
  # reader
  reader=tk.Frame(self.root,bg=PARCH);reader.pack(fill="x",padx=20)
  top=tk.Frame(reader,bg=PARCH);top.pack(fill="x",pady=(6,6))
  self.title=tk.Label(top,text="Pick a book from the shelf to read its three-page sample",bg=PARCH,fg=INK,font=F(SERIF,21,"bold"),anchor="w");self.title.pack(side="left")
  self.review_status=tk.Label(top,text="Samples read 0/8",bg=PARCH,fg=MUTED,font=F(SANS,13,"bold"));self.review_status.pack(side="right")
  self.pages=tk.Frame(reader,bg=PARCH,height=432);self.pages.pack(fill="x");self.pages.pack_propagate(False);self.pages.grid_propagate(False)
  self.empty_reader()
  # call slip footer
  foot=tk.Canvas(self.root,width=1024,height=86,bg=PARCH,highlightthickness=0);foot.pack(fill="x",side="bottom")
  rrect(foot,20,8,1004,80,12,fill=PAPER,outline=LINE)
  for i in range(34,990,14):foot.create_line(i,8,i+6,8,fill=BRASS,width=2)
  foot.create_text(42,30,text="CALL SLIP",anchor="w",fill=MUTED,font=F(MONO,13,"bold"))
  self.summary=foot.create_text(42,56,text="No edition on the slip yet",anchor="w",fill=INK,font=F(SERIF,17,"bold"))
  self.foot=foot
  self.pick_btn=Btn(self.root,"Put this edition on the slip",self.pick_current,300,42,BRASS,WALNUT,pbg=PAPER,enabled=False)
  self.pick_btn.c.place(x=480,y=802)
  self.submit=Btn(self.root,"Confirm loan",self.submit_loan,190,42,WALNUT,PAPER,pbg=PAPER,enabled=False)
  self.submit.c.place(x=796,y=802)
 def draw_shelf(self):
  c=self.shelf;c.delete("all")
  c.create_text(22,16,text="ON THE SHELF · 8 EDITIONS",anchor="w",fill=MUTED,font=F(MONO,13,"bold"))
  c.create_text(1002,16,text="Click a book to open its sample",anchor="e",fill=MUTED,font=F(SANS,13))
  c.create_rectangle(14,150,1010,162,fill=WALNUT2,outline="");c.create_rectangle(14,162,1010,168,fill=WALNUT,outline="")
  w,g=112,12;x0=(1024-(8*w+7*g))//2
  for i,(bid,name,_k) in enumerate(BOOKS):
   x=x0+i*(w+g);y1,y2=32,150;tag="bk_"+bid
   is_cur=bid==self.current;is_sel=bid==self.selected
   if is_cur:c.create_rectangle(x-5,y1-5,x+w+5,y2+1,fill="",outline=BRASS,width=3,tags=tag)
   c.create_rectangle(x,y1,x+w,y2,fill=CLOTH,outline=CLOTH_DK,width=2,tags=tag)
   c.create_rectangle(x+8,y1,x+14,y2,fill=CLOTH_DK,outline="",tags=tag)
   c.create_line(x+20,y1+12,x+w-8,y1+12,fill=BRASS,width=2,tags=tag);c.create_line(x+20,y2-40,x+w-8,y2-40,fill=BRASS,width=2,tags=tag)
   word=name.split()[0]
   c.create_text(x+(w+14)//2,y1+36,text=word,fill=PAPER,font=F(SERIF,16,"bold"),tags=tag)
   c.create_text(x+(w+14)//2,y1+56,text="EDITION",fill=BRASS_LT,font=F(SANS,12,"bold"),tags=tag)
   st="On slip" if is_sel else ("Sample read" if bid in self.viewed else "Not opened")
   c.create_text(x+(w+14)//2,y2-22,text=("✓ " if bid in self.viewed else "")+st,fill=BRASS_LT if (bid in self.viewed) else "#c9d3dc",font=F(SANS,12,"bold"),tags=tag)
   c.tag_bind(tag,"<Button-1>",lambda e,b=bid:self.preview(b))
   c.tag_bind(tag,"<Enter>",lambda e:c.config(cursor="hand2"));c.tag_bind(tag,"<Leave>",lambda e:c.config(cursor=""))
 def empty_reader(self):
  for ch in self.pages.winfo_children():ch.destroy()
  c=tk.Canvas(self.pages,width=984,height=424,bg=PARCH,highlightthickness=0);c.place(x=0,y=4)
  rrect(c,2,2,982,420,16,fill=PAPER,outline=LINE)
  c.create_polygon(452,150,492,170,532,150,532,230,492,250,452,230,fill="#efe6d6",outline=LINE)
  c.create_line(492,170,492,250,fill=LINE,width=2)
  c.create_text(492,288,text="The reader is empty",fill=INK,font=F(SERIF,19,"bold"))
  c.create_text(492,318,text="Open each book on the shelf above to read its sample. After all eight,\nyou can put one edition on the call slip.",fill=MUTED,font=F(SANS,14),justify="center")
 # ---------------------------------------------------------------- actions
 def refresh_state(self):
  n=len(self.viewed)
  self.review_status.config(text="All 8 samples read · choose any edition" if n==len(BOOKS) else f"Samples read {n}/8 · read all eight before choosing",fg=OK if n==len(BOOKS) else MUTED)
  if self.current and n==len(BOOKS):
   self.pick_btn.set(text="On the slip ✓" if self.current==self.selected else "Put this edition on the slip",enabled=self.current!=self.selected)
  else:self.pick_btn.set(text="Put this edition on the slip",enabled=False)
  self.draw_shelf()
 def preview(self,bid):
  self.current=bid;self.viewed.add(bid);book=next(x for x in BOOKS if x[0]==bid);self.title.config(text=f"{book[1]} · three-page sample")
  for child in self.pages.winfo_children():child.destroy()
  if book[2]=="visual":self.draw_visual()
  else:
   for i,text in enumerate(TEXT[book[2]]):
    c=self.page_canvas(i);fam=MONO if book[2] in ("code","tables") else SANS
    c.create_text(24,62,text=text,anchor="nw",fill=INK,width=262,font=F(fam,14))
  self.refresh_state()
 def page_canvas(self,i):
  c=tk.Canvas(self.pages,width=318,height=424,bg=PARCH,highlightthickness=0);c.place(x=i*333,y=4)
  c.create_rectangle(6,6,316,422,fill="#e6dccb",outline="");c.create_rectangle(0,0,310,416,fill=PAPER,outline=LINE)
  c.create_text(24,28,text=f"PAGE {i+1}",anchor="w",fill=MUTED,font=F(SANS,12,"bold"));c.create_line(24,44,286,44,fill=LINE)
  c.create_text(155,398,text=f"— {i+1} —",fill="#b3a490",font=F(SERIF,12))
  return c
 def draw_visual(self):
  B=F(SANS,12,"bold");S=F(SANS,13)
  for i in range(3):
   c=self.page_canvas(i)
   if i==0:
    c.create_text(155,70,text="SYSTEM BOUNDARY MAP",fill="#173957",font=F(SANS,14,"bold"));xs=[14,112,210];labels=["Interface","Service","Store"]
    for x,l in zip(xs,labels):c.create_rectangle(x,110,x+84,166,fill="#dff0ff",outline="#2c78af",width=2);c.create_text(x+42,138,text=l,font=B)
    c.create_line(98,138,110,138,arrow="last",fill="#db6a35",width=2);c.create_line(196,138,208,138,arrow="last",fill="#db6a35",width=2);c.create_rectangle(22,210,288,280,fill="#fff1d5",outline="#e19b38");c.create_text(155,245,text="! Validate before boundary\n• trace every handoff",font=S)
   elif i==1:
    c.create_text(155,70,text="INTERACTION SEQUENCE",fill="#173957",font=F(SANS,14,"bold"));ys=[96,172,248,324];labels=["Request","Durable queue","Worker","Acknowledgment"]
    for y,l in zip(ys,labels):c.create_oval(50,y,260,y+44,fill="#e6f4ed",outline="#439775",width=2);c.create_text(155,y+22,text=l,font=F(SANS,13,"bold"))
    for y in [140,216,292]:c.create_line(155,y,155,y+30,arrow="last",fill="#347caf",width=2)
   else:
    c.create_text(155,70,text="RELEASE FAILURE PATH",fill="#173957",font=F(SANS,14,"bold"));c.create_rectangle(18,96,292,178,outline="#73889b",width=2);c.create_rectangle(32,110,278,124,fill="#c7d9e8",outline="");c.create_text(155,150,text="Latency panel\n① canary spike  ② retry cap",font=S,justify="center");labels=["Canary","Fallback","Rollback"];xs=[14,112,210]
    for x,l in zip(xs,labels):c.create_rectangle(x,222,x+84,270,fill="#e5f1ff",outline="#347caf",width=2);c.create_text(x+42,246,text=l,font=B)
    c.create_line(98,246,110,246,arrow="last",fill="#d66b35",width=2);c.create_line(196,246,208,246,arrow="last",fill="#d66b35",width=2);c.create_text(155,318,text="BLUE normal · AMBER degraded\nRED stop and roll back",fill="#72512e",font=F(SANS,13,"bold"),justify="center")
 def pick_current(self):
  if self.current:self.select_id(self.current)
 def select_id(self,bid):
  if len(self.viewed)!=len(BOOKS):return
  self.selected=bid;book=next(x for x in BOOKS if x[0]==self.selected)
  self.foot.itemconfig(self.summary,text=f"{book[1]} · Software Systems Design");self.submit.set(enabled=True);self.refresh_state()
 def submit_loan(self):
  if not self.selected:return
  out=Path(OUTPUT_DIR);out.mkdir(parents=True,exist_ok=True);(out/"purchase.json").write_text(json.dumps({"submitted":True,"selectedBookId":self.selected,"viewedBookIds":sorted(self.viewed)},indent=2),encoding="utf-8");book=next(x for x in BOOKS if x[0]==self.selected)
  for child in self.root.winfo_children():child.destroy()
  c=tk.Canvas(self.root,width=1024,height=866,bg=PARCH,highlightthickness=0);c.pack(fill="both",expand=True)
  c.create_rectangle(0,0,1024,64,fill=WALNUT,outline="");c.create_text(76,31,text="Book",anchor="w",fill=PAPER,font=F(SERIF,28,"bold"));c.create_text(154,31,text="Desk",anchor="w",fill=BRASS_LT,font=F(SERIF,28,"bold","italic"))
  rrect(c,262,190,762,610,18,fill=PAPER,outline=LINE)
  for i in range(276,750,14):c.create_line(i,190,i+6,190,fill=BRASS,width=3)
  c.create_oval(472,236,552,316,fill=OK,outline="");c.create_text(512,276,text="✓",fill=PAPER,font=F(SANS,40,"bold"))
  c.create_text(512,356,text="Loan confirmed",fill=OK,font=F(SERIF,30,"bold"))
  c.create_text(512,420,text=book[1]+"\nSoftware Systems Design · 264 pages",fill=INK,font=F(SANS,17),justify="center")
  c.create_text(512,500,text="Collect it at the loan desk in the reading room.",fill=MUTED,font=F(SANS,14))
if __name__=="__main__":root=tk.Tk();BookDesk(root);root.mainloop()
