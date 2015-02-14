DVImatrix848.ico:


%.ico: %.png
	convert $^ $@


%.png: %.svg
	inkscape --export-png=$@ --export-background-opacity=0 --without-gui $^
