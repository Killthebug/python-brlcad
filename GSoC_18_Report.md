# Python BRL-CAD
# Google Summer of Code 2018

Project : The project started off as finessing the exisiting python BRL-CAD architecture but soon moved to making procedural geometry easy to access and use.

### Major things that were achieved during this project are :
<ol>
<li> The python BRL-CAD [tcl approach] () was made completely useable by introducing a lot of missing primitives.
<li> The tcl approach was also equipped with a script parser for implementing procedural geometry.
<li> The python BRL-CAD ctypesgen approach was updated to be compatible with the latest version of BRLCAD.
<li> Few missing primitives were added.
<li> Two minor resources were developed too that might be useful for future references.
<ul>
  <li>List of primitives implemented in python BR-LCAD (http://bit.ly/PyBRLCADPrimitives)
  <li>List of wdb functions implemented in python BRLCAD (http://bit.ly/wdb_functions)
</ul>
<li> Barebones for the Script primitive was introduced.
<li> Describe Function for the script primitive was implemented.
<li> A scene having most of the primitives was created entirely using python BRL-CAD.
<li> Examples for procedural geometry were introduced : SGI cube (https://brlcad.org/wiki/SGI_Cube) was created using procedural geometry.
<li> A blog style guide was written to introduce and work with procedural geometry.
</ol>

### Patch Files
65 patches have been condensed in to three major patches.
<ol>
<li> TCL Script Parser and Procedural Geometry Parser
<ul> 
<li> Patch : http://bit.ly/tcl_parser_patch
<li> Github Project : https://github.com/Killthebug/python-brlcad-tcl
</ul>
<li> Ctypesgen Procedural Geometry 
<ul> 
<li>Patch : http://bit.ly/ctypesgen
<li>Github Project : https://github.com/Killthebug/python-brlcad/
</ul>
<li> Code for rt_script_describe()
<ul>
<li>Patch : http://bit.ly/script_describe
<li>Sourceforge Project : https://sourceforge.net/p/brlcad/code/HEAD/tree/brlcad/trunk/src/librt/primitives/script/
</ul>
  
### Remaining Work
<ol>
  <li> Fix broken 2-d primitives : sketch, extrude and revolve.
  <li> Couple script primitive with python brlcad.
  <li> Introduce more examples for procedural geometry
  <li> In-depth documentation (Maybe)
<ol>
