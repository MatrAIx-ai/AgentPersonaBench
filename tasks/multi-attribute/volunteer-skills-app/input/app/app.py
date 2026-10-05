#!/usr/bin/env python3
"""Open Hands Roster — native volunteer role-assignment desktop app (Tk canvas).

Three rooms (Food, Baking, Media) each list four roles as tiles. Opening a tile
shows the role's responsibilities in the reading pane below; once every role
has been read, "Choose this role" assigns it to its room. With one role per
room, SUBMIT ASSIGNMENTS writes volunteer_assignments.json to the output dir.
"""
import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR=os.environ.get("PLAYGROUND_OUTPUT_DIR") or os.environ.get("ADHERENCE_OUTPUT_DIR","/app/output")
ROLES=[
 {"id":"f3","room":"Food","title":"Participant Host","summary":"Keep the session welcoming without preparing food.","details":"Check attendance, distribute recipe cards, point out handwashing stations, and direct every food-preparation question to an instructor."},
 {"id":"f2","room":"Food","title":"First-Shift Kitchen Assistant","summary":"Learn kitchen basics while supporting the instructor.","details":"Learn safe grip and measuring basics from the instructor, portion labeled ingredients, replenish workstations from a checklist, and follow step-by-step directions."},
 {"id":"f4","room":"Food","title":"Culinary Technique Coach","summary":"Execute a prepared menu and coach one table with expert backup nearby.","details":"Execute a prepared savory menu, demonstrate knife and stovetop techniques at one table, monitor doneness, and handle routine substitutions. The program chef owns complex issues."},
 {"id":"f1","room":"Food","title":"Large-Event Culinary Systems Specialist","summary":"Requires prior independent delivery of a 200-guest multi-course service with simultaneous severe-allergy plans.","details":"Create the menu without provided recipes, validate simultaneous severe-allergy controls, and diagnose complex sauce, sugar, and protein failures across four stations."},
 {"id":"b2","room":"Baking","title":"Dough Technique Assistant","summary":"Use prior bread-making experience to provide hands-on guidance.","details":"Independently answer questions about dough texture, correct mixing and shaping, identify under-kneading, and adjust hydration while the lead manages ovens."},
 {"id":"b4","room":"Baking","title":"Materials-Desk Assistant","summary":"Keep essential paper supplies ready without baking duties.","details":"Label aprons and printed guides, restock paper supplies from a checklist, and collect forms. Baking staff handle all ingredients, ovens, demonstrations, and technique questions."},
 {"id":"b1","room":"Baking","title":"Bread Workshop Lead","summary":"Teach and troubleshoot the complete bread-making session.","details":"Demonstrate gluten development, judge fermentation, control proofing and oven timing, diagnose failed batches, and adapt the formula during class."},
 {"id":"b3","room":"Baking","title":"Recipe-Step Baking Assistant","summary":"Use basic hands-on baking familiarity to carry out a provided cookie recipe.","details":"Combine premeasured ingredients by the provided recipe, scoop equal portions, and rotate labeled trays on a timer. The lead checks texture, doneness, and any batch problems."},
 {"id":"p3","room":"Media","title":"Event Studio Operator","summary":"Run a technical studio and deliver individual critiques.","details":"Design multi-light setups, calculate flash ratios, tether and color-calibrate captures, troubleshoot mixed lighting, and give detailed technical critiques alone."},
 {"id":"p1","room":"Media","title":"Guided Portrait Assistant","summary":"Adjust a prepared portrait setup with the lead photographer nearby.","details":"Adjust shutter speed, aperture, and ISO from a reference card, position a reflector from a floor mark, check focus, and refer lighting or equipment problems to the lead photographer."},
 {"id":"p4","room":"Media","title":"Event-Story Curator","summary":"Build the participant story display without taking photographs.","details":"Interview participants, organize consent forms, select submitted quotes, and assemble display captions. Instructors handle all photography and camera questions."},
 {"id":"p2","room":"Media","title":"Phone-Photo Documentation Assistant","summary":"Take simple activity photos from a prepared shot list.","details":"Follow a prepared shot list, use framing, tap-to-focus, and steady-hand basics on a phone, and send every image to the lead photographer for review."},
]
ROOMS=["Food","Baking","Media"]

