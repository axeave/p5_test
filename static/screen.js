const socket = io('/screen');
let p5Canvas;
let allSketches = [];
let currentSketchIndex = 0;
let insertComplete = false;
let previousSketchEndX = null;
let previousSketchEndY = null;
const MAX_SKETCHES = 3;
const FADE_DURATION = 120;
let fadingSketches = [];

// インサートのための変数を追加
let currentLineIndex = 0;
let insertProgress = 0;
const insert_DURATION = 3; // インサートの長さ（フレーム数）

function setup() {
    p5Canvas = createCanvas(600, 400);
    background(230);
    stroke(0, 0, 0, 255);
    strokeWeight(2);
}

function drawLine(line, alpha, progress = 1) {
    p5Canvas.stroke(0, 0, 0, alpha);
    
    // インサートの進行に応じて線の一部を描画
    const dx = line.end_x - line.start_x;
    const dy = line.end_y - line.start_y;
    p5Canvas.line(line.start_x, line.start_y, line.start_x + dx * progress, line.start_y + dy * progress);
}

function draw() {
    p5Canvas.background(230);

    // フェードアウト中のスケッチを描画
    for (let i = fadingSketches.length - 1; i >= 0; i--) {
        const sketch = fadingSketches[i];
        const fadeProgress = (frameCount - sketch.fadeStartFrame) / FADE_DURATION;
        if (fadeProgress >= 1) {
            fadingSketches.splice(i, 1);
            continue;
        }
        const alpha = map(fadeProgress, 0, 1, 255, 0);
        sketch.lines.forEach(line => drawLine(line, alpha));

        // フェードアウト中の接続線を描画
        if (sketch.prevSketch && sketch.lines.length > 0 && sketch.prevSketch.lines.length > 0) {
            // フェードアウト開始時に固定した座標を使用
            if (sketch.fadeStartPoint && sketch.prevSketch.fadeEndPoint) {
                drawLine({ start_x: sketch.prevSketch.fadeEndPoint.x, start_y: sketch.prevSketch.fadeEndPoint.y, end_x: sketch.fadeStartPoint.x, end_y: sketch.fadeStartPoint.y }, alpha);
            }
        }
    }

    // 通常のスケッチを描画
    if (allSketches.length > 0) {
        const startSketchIndex = Math.max(0, allSketches.length - MAX_SKETCHES);
        for (let i = startSketchIndex; i < allSketches.length; i++) {
            const sketch = allSketches[i];
            const alpha = map(i, startSketchIndex, allSketches.length - 1, 100, 255);

            // インサートが完了していない場合は、現在の線までを描画
            if (i === allSketches.length - 1 && !insertComplete) {
                for (let j = 0; j < currentLineIndex; j++) {
                    drawLine(sketch.lines[j], alpha);
                }
                // 現在の線をインサート付きで描画
                if (currentLineIndex < sketch.lines.length) {
                    drawLine(sketch.lines[currentLineIndex], alpha, insertProgress);
                }
            } else {
                // インサートが完了している場合は、すべての線を描画
                sketch.lines.forEach(line => drawLine(line, alpha));
            }

            // スケッチ間の接続線を描画
            if (i > 0) {
                const prevSketch = allSketches[i - 1];
                if (sketch.lines.length > 0 && prevSketch.lines.length > 0) {
                    if (sketch.firstPoint && prevSketch.lastPoint) {
                        drawLine({ start_x: prevSketch.lastPoint.x, start_y: prevSketch.lastPoint.y, end_x: sketch.firstPoint.x, end_y: sketch.firstPoint.y }, alpha);
                    }
                }
            }
        }

        // インサートの更新
        if (!insertComplete) {
            insertProgress += 1 / insert_DURATION;
            if (insertProgress >= 1) {
                insertProgress = 0;
                currentLineIndex++;
                if (currentLineIndex >= allSketches[allSketches.length - 1].lines.length) {
                    insertComplete = true;
                    currentLineIndex = 0;
                }
            }
        }
    }
}

socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('new_sketch', (data) => {
    console.log('New sketch received:', data);
    const sketchId = data.sketch_id;
    const lines = data.lines;

    const newSketch = {
        id: sketchId,
        lines: lines,
        firstPoint: lines.length > 0 ? { x: lines[0].start_x, y: lines[0].start_y } : null,
        lastPoint: lines.length > 0 ? { x: lines[lines.length - 1].end_x, y: lines[lines.length - 1].end_y } : null,
        fadeStartPoint: null,
        fadeEndPoint: null,
    };
    allSketches.push(newSketch);

    while (allSketches.length > MAX_SKETCHES) {
        const removedSketch = allSketches.shift();
        removedSketch.fadeStartFrame = frameCount;
        if (removedSketch.lines.length > 0) {
            removedSketch.fadeStartPoint = { x: removedSketch.lastPoint.x, y: removedSketch.lastPoint.y };
        }
        if (allSketches.length > 0 && allSketches[0].lines.length > 0) {
            allSketches[0].fadeEndPoint = { x: allSketches[0].firstPoint.x, y: allSketches[0].firstPoint.y };
            removedSketch.prevSketch = allSketches[0];
        }
        fadingSketches.push(removedSketch);
    }

    // 新しいスケッチを受け取ったらインサートをリセット
    insertComplete = false;
    currentLineIndex = 0;
    insertProgress = 0;
});