from pygifsicle import gifsicle

gifsicle(
    sources="input.gif", # or a single_file.gif
    destination="optimized.gif", # or just omit it and will use the first source provided.
    optimize=False, # Whether to add the optimize flag or not
    colors=256, # Number of colors to use
    options=["-O3", "--lossy=120"] # Options to use.
)