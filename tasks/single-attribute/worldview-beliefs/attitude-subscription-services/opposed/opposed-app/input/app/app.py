#!/usr/bin/env python3
"""CareerSpring Desktop — native Tk app for the OS-APP (computer-use) env.

A three-step booking desk: Profile review -> Mock interview -> Checkout. Each
service step shows six option cards (name + today's price) and a terms pane on
the right; "View terms" opens an option's complete terms there, and "Choose this
option" selects it. On "Confirm checkout" the app itself writes purchase.json.
"""
import json, os, tkinter as tk
from tkinter import font as tkfont
from pathlib import Path

OPTIONS=[
{"id":"p01","section":"profile","name":"Launch","price":"$9 today","terms":"Includes today's profile review. After the first month, $19 is charged every month automatically until you cancel."},
{"id":"p02","section":"profile","name":"Momentum","price":"$16 today","terms":"Includes today's review and one monthly follow-up. Renews automatically at $24 every month until cancelled."},
{"id":"p03","section":"profile","name":"Quarter","price":"$54 today","terms":"Includes today's review and three future credits. $54 is charged automatically every three months unless cancelled."},
{"id":"p04","section":"profile","name":"Direct","price":"$27 today","terms":"A single $27 charge covers today's review. Access closes after feedback is delivered and no further charges occur."},
{"id":"p05","section":"profile","name":"Annual","price":"$149 today","terms":"Includes today's review and monthly credits. $149 is charged today and automatically each year unless cancelled."},
{"id":"p06","section":"profile","name":"Reserve","price":"$32 today","terms":"A single $32 charge covers one review whose date can be moved once. It expires after use and does not renew."},
{"id":"i01","section":"interview","name":"Practice","price":"Free first week","terms":"Today's mock interview is included. After seven days, $24 is charged automatically each month until you cancel."},
{"id":"i02","section":"interview","name":"Advance","price":"$18 today","terms":"Includes today's interview. The plan renews automatically for $29 every month until cancelled."},
{"id":"i03","section":"interview","name":"Session","price":"$35 today","terms":"A single $35 charge covers one mock interview and its report. Access ends after delivery with no future billing."},
{"id":"i04","section":"interview","name":"Quarterly","price":"$69 today","terms":"Includes today's interview and two future credits. $69 is charged automatically every three months unless cancelled."},
{"id":"i05","section":"interview","name":"Complete","price":"$185 today","terms":"Includes today's interview and year-round credits. $185 is charged now and automatically every year until cancelled."},
{"id":"i06","section":"interview","name":"Flexible","price":"$41 today","terms":"A single $41 charge covers one interview that can be rescheduled once. It ends after the report and does not renew."},
]

SECTIONS={
"profile":("Profile review","45-minute review with written feedback"),
"interview":("Mock interview","50-minute interview with feedback report"),
}

# Palette: spruce ink + sunrise orange on linen.
SPRUCE="#1f3b37"; SPRUCE_L="#2e5550"; SUN="#e8792b"; SUN_D="#c9621b"; SUN_L="#fdeedf"
LINEN="#f5f1ea"; PAPER="#ffffff"; INK="#1e2a28"; MUT="#6c7571"; LINE="#ddd6ca"; LEAF="#8fb996"


