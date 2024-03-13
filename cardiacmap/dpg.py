import dearpygui.dearpygui as dpg
import dearpygui.demo as demo
import cv2
import numpy as np

# dpg.create_context()
# dpg.create_viewport(title='Custom Title', width=1000, height=1000)

# demo.show_demo()

# dpg.setup_dearpygui()
# dpg.show_viewport()
# dpg.start_dearpygui()
# dpg.destroy_context()

# Load or initialize your image
image_path = "newplot.png"
original_image = cv2.imread(image_path)
# Ensure image is in RGB format for DearPyGui
original_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)

# Create an array to serve as our drawing mask, initialize to zeros (nothing drawn)
mask = np.zeros(original_image.shape[:2], dtype=np.uint8)

# Variables to track drawing
drawing = False # true if mouse is pressed
ix, iy = -1, -1

# Mouse callback function
def draw_callback(sender, app_data):
    global ix, iy, drawing, mask

    if app_data[1] == 0: # If left mouse button pressed
        drawing = True
        ix,iy = app_data[2], app_data[3]
    elif app_data[1] == 2:  # Mouse move event
        if drawing:
            cv2.line(mask, (ix, iy), (app_data[2], app_data[3]), (255), 5)
            cv2.line(original_image, (ix, iy), (app_data[2], app_data[3]), (255, 0, 0), 5)
            ix, iy = app_data[2], app_data[3]
            update_image_texture()
    else:  # Mouse button released
        drawing = False

def update_image_texture():
    # Whenever the image is updated, we need to reapply it as a texture
    _, imgbytes = cv2.imencode(".png", original_image)
    texture_data = np.frombuffer(imgbytes, np.uint8)
    dpg.set_value(image_texture, texture_data)

def save_mask():
    cv2.imwrite('mask.png', mask)
    print("Mask saved!")


print('hello')

with dpg.window(label="Image Annotator"):
    # Add a button to save the mask

    dpg.add_button(label="Save Mask", callback=save_mask)
    
    # Convert image to texture
    _, imgbytes = cv2.imencode(".png", original_image)
    texture_data = np.frombuffer(imgbytes, np.uint8)

    image_texture = dpg.add_static_texture(original_image.shape[1], original_image.shape[0], texture_data, parent=dpg.last_container())
    dpg.add_image(image_texture)

    # Add drawing handler
    with dpg.handler_registry():
        dpg.add_mouse_drag_handler(callback=draw_callback)
        dpg.add_mouse_click_handler(callback=draw_callback)

dpg.create_viewport(title='Custom Title', width=600, height=400)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()