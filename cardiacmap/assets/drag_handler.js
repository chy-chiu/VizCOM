
if (!window.dash_clientside) {
    window.dash_clientside = {};
}

window.dash_clientside.clientside = {
    setup_drag_listener: function (_refresher, graphDivId, hiddenDivId) {

        if (!(typeof graphDivId === 'string' || graphDivId instanceof String)) {
            graphDivId = JSON.stringify(graphDivId, Object.keys(graphDivId).sort());
        };

        if (!(typeof hiddenDivId === 'string' || hiddenDivId instanceof String)) {
            hiddenDivId = JSON.stringify(hiddenDivId, Object.keys(hiddenDivId).sort());
        };


        const collection = document.getElementsByClassName("nsewdrag");
        const canvasDiv = collection[0];

        const graphDiv = document.getElementById(graphDivId);
        // console.log(graphDiv.width);
        // console.log(canvasDiv.width);

        const canvasWidth = 128;
        const canvasHeight = 128;
        const dragThrottle = 200;

        const throttleFunction = (func, delay) => {

            // Previously called time of the function
            let prev = 0;
            return (...args) => {
                // Current called time of the function
                let now = new Date().getTime();

                if (now - prev > delay) {
                    prev = now;

                    return func(...args);
                }
            }
        }

        // Function to handle mouse move
        const handleMouseMove = function (moveEvent) {

            const WINDOW_OFFSET = 10.4;

            const rect = graphDiv.getBoundingClientRect();

            // Doing minWidth because the canvas is a rectangle
            const minWidth = Math.min(rect.width, rect.height);

            // Calculate offset within the actual graph element
            const offsetX = moveEvent.clientX - rect.left - (rect.width + WINDOW_OFFSET - minWidth) / 2;
            const offsetY = moveEvent.clientY - rect.top - (rect.height + WINDOW_OFFSET - minWidth) / 2;

            console.log(offsetX, offsetY);

            // Normalize/Map the offset to canvas (128x128)
            const mappedX = Math.max(Math.min(Math.floor((offsetX / (minWidth - WINDOW_OFFSET)) * canvasWidth), 127), 0);
            const mappedY = Math.max(Math.min(Math.floor((offsetY / (minWidth - WINDOW_OFFSET)) * canvasHeight), 127), 0);

            const inputElement = document.getElementById(hiddenDivId);

            const event = new Event("drag-change");
            inputElement.dispatchEvent(event);

            if (inputElement) {
                inputElement.innerText = JSON.stringify({ x: mappedX, y: mappedY });
            }
        };

        // Ensure we have the graph div
        if (graphDiv) {
            graphDiv.onmousedown = function (downEvent) {

                const rect = graphDiv.getBoundingClientRect();

                const inputElement = document.getElementById(hiddenDivId);
                const event = new Event('drag-mousedown');
                inputElement.dispatchEvent(event);

                handleMouseMove(downEvent);

                const throttledMouseMove = throttleFunction(handleMouseMove, dragThrottle)

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

        return '{"x":64, "y": 64}';
    },

    // // This is no longer necessary
    // update_signal_clientside: function (n_intervals, signalPatch, activeFile, graphFigure1, graphFigure2) {

    //     const PATCH_SIZE = 8;

    //     const positionElement = document.getElementById('hidden-div');

    //     const position = JSON.parse(positionElement.innerText)

    //     const x_offset = position.x % PATCH_SIZE;
    //     const y_offset = position.y % PATCH_SIZE;

    //     var patch_offset = x_offset * PATCH_SIZE + y_offset;

    //     const fileMetadata = JSON.parse(activeFile)

    //     patchArray = JSON.parse(signalPatch);

    //     if (patchArray) {

    //         var signal_1 = {
    //             "data": [{
    //                 "y": patchArray.signal_0.slice(patch_offset * fileMetadata.frames, patch_offset * fileMetadata.frames + fileMetadata.frames),
    //                 "type": "line"
    //             }],
    //             "layout": {
    //             }
    //         };

    //         var signal_2 = {
    //             "data": [{
    //                 "y": patchArray.signal_1.slice(patch_offset * fileMetadata.frames, patch_offset * fileMetadata.frames + fileMetadata.frames),
    //                 "type": "line"
    //             }],
    //             "layout": {
    //             }
    //         };

    //         var positionTracker = [{
    //                 type: "circle",
    //                 x0: position.x - 2,
    //                 y0: position.y - 2,
    //                 x1: position.x + 2,
    //                 y1: position.y + 2,
    //                 line: {
    //                     color: "red"
    //                 },
    //                 fillcolor: "red"
    //             }
    //         ];


    //         if (graphFigure1.layout) {
    //             console.log(graphFigure1.layout)

    //             graphFigure1.layout.shapes = positionTracker
    //         }

    //         if (graphFigure2.layout) {
    //             graphFigure2.layout.shapes = positionTracker
    //         }

    //         // console.log(graphFigure1.layout)

    //         return [{ "x": position.x, "y": position.y }, signal_1, signal_2, graphFigure1, graphFigure2];

    //     } else {
    //         return [{ "x": 64, "y": 64 }, { "data": [], "layout": {} }, { "data": [], "layout": {} }];

    //     }


    // },
}