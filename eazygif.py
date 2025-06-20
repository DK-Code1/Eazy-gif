import customtkinter as ctk
from CTkToolTip import *
from tkinter import filedialog, Event
from PIL import Image, ImageTk

import os
import cv2
import platform

import threading
import time

import importlib # debug
import ffexports
import settings
from pymediainfo import MediaInfo


os.environ["PATH"] = os.path.dirname(__file__) + os.pathsep + os.environ["PATH"]
context = "auto" if platform.system() == "Windows" else "x11" # Linux uses x11 for mpv embedding into the frame  

import mpv

# Tkinter GUI to display frames
class VideoTools:
    def __init__(self, root, video_path):
        self.root = root
        self.video_path = video_path

        self.video_name = os.path.basename(self.video_path)

        self.cap = cv2.VideoCapture(self.video_path, cv2.CAP_ANY)



        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))


        print("frame count is", self.frame_count)

        self.audio_tracks = self.get_audio_count()

        print(self.audio_tracks)


        self.videosettings = settings.videosettings(self) ## initialize video settings

        self.start = 0  # cut position in frames, initial is 0
        self.finish = 0

    
        #Cut position canvas
        self.color_canvas = ctk.CTkCanvas(root, bg = "Yellow")


        
        self.player_frame = ctk.CTkFrame(root, fg_color="#363c49")

        self.player_frame.pack(pady=10, padx= 10, fill="both", expand=True)

        self.root.update_idletasks() # Wait for frame widget, it's important to wait before appending mpv




        self.player = mpv.MPV(wid=str(int(self.player_frame.winfo_id())), vo='gpu', gpu_context=context, keepaspect=True, background_color="#363c49")
        self.player.loadfile(self.video_path)
        self.player.command("cycle", "pause")
        self.player.property_add("keep-open")
        self.player.property_add("keepaspect-window")
        
        self.player.observe_property("time-pos", self.observer_func)
        self.player.observe_property("core-idle", self.toggle_idle)

        self.is_idle = True

        self.player_frame.bind("<Button>", self.crop_handle)
        self.player_frame.bind("<B1-Motion>", self.crop_handle_drag)
        self.player_frame.bind("<ButtonRelease>", self.crop_validation)
        self.player_frame.bind("<MouseWheel>", self.handle_wheel) 
        self.player_frame.bind("<Configure>", self.resize_handle)


        
        self.crop_line_x1 = ctk.CTkButton(root, text="",fg_color=("white", "cyan"),corner_radius=0,height=4, width=4, cursor="sizing")
        self.crop_line_x2 = ctk.CTkButton(root, text="",fg_color=("white", "cyan"),corner_radius=0,height=4, width=4, cursor="sizing")
        self.crop_line_y1 = ctk.CTkButton(root, text="",fg_color=("white", "cyan"),corner_radius=0,height=4, width=4, cursor="sizing")
        self.crop_line_y2 = ctk.CTkButton(root, text="",fg_color=("white", "cyan"),corner_radius=0,height=4, width=4, cursor="sizing")

        self.crop_line_x1.bind("<B1-Motion>", lambda e: self.resize_border_by_side(e, "left"), add="+")
        self.crop_line_x2.bind("<B1-Motion>", lambda e: self.resize_border_by_side(e, "right"), add="+")
        self.crop_line_y1.bind("<B1-Motion>", lambda e: self.resize_border_by_side(e, "top"), add="+")
        self.crop_line_y2.bind("<B1-Motion>", lambda e: self.resize_border_by_side(e, "bottom"), add="+")

        self.crop_line_x1.bind("<ButtonRelease>", self.crop_validation, add="+")
        self.crop_line_x2.bind("<ButtonRelease>", self.crop_validation, add="+")
        self.crop_line_y1.bind("<ButtonRelease>", self.crop_validation, add="+")
        self.crop_line_y2.bind("<ButtonRelease>", self.crop_validation, add="+")

        #print("\n", f"estimated frame count from mpv is: {self.player._get_property("estimated-frame-count")} \n estimated from opencv2 is : {self.frame_count}")




        self.crop_created = False
        self.crop_finished = False
        self.latest_coords = [0,0,0,0]
        self.crop_percentages = "no"
        self.crop_start = (0,0)
        
        self.cut_finished = False
        




        #### OSD-DIMENSIONS on mpv could help

        # Add a slider to navigate frames

        self.current_frame = ctk.IntVar()

        self.slider = ctk.CTkSlider(root, from_=0, to=self.frame_count, number_of_steps=self.frame_count -1, variable=self.current_frame ,command=self.extract_frame_mpv)
        self.slider.pack( pady=10,fill=ctk.X)

        self.tooltip_slider = CTkToolTip(self.slider, message="0")



        #self.slider.lift()




        self.frame = ctk.CTkFrame(root)

        self.frame.pack()

        self.backward_button = ctk.CTkButton(self.frame, text="0.5s <<", border_width=2, border_color="black", command=lambda: self.button_seek("backward"))
        self.backward_button.pack(side="left")

        self.playbutton = ctk.CTkButton(self.frame, text="Play / Pause", border_width=2, border_color="black", command=lambda: self.player.command("cycle", "pause"))
        self.playbutton.pack(side="left")

        self.forward_button = ctk.CTkButton(self.frame, text=">> 0.5s", border_width=2, border_color="black", command=lambda: self.button_seek("forward"))
        self.forward_button.pack(side="left")


        self.options_frame = ctk.CTkFrame(root)



        self.size_frame= ctk.CTkFrame(self.options_frame)

        self.size_label = ctk.CTkLabel(self.size_frame, text="Size(px):")
        self.size_entry = ctk.CTkEntry(self.size_frame)
        self.size_entry.insert(ctk.END, "500")
        self.tooltip_size= CTkToolTip(self.size_entry, message="Size of the output, being WIDTH (This input) x Auto, it maintains aspect ratio of the input.")


        self.size_label.pack(side= "left")
        self.size_entry.pack(side= "left")
        self.size_frame.pack(anchor="e")

        self.fps_frame= ctk.CTkFrame(self.options_frame)

        self.fps_label = ctk.CTkLabel(self.fps_frame, text="Fps:")
        self.fps_entry = ctk.CTkEntry(self.fps_frame)
        self.fps_entry.insert(ctk.END, self.fps)

        self.fps_label.pack(side= "left")
        self.fps_entry.pack(side= "left")
        self.fps_frame.pack(anchor="e")
        self.tooltip_fps= CTkToolTip(self.fps_entry, message="Fps of the output, for Gif files is recommended to use maximum of 30fps, for videos it is recommended to use the original.")

               
        self.speed_frame= ctk.CTkFrame(self.options_frame)

        self.speed_label = ctk.CTkLabel(self.speed_frame, text="Speed:")
        self.speed_entry = ctk.CTkEntry(self.speed_frame)
        self.speed_entry.insert(ctk.END, 1)

        self.tooltip_speed= CTkToolTip(self.speed_entry, message="Speed of the output, 1 being normal speed, half speed is 0.5, double video speed is 2.")


        

        self.speed_label.pack(side= "left")
        self.speed_entry.pack(side= "left")
        self.speed_frame.pack(anchor="e")





        self.options_frame.pack(side="left")


        self.start_button = ctk.CTkButton(root, text="Set start", command= lambda:  self.set_start(self.current_frame.get()), border_width=2 ,border_color="black")
        self.start_button.pack(pady=2,)

        self.tooltip_start = CTkToolTip(self.start_button, message="Marks the start cut of the output file.")

        self.final_button = ctk.CTkButton(root, text="Set finish", command= lambda: self.set_finish(self.current_frame.get()), border_width=2 ,border_color="black")
        self.final_button.pack(pady=2, )

        self.tooltip_end = CTkToolTip(self.final_button, message="Marks the end cut of the output file.")

        self.cut_button = ctk.CTkButton(root, text="Cut video (No reencode)", command= lambda: self.cut_video(), border_width=2 ,border_color="black")
        self.cut_button.pack(pady=2, )

        self.tooltip_cutvideo = CTkToolTip(self.cut_button, message="This option allows you to cut the video but without being able to crop it.")

        self.convert_button = ctk.CTkButton(root, text="Convert", command= lambda: self.export_video(), border_width=2 ,border_color="black")
        self.convert_button.pack(pady=2, )

        self.tooltip_convert = CTkToolTip(self.convert_button, message="Converts the video with reencoding and being able to use cropping.")
        


        self.create_gif_button = ctk.CTkButton(root, text="Create gif", state="disabled" ,border_width=2 ,border_color="black", command= lambda: self.create_gif(file, output, frame_to_time(self.start, self.fps), frame_to_time(self.finish, self.fps), "", 500))
        self.create_gif_button.pack(pady=2, )

        self.clear_button = ctk.CTkButton(root, text="Video settings", border_width=2 ,border_color="black", command=lambda: self.videosettings.toggle_visibility())
        self.clear_button.pack()

        self.crop_button = ctk.CTkButton(root, text="Toggle cropping", border_width=2 ,border_color="black", command=self.add_crop_borders)
        self.crop_button.pack()

        self.tooltip_crop = CTkToolTip(self.crop_button, message="Enable or disable cropping to the video output, normally you can click and draw cropping borders easily, but linux users may need to click this first")

        # self.crop_button = ctk.CTkButton(root, text="Calculate crop", border_width=2 ,border_color="black", command=self.calculate_crop)
        # self.crop_button.pack()
        


        #self.canvas.bind("<Button>", self.handle_click)
        #self.canvas.bind("<ButtonRelease>", self.handle_release)
        #self.canvas.bind("<Motion>", self.handle_movement)
        #self.canvas.bind("<B1-Motion>", self.handle_drag)

        #root.after(100, self.slider.set(0)) ##CTKslider workaround to set position on start

        #root.after(100, self.extract_frame, 0) ##Must be after render to extract and resize the frame to window size

        #root.after(200,self.canvas.bind, "<Configure>", self.on_resize) ## Old, set image with opencv2
    
        root.after(200,self.slider.bind, "<Configure>", self.on_resize_slider)

        root.mainloop()

    # def view_gif(self):
    #     gif_viewer = GifViewer.gifFrameViewer()

    def toggle_idle(self, property_name, new):

        #print("toggled!")

        self.is_idle = new
        
    def observer_func(self, name, value):
        #print("\n pos changed!!", name, value)

        #if not self.is_idle:
        if value:
            to_frame = int(value * self.fps)
            self.current_frame.set(to_frame)
            self.root.title(f"{self.video_name} ({frame_to_time(to_frame, self.fps)}) - Eazy gif")
            if self.start > 0:
                if not self.cut_finished:
                    self.move_cut_canvas()



    def resize_border_by_side(self, event, side): ## Might need improvement

        ## get current coords while compensating the video frame padding
        coords = [self.crop_line_x1.winfo_x() - 10, self.crop_line_y1.winfo_y() -10, self.crop_line_x2.winfo_x() -10, self.crop_line_y2.winfo_y() -10] 
        new_coords = coords

        #resize the selected border area

        if side == "left":

            new_coords[0] = coords[0] + event.x
            if coords[2] - new_coords[0] > 10: # set a minimum resize of 10
                self.position_crop_borders(new_coords)
                return

        if side == "right":

            new_coords[2] = coords[2] + event.x
            if coords[2] - new_coords[0] > 10: # set a minimum resize of 10
                self.position_crop_borders(new_coords)
                return

        if side == "top":
            
            new_coords[1] = coords[1] + event.y
            if coords[3] - coords[1] > 10:
                self.position_crop_borders(new_coords)
                return
       
        if side == "bottom":
            frame_height = self.player_frame.winfo_height()

            new_coords[3] = coords[3] + event.y if coords[3] + event.y <  frame_height else frame_height
            if coords[3] - coords[1] > 10:
                self.position_crop_borders(new_coords)
                return

    def button_seek(self, direction): ## Seek by half a second buttons
        if direction == "forward":
            self.player.seek(amount="0.5",precision="exact")
            self.slider.set(self.player._get_property("estimated-frame-number"))

        else:
            self.player.seek(amount="-0.5",precision="exact")
            self.slider.set(self.player._get_property("estimated-frame-number"))
    


    def crop_validation(self,event):

        print("button released")

        if event.num == 1:

            print("validating crop")
    
            #player_frame_start_x = self.player_frame.winfo_x()
            #player_frame_start_y = self.player_frame.winfo_y()
    
            player_frame_width = self.player_frame.winfo_width()
            player_frame_height = self.player_frame.winfo_height()
    
            coords = [self.crop_line_x1.winfo_x() - 10, self.crop_line_y1.winfo_y() -10, self.crop_line_x2.winfo_x() -10, self.crop_line_y2.winfo_y() -10] 
    
            print("cords are: ", coords)
    
            player_spaces = self.player._get_property("osd-dimensions") # Get borders of the player, they appear when video auto resizes to window size.
            player_blank_space = player_spaces["ml"], player_spaces["mt"], player_spaces["mr"], player_spaces["mb"] # Get them into an array

            new_coords = coords

            if coords[0] < player_blank_space[0]:
                print("coords out of bound")
                new_coords[0] = player_blank_space[0] -4

            if coords[1] < player_blank_space[1]:
                new_coords[1] = player_blank_space[1] -4

            if coords[2] > player_frame_width - player_blank_space[2]:
                new_coords[2] = player_frame_width - player_blank_space[2]
                
            if coords[3] > player_frame_height - player_blank_space[3]:
                new_coords[3] = player_frame_height - player_blank_space[3]

            print(new_coords)

            self.position_crop_borders(new_coords)
            
            self.crop_finished = True
            self.save_percentages()
            
    
            



    def resize_handle(self, event):

        dimensions = self.player._get_property("osd-dimensions")


        #self.player.string_command("show_text", dimensions)

        if self.crop_finished:
            
            player_spaces = self.player._get_property("osd-dimensions")
            player_blank_space = player_spaces["ml"], player_spaces["mt"], player_spaces["mr"], player_spaces["mb"]

            horizontal_black_bars = player_blank_space[0] + player_blank_space[2]
            vertical_black_bars = player_blank_space[1] + player_blank_space[3]

            new_x =  player_blank_space[0] + (self.crop_percentages[0] * (player_spaces["w"] - horizontal_black_bars) ) 
            new_y =  player_blank_space[1] + (self.crop_percentages[1] * (player_spaces["h"] - vertical_black_bars) )

            new_x2 = player_blank_space[0] + (self.crop_percentages[2] * (player_spaces["w"] - horizontal_black_bars) )
            new_y2 = player_blank_space[1] + (self.crop_percentages[3] * (player_spaces["h"] - vertical_black_bars) )
            
            


            print("recalculated dimensions are: ",  new_x, new_y, new_x2, new_y2) 

            

            self.position_crop_borders((new_x -4, new_y -4, new_x2, new_y2)) #Applying 4 considering the width of the border

    def save_percentages(self):

        ## latest coords already adjust the 10px padding of the frame

        coords = self.latest_coords 

        print("latest coords: ", coords)

        #print(f"player dimensions are,x = {self.player_frame.winfo_screenwidth()}, y={self.player_frame.winfo_screenheight()}")

        player_spaces = self.player._get_property("osd-dimensions") # Get general dimensions of the player

        player_blank_space = player_spaces["ml"], player_spaces["mt"], player_spaces["mr"], player_spaces["mb"] # Get black bards, they appear when video auto resizes to window size.

        print("blank spaces are: ", player_blank_space)

        ## +4 to compensate the border width, x2 and y2 doesn't need them because winfo_x and winfo_y starts just where the border starts visually
        x1 = (coords[0]+4) - player_blank_space[0] # Calculating considering all spaces
        y1 = (coords[1]+4) - player_blank_space[1]
        x2 = (coords[2]) - player_blank_space[0]
        y2 = (coords[3]) - player_blank_space[1]

        print(x1,y1,x2,y2)

        print("player spaces are: w and h =  ", player_spaces["w"], player_spaces["h"])


        x1_percentage = (x1 ) / (player_spaces["w"] - (player_blank_space[0] + player_blank_space[2]) ) # Percentage of relative position
        y1_percentage = (y1 ) / (player_spaces["h"] - (player_blank_space[1] + player_blank_space[3]) )

        x2_percentage = (x2) / (player_spaces["w"] - (player_blank_space[0] + player_blank_space[2]) )
        y2_percentage = (y2) / (player_spaces["h"] - (player_blank_space[1] + player_blank_space[3]) )

        print("y2 *100 = ", y2*100)
        print("spaces h - blank space= ", player_spaces["h"] - player_blank_space[3])



        self.crop_percentages = [x1_percentage, y1_percentage, x2_percentage, y2_percentage ]

        print(self.crop_percentages)


    def position_crop_borders(self, coords):

        self.crop_line_x1.place(in_=self.player_frame, x=coords[0], y=coords[1])
        self.crop_line_x1.configure(height=coords[3] - coords[1])

        self.crop_line_y1.place(in_=self.player_frame, x=coords[0], y=coords[1])
        self.crop_line_y1.configure(width=coords[2] - coords[0])


        self.crop_line_x2.place(in_=self.player_frame, x=coords[2], y=coords[1])
        self.crop_line_x2.configure(height=coords[3] - coords[1])


        self.crop_line_y2.place(in_=self.player_frame, x=coords[0], y=coords[3])
        self.crop_line_y2.configure(width=coords[2] - coords[0])

        self.latest_coords = coords

        #if self.crop_latest_size_percentages == "no":
        #    self.save_percentages()

    def add_crop_borders(self):

        print("adding new crop!!")

        if not self.crop_created:

            player_frame_width = self.player_frame.winfo_width() ## Video width used to calculate position
            player_frame_height = self.player_frame.winfo_height()
    
            start_pos = [20, 20, player_frame_width, player_frame_height]
            self.latest_coords = start_pos
            
    
            
    
            self.position_crop_borders(start_pos)
    
            self.root.update_idletasks()
            self.crop_created = True
    
            fake_event = Event()
    
            fake_event.num = 1
    
            self.crop_validation(fake_event)
        else:

            self.crop_line_x1.place_forget()
            self.crop_line_x2.place_forget()
            self.crop_line_y1.place_forget()
            self.crop_line_y2.place_forget()
            self.crop_created = False
            self.crop_finished = False
            self.crop_percentages = "no"







        

    def crop_handle_drag(self, event):
        #print(event)
        if self.crop_created and not self.crop_finished: ## Will work later

            player_frame_width = self.player_frame.winfo_width() ## Video width used to calculate position
            player_frame_height = self.player_frame.winfo_height()


            fixed_y = event.y if  event.y < player_frame_height else player_frame_height ## Don't allow crop go outside video frame
            fixed_x = event.x if  event.x < player_frame_width else player_frame_width

            #print(fixed_x, fixed_y)


            if fixed_y < self.crop_start[1]:
               if fixed_x < self.crop_start[0]:
                    coords = [fixed_x, fixed_y, self.crop_start[0], self.crop_start[1]]
                    self.position_crop_borders(coords)
                    return
               else:
                    coords = [self.crop_start[0], fixed_y, fixed_x, self.crop_start[1]]
                    self.position_crop_borders(coords)
                    return
            if fixed_x < self.crop_start[0]:
                    
                    coords = [fixed_x, self.crop_start[1], self.crop_start[0], fixed_y]
                    self.position_crop_borders(coords)
                    return                


            else:
                #print("proceed anyways")
                coords = [self.crop_start[0], self.crop_start[1], fixed_x, fixed_y]
                self.position_crop_borders(coords)



    def crop_handle(self, event):
        print(event)
        if event.num == 1: #left click
            if not self.crop_created:
                self.crop_start = (event.x, event.y)

                self.position_crop_borders([event.x, event.y, event.x +10, event.y+10])
                # self.crop_line_x1.place(in_=self.player_frame, x=event.x, y=event.y)
                # self.crop_line_x2.place(in_=self.player_frame, x=event.x, y=event.y +10)
                # self.crop_line_y1.place(in_=self.player_frame, x=event.x, y=event.y)
                # self.crop_line_y2.place(in_=self.player_frame, x=event.x, y=event.y +10)

                self.crop_created = True
        if event.num == 3: #right click
            self.crop_line_x1.place_forget()
            self.crop_line_x2.place_forget()
            self.crop_line_y1.place_forget()
            self.crop_line_y2.place_forget()
            self.crop_created = False
            self.crop_finished = False
            self.crop_percentages = "no"






    def extract_frame_mpv(self, framenumber):

        #print("directly changed")

        percentage = (framenumber *100 ) / self.frame_count

        #print("percentage is: ", percentage)


        self.tooltip_slider.configure(message=int(framenumber))

        self.player.seek(amount=str(percentage),reference="absolute-percent", precision="exact")

        #timestamp = self.player._get_property("time-pos/full")
        #timestamp2 = self.player._get_property("video-frame-info/estimated-smpte-timecode")
       
        #print(timestamp)
        #print(timestamp2)
        #print(self.player.prop)
        #print("\n", f"estimated frame from mpv is: {self.player._get_property("estimated-frame-number")} \n estimated from opencv2 is : {framenumber}")

        if self.start > 0: #update canvas if user is cutting the video.
            self.move_cut_canvas()

    



    def handle_movement(self, event): ##Mouse movement // Resizing border

        if self.border_exists: # Check if border exists first.

            # This code sets the border part that is currently being selected so the drag event can resize it

            rectangle = self.canvas.bbox(self.image_border)
    
            in_range_x = False
            in_range_y = False
            in_range_x2 = False
            in_range_y2 = False
    
            in_range = lambda a : a in range(-5, 5 )
    
            self.canvas.configure(cursor = "arrow")
    
            if in_range(rectangle[0] - event.x):
                in_range_x = True
            if in_range(rectangle[1] - event.y):
                in_range_y = True
            if in_range(rectangle[2] - event.x):
                in_range_x2 = True
            if in_range(rectangle[3] - event.y):
                in_range_y2 = True
    
            if in_range_x and event.y > rectangle[1]:
                #print("touched left border")
                self.canvas.configure(cursor = "sizing")
                self.resizing_part = "x"
    
            if in_range_y:
                #print("touched upper border")
                self.canvas.configure(cursor = "sizing")
                self.resizing_part = "y"
    
            if in_range_x2:
                #print("touched right border")
                self.canvas.configure(cursor = "sizing")
                self.resizing_part = "x2"
    
            if in_range_y2:
                #print("touched bottom border")
                self.canvas.configure(cursor = "sizing")
                self.resizing_part = "y2"
    

    def handle_wheel(self, event):
        #print(event)

        #if event.delta > 0:
        #    print("wheel up")
        #    self.slider.set(int(self.slider.get() +1)) #slider +1 
        #    self.extract_frame(int(self.slider.get())) #set frame +1 

        #else:
        #    print("wheel down")
        #    self.slider.set(int(self.slider.get() -1)) #slider -1 
        #    self.extract_frame(int(self.slider.get())) #set frame -1 

        if event.delta > 0:
            self.player.frame_step()
        else:
            self.player.frame_back_step()




    def move_cut_canvas(self):

        if self.start > 0:

            #print("moving cut canvas")

            finish_cut = self.finish if self.finish != 0 else self.slider.get()
            
            slider_width = self.slider.winfo_width()
    
            frame_start = (self.start * 100) / self.frame_count
    
            frame_finish = (finish_cut * 100) / self.frame_count
    
            start_color = (frame_start * slider_width) / 100
    
            end_color =  (frame_finish * slider_width) / 100
    
            color_width = end_color - start_color
    
            self.color_canvas.place(height=45, width=color_width,x= start_color, y=self.slider.winfo_y()-10)

            




    def go_forward(self, direction):
        if direction == "forward":
            self.slider.set(self.slider.get() + 12)
        else:
            self.slider.set(self.slider.get() - 12)

        self.extract_frame(int(self.slider.get()))

    def create_gif(self, input_file, output, start_time, end_time, thetext, size):

        crop = "no" #initially no crop

        if self.crop_created: #if user added crop, use it.
            crop = self.calculate_crop()
                
        fps = float(self.fps_entry.get())

        speed = self.speed_entry.get()

        size = self.size_entry.get()

        importlib.reload(ffexports) # good for debug

        ffexports.convert_gif(input_file, output, start_time, end_time, thetext, size, crop, fps, speed)



    def export_video(self):

        importlib.reload(ffexports) # good for debug

        crop = "no"

        if self.crop_finished:
                crop = self.calculate_crop()


        basename = os.path.basename(self.video_path)

        format = self.videosettings.format.get()

        size = self.size_entry.get()

        title = self.videosettings.title.get()
        audio_track = self.videosettings.audio_track.get()
        volume = self.videosettings.volume_db.get()
        preset = self.videosettings.preset.get()
        crf = self.videosettings.crf.get()
        maxsize = self.videosettings.max_size.get()

        duration = self.frame_count / self.fps

        print(title, audio_track, volume)

        



        output = os.path.splitext(basename)[0] + f" - 1.{format}"
        print(output)

        start = frame_to_time(self.start, self.fps)
        end = frame_to_time(self.finish, self.fps)

        #gifs.convert(self.video_path, output, size, crf,audio_track, volume,  title, preset ,start, end, crop)

        threading.Thread(target= ffexports.convert, args=(self.video_path, output, size, crf,audio_track, volume,  title, preset ,start, end, crop, format), kwargs={"video_duration": duration, "max_size": maxsize}).start()


    def cut_video(self):


        importlib.reload(ffexports)

        basename = os.path.basename(self.video_path)

        print(basename)

        output = basename
        print(output)

        start = frame_to_time(self.start, self.fps)
        end = frame_to_time(self.finish, self.fps)

        ffexports.output_video_cut(self.video_path, output, start, end )


    def calculate_crop(self): ## MPV crop
        
        coords = self.latest_coords 

        print("latest coords: ", coords)

        #print(f"player dimensions are,x = {self.player_frame.winfo_screenwidth()}, y={self.player_frame.winfo_screenheight()}")

        player_spaces = self.player._get_property("osd-dimensions") # Get general dimensions of the player

        player_blank_space = player_spaces["ml"], player_spaces["mt"], player_spaces["mr"], player_spaces["mb"] # Get black bards, they appear when video auto resizes to window size.

        print("blank spaces are: ", player_blank_space)

        ## +4 to compensate the border width, x2 and y2 doesn't need them because winfo_x and winfo_y starts just where the border starts visually
        x1 = (coords[0]+4) - player_blank_space[0] # Calculating considering all spaces
        y1 = (coords[1]+4) - player_blank_space[1]
        x2 = (coords[2]) - player_blank_space[0]
        y2 = (coords[3]) - player_blank_space[1]

        print("x1 is: ", x1)
        print("y1 is: ", y1)
        
        print("x2 is: ", x2)
        print("y2 is: ", y2)

        x1_percentage = (x1 ) / (player_spaces["w"] - (player_blank_space[0] + player_blank_space[2]) ) # Percentage of relative position
        y1_percentage = (y1 ) / (player_spaces["h"] - (player_blank_space[1] + player_blank_space[3]) )

        #x2_percentage = (x2) / (player_spaces["w"] - (player_blank_space[0] + player_blank_space[2]) )
        #y2_percentage = (y2) / (player_spaces["h"] - (player_blank_space[1] + player_blank_space[3]) )

        print(f"percentages are: x={x1_percentage}, y={y1_percentage}")

        x1_final =  self.width * x1_percentage # Applied relative position by percentage
        y1_final =  self.height * y1_percentage

        increment_x = (self.width / (player_spaces["w"] - (player_blank_space[0] + player_blank_space[2])))
        increment_y = (self.height / (player_spaces["h"] - (player_blank_space[1] + player_blank_space[3])))

        final_width = (x2  - x1) * increment_x ##Apply +2 to compensate border width
        final_height = (y2  -y1) * increment_y 


        param = f"{int(final_width)}:{int(final_height)}:{int(x1_final)}:{int(y1_final)}"

        print(param)


        return  param

    


    def handle_click(self, event): # Create or delete crop border

        print("should create a new border")

        if event.num == 3:  ## Delete crop border if it exists
            if self.image_border is not None:
                if self.canvas.find_withtag(self.image_border):
                    self.canvas.delete(self.image_border)
                    self.border_exists = False
                    self.resizing_part = None
            return
        
        if not self.border_exists: ## Create crop border

            if event.num == 1:

            
                self.image_border = self.canvas.create_rectangle(event.x, event.y, event.x + 5, event.y + 5, outline="white", width=2)
    
                self.border_exists = True
    
    def handle_release(self, event):

        rectangle = list(self.canvas.bbox(self.image_border)) ##convert to list to allow array manipulation

        image = list(self.canvas.bbox(self.image_canvas))


        print("bbox for image ", image)
        print("bbox for rectangle", rectangle)

        if rectangle[1] < image[1]: ##Fix TOP Y Position
            print("changed!!")
            rectangle[1] = image[1] +1 #Compensate rectangle height?
            self.canvas.coords(self.image_border, *rectangle)

        if rectangle[3] > image[3]: ##Fix Bottom Y Position
            print("changed!!")
            rectangle[3] = image[3] - 1 #Compensate rectangle height?
            self.canvas.coords(self.image_border, *rectangle)


        if rectangle[0] < image[0]: ##Fix TOP Y Position
            print("changed!!")
            rectangle[0] = image[0] +1 #Compensate rectangle height?
            self.canvas.coords(self.image_border, *rectangle)

        if rectangle[2] > image[2]: ##Fix Bottom Y Position
            print("changed!!")
            rectangle[2] = image[2] - 1 #Compensate rectangle height?
            self.canvas.coords(self.image_border, *rectangle)

        rectangle = self.canvas.bbox(self.image_border)

        image = self.canvas.bbox(self.image_canvas)

        print(image)
        print(rectangle)


        self.resizing_part = "done" ## Changes None to "done" so we can resize the crop border later

        self.set_percentages()

        if rectangle[2] - rectangle[0] < 10: ##Deletes the crop border if it is too small
            if self.image_border is not None:
                if self.canvas.find_withtag(self.image_border):
                    self.canvas.delete(self.image_border)
                    self.border_exists = False
                    self.resizing_part = None

    





    def resize_border(self, event): ##Apply crop_border resizing on resize event
        if self.border_exists:
            image = list(self.canvas.bbox(self.image_canvas))
            
            image_width = image[2] - image[0]
            image_height = image[3] - image[1]
            
            x1_new = (self.percentages[0] * image_width) / 100
            x2_new = (self.percentages[2] * image_width) / 100
            
            y1_new = (self.percentages[1] * image_height) / 100
            y2_new = (self.percentages[3] * image_height) / 100
            
            ## New dimensions are calculated based on percentages (it is easier to do but may be innacurate by 1 pixel)
            ## We add up the canvas offset based on image[0] (the first coord of the image)
            new_dimensions = int(image[0] + x1_new), int(image[1] + y1_new), int(image[0] + x2_new ), int(image[1] + y2_new)
            
            self.canvas.coords(self.image_border, new_dimensions)


            

    def set_percentages(self):

        print("setting percentages")

        rectangle = list(self.canvas.bbox(self.image_border))
        image = list(self.canvas.bbox(self.image_canvas))

        image_width = image[2] - image[0]
        image_height = image[3] - image[1]

        x1_percentage = ((image[0] - rectangle[0]) * 100) / image_width
        y1_percentage = ((image[1] - rectangle[1]) * 100) / image_height
        x2_percentage = ((image[0] - rectangle[2]) * 100) / image_width
        y2_percentage = ((image[1] - rectangle[3]) * 100) / image_height
        
        ##abs value to work with negative and positive resizing : ) 
        self.percentages = (abs(x1_percentage), abs(y1_percentage), abs(x2_percentage), abs(y2_percentage))







    def on_resize(self, event):
        #self.canvas.config(width=event.width, height=event.height)


        #print(event)

        print("Trigerred on resize event!!")

        self.set_image()
        self.resize_border(event)


    def on_resize_slider(self, event):
        self.move_cut_canvas()


    def set_start(self, number):
        self.start = int(self.player._get_property("estimated-frame-number"))

        if self.start < self.finish:
            self.create_gif_button.configure(state= "normal")

        self.move_cut_canvas()
        
    def set_finish(self, number):
        self.finish = int(self.player._get_property("estimated-frame-number"))
        if self.start < self.finish:
            self.create_gif_button.configure(state= "normal")
            self.color_canvas.config(bg="green")
            self.cut_finished = True
        self.move_cut_canvas()

    def get_audio_count(self):
        mediainfo = MediaInfo.parse(self.video_path)
    
        audio_count = []
        
        for track in mediainfo.tracks:
            if track.track_type == "Audio":
                audio_track = {"language": track.language if track.language else "und", "codec": track.codec_id, "bitrate": track.bit_rate}
                audio_count.append(audio_track)
                
        return audio_count




     ######## Before MPV

