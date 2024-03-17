

if (!window.dash_clientside) {
    window.dash_clientside = {};
}

window.dash_clientside.clientside = {
    setup_drag_listener: function () {
        const graphDiv1 = document.getElementById('graph-image-1');
        const graphDiv2 = document.getElementById('graph-image-2');
        const canvasWidth = 128;
        const canvasHeight = 128;
        const dragThrottle = 100;

        const throttleFunction = (func, delay) => {
 
            // Previously called time of the function
            let prev = 0;
            return (...args) => {
                // Current called time of the function
                let now = new Date().getTime();
 
                if (now - prev > delay) {
                    prev = now;
 
                    // "..." is the spread
                    // operator here 
                    // returning the function with the 
                    // array of arguments
                    return func(...args);
                }
            }
        }

        // TODO: I am lazy so I just C+Ped the code twice. I should refactor the below to one chunk handling mutliple in the future.

        // Function to handle mouse move
        const handleMouseMove1 = function (moveEvent) {
            const rect1 = graphDiv1.getBoundingClientRect();

            // Doing minWidth because the canvas is a rectangle
            const minWidth = Math.min(rect1.width, rect1.height);

            // Calculate offset within the actual graph element
            const offsetX = moveEvent.clientX - rect1.left - (rect1.width - minWidth) / 2;
            const offsetY = moveEvent.clientY - rect1.top - (rect1.height - minWidth) / 2;

            // Normalize/Map the offset to desired coordinate system (128x128)
            const mappedX = Math.max(Math.min(Math.round((offsetX / minWidth) * canvasWidth), 127), 0);
            const mappedY = Math.max(Math.min(Math.round((offsetY / minWidth) * canvasHeight), 127), 0);

            const inputElement = document.getElementById('hidden-div');

            const event = new Event("drag-change");
            inputElement.dispatchEvent(event);

            if (inputElement) {
                inputElement.innerText = JSON.stringify({ x: mappedX, y: mappedY });
            }
            // Use mappedX and mappedY as needed.
        };

        const handleMouseMove2 = function (moveEvent) {
            const rect2 = graphDiv2.getBoundingClientRect();

            // Doing minWidth because the canvas is a rectangle
            const minWidth = Math.min(rect2.width, rect2.height);

            // Calculate offset within the actual graph element
            const offsetX = moveEvent.clientX - rect2.left - (rect2.width - minWidth) / 2;
            const offsetY = moveEvent.clientY - rect2.top - (rect2.height - minWidth) / 2;

            // Normalize/Map the offset to desired coordinate system (128x128)
            const mappedX = Math.max(Math.min(Math.round((offsetX / minWidth) * canvasWidth), 127), 0);
            const mappedY = Math.max(Math.min(Math.round((offsetY / minWidth) * canvasHeight), 127), 0);

            const inputElement = document.getElementById('hidden-div');

            const event = new Event("drag-change");
            inputElement.dispatchEvent(event);

            if (inputElement) {
                inputElement.innerText = JSON.stringify({ x: mappedX, y: mappedY });
            }
            // Use mappedX and mappedY as needed.
        };

        // Ensure we have the graph div
        if (graphDiv1) {
            graphDiv1.onmousedown = function (downEvent) {
                const rect = graphDiv1.getBoundingClientRect();

                const inputElement = document.getElementById('hidden-div');
                const event = new Event('drag-mousedown');
                inputElement.dispatchEvent(event);

                handleMouseMove1(downEvent);

                const throttledMouseMove = throttleFunction(handleMouseMove1, dragThrottle)

                // Assign mousemove listener
                document.addEventListener('mousemove', throttledMouseMove);

                document.onmouseup = function (upEvent) {
                    // On drag end, to remove mousemove listener

                    const event = new Event('drag-mouseup');
                    inputElement.dispatchEvent(event);

                    document.removeEventListener('mousemove', throttledMouseMove);
                    document.onmouseup = null;
                };

                // Prevent default dragging behavior
                document.ondragstart = function () { return false; };

                return false; // Prevent text selection during drag in some browsers
            };
        }

        if (graphDiv2) {
            graphDiv2.onmousedown = function (downEvent) {
                const rect = graphDiv2.getBoundingClientRect();

                const inputElement = document.getElementById('hidden-div');
                const event = new Event('drag-mousedown');
                inputElement.dispatchEvent(event);

                handleMouseMove2(downEvent);

                const throttledMouseMove = throttleFunction(handleMouseMove2, dragThrottle)

                // Assign mousemove listener
                document.addEventListener('mousemove', throttledMouseMove);

                document.onmouseup = function (upEvent) {
                    // On drag end, to remove mousemove listener

                    const event = new Event('drag-mouseup');
                    inputElement.dispatchEvent(event);

                    document.removeEventListener('mousemove', throttledMouseMove);
                    document.onmouseup = null;
                };

                // Prevent default dragging behavior
                document.ondragstart = function () { return false; };

                return false; // Prevent text selection during drag in some browsers
            };
        }

        console.log("Drag handler function set up")

        return '{"x":123, "y": 123}';
    },

    update_signal_clientside: function (n_intervals, signalPatch, activeFile, graphFigure1, graphFigure2) {

        const PATCH_SIZE = 8;

        const positionElement = document.getElementById('hidden-div');

        const position = JSON.parse(positionElement.innerText)

        const x_offset = position.x % PATCH_SIZE;
        const y_offset = position.y % PATCH_SIZE;

        var patch_offset = x_offset * PATCH_SIZE + y_offset;

        const fileMetadata = JSON.parse(activeFile)

        patchArray = JSON.parse(signalPatch);

        if (patchArray) {

            var signal_1 = {
                "data": [{
                    "y": patchArray.signal_0.slice(patch_offset * fileMetadata.frames, patch_offset * fileMetadata.frames + fileMetadata.frames),
                    "type": "line"
                }],
                "layout": {
                }
            };

            var signal_2 = {
                "data": [{
                    "y": patchArray.signal_1.slice(patch_offset * fileMetadata.frames, patch_offset * fileMetadata.frames + fileMetadata.frames),
                    "type": "line"
                }],
                "layout": {
                }
            };

            var positionTracker = [{
                    type: "circle",
                    x0: position.x - 2,
                    y0: position.y - 2,
                    x1: position.x + 2,
                    y1: position.y + 2,
                    line: {
                        color: "red"
                    },
                    fillcolor: "red"
                }
            ];


            if (graphFigure1.layout) {
                console.log(graphFigure1.layout)

                graphFigure1.layout.shapes = positionTracker
            }

            if (graphFigure2.layout) {
                graphFigure2.layout.shapes = positionTracker
            }
            
            // console.log(graphFigure1.layout)
            
            return [{ "x": position.x, "y": position.y }, signal_1, signal_2, graphFigure1, graphFigure2];

        } else {
            return [{ "x": 64, "y": 64 }, { "data": [], "layout": {} }, { "data": [], "layout": {} }];

        }


    },
}