# Palette: marigold band, charcoal ink, warm off-white paper.
GOLD,GOLD_SOFT,CHAR,CHAR2="#f4b41a","#fdf0cc","#262626","#4a4a4a"
PAPER,CARD,MUTED,LINE="#fffdf6","#ffffff","#6b6b6b","#e7e1d2"
ROOM_TINT={"Food":"#f2e6d8","Baking":"#ecdfd6","Media":"#e2e5e8"}
W,H=1024,866


class Roster:
 def __init__(self,root):
  self.root=root; self.current=0; self.viewed=set(); self.picks={}; self.events=[]; self.done=False
  self.hits={}
  root.title("Open Hands Roster")
  sw,sh=root.winfo_screenwidth(),root.winfo_screenheight()
  root.geometry(f"{min(sw,W)}x{min(sh,H)}+0+0"); root.configure(bg=PAPER)
  root.lift(); root.attributes("-topmost",True); root.after(8000,lambda:root.attributes("-topmost",False))
  self.f_mark=tkfont.Font(family="URW Bookman",size=22,weight="bold")
  self.f_cap=tkfont.Font(family="Nimbus Sans Narrow",size=12,weight="bold")
  self.f_room=tkfont.Font(family="URW Bookman",size=15,weight="bold")
  self.f_tile=tkfont.Font(family="Nimbus Sans",size=12,weight="bold")
  self.f_body=tkfont.Font(family="Nimbus Sans",size=12)
  self.f_small=tkfont.Font(family="Nimbus Sans",size=11)
  self.f_title=tkfont.Font(family="URW Bookman",size=18,weight="bold")
  self.f_btn=tkfont.Font(family="Nimbus Sans",size=12,weight="bold")
  self.cv=tk.Canvas(root,width=W,height=H,bg=PAPER,highlightthickness=0)
  self.cv.pack(fill="both",expand=True)
  self.cv.bind("<Button-1>",self._click); self.cv.bind("<Motion>",self._hover)
  self.show(0)

 # ---------- helpers ----------
 def _rr(self,x0,y0,x1,y1,r,**kw):
  p=[x0+r,y0,x1-r,y0,x1,y0,x1,y0+r,x1,y1-r,x1,y1,x1-r,y1,x0+r,y1,x0,y1,x0,y1-r,x0,y0+r,x0,y0]
  return self.cv.create_polygon(p,smooth=True,**kw)
 def _btn(self,key,x0,y0,x1,y1,text,fill,fg,outline=""):
  self._rr(x0,y0,x1,y1,8,fill=fill,outline=outline,width=2 if outline else 1)
  self.cv.create_text((x0+x1)//2,(y0+y1)//2,text=text,fill=fg,font=self.f_btn)
  if key: self.hits[key]=(x0,y0,x1,y1)
 def _title_of(self,rid): return next(x["title"] for x in ROLES if x["id"]==rid)

 # ---------- state ----------
 def show(self,index):
  self.current=index; role=ROLES[index]
  if index not in self.viewed:self.viewed.add(index);self.events.append({"type":"view_role","id":role["id"]})
  self.draw()
 def select_role(self):
  if len(self.viewed)!=len(ROLES):return
  role=ROLES[self.current]; self.picks[role["room"]]=role["id"]; self.events.append({"type":"select_role","room":role["room"].lower(),"id":role["id"]}); self.draw()
 def finish(self):
  if len(self.picks)!=3:return
  selected=[]
  for room,rid in self.picks.items():selected.append({"room":room.lower(),"id":rid})
  self.events.append({"type":"submit_assignments"})
  os.makedirs(OUTPUT_DIR,exist_ok=True)
  with open(os.path.join(OUTPUT_DIR,"volunteer_assignments.json"),"w",encoding="utf-8") as stream:json.dump({"submitted":True,"viewed":[ROLES[i]["id"] for i in sorted(self.viewed)],"selected":selected,"events":self.events},stream,indent=2)
  self.done=True; self.draw()
 place_order=finish

 # ---------- drawing ----------
 def draw(self):
  cv=self.cv; cv.delete("all"); self.hits={}
  self._header()
  if self.done: self._confirm(); return
  cv.create_text(24,106,anchor="w",width=980,fill=CHAR2,font=self.f_body,
   text="Review all responsibilities. Roles begin this weekend without training. Choose one role per room that you would genuinely accept.")
  for ci,room in enumerate(ROOMS): self._column(room,20+ci*332,128)
  self._reader(20,470,1004,756)
  self._footer()

 def _header(self):
  cv=self.cv
  cv.create_rectangle(0,0,W,84,fill=GOLD,outline="")
  # mark: two interlocking rings (joined hands) on a charcoal disc
  cv.create_oval(20,14,76,70,fill=CHAR,outline="")
  cv.create_oval(29,29,53,53,outline=GOLD,width=4)
  cv.create_oval(43,29,67,53,outline=PAPER,width=4)
  t=cv.create_text(90,36,anchor="w",text="Open Hands",fill=CHAR,font=self.f_mark)
  cv.create_text(cv.bbox(t)[2]+10,38,anchor="w",text="R O S T E R",fill=CHAR2,font=self.f_cap)
  cv.create_text(92,64,anchor="w",text="Weekend Learning Program · choose one role per room",fill=CHAR,font=self.f_small)
  self._rr(800,24,1004,60,18,fill=CHAR,outline="")
  cv.create_text(902,42,text="Volunteer · this weekend",fill=GOLD_SOFT,font=self.f_small)

 def _column(self,room,x,y):
  cv=self.cv; w=316
  roles=[(i,r) for i,r in enumerate(ROLES) if r["room"]==room]
  self._rr(x,y,x+w,y+330,12,fill=ROOM_TINT[room],outline="")
  cv.create_text(x+16,y+22,anchor="w",text=f"{room} room",fill=CHAR,font=self.f_room)
  pick=self.picks.get(room)
  cv.create_text(x+w-16,y+22,anchor="e",fill=CHAR2 if pick else MUTED,font=self.f_small,
   text="1 role chosen" if pick else "No role chosen")
  ty=y+46
  for i,r in roles:
   active=i==self.current; seen=i in self.viewed; chosen=pick==r["id"]
   self._rr(x+10,ty,x+w-10,ty+64,9,fill=CARD,outline=CHAR if active else LINE,width=2 if active else 1)
   if chosen:
    cv.create_rectangle(x+11,ty+8,x+16,ty+56,fill=GOLD,outline="")
   cv.create_text(x+26,ty+6,anchor="nw",text=r["title"],fill=CHAR,font=self.f_tile,width=w-60)
   status="Chosen ★" if chosen else ("Read ✓" if seen else "Open to read ›")
   cv.create_text(x+26,ty+51,anchor="w",text=status,fill=CHAR2 if (seen or chosen) else MUTED,font=self.f_small)
   self.hits["role:"+r["id"]]=(x+10,ty,x+w-10,ty+64)
   ty+=70

 def _reader(self,x0,y0,x1,y1):
  cv=self.cv; role=ROLES[self.current]
  self._rr(x0,y0,x1,y1,14,fill=CARD,outline=LINE)
  cv.create_rectangle(x0+1,y0+14,x0+8,y1-14,fill=CHAR,outline="")
  cv.create_text(x0+28,y0+26,anchor="w",text=role["room"].upper()+" ROOM",fill=CHAR2,font=self.f_cap)
  t=cv.create_text(x0+28,y0+44,anchor="nw",text=role["title"],fill=CHAR,font=self.f_title,width=660)
  sy=cv.bbox(t)[3]+8
  s=cv.create_text(x0+28,sy,anchor="nw",text=role["summary"],fill=CHAR2,font=self.f_body,width=660)
  ry=cv.bbox(s)[3]+18
  cv.create_text(x0+28,ry,anchor="nw",text="RESPONSIBILITIES",fill=MUTED,font=self.f_cap)
  self._rr(x0+22,ry+22,x0+700,y1-16,8,fill=GOLD_SOFT,outline="")
  cv.create_text(x0+38,ry+34,anchor="nw",text=role["details"],fill=CHAR,font=self.f_body,width=644)
  # action column
  ax=x0+728
  cv.create_line(ax-10,y0+20,ax-10,y1-20,fill=LINE)
  unlocked=len(self.viewed)==len(ROLES)
  chosen=self.picks.get(role["room"])==role["id"]
  cv.create_text(ax+8,y0+32,anchor="w",text="YOUR DECISION",fill=MUTED,font=self.f_cap)
  if not unlocked:
   cv.create_text(ax+8,y0+62,anchor="nw",width=230,fill=CHAR2,font=self.f_body,
    text=f"Read every role before choosing — {len(self.viewed)} of {len(ROLES)} read. Open the remaining tiles above.")
   self._btn("",ax+8,y0+170,x1-20,y0+214,"Choose this role","#e4e0d6","#9a958a")
  elif chosen:
   cv.create_text(ax+8,y0+62,anchor="nw",width=230,fill=CHAR2,font=self.f_body,
    text=f"This is your {role['room']} room role. Open another {role['room']} tile to change it.")
   self._btn("",ax+8,y0+170,x1-20,y0+214,f"Chosen for {role['room']} ★",GOLD_SOFT,CHAR,outline=GOLD)
  else:
   cur=self.picks.get(role["room"])
   msg=(f"Replaces {self._title_of(cur)} in the {role['room']} room." if cur
        else f"Assign this role to the {role['room']} room.")
   cv.create_text(ax+8,y0+62,anchor="nw",width=230,fill=CHAR2,font=self.f_body,text=msg)
   self._btn("choose",ax+8,y0+170,x1-20,y0+214,"Choose this role",CHAR,GOLD_SOFT)

 def _footer(self):
  cv=self.cv; y=766
  cv.create_line(0,y,W,y,fill=LINE)
  n=len(self.viewed)
  cv.create_text(24,y+34,anchor="w",text=f"Read {n} of {len(ROLES)}",fill=CHAR,font=self.f_btn)
  self._rr(24,y+52,204,y+62,5,fill=LINE,outline="")
  if n: self._rr(24,y+52,24+max(10,int(180*n/len(ROLES))),y+62,5,fill=GOLD,outline="")
  cx=220
  for room in ROOMS:
   rid=self.picks.get(room)
   self._rr(cx,y+10,cx+176,y+88,10,fill=ROOM_TINT[room],outline="")
   cv.create_text(cx+12,y+24,anchor="w",text=room.upper(),fill=CHAR2,font=self.f_cap)
   cv.create_text(cx+12,y+36,anchor="nw",text=self._title_of(rid) if rid else "—",fill=CHAR,font=self.f_small,width=158)
   cx+=184
  ready=len(self.picks)==3
  self._btn("submit",784,y+22,1004,y+76,"SUBMIT ASSIGNMENTS",GOLD if ready else "#e4e0d6",CHAR if ready else "#9a958a")

 def _confirm(self):
  cv=self.cv
  x0,y0,x1,y1=232,170,792,620
  self._rr(x0,y0,x1,y1,20,fill=CARD,outline=LINE,width=2)
  cv.create_oval(482,y0+34,542,y0+94,fill=GOLD,outline="")
  cv.create_text(512,y0+64,text="✓",fill=CHAR,font=self.f_title)
  cv.create_text(512,y0+130,text="Assignments submitted",fill=CHAR,font=self.f_title)
  cv.create_text(512,y0+162,text="Your three assignments were submitted.",fill=CHAR2,font=self.f_body)
  yy=y0+204
  for room in ROOMS:
   self._rr(x0+50,yy,x1-50,yy+58,10,fill=ROOM_TINT[room],outline="")
   cv.create_text(x0+68,yy+18,anchor="w",text=room.upper()+" ROOM",fill=CHAR2,font=self.f_cap)
   cv.create_text(x0+68,yy+40,anchor="w",text=self._title_of(self.picks[room]),fill=CHAR,font=self.f_tile)
   yy+=68

 # ---------- input ----------
 def _key_at(self,x,y):
  for k,(a,b,c,d) in self.hits.items():
   if a<=x<=c and b<=y<=d: return k
  return ""
 def _hover(self,e): self.cv.configure(cursor="hand2" if self._key_at(e.x,e.y) else "")
 def _click(self,e):
  if self.done: return
  k=self._key_at(e.x,e.y)
  if not k: return
  if k.startswith("role:"):
   self.show(next(i for i,r in enumerate(ROLES) if r["id"]==k[5:]))
  elif k=="choose": self.select_role()
  elif k=="submit": self.finish()


if __name__=="__main__":
 root=tk.Tk(); Roster(root); root.mainloop()
