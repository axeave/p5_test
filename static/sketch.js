// グローバル変数
let drawing = false;
let previousX, previousY;
let currentLinesBuffer = [];
let p5Canvas;
let sketchId; // 現在のスケッチIDを保持

function setup() {
    p5Canvas = createCanvas(600, 400);
    let canvasElement = document.querySelector('canvas');
    let controlsDiv = document.getElementById('controls');
    if (controlsDiv && canvasElement) {
        controlsDiv.insertAdjacentElement('afterend', canvasElement);
    }

    background(230);
    stroke(0);
    strokeWeight(2);

    p5Canvas.mousePressed(startDrawing); // マウスが押された時の処理
    p5Canvas.mouseReleased(endDrawing);   // マウスが離された時の処理
}

async function startDrawing() {
    if (mouseX > 0 && mouseX < width && mouseY > 0 && mouseY < height) {
        drawing = true;
        previousX = mouseX;
        previousY = mouseY;

        // 新しいスケッチを作成し、sketchId を取得
        const sketchResponse = await fetch('/api/create_sketch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        });

        if (!sketchResponse.ok) {
            const errorResult = await sketchResponse.json();
            throw new Error(`スケッチの作成に失敗しました: ${errorResult.error || sketchResponse.status}`);
        }

        const sketchResult = await sketchResponse.json();
        sketchId = sketchResult.sketch_id;
        console.log('Sketch created with ID:', sketchId);
    }
}

async function endDrawing() {
    drawing = false;
    if (currentLinesBuffer.length > 0) {
        await saveSketch(); // 線が描かれていれば保存
    }
}


function mouseDragged() {
    if (drawing) {
        const currentX = mouseX;
        const currentY = mouseY;
        line(previousX, previousY, currentX, currentY);
        currentLinesBuffer.push({
            start_x: previousX,
            start_y: previousY,
            end_x: currentX,
            end_y: currentY,
        });
        previousX = currentX;
        previousY = currentY;
    }
}

async function saveSketch() {
    if (!sketchId) {
        alert('スケッチIDがありません。描画を開始してください。');
        return;
    }

    try {
        const linesResponse = await fetch('/api/save_lines', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sketch_id: sketchId, lines: currentLinesBuffer }),
        });

        if (!linesResponse.ok) {
            const errorResult = await linesResponse.json();
            throw new Error(`線の保存に失敗しました: ${errorResult.error || linesResponse.status}`);
        }

        const linesResult = await linesResponse.json();
        console.log('Lines saved:', linesResult.message);

        currentLinesBuffer = [];
        background(230);
        window.location.href = ''; 

    } catch (error) {
        console.error('スケッチの保存中にエラーが発生しました:', error);
        alert(`エラーが発生しました: ${error.message}`);
    }
}

// 以前の handleSaveSketch 関数は削除またはコメントアウト