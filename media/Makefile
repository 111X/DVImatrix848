DVImatrix848.ico:


%.ico: %.png
	convert $^ $@
	icotool -c -o $@ $^


%.png: %.svg
	inkscape --export-png=$@ --export-background-opacity=0 --without-gui $^
