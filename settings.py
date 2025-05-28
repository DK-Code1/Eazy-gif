import customtkinter as ctk
from CTkToolTip import *



class videosettings(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent.root)
        self.title("Video Settings")
        self.geometry("300x350")





        self.withdraw()

        self.parent = parent

        self.mp4_values = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
        self.webm_values = ["cpu-used=5","cpu-used=4","cpu-used=3","cpu-used=2","cpu-used=1","cpu-used=0"]


        self.title = ctk.StringVar(value="Video")
        self.format = ctk.StringVar(value="mkv")
        self.preset = ctk.StringVar(value="veryslow")
        self.audio_track = ctk.IntVar(value=0)
        self.volume_db = ctk.IntVar(value=0)
        self.crf = ctk.IntVar(value = 23)


        self.options_frame = ctk.CTkFrame(self)

        self.title_frame= ctk.CTkFrame(self.options_frame)
        self.title_label = ctk.CTkLabel(self.title_frame, text="Video title (internal): ")
        self.title_entry = ctk.CTkEntry(self.title_frame, textvariable=self.title)
        self.tooltip_title = CTkToolTip(self.title_entry, message="The internal title of the video, some players show up this value")

        self.title_label.pack(side= "left")
        self.title_entry.pack(side= "left")
        self.title_frame.pack(anchor="e")

        self.format_frame= ctk.CTkFrame(self.options_frame)
        self.format_label = ctk.CTkLabel(self.format_frame, text="Format: ")
        self.format_entry = ctk.CTkComboBox(self.format_frame, values=["mkv", "mp4", "webm"], variable=self.format, command=self.format_changed)
        self.tooltip_format = CTkToolTip(self.format_entry, message="Extension format of the video, mkv and mp4 uses libx264 codec \n webm format uses vp9")


        self.format_label.pack(side= "left")
        self.format_entry.pack(side= "left")
        self.format_frame.pack(anchor="e")

        self.preset_frame= ctk.CTkFrame(self.options_frame)
        self.preset_label = ctk.CTkLabel(self.preset_frame, text="Preset: ")
        self.preset_entry = ctk.CTkComboBox(self.preset_frame, values=self.mp4_values, variable=self.preset)
        self.tooltip_preset = CTkToolTip(self.preset_entry, message="Preset of the encoder, for mp4/mkv lower values delivers a better quality video at the cost of encoding speed \n for webm with vp9 is also the same, where cpu-used=0 has the best quality")
        
        self.preset_label.pack(side= "left")
        self.preset_entry.pack(side= "left")
        self.preset_frame.pack(anchor="e")
        
        self.crf_frame= ctk.CTkFrame(self.options_frame)
        self.crf_label = ctk.CTkLabel(self.crf_frame, text="Crf (quality): ")
        self.crf_entry = ctk.CTkEntry(self.crf_frame, textvariable=self.crf)
        self.tooltip_crf = CTkToolTip(self.crf_entry, message="Crf determines the quality of the video (bitrate), for mp4/mkv crf 16-18 is almost lossless, crf 20-22 is high quality with good file size, higher values deliver worse quality but lower file size" \
        "\n for webm with vp9 codec: 20-24 is lossless, 26 is high quality with good file size, higher values have worse quality but lower file size")

        
        self.crf_label.pack(side= "left")
        self.crf_entry.pack(side= "left")
        self.crf_frame.pack(anchor="e")



        print([x["language"] for x in self.parent.audio_tracks])


        self.audio_track_frame= ctk.CTkFrame(self.options_frame)
        self.audio_track_label = ctk.CTkLabel(self.audio_track_frame, text="Audio track: ")
        self.audio_track_entry = ctk.CTkComboBox(self.audio_track_frame, values=[x["language"] for x in self.parent.audio_tracks], command=self.choose_track)
        self.tooltip_audio_track = CTkToolTip(self.audio_track_entry, message="Audio track for the video")


        self.audio_track_label.pack(side= "left")
        self.audio_track_entry.pack(side= "left")
        self.audio_track_frame.pack(anchor="e") 

        self.volume_frame= ctk.CTkFrame(self.options_frame)
        self.volume_label = ctk.CTkLabel(self.volume_frame, text="Volume: ")
        self.volume_entry = ctk.CTkEntry(self.volume_frame, textvariable=self.volume_db)
        self.tooltip_volume = CTkToolTip(self.volume_entry, message="Volume offset for the output file in dB, e.g: 0 is same volume, -5 is -5dB in volume, 5 is +5dB on volume.")

        self.volume_label.pack(side= "left")
        self.volume_entry.pack(side= "left")
        self.volume_frame.pack(anchor="e") 

        self.options_frame.pack(side="left")

        #self.bind("<Button>", self.trace)


        self.protocol("WM_DELETE_WINDOW", self.onclose)
    
    def format_changed(self, event):
        format = self.format_entry.get()
        if format == "webm":
            self.preset.set(self.webm_values[-1])
            self.preset_entry.configure(values=self.webm_values)
        else:
            self.preset.set(self.mp4_values[-1])
            self.preset_entry.configure(values=self.mp4_values)
            

    def choose_track(self, selected):
        self.audio_track.set(self.audio_track_entry._values.index(selected)) ##set the current audio track as selected
        print(self.audio_track)


    def trace(self, event):
        print(self.title.get())
        print(self.format.get())
        print(self.preset.get())
        print(self.audio_track.get())
        print(self.volume_db.get())



    def toggle_visibility(self):
        state = self.wm_state()

        if state == "normal":
            self.withdraw()
            
        else:
            self.transient(self.parent.root)
            self.deiconify()
            

    def onclose(self):
        self.withdraw()

