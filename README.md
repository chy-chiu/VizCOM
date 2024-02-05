# CardiacMap
CS8903 - Cardiac Optical Mapping - Prof. Elizabeth Cherry

## Overview
This is a rewrite of the cardiac optical mapping software for better performance and maintainability.

This software is mostly built upon Plotly Dash, a Python framework for interactive data visualization

## Installation
1. Git clone this repo
2. Set up virtual environment

`conda create --name cardiacmap --file requirements.txt`

3. Activate virtual environment

`conda activate cardiacmap`


## To run the app
Currently you will need a file named `2012-02-13_Exp000_Rec005_Cam3-Blue.dat` for the script to work (as a placeholder file until we sort out upload function)

Put the file as the same folder as `app.py`. The file can be downloaded here:
https://www.dropbox.com/scl/fi/9yowq5d9jtd4mo451f4f5/2012-02-13_Exp000_Rec005_Cam3-Blue.dat?rlkey=tlrtc7vutewgy6hchdmjwfp77&dl=0

Run `python app.py` in the root folder, then open the webapp on `127.0.0.1:8050`

## Development
To write: 
Standard software practices with pull requests etc