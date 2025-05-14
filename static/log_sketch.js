async function fetchAllSketchLines() {
    try {
        const response = await fetch('/api/get_all_sketch_lines');
        if (!response.ok) {
            throw new Error(`全てのスケッチの線画データの取得に失敗しました: ${response.status}`);
        }
        const lines = await response.json();
        return lines;
    } catch (error) {
        console.error('全てのスケッチの線画データの取得中にエラーが発生しました:', error);
        return [];
    }
}

function drawAllSketches(parent, allLines) {
    const canvas = document.createElement('canvas');
    canvas.width = 600;
    canvas.height = 400;
    parent.appendChild(canvas);

    const p5Instance = new p5(p => {
        p.setup = () => {
            p.createCanvas(canvas.width, canvas.height);
            p.background(230);
            p.stroke(0);
            p.strokeWeight(2);

            let previousSketchEndX = null;
            let previousSketchEndY = null;
            let previousSketchId = null; // 前のスケッチのIDを保持

            if (allLines.length > 0) {
                allLines.forEach((line, index) => {
                    p.line(line.start_x, line.start_y, line.end_x, line.end_y);

                    // 新しいスケッチの開始時に前のスケッチの終了点から線を引く
                    if (index > 0 &&
                        (line.start_x !== allLines[index - 1].end_x || line.start_y !== allLines[index - 1].end_y) &&
                        line.sketch_id !== previousSketchId) { // 修正: スケッチIDが異なる場合のみ接続
                        if (previousSketchEndX !== null && previousSketchEndY !== null) {
                            p.line(previousSketchEndX, previousSketchEndY, line.start_x, line.start_y);
                        }
                    }

                    // 現在のスケッチの最後の点を保存
                    if (line.sketch_end_x !== line.end_y && line.sketch_end_y !== line.end_x) {
                        previousSketchEndX = line.end_x;
                        previousSketchEndY = line.end_y;
                    }
                    previousSketchId = line.sketch_id; // 現在のスケッチIDを更新
                });
            }
        };
    }, parent);
}

async function displayAllSketches() {
    const sketchesContainer = document.getElementById('sketches-container');
    const allLines = await fetchAllSketchLines();

    if (allLines.length === 0) {
        sketchesContainer.textContent = '保存されたスケッチはありません。';
        return;
    }

    drawAllSketches(sketchesContainer, allLines);
}

displayAllSketches();