# DVImatrix848

simple control program for the [Gefen EXT-DVI-848](http://www.gefen.com/kvm/ext-dvi-848.jsp?prod_id=5311), an 8x8 routing matrix for DVI-signals.

##Building a standalong application on W32

You will need a number of things installed
- Python2.7
- PySide (`pip install PySide`)
- py2exe http://www.py2exe.org/
- pyserial http://pyserial.sourceforge.net/
- pywin32 http://sourceforge.net/projects/pywin32/files/pywin32/
- Microsoft Visual C++ 2008 Redistributable Package (9.0.21022.8) http://www.microsoft.com/en-us/download/details.aspx?id=29

Once everything is in place, run:

~~~bash
python.exe .\setup.py py2exe
~~~

##Gefen EXT-DVI-848
Documentation about the device can be found at http://www.gefen.com/pdf/EXT-DVI-848.pdf

The interesting parts (commands to controal the device via the serial line) can be found in *Appendix B*.

###RS232 settings
- Bits per second: 19200
- Data bits: 8
- Parity: None
- Stop bits: 1
- Flow Control: None

###Switching Command (shortcut)
First character indicates the output monitor. Second character indicates the input
number. E.g. to route input *5* to output monitor *A*, use:

    A5

###Matrix Status Command (shortcut)
The `M` or `m` command will return the current routing state.

###Routing Command (shortcut)
This command sets the matrix routing state according to a preset routing state.
First character is `S` or `s`, second character indicates the state that is set by
function `#PSASRS` or `#MSASRS`

###Set Preset Routing State
This function enables the user to determine up to 10 routing states to save in
memory.

    #PSASRS␣<ID>␣<inA>␣<inB>␣<inC>␣<inD>␣<inE>␣<inF>␣<inG>␣<inH>\r

`<ID`> names the routing state and is a number in the range *0..9*, and
`<in*>` defines the input route to the given monitor, and is a number in the range *1..8*.

###Set Current Matrix As Routing State

    #MSASRS␣<ID>\r

###Print Routing State Table

    #PRRS\r