#     def on_window_mapped(self):
#         self.extract_frame(0)

#     def extract_frame(self, framenumber):


#         selected_frame = int(float(framenumber))

#         if selected_frame != self.current_frame or self.current_frame == 0:
#             self.current_frame = selected_frame
    
#             if self.finish == 0: #update colored cut
#                 self.move_cut_canvas()
    
    
    
    
    
#             print(selected_frame)
    
#             timestamp = frame_to_time(self.current_frame, self.fps)
    
#             self.root.title(f"Gif tool: {os.path.basename(self.video_path)} ({timestamp})")
    
#             startsecond = time.time()
    
    
#             #################### FFMPEG WITH JPG
    
    
    
#             # out, _ = (
#             #   ffmpeg
#             #   .input(self.video_path, ss=timestamp)
#             #   .output('pipe:', format='image2', vcodec="mjpeg", vframes=1, loglevel= "quiet")
#             #   .run(capture_stdout=True)
#             # )
     
#             # image = Image.open(io.BytesIO(out))
#             # self.current_image = image
    
    
    
#             ############### FFMPEG WITH RAWVIDEO
    
    
#            # out, _ = (
#            #    ffmpeg
#            #    .input(self.video_path, ss=timestamp)  # Seek to the timestamp
#            #    .output('pipe:', format='rawvideo', pix_fmt='rgb24', vframes=1, loglevel= "error")  # Extract only 1 frame
#            #    .run(capture_stdout=True)
#            # )
# #    
# #    
#            # frame = np.frombuffer(out, np.uint8).reshape([height, width, 3])
# #    
# #    
#            # self.current_image = Image.fromarray(frame)
    
    
#             # ################################## OPENCV
    
    
#             theimage = self.get_frame_number_opencv()
    
