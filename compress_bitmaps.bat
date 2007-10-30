echo off
optipng -zc9 -zm9 -zs0 -f0 *.bmp
if %ERRORLEVEL% == 9009 (
	cls
	echo.
	echo This is a useful script for compressing large bitmaps.
	echo To use it you must install OptiPNG from http://optipng.sourceforge.net/
	echo.
	cmd -k
) else (
	if not exist *.bmp (
		cls
		echo.
		echo There are no bitmap files in this directory to compress.
		echo.
		cmd -k
	) else (
		if %ERRORLEVEL% == 0 del *.bmp
	)
)
echo on