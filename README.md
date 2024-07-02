# CardiacMap
CS8903 - Cardiac Optical Mapping - Prof. Elizabeth Cherry

## Overview
This is a rewrite of the cardiac optical mapping software for better performance and maintainability.

This software is mostly built upon Qt (PySide6) and pyqtgraph, a Python framework for interactive data visualization

## Development
1. Git clone this repo
2. Set up virtual environment

`conda create --name cardiacmap --file requirements.txt`

3. Activate virtual environment

`conda activate cardiacmap`

4. Install cardiacmap as a module

`pip install -e .`

## To run the app

1. Run `python app.py` in the root folder, then open the webapp on `127.0.0.1:8051`

## To load files

1. Put any voltage .dat data into `./data` folder and it would show up in the app 

## To compile to executable

Compilation uses [PyInstaller](https://pyinstaller.org/en/stable/). To compile, run it on app.py as per the instructions. Remember to set the debug flag as false. 

## Development guidelines
Employ standard software practices
Small / bug fixes can be committed to main
Large / breaking changes please create a separate branch to avoid conflicts + code review from other team members as needed