#             img = cv2.cvtColor(theimage, cv2.COLOR_BGR2RGB)
#             im_pil = Image.fromarray(img)
    
#             self.current_image = im_pil

#             # image = Image.fromarray(frame)
    
#             # self.current_image = ImageTk.PhotoImage(image)
    
#             self.set_image()
    
    
    
#             end = time.time()
#             print("it took ", end - startsecond," seconds")



    # def get_frame_number_opencv(self):
        


    #     #print("reading frames with opencv2, file is ", self.video_path, " and frame is ", self.current_frame)
        

    #     startsecond = time.time()
        
    #     self.cap.set(cv2.CAP_PROP_POS_FRAMES, int(self.current_frame))


        
    #     success, frame = self.cap.read()
        
    #     if not success:
    #         raise ValueError(f"Frame {self.current_frame} not found")

    #     end = time.time()
    #     print("seeking took ", end - startsecond," seconds")
        
    #     return frame  # BGR format (use cv2.cvtColor to convert to RGB)
    



    # def calculate_crop(self): ### Calculate crop opencv2

    #     self.move_canvas()

    #     rectangle = self.canvas.bbox(self.image_border)

    #     image = self.canvas.bbox(self.image_canvas)

    #     print(image)
    #     print(rectangle)


    #     border_width = rectangle[2] - rectangle[0]
    #     border_height = rectangle[3] - rectangle[1]

    #     image_width = image[2] - image[0]
    #     image_height = image[3] - image[1]

    #     print("width and heigth of image ", image_width, image_height)
    #     print("width and heigth of border ", border_width, border_height)


    #     width_increment =  (self.width / image_width) 
    #     height_increment = (self.height / image_height)

    #     print("increments x y are ", width_increment, height_increment)

    #     crop_width = border_width * width_increment
    #     crop_height = border_height * height_increment

    #     preXdistance = rectangle[0] - image[0]
    #     preYdistance = rectangle[1] - image[1]

    #     print("pre distance x y ", preXdistance, preYdistance)

    #     posX = preXdistance * width_increment
    #     posY = preYdistance * height_increment


    #     if posY <= 0:
    #         posY = 0
        



    #     param = f"{int(crop_width)}:{int(crop_height)}:{int(posX)}:{int(posY)}"

    #     print(param)


    #     return  param



    # def resize_image(self):

    #     start = time.time()

    #     canvas_width = int(self.canvas.winfo_width())
    #     canvas_height = int(self.canvas.winfo_height())

    #    # print("canvas size is ", canvas_width, "x ", canvas_height)

    #     image_width,image_height = self.current_image.size

    #    # print("original resolution is:", image_width, "x ", image_height)

    #     width_ratio = canvas_width / image_width
    #     height_ratio = canvas_height / image_height

    #     scale_ratio = min(width_ratio, height_ratio)

    #     new_width = int(image_width * scale_ratio)
    #     new_height = int(image_height * scale_ratio)

    #    # print("New resolution is ", new_width, "x ", new_height)


    #     resized_image = self.current_image.resize((new_width, new_height), Image.BICUBIC)

    #     final_resized = ImageTk.PhotoImage(resized_image)

    #     self.final_image = final_resized

    #     end = time.time()
    #    # print("resize took ", end-start)



    # def set_image(self): 
    #     self.resize_image()
    #     self.image_canvas = self.canvas.create_image(int(self.canvas.winfo_width()) / 2, int(self.canvas.winfo_height()) /2, anchor=ctk.CENTER, image=self.final_image)
        
    #     if self.image_border is not None: ### set zindex of the border
    #         if self.canvas.find_withtag(self.image_border):
    #             self.canvas.tag_raise(self.image_border)




    # def update_frame(self, frame_index): ## Old method
    #     # Convert the frame index to an integer
    #     frame_index = int(frame_index)
    #     self.current_frame = frame_index

    #     #print(frame_index, self.fps)

    #     # Calculate the timestamp for the frame
    #     timestamp = frame_to_time(self.current_frame, self.fps)



    #     print(timestamp)

    #     # Extract the specific frame using ffmpeg
    #     out, _ = (
    #         ffmpeg
    #         .input(self.video_path, ss=timestamp)  # Seek to the timestamp
    #         .output('pipe:', format='rawvideo', pix_fmt='rgb24', vframes=1, loglevel= "quiet")  # Extract only 1 frame
    #         .run(capture_stdout=True)
    #     )

    #     # Convert the raw frame data to a numpy array
    #     frame = np.frombuffer(out, np.uint8).reshape([height, width, 3])

    #     # Convert the frame to a PIL image
    #     aspectratio = height / width

    #     desiredwidth = int(self.canvas.winfo_width())
    #     print("desired width is ", desiredwidth)

    #     newheigth = aspectratio * desiredwidth
    

    #     print("aspect ratio is ", aspectratio, "and new height is ", newheigth)


    #     image = Image.fromarray(frame).resize((int(desiredwidth), int(newheigth)))

    #     #print("canvas size is ", int(self.canvas.winfo_width()), int(self.canvas.winfo_height()))

    #     # Convert the PIL image to a Tkinter-compatible image
    #     self.tk_image = ImageTk.PhotoImage(image)

    #     # Update the canvas with the new image
    #     self.canvas.create_image(0, 0, anchor=ctk.NW, image=self.tk_image)







def frame_to_time(frame_number, framerate):
    # Calculate total seconds from the frame number
    total_seconds = int(frame_number) / framerate

    # Calculate hours, minutes, and seconds
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60

    # Format the time string
    time_str = f"{hours:02}:{minutes:02}:{seconds:06.3f}"
    return time_str


if __name__ == "__main__":

    #Main window
    root = ctk.CTk()
    
    root.title("Eazy gif")
    root.geometry("600x600")

    file = filedialog.askopenfilename()

    output = os.path.splitext(os.path.basename(file))[0]
    
    giftools = VideoTools(root, file)
