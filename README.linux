-------------------
System Requirements
-------------------

In addition to the hardware requirements (which will be the same as the other
platforms) your system will need these libraries installed:

* GTK+ 2+
* SDL 1.2+
* SDL_image

And some kind of OpenGL implementation, so:

* libgl
* libglu



-------------------
Commandline Options
-------------------

-sound_output : sets the sound system to use. Possible values:
    ALSA - Use the Advanced Linux Sound Architecture. (default)
    OSS  - Use the Open Sound System.
    ESD  - Use the Enlightenment Sound Daemon.
    
If you need to use one of the alternative systems and want to avoid 
having to run from a terminal everytime, add the switch and the sound
system required to the df script. 



-------------------
  Known   Issues
-------------------

* If the mouse cursor is enabled, and you are running fullscreen
  it reacts strangely around the leftmost and topmost edges of the screen.
* Recorded movies will flicker every few frames, with artifacts on
  larger screen sizes.
* If the lock keys (caps lock, num lock, etc) do not work for you, open
  the df file in a text editor and remove the line that reads
  
  export SDL_DISABLE_LOCK_KEYS=1
  
  it's a work around for a bug in the SDL package in Debian based distributions,
  that reverses the behaviour of the above environmental variable.