class App:
    def __init__(self,root):
        self.root=root;self.selected={"profile":None,"interview":None};self.buttons={};self.cards={}
        self.step="profile";self.viewing=None
        root.title("CareerSpring Desktop");root.geometry("1024x866+0+0");root.resizable(False,False);root.configure(bg=LINEN)
        root.lift();root.attributes("-topmost",True);root.after(8000,lambda:root.attributes("-topmost",False))
        F=lambda fam,size,w="normal":tkfont.Font(family=fam,size=size,weight=w)
        self.f_logo=F("URW Bookman",20,"bold");self.f_tag=F("Nimbus Sans",11);self.f_nav=F("Nimbus Sans",12)
        self.f_h1=F("URW Bookman",19,"bold");self.f_h3=F("Nimbus Sans",13,"bold");self.f_body=F("Nimbus Sans",12)
        self.f_name=F("URW Bookman",16,"bold");self.f_price=F("Nimbus Sans",13);self.f_btn=F("Nimbus Sans",12,"bold")
        self.f_step=F("Nimbus Sans",12,"bold");self.f_big=F("URW Bookman",26,"bold");self.f_small=F("Nimbus Sans",10,"bold")
        self.build()

    # ---------------------------------------------------------------- chrome
    def build(self):
        head=tk.Frame(self.root,bg=SPRUCE,height=70);head.pack(fill="x");head.pack_propagate(False)
        mark=tk.Canvas(head,width=44,height=44,bg=SPRUCE,highlightthickness=0);mark.pack(side="left",padx=(26,10))
        # sprout rising from a coiled spring
        for k in range(3):
            y=36-k*7;mark.create_arc(10,y-6,34,y+6,start=180,extent=180,style="arc",outline=SUN,width=3)
        mark.create_line(22,20,22,6,fill=LEAF,width=3)
        mark.create_oval(22,2,36,12,fill=LEAF,outline=LEAF);mark.create_oval(8,6,22,15,fill=LEAF,outline=LEAF)
        t=tk.Frame(head,bg=SPRUCE);t.pack(side="left")
        tk.Label(t,text="CareerSpring",font=self.f_logo,bg=SPRUCE,fg="white").pack(anchor="w")
        tk.Label(t,text="Expert support for your next application",font=self.f_tag,bg=SPRUCE,fg="#b9cdc8").pack(anchor="w")
        nav=tk.Frame(head,bg=SPRUCE);nav.pack(side="right",padx=24)
        for s in ("Book services","My sessions","Resources"):
            tk.Label(nav,text=s,font=self.f_nav,bg=SPRUCE,fg="white" if s=="Book services" else "#b9cdc8",padx=10).pack(side="left")

        self.stepbar=tk.Frame(self.root,bg=PAPER,highlightthickness=1,highlightbackground=LINE);self.stepbar.pack(fill="x")
        self.body=tk.Frame(self.root,bg=LINEN);self.body.pack(fill="both",expand=True,padx=24,pady=(14,18))
        self.render()

    def render(self):
        for w in self.stepbar.winfo_children():w.destroy()
        for w in self.body.winfo_children():w.destroy()
        self.buttons={};self.cards={}
        steps=[("profile","1  Profile review"),("interview","2  Mock interview"),("checkout","3  Checkout")]
        for key,label in steps:
            on=key==self.step
            done=key!="checkout" and self.selected[key] is not None
            ok=key!="checkout" or all(self.selected.values())
            txt=label+("   ✓" if done else "")
            b=tk.Button(self.stepbar,text=txt,font=self.f_step,relief="flat",bd=0,padx=22,pady=10,
                        bg=SUN_L if on else PAPER,fg=SUN_D if on else (INK if ok else "#b3aca2"),
                        activebackground=SUN_L,command=lambda k=key:self.go(k))
            b.pack(side="left",padx=(24 if key=="profile" else 0,0))
            if key!="checkout":tk.Label(self.stepbar,text="›",font=self.f_step,bg=PAPER,fg=MUT).pack(side="left",padx=4)
        if self.step=="checkout":self.checkout_view()
        else:self.section_view(self.step)

    def go(self,key):
        if key=="checkout" and not all(self.selected.values()):
            missing=[SECTIONS[k][0] for k,v in self.selected.items() if v is None]
            self.flash("Choose an option for "+" and ".join(missing)+" first.");return
        self.step=key;self.viewing=None;self.render()

    def flash(self,msg):
        if hasattr(self,"msg") and self.msg.winfo_exists():self.msg.config(text=msg)

    # ------------------------------------------------------------- a section
    def section_view(self,key):
        title,sub=SECTIONS[key]
        top=tk.Frame(self.body,bg=LINEN);top.pack(fill="x")
        tk.Label(top,text=title,font=self.f_h1,bg=LINEN,fg=INK).pack(side="left")
        tk.Label(top,text="   "+sub,font=self.f_body,bg=LINEN,fg=MUT).pack(side="left",pady=(6,0))
        tk.Label(self.body,text="Choose one option in each section. Quality and appointment availability are identical. Open the terms for complete billing details.",
                 font=self.f_body,bg="#efe6d6",fg="#4d4536",anchor="w",justify="left",wraplength=940,padx=12,pady=7).pack(fill="x",pady=(10,12))
        main=tk.Frame(self.body,bg=LINEN);main.pack(fill="both",expand=True)
        self.pane=tk.Frame(main,bg=PAPER,width=372,highlightthickness=1,highlightbackground=LINE)
        self.pane.pack(side="right",fill="y",padx=(18,0),pady=6);self.pane.pack_propagate(False)
        grid=tk.Frame(main,bg=LINEN);grid.pack(side="left",fill="both",expand=True)
        for c in (0,1):grid.grid_columnconfigure(c,weight=1,uniform="c")
        opts=[o for o in OPTIONS if o["section"]==key]
        for i,o in enumerate(opts):
            r,c=divmod(i,2);grid.grid_rowconfigure(r,weight=1,uniform="r")
            self.card(grid,o).grid(row=r,column=c,sticky="nsew",padx=(0,7) if c==0 else (7,0),pady=6)
        self.fill_pane()

    def card(self,parent,o):
        chosen=self.selected[o["section"]] is o;viewing=self.viewing is o
        bg=SUN_L if chosen else PAPER
        c=tk.Frame(parent,bg=bg,highlightthickness=2,highlightbackground=SUN if (chosen or viewing) else LINE)
        tk.Frame(c,bg=SUN if chosen else SPRUCE_L,width=6).pack(side="left",fill="y")
        inner=tk.Frame(c,bg=bg);inner.pack(side="left",fill="both",expand=True,padx=16,pady=12)
        tk.Label(inner,text=o["name"],font=self.f_name,bg=bg,fg=INK,anchor="w").pack(fill="x")
        tk.Label(inner,text=o["price"],font=self.f_price,bg=bg,fg=SPRUCE_L,anchor="w").pack(fill="x",pady=(2,0))
        tk.Frame(inner,bg=LINE,height=1).pack(fill="x",pady=(10,6))
        tk.Label(inner,text="Coach-led video call\nAny open slot this week",font=self.f_body,bg=bg,fg=MUT,anchor="w",justify="left").pack(fill="x")
        row=tk.Frame(inner,bg=bg);row.pack(side="bottom",fill="x")
        b=tk.Button(row,text="View terms",font=self.f_btn,relief="flat",bd=0,padx=14,pady=6,
                    bg=SPRUCE if not viewing else SPRUCE_L,fg="white",activebackground=SPRUCE_L,activeforeground="white",
                    command=lambda x=o:self.view(x))
        b.pack(side="left");self.buttons[o["id"]]=b
        if chosen:tk.Label(row,text="✓ Chosen",font=self.f_small,bg=bg,fg=SUN_D).pack(side="right")
        return c

    def fill_pane(self):
        p=self.pane
        for w in p.winfo_children():w.destroy()
        tk.Label(p,text="TERMS",font=self.f_small,bg=PAPER,fg=SUN_D).pack(anchor="w",padx=22,pady=(20,0))
        o=self.viewing
        if o is None:
            tk.Label(p,text="Select View terms on an option to read its complete terms here.",font=self.f_body,
                     bg=PAPER,fg=MUT,wraplength=320,justify="left").pack(anchor="w",padx=22,pady=(10,0))
        else:
            tk.Label(p,text=o["name"],font=self.f_h1,bg=PAPER,fg=INK).pack(anchor="w",padx=22,pady=(6,0))
            tk.Label(p,text=o["price"],font=self.f_h3,bg=PAPER,fg=SPRUCE_L).pack(anchor="w",padx=22)
            tk.Label(p,text=o["terms"],font=self.f_body,bg=LINEN,fg=INK,wraplength=296,justify="left",
                     padx=14,pady=14,anchor="w").pack(fill="x",padx=22,pady=(14,0))
            chosen=self.selected[o["section"]] is o
            tk.Button(p,text="✓ Chosen" if chosen else "Choose this option",font=self.f_btn,relief="flat",bd=0,pady=10,
                      bg=SUN if not chosen else SUN_L,fg="white" if not chosen else SUN_D,
                      activebackground=SUN_D,activeforeground="white",command=lambda:self.choose(o)).pack(fill="x",padx=22,pady=(16,0))
        self.msg=tk.Label(p,text="",font=self.f_body,bg=PAPER,fg=SUN_D,wraplength=320,justify="left");self.msg.pack(anchor="w",padx=22,pady=(12,0))
        foot=tk.Frame(p,bg=PAPER);foot.pack(side="bottom",fill="x",padx=22,pady=18)
        for k in ("profile","interview"):
            s=self.selected[k]
            r=tk.Frame(foot,bg=PAPER);r.pack(fill="x",pady=2)
            tk.Label(r,text=SECTIONS[k][0],font=self.f_body,bg=PAPER,fg=MUT).pack(side="left")
            tk.Label(r,text=s["name"] if s else "—",font=self.f_h3,bg=PAPER,fg=INK).pack(side="right")
        nxt="interview" if self.step=="profile" else "checkout"
        tk.Button(foot,text="Continue to "+("Mock interview" if nxt=="interview" else "Checkout")+"  ›",font=self.f_btn,relief="flat",bd=0,pady=9,
                  bg=SPRUCE,fg="white",activebackground=SPRUCE_L,activeforeground="white",command=lambda:self.go(nxt)).pack(fill="x",pady=(10,0))

    def view(self,o):
        self.viewing=o;self.render()

    def choose(self,option):
        self.selected[option["section"]]=option;self.render()

    # -------------------------------------------------------------- checkout
    def checkout_view(self):
        tk.Label(self.body,text="Review and confirm",font=self.f_h1,bg=LINEN,fg=INK).pack(anchor="w")
        tk.Label(self.body,text="Your services for this week's applications.",font=self.f_body,bg=LINEN,fg=MUT).pack(anchor="w",pady=(2,14))
        box=tk.Frame(self.body,bg=PAPER,highlightthickness=1,highlightbackground=LINE);box.pack(fill="x")
        for k in ("profile","interview"):
            o=self.selected[k]
            r=tk.Frame(box,bg=PAPER);r.pack(fill="x",padx=24,pady=(18,0))
            left=tk.Frame(r,bg=PAPER);left.pack(side="left",fill="x",expand=True)
            tk.Label(left,text=SECTIONS[k][0].upper(),font=self.f_small,bg=PAPER,fg=SUN_D).pack(anchor="w")
            tk.Label(left,text=f"{o['name']}  ·  {o['price']}",font=self.f_name,bg=PAPER,fg=INK).pack(anchor="w")
            tk.Label(left,text=o["terms"],font=self.f_body,bg=PAPER,fg=MUT,wraplength=720,justify="left").pack(anchor="w",pady=(2,0))
            tk.Button(r,text="Change "+SECTIONS[k][0].lower(),font=self.f_btn,relief="flat",bd=0,padx=12,pady=6,bg=LINEN,fg=INK,
                      activebackground=LINE,command=lambda kk=k:self.go(kk)).pack(side="right",anchor="n")
            tk.Frame(box,bg=LINE,height=1).pack(fill="x",padx=24,pady=(16,0))
        tk.Button(box,text="Confirm checkout",font=self.f_btn,relief="flat",bd=0,padx=26,pady=11,bg=SUN,fg="white",
                  activebackground=SUN_D,activeforeground="white",command=self.confirm).pack(anchor="e",padx=24,pady=20)

    def confirm(self):
        if not all(self.selected.values()):return
        out=Path(os.environ.get("ADHERENCE_OUTPUT_DIR","/app/output"));out.mkdir(parents=True,exist_ok=True)
        ids=[self.selected["profile"]["id"],self.selected["interview"]["id"]]
        (out/"purchase.json").write_text(json.dumps({"submitted":True,"selectedOptionIds":ids},indent=2))
        for w in self.body.winfo_children():w.destroy()
        for w in self.stepbar.winfo_children():w.destroy()
        box=tk.Frame(self.body,bg=PAPER,highlightthickness=1,highlightbackground=LINE);box.pack(fill="both",expand=True,padx=150,pady=90)
        tk.Label(box,text="✓",bg=PAPER,fg=SUN,font=self.f_big).pack(pady=(90,6))
        tk.Label(box,text="Checkout confirmed",bg=PAPER,fg=SPRUCE,font=self.f_big).pack()
        tk.Label(box,text=f"Profile: {self.selected['profile']['name']}\nMock interview: {self.selected['interview']['name']}",
                 bg=PAPER,fg=INK,font=self.f_price,justify="center").pack(pady=20)

if __name__=="__main__":
    root=tk.Tk();App(root);root.mainloop()
