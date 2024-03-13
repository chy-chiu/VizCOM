if (!window.dash_clientside) {
    window.dash_clientside = {};
}

window.dash_clientside.clientside = {
    setup_drag_listener: function () {
        const graphDiv = document.getElementById('graph-image-1');
        const canvasWidth = 128;
        const canvasHeight = 128;

        // Function to handle mouse move
        const handleMouseMove = function (moveEvent) {
            const rect = graphDiv.getBoundingClientRect();

            // Doing minWidth because the canvas is a rectangle
            const minWidth = Math.min(rect.width, rect.height);

            // Calculate offset within the actual graph element
            const offsetX = moveEvent.clientX - rect.left - (rect.width - minWidth) / 2;
            const offsetY = moveEvent.clientY - rect.top - (rect.height - minWidth) / 2;

            // Normalize/Map the offset to desired coordinate system (128x128)
            const mappedX = Math.max(Math.min(Math.round((offsetX / minWidth) * canvasWidth), 127), 0);
            const mappedY = Math.max(Math.min(Math.round((offsetY / minWidth) * canvasHeight), 127), 0);

            const inputElement = document.getElementById('hidden-div');

            if (inputElement) {
                inputElement.innerText = JSON.stringify({ x: mappedX, y: mappedY });
            }
            // Use mappedX and mappedY as needed.
        };

        // Ensure we have the graph div
        if (graphDiv) {
            graphDiv.onmousedown = function (downEvent) {
                const rect = graphDiv.getBoundingClientRect();

                const inputElement = document.getElementById('hidden-div');
                const event = new Event('drag-mousedown');
                inputElement.dispatchEvent(event);

                // Assign mousemove listener
                document.addEventListener('mousemove', handleMouseMove);

                document.onmouseup = function (upEvent) {
                    // On drag end, to remove mousemove listener

                    const event = new Event('drag-mouseup');
                    inputElement.dispatchEvent(event);

                    document.removeEventListener('mousemove', handleMouseMove);
                    document.onmouseup = null;
                };

                // Prevent default dragging behavior
                document.ondragstart = function () { return false; };

                return false; // Prevent text selection during drag in some browsers
            };
        }

        return '{"x":-1, "y": -1}';
    },

    update_signal_clientside: function (n_intervals, signalPatch, activeFile) {


        const PATCH_SIZE = 8;

        const positionElement = document.getElementById('hidden-div');

        const position = JSON.parse(positionElement.innerText)


        const x_offset = position.x % PATCH_SIZE;
        const y_offset = position.y % PATCH_SIZE;

        var patch_offset = x_offset * PATCH_SIZE + y_offset;

        const fileMetadata = JSON.parse(activeFile)

        patchArray = JSON.parse(signalPatch);

        var figure_1 = {
            "data": [{
                "y": patchArray.signal_0.slice(patch_offset * fileMetadata.frames, patch_offset * fileMetadata.frames + fileMetadata.frames),
                "type": "line"
            }],
            "layout": {
            }
        };

        var figure_2 = {
            "data": [{
                "y": patchArray.signal_1.slice(patch_offset * fileMetadata.frames, patch_offset * fileMetadata.frames + fileMetadata.frames),
                "type": "line"
            }],
            "layout": {
            }
        };
        
        return [{"x": position.x, "y": position.y}, figure_1, figure_2];
    },
}