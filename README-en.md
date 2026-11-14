# Escurses
A Python library that lets you make terminal games

[Jump to homepage](./README.md)

## Why should you choose Escurses?
  - **Cross-platform support**
    It works on Windows and on Linux
    So you don't need to worry about the library being incompatible with your system, unless you're using macOS
  - **Easy to use**
    You just need to download it and drop it into your code directory, and then you can use it!
  - **Maintained**
    You probably don't know about pycurses; that's a very, very old library that has long been unmaintained
    EScurses is much newer than it, which means you can rest assured it won't suddenly stop being updated
    But the author also has to go to school QAQ (I'm just a fifth-grade kid)

> I don't have a MacBook because it's not a common thing; it's too expensive, at least for me
> So... if you have a MacBook, please help me test whether this library works on macOS
> I need help :)

## Documentation
First, if you're a Linux user, I have to teach you a function
  - **`linuxTerminalCheck()`**
      This function is used to check whether you are in a tty environment. Whether you want blocking input or non-blocking input, you need to use this function to check the environment
      When it returns `True`, it means you really are in a tty environment, but if it returns `False`, that means you may not be in a pure tty environment, which may cause blocking confusion

Then there are the following functions
  - **`getTerminalSize()`**
    This function returns a tuple whose first element is the screen length (measured in characters) and whose second element is the screen width
  - **`initGame()`**
    It is responsible for initializing `_maxScreenWidth` and `_maxScreenHeight`. Of course, I don't recommend using these two variables directly for your game; they are internal variables
  - **`clear()`**
    Very simple, it just clears the screen, but maybe not so simple after all
    It contains a new variant of dirty-rectangle rendering that I invented myself: dirty-rectangle clearing
    Simply put, it records which rows were dirty just now, and when called, it clears those dirty rows
    This is an algorithm I completely invented myself. Celebrate! 🎉
  - **`getch(nodelay=True)`**
    The hardest one to implement, because it includes both Windows input and Linux input, and the input on both systems has separate blocking and non-blocking versions, controlled by the `nodelay` parameter, which defaults to `True`
    If you enable non-blocking input, then when you haven't pressed any key, it will return `None`
    On Linux, it is only guaranteed to work inside a pure tty
    And as for how to get the function keys that are pressed, you can use the mapping table corresponding to the system you are using
    For example, Windows uses WINDOWSKEYMAP, Linux uses LINUXKEYMAP, and macOS has no dedicated adaptation, and we currently haven't cracked Windows function key detection 🤔, so this feature currently only supports Linux
    You can use it like this
    ```python
    ch = escurses.getch()
    if ch == escurses.LINUXKEYMAP['KEYUP']:  # KEYUP is the up arrow; similar ones include KEYDOWN, F11, etc. They are all uppercase with no underscores
      # Put your code here
      pass
    ```
  - **`drawChar(x, y, char, color)`**
    It draws the character you pass in at the specified `x` and `y`, and then that's it, just that simple
    As for its principle... well, I can explain
    Actually, we also have an internal variable `_screen`, which is an array storing the character corresponding to each position. When you call this function, it combines the character you pass in with the coordinates you pass in into a tuple and puts it into the corresponding position in this array, but the coordinate of the top-left corner of the screen is actually (1,1) rather than (0,0), which needs attention
    We thoughtfully swapped `x` and `y` for you, because actual drawing uses `y` first and `x` second, but we don't want you to suffer, so we swapped `x` and `y` in this function
    Also, when you pass the corresponding parameter to color, you can change the character's color. The color constants are already built into the library, such as `COLORRED`. The default value of this parameter is `COLORDEFAULT`
  - **`drawStr(x, y, string, color)`**
    Internally it calls `drawChar` repeatedly. `x` and `y` are the starting coordinates of the string, printed from left to right. The parameters are similar to those of `drawChar`
  - **`refresh()`**
    Calling this function will iterate through the characters in the `_screen` array one by one and draw them to the screen, but not all of them, because dirty-rectangle rendering is actually used here to save performance
  - **`cursorEcho(echo)`**
    When you pass `False` to `echo`, this hides your cursor
    If you pass `True`, the cursor is shown again
    And the default value of `echo` is `False`
  - **`exitGame()`**
    Used to exit the game
  - **`frameStart()`**
    If you want to control the frame rate, you can try this. Call it at the beginning of each main loop. Be sure to call it at the very, very beginning, with no other code before it. Then use it together with `sleepForFrame()` to control the frame rate
  - **`sleepForFrame`**
    It controls the frame rate to the frame rate you pass in by pausing slightly, which is a great thing for some people who don't want to manually write lots of calculations
  - **`theLifeAndEverythingAndUniverseUltimateAnswer()`**
    I admit its function name is really long. This is an Easter egg function; no matter how you call it, it always returns 42

That's basically all the content. I wish you all the best in making great games!

***Translated By DeepSeek***