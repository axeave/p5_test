async function fetchSurroundingSketchLines(sketchId) {
    try {
        const response = await fetch(`/api/get_surrounding_sketch_lines/${sketchId}`);
        if (!response.ok) {
            throw new Error(`指定されたスケッチ周辺の線画データの取得に失敗しました: ${response.status}`);
        }
        const lines = await response.json();
        return lines;
    } catch (error) {
        console.error('指定されたスケッチ周辺の線画データの取得中にエラーが発生しました:', error);
        return [];
    }
}

function drawAnimatedSketches(parent, allLines, initialSketchId) {
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
        };

        let currentLineIndex = 0;
        let animationComplete = false;
        let previousEndX = null;
        let previousEndY = null;

        p.draw = () => {
            p.background(230); // 毎回背景を描画して残像を防ぐ

            if (!animationComplete) {
                if (currentLineIndex < allLines.length) {
                    const line = allLines[currentLineIndex];

                    // 現在の線の描画
                    p.line(line.start_x, line.start_y, line.end_x, line.end_y);

                    // スケッチ間の接続
                    if (previousEndX !== null && previousEndY !== null) {
                        // 同じスケッチ内の線は繋げないようにする条件を追加
                        if (line.sketch_id !== allLines[currentLineIndex - 1].sketch_id) {
                            p.line(previousEndX, previousEndY, line.start_x, line.start_y);
                        }
                    }

                    previousEndX = line.end_x;
                    previousEndY = line.end_y;
                    currentLineIndex++;
                } else {
                    animationComplete = true;
                }
            } else {
                // アニメーション完了後も最後の状態を維持
            }

            // アニメーションが完了していない場合でも、常に描画を行う
            if (currentLineIndex > 0) {
                for (let i = 0; i < currentLineIndex; i++) {
                    const l = allLines[i];
                    p.line(l.start_x, l.start_y, l.end_x, l.end_y);

                    if (i > 0 && l.sketch_id !== allLines[i - 1].sketch_id) {
                        p.line(allLines[i - 1].end_x, allLines[i - 1].end_y, l.start_x, l.start_y);
                    }
                }
            }
        };
    }, parent);
}

async function displaySurroundingSketches(initialSketchId) {
    const sketchesContainer = document.getElementById('sketches-container');
    const allLines = await fetchSurroundingSketchLines(initialSketchId);

    if (allLines.length === 0) {
        sketchesContainer.textContent = '指定されたスケッチ周辺のデータはありません。';
        return;
    }

    drawAnimatedSketches(sketchesContainer, allLines, initialSketchId);
}