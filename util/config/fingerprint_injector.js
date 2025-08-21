// IIFE to prevent polluting the global scope
(function() {
    'use strict';

    // --- Canvas Fingerprint Spoofing ---
    try {
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;

        // Add a small, random noise to the canvas image data
        const noisify = function(canvas, context) {
            const imageData = originalGetImageData.call(context, 0, 0, canvas.width, canvas.height);
            for (let i = 0; i < imageData.data.length; i += 4) {
                // Generate a random noise value (-2 to 2)
                const noise = Math.floor(Math.random() * 5) - 2;
                imageData.data[i] = imageData.data[i] + noise;
                imageData.data[i + 1] = imageData.data[i + 1] + noise;
                imageData.data[i + 2] = imageData.data[i + 2] + noise;
            }
            context.putImageData(imageData, 0, 0);
        };

        HTMLCanvasElement.prototype.toDataURL = function() {
            noisify(this, this.getContext('2d'));
            return originalToDataURL.apply(this, arguments);
        };

        CanvasRenderingContext2D.prototype.getImageData = function() {
            noisify(this.canvas, this);
            return originalGetImageData.apply(this, arguments);
        };
    } catch (e) {
        console.error('Failed to spoof Canvas fingerprint:', e);
    }

    // --- WebGL Fingerprint Spoofing ---
    try {
        const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            // Spoof Renderer and Vendor
            if (parameter === this.RENDERER) {
                return 'NVIDIA GeForce RTX 3080'; // Common high-end GPU
            }
            if (parameter === this.VENDOR) {
                return 'NVIDIA Corporation';
            }
            return originalGetParameter.apply(this, arguments);
        };

        // Also for WebGL2
        if (window.WebGL2RenderingContext) {
            const originalGetParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === this.RENDERER) {
                    return 'NVIDIA GeForce RTX 3080';
                }
                if (parameter === this.VENDOR) {
                    return 'NVIDIA Corporation';
                }
                return originalGetParameter2.apply(this, arguments);
            };
        }
    } catch (e) {
        console.error('Failed to spoof WebGL fingerprint:', e);
    }

    console.log('Advanced fingerprint injector script loaded.');

})();
